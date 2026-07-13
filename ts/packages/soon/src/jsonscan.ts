/**
 * Incremental JSON scanning: parse one JSON value starting at an index,
 * returning the value and the end index (the equivalent of Python's
 * json.JSONDecoder().raw_decode).
 */

import { SoonDecodeError } from "./errors.js";
import type { JsonValue } from "./types.js";

const LITERAL = /-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|true|false|null/y;

function scanString(s: string, start: number): number {
  let j = start + 1;
  while (j < s.length) {
    const ch = s[j];
    if (ch === "\\") {
      j += 2;
      continue;
    }
    if (ch === '"') return j + 1;
    j++;
  }
  throw new SoonDecodeError(`unterminated string at index ${start}`);
}

export function rawDecode(s: string, start: number): [JsonValue, number] {
  const c = s[start];
  if (c === undefined) {
    throw new SoonDecodeError("expected a JSON value, found end of input");
  }
  let end: number;
  if (c === '"') {
    end = scanString(s, start);
  } else if (c === "{" || c === "[") {
    let depth = 0;
    let inString = false;
    let j = start;
    end = -1;
    while (j < s.length) {
      const ch = s[j];
      if (inString) {
        if (ch === "\\") j++;
        else if (ch === '"') inString = false;
      } else if (ch === '"') {
        inString = true;
      } else if (ch === "{" || ch === "[") {
        depth++;
      } else if (ch === "}" || ch === "]") {
        depth--;
        if (depth === 0) {
          end = j + 1;
          break;
        }
      }
      j++;
    }
    if (end === -1) {
      throw new SoonDecodeError(`unterminated JSON value at index ${start}`);
    }
  } else {
    LITERAL.lastIndex = start;
    const m = LITERAL.exec(s);
    if (!m) {
      throw new SoonDecodeError(`expected a JSON value at index ${start}`);
    }
    end = start + m[0].length;
  }
  let value: JsonValue;
  try {
    value = JSON.parse(s.slice(start, end)) as JsonValue;
  } catch (exc) {
    throw new SoonDecodeError(`bad JSON value: ${(exc as Error).message}`);
  }
  return [value, end];
}
