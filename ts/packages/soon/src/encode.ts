/** SOON encoder (SPEC §4, §7, §8). */

import { SoonEncodeError } from "./errors.js";
import { compactJson, isScalar, scalarLiteral } from "./scalars.js";
import {
  type Field,
  OBJECT,
  PARRAY,
  RAW,
  SCALAR,
  type Shape,
  TABLE,
  inferShape,
  serializeShape,
} from "./shape.js";
import { getEncoder, textCost } from "./tokencost.js";
import type { JsonObject, JsonValue } from "./types.js";

const INDENT = "  ";
const KEY_TOKEN = /^[A-Za-z0-9_\-]+$/;
const NAME_SANITIZE = /[^A-Za-z0-9_]/g;

/**
 * A cost function measures a candidate encoding fragment. Defaults to
 * character length; when `tokenizer` is passed it returns real BPE token
 * counts. Threaded via `Registry.cost` so every local decision with a real
 * alternative (table vs. inline-JSON fallback) is measured in the same
 * unit as the outer document-level compare in `encode()`.
 */
export type CostFn = (s: string) => number;

export interface EncodeOptions {
  /**
   * - `auto` (default): SOON, falling back to compact JSON whenever SOON
   *   would not be strictly smaller (never-worse guarantee, SPEC §2.1).
   * - `soon`: force the SOON encoding (root scalars still use JSON).
   * - `json`: force compact JSON.
   */
  mode?: "auto" | "soon" | "json";
  /**
   * Name of a bundled tokenizer (e.g. `"o200k_base"`) used to measure
   * candidate encodings in real tokens rather than characters. When set,
   * every local cost decision inside the encoder uses token cost too, so
   * the SOON-vs-JSON choice is made in the same unit an LLM would bill in.
   * Requires `js-tiktoken` to be installed as a peer dependency.
   */
  tokenizer?: string | undefined;
}

/**
 * Named shape declarations, deduplicated by structural signature.
 *
 * `peek` returns the name a subsequent `register` would assign without
 * committing state — so the local cost estimator in `tryTable` can
 * measure the exact string that will be emitted (including a possibly
 * collision-suffixed name) before deciding whether the table is worth
 * registering at all.
 */
class Registry {
  private readonly bySig = new Map<string, string>();
  private readonly names = new Set<string>();
  readonly decls: Array<[string, string]> = [];
  readonly cost: CostFn;

  constructor(cost: CostFn) {
    this.cost = cost;
  }

  has(sig: string): boolean {
    return this.bySig.has(sig);
  }

  private mint(hint: string): string {
    let base = hint.replace(NAME_SANITIZE, "") || "shape";
    if (/^\d/.test(base)) base = "s" + base;
    let name = base;
    for (let i = 2; this.names.has(name); i++) name = `${base}${i}`;
    return name;
  }

  peek(sig: string, hint: string): string {
    const existing = this.bySig.get(sig);
    return existing !== undefined ? existing : this.mint(hint);
  }

  register(shape: Shape, hint: string): string {
    const sig = serializeShape(shape);
    const existing = this.bySig.get(sig);
    if (existing !== undefined) return existing;
    const name = this.mint(hint);
    this.names.add(name);
    this.bySig.set(sig, name);
    this.decls.push([name, sig]);
    return name;
  }
}

/** Encode a JSON value as a SOON document. */
export function encode(data: JsonValue, options: EncodeOptions = {}): string {
  const mode = options.mode ?? "auto";
  if (mode !== "auto" && mode !== "soon" && mode !== "json") {
    throw new SoonEncodeError(`unknown mode: ${String(mode)}`);
  }
  const cj = compactJson(data);
  if (mode === "json") return cj;
  const encoder = getEncoder(options.tokenizer);
  // textCost's null branch already returns text.length, so we can hand it
  // the encoder directly without a separate charCost helper.
  const cost: CostFn = (s) => textCost(s, encoder);
  const doc = encodeSoon(data, cost);
  if (doc === null) return cj;
  if (mode === "soon") return doc;
  return cost(doc) < cost(cj) ? doc : cj;
}

/**
 * Internal helper: build the SOON body (or return null if no SOON shape
 * applies). Exported for `stats()` so it can share cost work with the
 * auto-mode decision instead of re-tokenizing. Not part of the public API.
 */
export function encodeSoon(data: JsonValue, cost: CostFn): string | null {
  const reg = new Registry(cost);
  let body: string[] | null;
  if (data !== null && typeof data === "object" && !Array.isArray(data)) {
    body = Object.keys(data).length > 0 ? entries(data, 0, reg) : null;
  } else if (Array.isArray(data)) {
    body = rootArray(data, reg);
  } else {
    body = null;
  }
  if (body === null) return null;
  const decls = reg.decls.map(([name, sig]) => `SHAPE ${name} = ${sig}`);
  return [...decls, ...body].join("\n");
}

function keyToken(key: string): string {
  return KEY_TOKEN.test(key) ? key : JSON.stringify(key);
}

function entries(obj: JsonObject, depth: number, reg: Registry): string[] {
  const pad = INDENT.repeat(depth);
  const lines: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const kt = keyToken(key);
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      if (Object.keys(value).length === 0) {
        lines.push(`${pad}${kt}: !{}`);
      } else {
        lines.push(`${pad}${kt}:`);
        lines.push(...entries(value, depth + 1, reg));
      }
    } else if (Array.isArray(value)) {
      lines.push(...arrayEntry(kt, value, key, pad, reg));
    } else {
      lines.push(`${pad}${kt}: ${scalarLiteral(value)}`);
    }
  }
  return lines;
}

function arrayEntry(
  kt: string,
  value: JsonValue[],
  hint: string,
  pad: string,
  reg: Registry,
): string[] {
  if (value.every((x) => isScalar(x))) {
    const inline = value.map((x) => scalarLiteral(x)).join(",");
    const head = `${pad}${kt}[${value.length}]:`;
    return [inline ? `${head} ${inline}` : head];
  }
  const headerPrefix = `${pad}${kt}[${value.length}]`;
  const jsonLine = `${pad}${kt}: !${compactJson(value)}`;
  const table = tryTable(value, hint, reg, headerPrefix, jsonLine);
  if (table !== null) {
    const [name, rows] = table;
    return [`${headerPrefix}<${name}>:`, ...rows];
  }
  return [jsonLine];
}

/**
 * Decide whether `value` should be emitted as a SOON table.
 *
 * `headerPrefix` is the caller-supplied string that will precede the
 * `<name>:` marker in the emitted header (e.g. `` `${pad}${kt}[N]` `` for
 * an inline array, `` `[N]` `` for a root array). `jsonLine` is the
 * concrete JSON fallback the caller would emit if this returns null.
 *
 * The cost estimate tokenizes the actual emitted SOON fragment —
 * including the header, the resolved shape name, and (when the shape is
 * new) its `SHAPE` declaration — so the local decision agrees with what
 * `encode()` will observe at the document level.
 */
function tryTable(
  value: JsonValue[],
  hint: string,
  reg: Registry,
  headerPrefix: string,
  jsonLine: string,
): [string, string[]] | null {
  if (
    value.length < 2 ||
    !value.every((x) => x !== null && typeof x === "object" && !Array.isArray(x))
  ) {
    return null;
  }
  const elements = value as JsonObject[];
  const shape = inferShape(elements);
  const sig = serializeShape(shape);
  const rows = elements.map((el) => tuple(el, shape));
  const name = reg.peek(sig, hint);
  const body = `${headerPrefix}<${name}>:\n${rows.join("\n")}`;
  const soonFragment = reg.has(sig) ? body : `SHAPE ${name} = ${sig}\n${body}`;
  if (reg.cost(soonFragment) >= reg.cost(jsonLine)) return null;
  reg.register(shape, hint);
  return [name, rows];
}

function rootArray(value: JsonValue[], reg: Registry): string[] | null {
  if (value.every((x) => isScalar(x))) {
    const inline = value.map((x) => scalarLiteral(x)).join(",");
    const head = `[${value.length}]:`;
    return [inline ? `${head} ${inline}` : head];
  }
  // At root, the JSON fallback is the whole compact JSON of the value;
  // there is no key/padding to prepend.
  const headerPrefix = `[${value.length}]`;
  const jsonLine = compactJson(value);
  const table = tryTable(value, "item", reg, headerPrefix, jsonLine);
  if (table !== null) {
    const [name, rows] = table;
    return [`${headerPrefix}<${name}>:`, ...rows];
  }
  return null;
}

function tuple(el: JsonObject, shape: Shape): string {
  const parts: string[] = [];
  for (const f of shape.fields) {
    if (!(f.name in el)) {
      parts.push("_");
    } else {
      parts.push(fieldValue(el[f.name] as JsonValue, f));
    }
  }
  return "(" + parts.join(",") + ")";
}

function fieldValue(value: JsonValue, f: Field): string {
  if (f.kind === RAW) return "!" + compactJson(value);
  if (value === null) return "null";
  if (f.kind === SCALAR) return scalarLiteral(value);
  if (f.kind === OBJECT) return tuple(value as JsonObject, f.shape as Shape);
  if (f.kind === TABLE) {
    return (
      "[" +
      (value as JsonObject[]).map((el) => tuple(el, f.shape as Shape)).join(",") +
      "]"
    );
  }
  if (f.kind === PARRAY) {
    return "[" + (value as JsonValue[]).map((x) => scalarLiteral(x)).join(",") + "]";
  }
  /* c8 ignore next */
  throw new SoonEncodeError(`unknown field kind: ${String(f.kind)}`);
}
