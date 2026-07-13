/** SOON decoder (SPEC sections 4-6 and 9). Treats all input as untrusted. */

import { SoonDecodeError } from "./errors.js";
import { rawDecode } from "./jsonscan.js";
import { parseLiteral } from "./scalars.js";
import {
  type Field,
  OBJECT,
  PARRAY,
  type Shape,
  ShapeParser,
  TABLE,
} from "./shape.js";
import type { JsonObject, JsonValue } from "./types.js";

const SHAPE_DECL = /^SHAPE ([A-Za-z_][A-Za-z0-9_]*) = (\{.*\})$/;
const ROOT_ARRAY = /^\[(\d+)\](?:<([A-Za-z_][A-Za-z0-9_]*)>)?:(.*)$/;
const ENTRY_ARRAY = /\[(\d+)\](?:<([A-Za-z_][A-Za-z0-9_]*)>)?:(.*)/y;
const KEY_TOKEN = /[A-Za-z0-9_\-]+/y;
const MISSING = Symbol("missing");

/** Decode a SOON document back to its JSON value. */
export function decode(text: string): JsonValue {
  if (typeof text !== "string") {
    throw new SoonDecodeError(`expected string, got ${typeof text}`);
  }
  // SPEC §2.1: JSON fallback documents.
  try {
    return JSON.parse(text) as JsonValue;
  } catch {
    /* not a JSON fallback document */
  }
  return new Parser(text).parse();
}

class Parser {
  private readonly lines: string[];
  private i = 0;
  private readonly shapes = new Map<string, Shape>();

  constructor(text: string) {
    this.lines = text.split("\n");
  }

  parse(): JsonValue {
    if (!this.lines.some((line) => line.trim())) {
      throw new SoonDecodeError("empty document");
    }
    while (this.i < this.lines.length) {
      const m = SHAPE_DECL.exec(this.lines[this.i] as string);
      if (!m) break;
      const name = m[1] as string;
      if (this.shapes.has(name)) {
        throw new SoonDecodeError(`duplicate shape declaration: ${name}`);
      }
      this.shapes.set(name, new ShapeParser(m[2] as string).parse());
      this.i++;
    }
    this.skipBlanks();
    if (this.i >= this.lines.length) {
      throw new SoonDecodeError("document has shape declarations but no body");
    }
    const m = ROOT_ARRAY.exec(this.lines[this.i] as string);
    let value: JsonValue;
    if (m) {
      this.i++;
      value = this.arrayValue(Number(m[1]), m[2], m[3] as string);
    } else {
      const block = this.block(0);
      if (Object.keys(block).length === 0) {
        throw new SoonDecodeError("invalid document");
      }
      value = block;
    }
    this.skipBlanks();
    if (this.i < this.lines.length) {
      throw new SoonDecodeError(`trailing content at line ${this.i + 1}`);
    }
    return value;
  }

  private skipBlanks(): void {
    while (this.i < this.lines.length && !(this.lines[this.i] as string).trim()) {
      this.i++;
    }
  }

  private block(depth: number): JsonObject {
    const out: JsonObject = {};
    while (this.i < this.lines.length) {
      const line = this.lines[this.i] as string;
      if (!line.trim()) {
        this.i++;
        continue;
      }
      const indent = line.length - line.replace(/^ +/, "").length;
      if (indent < depth * 2) break;
      if (indent !== depth * 2) {
        throw new SoonDecodeError(`bad indentation at line ${this.i + 1}`);
      }
      this.i++;
      const [key, pos] = this.key(line, indent);
      if (Object.prototype.hasOwnProperty.call(out, key)) {
        throw new SoonDecodeError(`duplicate key ${JSON.stringify(key)} at line ${this.i}`);
      }
      const c = line[pos] ?? "";
      if (c === "[") {
        ENTRY_ARRAY.lastIndex = pos;
        const m = ENTRY_ARRAY.exec(line);
        if (!m || pos + m[0].length !== line.length) {
          throw new SoonDecodeError(`malformed array entry at line ${this.i}`);
        }
        out[key] = this.arrayValue(Number(m[1]), m[2], m[3] as string);
      } else if (c === ":") {
        const rest = line.slice(pos + 1);
        if (rest === "") {
          out[key] = this.block(depth + 1);
        } else if (rest.startsWith(" ")) {
          out[key] = this.scalarEntry(rest.slice(1));
        } else {
          throw new SoonDecodeError(`malformed entry at line ${this.i}`);
        }
      } else {
        throw new SoonDecodeError(`malformed entry at line ${this.i}`);
      }
    }
    return out;
  }

  private key(line: string, pos: number): [string, number] {
    if (line[pos] === '"') {
      const [key, end] = rawDecode(line, pos);
      if (typeof key !== "string") {
        throw new SoonDecodeError(`object key must be a string at line ${this.i}`);
      }
      return [key, end];
    }
    KEY_TOKEN.lastIndex = pos;
    const m = KEY_TOKEN.exec(line);
    if (!m) {
      throw new SoonDecodeError(`expected key at line ${this.i}`);
    }
    return [m[0], pos + m[0].length];
  }

  private scalarEntry(rest: string): JsonValue {
    if (rest.startsWith("!")) {
      return fullJson(rest.slice(1), "inline JSON value");
    }
    if (rest.startsWith('"')) {
      const value = fullJson(rest, "quoted string");
      if (typeof value !== "string") {
        throw new SoonDecodeError("quoted entry value must be a string");
      }
      return value;
    }
    if (rest === "") {
      throw new SoonDecodeError("empty entry value");
    }
    return parseLiteral(rest);
  }

  private arrayValue(n: number, shapeName: string | undefined, rest: string): JsonValue[] {
    if (shapeName !== undefined) {
      if (rest.trim()) {
        throw new SoonDecodeError("unexpected content after table header");
      }
      const shape = this.shapes.get(shapeName);
      if (!shape) {
        throw new SoonDecodeError(`unknown shape: ${shapeName}`);
      }
      const rows: JsonValue[] = [];
      for (let r = 0; r < n; r++) {
        if (this.i >= this.lines.length) {
          throw new SoonDecodeError(
            `expected ${n} rows, found ${rows.length} (unexpected end of document)`,
          );
        }
        const row = this.lines[this.i] as string;
        this.i++;
        rows.push(new TupleParser(row, this.i).parseRow(shape));
      }
      return rows;
    }
    if (rest === "") {
      if (n !== 0) {
        throw new SoonDecodeError(`expected ${n} elements, found 0`);
      }
      return [];
    }
    if (!rest.startsWith(" ")) {
      throw new SoonDecodeError("malformed primitive array");
    }
    const values = new TupleParser(rest.slice(1), this.i).parseInlineList();
    if (values.length !== n) {
      throw new SoonDecodeError(`expected ${n} elements, found ${values.length}`);
    }
    return values;
  }
}

function fullJson(text: string, what: string): JsonValue {
  let value: JsonValue;
  let end: number;
  try {
    [value, end] = rawDecode(text, 0);
  } catch (exc) {
    throw new SoonDecodeError(`bad ${what}: ${(exc as Error).message}`);
  }
  if (text.slice(end).trim()) {
    throw new SoonDecodeError(`trailing characters after ${what}`);
  }
  return value;
}

/** Cursor-based parser for row tuples and inline scalar lists (SPEC §6). */
class TupleParser {
  private readonly s: string;
  private i = 0;
  private readonly lineNo: number;

  constructor(s: string, lineNo = 0) {
    this.s = s;
    this.lineNo = lineNo;
  }

  private err(msg: string): SoonDecodeError {
    return new SoonDecodeError(`line ${this.lineNo}: ${msg} (at column ${this.i + 1})`);
  }

  private peek(): string {
    return this.s[this.i] ?? "";
  }

  private expect(ch: string): void {
    if (this.peek() !== ch) {
      throw this.err(`expected '${ch}'`);
    }
    this.i++;
  }

  private skipWs(): void {
    while (this.s[this.i] === " ") this.i++;
  }

  private boundary(j: number): boolean {
    const c = this.s[j];
    return c === undefined || c === "," || c === ")" || c === "]";
  }

  parseRow(shape: Shape): JsonObject {
    const value = this.tuple(shape);
    this.skipWs();
    if (this.i !== this.s.length) {
      throw this.err("trailing characters in row");
    }
    return value;
  }

  parseInlineList(): JsonValue[] {
    const out = [this.scalarToken()];
    this.skipWs();
    while (this.i < this.s.length) {
      this.expect(",");
      out.push(this.scalarToken());
      this.skipWs();
    }
    return out;
  }

  private tuple(shape: Shape): JsonObject {
    this.skipWs();
    this.expect("(");
    const out: JsonObject = {};
    for (let idx = 0; idx < shape.fields.length; idx++) {
      if (idx) {
        this.skipWs();
        this.expect(",");
      }
      const f = shape.fields[idx] as Field;
      const value = this.fieldValue(f);
      if (value !== MISSING) {
        out[f.name] = value;
      }
    }
    this.skipWs();
    this.expect(")");
    return out;
  }

  private fieldValue(f: Field): JsonValue | typeof MISSING {
    this.skipWs();
    const c = this.peek();
    if (c === "") {
      throw this.err(`unexpected end of row in field '${f.name}'`);
    }
    if (c === "_" && this.boundary(this.i + 1)) {
      if (!f.optional) {
        throw this.err(`'_' used for required field '${f.name}'`);
      }
      this.i++;
      return MISSING;
    }
    if (c === "!") {
      this.i++;
      return this.rawJson();
    }
    if (c === "(") {
      if (f.kind !== OBJECT || !f.shape) {
        throw this.err(`unexpected tuple for field '${f.name}'`);
      }
      return this.tuple(f.shape);
    }
    if (c === "[") {
      return this.listValue(f);
    }
    return this.scalarToken();
  }

  private listValue(f: Field): JsonValue[] {
    this.expect("[");
    const out: JsonValue[] = [];
    this.skipWs();
    if (this.peek() === "]") {
      this.i++;
      return out;
    }
    for (;;) {
      if (f.kind === TABLE && f.shape) {
        out.push(this.tuple(f.shape));
      } else if (f.kind === PARRAY) {
        out.push(this.scalarToken());
      } else {
        throw this.err(`unexpected list for field '${f.name}'`);
      }
      this.skipWs();
      const c = this.peek();
      this.i++;
      if (c === ",") continue;
      if (c === "]") break;
      throw this.err("expected ',' or ']' in list");
    }
    return out;
  }

  private rawJson(): JsonValue {
    let value: JsonValue;
    let end: number;
    try {
      [value, end] = rawDecode(this.s, this.i);
    } catch (exc) {
      throw this.err(`bad inline JSON: ${(exc as Error).message}`);
    }
    this.i = end;
    return value;
  }

  private scalarToken(): JsonValue {
    this.skipWs();
    if (this.peek() === '"') {
      const value = this.rawJson();
      if (typeof value !== "string") {
        throw this.err("quoted value must be a string");
      }
      return value;
    }
    let j = this.i;
    while (j < this.s.length && !this.boundary(j)) j++;
    const token = this.s.slice(this.i, j);
    if (token === "") {
      throw this.err("empty value");
    }
    this.i = j;
    return parseLiteral(token);
  }
}
