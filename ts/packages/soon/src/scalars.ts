/**
 * Scalar literal encoding/decoding (SPEC §5). Must match the Python
 * reference implementation byte for byte.
 */

import { SoonEncodeError } from "./errors.js";
import type { JsonValue } from "./types.js";

/** SPEC §5.1.5 — deterministic, language-independent number detection. */
export const NUMBER_LIKE = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/;
export const INT_TOKEN = /^-?\d+$/;
const SAFE_UNQUOTED = /^[A-Za-z0-9_.+\-@/ ]+$/;
const KEYWORDS = new Set(["null", "true", "false"]);

export function compactJson(value: unknown): string {
  const out = JSON.stringify(value, (_key, v: unknown) => {
    if (typeof v === "number" && !Number.isFinite(v)) {
      throw new SoonEncodeError("non-finite numbers are not supported");
    }
    if (typeof v === "bigint" || typeof v === "function" || typeof v === "symbol") {
      throw new SoonEncodeError(`value is not JSON-serializable: ${typeof v}`);
    }
    return v;
  });
  if (out === undefined) {
    throw new SoonEncodeError("value is not JSON-serializable: undefined");
  }
  return out;
}

export function isScalar(value: unknown): boolean {
  return (
    value === null ||
    typeof value === "boolean" ||
    typeof value === "number" ||
    typeof value === "string"
  );
}

/** SPEC §5.1 — may this string be emitted without quotes? */
export function isSafeUnquoted(s: string): boolean {
  if (!s || s === "_" || KEYWORDS.has(s)) return false;
  if (s.startsWith(" ") || s.endsWith(" ")) return false;
  if (!SAFE_UNQUOTED.test(s)) return false;
  return !NUMBER_LIKE.test(s);
}

/** Encode a scalar as a SOON literal (SPEC §5). */
export function scalarLiteral(value: JsonValue): string {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new SoonEncodeError("non-finite numbers are not supported");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return isSafeUnquoted(value) ? value : JSON.stringify(value);
  }
  throw new SoonEncodeError(`not a scalar: ${typeof value}`);
}

/** Decode a bare token (SPEC §5.2). */
export function parseLiteral(token: string): JsonValue {
  if (token === "null") return null;
  if (token === "true") return true;
  if (token === "false") return false;
  if (INT_TOKEN.test(token) || NUMBER_LIKE.test(token)) return Number(token);
  return token;
}
