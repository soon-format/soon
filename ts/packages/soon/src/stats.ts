/** Savings report: JSON vs SOON, by characters. */

import { encode } from "./encode.js";
import { compactJson } from "./scalars.js";
import type { JsonValue } from "./types.js";

export interface Stats {
  jsonChars: number;
  soonChars: number;
  fallback: boolean;
  saving: number;
}

/** Return a savings report for encoding `data` as SOON in `auto` mode. */
export function stats(data: JsonValue): Stats {
  const cj = compactJson(data);
  const doc = encode(data, { mode: "auto" });
  const saving = cj.length ? 1 - doc.length / cj.length : 0;
  return {
    jsonChars: cj.length,
    soonChars: doc.length,
    fallback: doc === cj,
    saving: Math.round(saving * 10000) / 10000,
  };
}
