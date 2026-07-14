/** Savings report: JSON vs SOON, by characters and (optionally) tokens. */

import { encode } from "./encode.js";
import { compactJson } from "./scalars.js";
import { getEncoder, textCost } from "./tokencost.js";
import type { JsonValue } from "./types.js";

export interface Stats {
  jsonChars: number;
  soonChars: number;
  fallback: boolean;
  saving: number;
  /** Present only when `tokenizer` is passed. */
  jsonTokens?: number;
  /** Present only when `tokenizer` is passed. */
  soonTokens?: number;
}

export interface StatsOptions {
  /**
   * Name of a `js-tiktoken` encoding (e.g. `"o200k_base"`). When set, the
   * report includes `jsonTokens` / `soonTokens` and `saving` is computed
   * from token counts rather than character counts.
   */
  tokenizer?: string;
}

/** Return a savings report for encoding `data` as SOON in `auto` mode. */
export function stats(data: JsonValue, options: StatsOptions = {}): Stats {
  const cj = compactJson(data);
  const tokenizer = options.tokenizer;
  const doc =
    tokenizer !== undefined
      ? encode(data, { mode: "auto", tokenizer })
      : encode(data, { mode: "auto" });
  const encoder = getEncoder(tokenizer);
  const report: Stats = {
    jsonChars: cj.length,
    soonChars: doc.length,
    fallback: doc === cj,
    saving: 0,
  };
  let base: number;
  let mine: number;
  if (encoder !== null) {
    report.jsonTokens = textCost(cj, encoder);
    report.soonTokens = textCost(doc, encoder);
    base = report.jsonTokens;
    mine = report.soonTokens;
  } else {
    base = cj.length;
    mine = doc.length;
  }
  const saving = base ? 1 - mine / base : 0;
  report.saving = Math.round(saving * 10000) / 10000;
  return report;
}
