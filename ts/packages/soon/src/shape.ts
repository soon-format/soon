/** Shape model, inference (SPEC §7) and shape-expression syntax (SPEC §3). */

import { SoonDecodeError } from "./errors.js";
import { rawDecode } from "./jsonscan.js";
import { isScalar } from "./scalars.js";
import type { JsonObject, JsonValue } from "./types.js";

export const SCALAR = "scalar";
export const OBJECT = "object";
export const TABLE = "table";
export const PARRAY = "parray";
export const RAW = "raw";
const EMPTY = "empty"; // internal classification for []
const NULL = "null"; // internal classification for null

export type FieldKind =
  | typeof SCALAR
  | typeof OBJECT
  | typeof TABLE
  | typeof PARRAY
  | typeof RAW;

export interface Field {
  name: string;
  kind: FieldKind;
  optional: boolean;
  shape?: Shape;
}

export interface Shape {
  fields: Field[];
}

const FIELD_NAME = /^[A-Za-z0-9_\-]+$/;
const FIELD_NAME_AT = /[A-Za-z0-9_\-]+/y;

export function fieldNameToken(name: string): string {
  return FIELD_NAME.test(name) ? name : JSON.stringify(name);
}

/** Canonical shape expression; doubles as the structural signature. */
export function serializeShape(shape: Shape): string {
  const parts: string[] = [];
  for (const f of shape.fields) {
    let t = (f.optional ? "?" : "") + fieldNameToken(f.name);
    if (f.kind === OBJECT) t += ":" + serializeShape(f.shape as Shape);
    else if (f.kind === TABLE) t += ":[" + serializeShape(f.shape as Shape) + "]";
    else if (f.kind === PARRAY) t += ":[]";
    else if (f.kind === RAW) t += ":!";
    parts.push(t);
  }
  return "{" + parts.join(",") + "}";
}

function classify(value: JsonValue): string {
  if (value === null) return NULL;
  if (Array.isArray(value)) {
    if (value.length === 0) return EMPTY;
    if (value.every((x) => typeof x === "object" && x !== null && !Array.isArray(x))) {
      return TABLE;
    }
    if (value.every((x) => isScalar(x))) return PARRAY;
    return RAW;
  }
  if (typeof value === "object") return OBJECT;
  return SCALAR;
}

interface FieldInfo {
  count: number;
  kinds: Set<string>;
  objs: JsonObject[];
  subelems: JsonObject[];
}

/** Infer the shape of a homogeneous-ish list of objects (SPEC §7). */
export function inferShape(elements: JsonObject[]): Shape {
  const order: string[] = [];
  const infos = new Map<string, FieldInfo>();
  const n = elements.length;
  for (const el of elements) {
    for (const [k, v] of Object.entries(el)) {
      let info = infos.get(k);
      if (!info) {
        info = { count: 0, kinds: new Set(), objs: [], subelems: [] };
        infos.set(k, info);
        order.push(k);
      }
      info.count++;
      const c = classify(v);
      info.kinds.add(c);
      if (c === OBJECT) info.objs.push(v as JsonObject);
      else if (c === TABLE) info.subelems.push(...(v as JsonObject[]));
    }
  }
  const fields: Field[] = [];
  for (const k of order) {
    const info = infos.get(k) as FieldInfo;
    const kinds = new Set(info.kinds);
    kinds.delete(NULL);
    let kind: FieldKind;
    let shape: Shape | undefined;
    const only = (...allowed: string[]) => [...kinds].every((x) => allowed.includes(x));
    if (kinds.size === 0 || only(SCALAR)) {
      kind = SCALAR;
    } else if (only(OBJECT)) {
      kind = OBJECT;
      shape = inferShape(info.objs);
    } else if (kinds.has(TABLE) && only(TABLE, EMPTY)) {
      kind = TABLE;
      shape = inferShape(info.subelems);
    } else if (only(PARRAY, EMPTY)) {
      kind = PARRAY;
    } else {
      kind = RAW;
    }
    const field: Field = { name: k, kind, optional: info.count < n };
    if (shape) field.shape = shape;
    fields.push(field);
  }
  return { fields };
}

/** Recursive-descent parser for shape expressions. */
export class ShapeParser {
  private readonly s: string;
  private i = 0;

  constructor(text: string) {
    this.s = text;
  }

  parse(): Shape {
    const shape = this.shape();
    if (this.i !== this.s.length) {
      throw new SoonDecodeError(
        `trailing characters in shape expression: ${this.s.slice(this.i)}`,
      );
    }
    return shape;
  }

  private peek(): string {
    return this.s[this.i] ?? "";
  }

  private expect(ch: string): void {
    if (this.peek() !== ch) {
      throw new SoonDecodeError(`expected '${ch}' at position ${this.i} in shape expression`);
    }
    this.i++;
  }

  private shape(): Shape {
    this.expect("{");
    const fields: Field[] = [];
    if (this.peek() === "}") {
      this.i++;
      return { fields };
    }
    for (;;) {
      fields.push(this.field());
      const c = this.peek();
      this.i++;
      if (c === ",") continue;
      if (c === "}") break;
      throw new SoonDecodeError("malformed shape expression: expected ',' or '}'");
    }
    return { fields };
  }

  private field(): Field {
    let optional = false;
    if (this.peek() === "?") {
      optional = true;
      this.i++;
    }
    const name = this.name();
    let kind: FieldKind = SCALAR;
    let shape: Shape | undefined;
    if (this.peek() === ":") {
      this.i++;
      const c = this.peek();
      if (c === "{") {
        shape = this.shape();
        kind = OBJECT;
      } else if (c === "[") {
        this.i++;
        if (this.peek() === "{") {
          shape = this.shape();
          kind = TABLE;
          this.expect("]");
        } else if (this.peek() === "]") {
          this.i++;
          kind = PARRAY;
        } else {
          throw new SoonDecodeError("malformed field type in shape expression");
        }
      } else if (c === "!") {
        this.i++;
        kind = RAW;
      } else {
        throw new SoonDecodeError("malformed field type in shape expression");
      }
    }
    const field: Field = { name, kind, optional };
    if (shape) field.shape = shape;
    return field;
  }

  private name(): string {
    if (this.peek() === '"') {
      const [name, end] = rawDecode(this.s, this.i);
      if (typeof name !== "string") {
        throw new SoonDecodeError("field name must be a string");
      }
      this.i = end;
      return name;
    }
    FIELD_NAME_AT.lastIndex = this.i;
    const m = FIELD_NAME_AT.exec(this.s);
    if (!m) {
      throw new SoonDecodeError(
        `expected field name at position ${this.i} in shape expression`,
      );
    }
    this.i += m[0].length;
    return m[0];
  }
}
