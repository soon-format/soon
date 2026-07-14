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
import type { JsonObject, JsonValue } from "./types.js";

const INDENT = "  ";
const KEY_TOKEN = /^[A-Za-z0-9_\-]+$/;
const NAME_SANITIZE = /[^A-Za-z0-9_]/g;

/**
 * A cost function measures a candidate encoding fragment. Defaults to
 * character length; when a tokenizer is configured (see issue #9 for TS
 * tokenizer parity) it returns real token counts. Threaded via
 * `Registry.cost` so every local decision (table vs. fallback, future
 * adaptive-block gate) agrees with the outer document-level compare in
 * `encode()`.
 */
export type CostFn = (s: string) => number;
const charCost: CostFn = (s) => s.length;

export interface EncodeOptions {
  /**
   * - `auto` (default): SOON, falling back to compact JSON whenever SOON
   *   would not be strictly smaller (never-worse guarantee, SPEC §2.1).
   * - `soon`: force the SOON encoding (root scalars still use JSON).
   * - `json`: force compact JSON.
   */
  mode?: "auto" | "soon" | "json";
}

/** Named shape declarations, deduplicated by structural signature. */
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

  register(shape: Shape, hint: string): string {
    const sig = serializeShape(shape);
    const existing = this.bySig.get(sig);
    if (existing !== undefined) return existing;
    let base = hint.replace(NAME_SANITIZE, "") || "shape";
    if (/^\d/.test(base)) base = "s" + base;
    let name = base;
    for (let i = 2; this.names.has(name); i++) name = `${base}${i}`;
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
  const cost = charCost;
  const doc = encodeSoon(data, cost);
  if (doc === null) return cj;
  if (mode === "soon") return doc;
  return cost(doc) < cost(cj) ? doc : cj;
}

function encodeSoon(data: JsonValue, cost: CostFn): string | null {
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
  const table = tryTable(value, hint, reg);
  if (table !== null) {
    const [name, rows] = table;
    return [`${pad}${kt}[${value.length}]<${name}>:`, ...rows];
  }
  return [`${pad}${kt}: !${compactJson(value)}`];
}

function tryTable(
  value: JsonValue[],
  hint: string,
  reg: Registry,
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
  const declCost = reg.has(sig) ? 0 : reg.cost(`SHAPE ${hint} = ${sig}\n`);
  // Rows are emitted joined by newlines; tokenize the joined block so token
  // costs account for BPE merges across the newline boundaries.
  const rowsCost = rows.length > 0 ? reg.cost(rows.join("\n") + "\n") : 0;
  if (declCost + rowsCost >= reg.cost(compactJson(value))) return null;
  const name = reg.register(shape, hint);
  return [name, rows];
}

function rootArray(value: JsonValue[], reg: Registry): string[] | null {
  if (value.every((x) => isScalar(x))) {
    const inline = value.map((x) => scalarLiteral(x)).join(",");
    const head = `[${value.length}]:`;
    return [inline ? `${head} ${inline}` : head];
  }
  const table = tryTable(value, "item", reg);
  if (table !== null) {
    const [name, rows] = table;
    return [`[${value.length}]<${name}>:`, ...rows];
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
