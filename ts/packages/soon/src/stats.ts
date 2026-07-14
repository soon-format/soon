/**
 * Savings report: JSON vs SOON, by characters and (optionally) tokens.
 *
 * Shares the encoder + cost computation with the auto-mode decision so a
 * single `stats()` call performs one tokenization pass per candidate
 * string, not two.
 */

import { type CostFn, encodeSoon } from "./encode.js";
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
   * Name of a bundled tokenizer (currently `"o200k_base"`). When set, the
   * report includes `jsonTokens` / `soonTokens` and `saving` is computed
   * from token counts rather than character counts.
   */
  tokenizer?: string | undefined;
}

/** Return a savings report for encoding `data` as SOON in `auto` mode. */
export function stats(data: JsonValue, options: StatsOptions = {}): Stats {
  const cj = compactJson(data);
  const encoder = getEncoder(options.tokenizer);
  const cost: CostFn = (s) => textCost(s, encoder);

  const cjCost = cost(cj);
  const soon = encodeSoon(data, cost);
  let doc: string;
  let docCost: number;
  let fallback: boolean;
  if (soon === null) {
    doc = cj;
    docCost = cjCost;
    fallback = true;
  } else {
    const soonCost = cost(soon);
    if (soonCost < cjCost) {
      doc = soon;
      docCost = soonCost;
      fallback = false;
    } else {
      doc = cj;
      docCost = cjCost;
      fallback = true;
    }
  }

  const report: Stats = {
    jsonChars: cj.length,
    soonChars: doc.length,
    fallback,
    saving: 0,
  };
  let base: number;
  let mine: number;
  if (encoder !== null) {
    report.jsonTokens = cjCost;
    report.soonTokens = docCost;
    base = cjCost;
    mine = docCost;
  } else {
    base = cj.length;
    mine = doc.length;
  }
  const saving = base ? 1 - mine / base : 0;
  report.saving = Math.round(saving * 10000) / 10000;
  return report;
}
