/**
 * Tokenizer support for real token-cost measurement.
 *
 * **Node-only.** This module uses `createRequire` to load `js-tiktoken` (an
 * optional peer dependency) synchronously — encode() and stats() are sync,
 * and the ranks module is CJS, so a static ESM `import` won't work. Browser
 * / Deno / Workers consumers should either:
 *   1. Never call `getEncoder` (all char-cost paths avoid this file's Node
 *      dependencies at runtime — but the top-level `node:module` import is
 *      resolved at load), OR
 *   2. Rely on the package's `browser` conditional export, which routes to
 *      `tokencost.browser.ts` — a stub that keeps char-cost callers working
 *      and throws a clear SoonError on any tokenizer call.
 *
 * See `package.json` `"exports"` for the routing, and issue #9 for the
 * parity story with the Python side.
 */

import { createRequire } from "node:module";

import { SoonError } from "./errors.js";

export type CostFn = (s: string) => number;

interface Encoder {
  encode(text: string): number[];
}

interface RanksModule {
  pat_str: string;
  special_tokens: Record<string, number>;
  bpe_ranks: string;
}

interface TiktokenLite {
  Tiktoken: new (ranks: RanksModule) => Encoder;
}

// Encodings whose ranks js-tiktoken ships AND that we vouch for on both
// runtimes. Keep this in sync with `python/src/soon_format/tokencost.py`'s
// `_BUNDLED`. Widening it requires proving parity in
// `tools/check_bundled_vocab.py` and bundling the vocab in the Python wheel.
const BUNDLED = new Set(["o200k_base"]);

const CACHE = new Map<string, Encoder>();

// Acquired lazily so simply *importing* this module doesn't force the
// resolution of `js-tiktoken`. If a consumer never calls getEncoder(),
// they never pay for the peer dependency.
const require_ = createRequire(import.meta.url);

function loadJsTiktoken(): TiktokenLite {
  try {
    return require_("js-tiktoken/lite") as TiktokenLite;
  } catch (exc) {
    throw new SoonError(
      "tokenizer support requires js-tiktoken; install with: npm install js-tiktoken",
      { cause: exc as Error },
    );
  }
}

function loadRanks(name: string): RanksModule {
  let mod: unknown;
  try {
    mod = require_(`js-tiktoken/ranks/${name}`);
  } catch (exc) {
    throw new SoonError(`failed to load ranks for ${name}`, {
      cause: exc as Error,
    });
  }
  // js-tiktoken's ranks submodules are CJS; depending on the host
  // (Node, bundler, Vitest transform) the module either exports the ranks
  // object directly (top-level has `pat_str`/`bpe_ranks`), wraps it as
  // `{ default: {...} }`, or both. Prefer the top-level shape when it
  // looks correct; otherwise unwrap `default`; validate the result
  // rather than trusting whatever we ended up with, so a future
  // interop shape change surfaces as a clear SoonError instead of
  // crashing deep inside js-tiktoken with "cannot read property of
  // undefined".
  const topLevel =
    mod !== null &&
    typeof mod === "object" &&
    "pat_str" in (mod as Record<string, unknown>) &&
    "bpe_ranks" in (mod as Record<string, unknown>)
      ? (mod as RanksModule)
      : undefined;
  const unwrapped =
    topLevel ??
    (mod !== null && typeof mod === "object"
      ? ((mod as { default?: unknown }).default as RanksModule | undefined)
      : undefined);
  if (
    unwrapped === undefined ||
    unwrapped === null ||
    typeof (unwrapped as RanksModule).pat_str !== "string" ||
    typeof (unwrapped as RanksModule).bpe_ranks !== "string"
  ) {
    throw new SoonError(
      `js-tiktoken ranks module for ${name} does not have the expected shape ` +
        "(missing pat_str / bpe_ranks); check the installed js-tiktoken version",
    );
  }
  return unwrapped;
}

/** Return an encoder for `name`, or `null` for character costing. */
export function getEncoder(name: string | null | undefined): Encoder | null {
  if (name == null) return null;
  const cached = CACHE.get(name);
  if (cached !== undefined) return cached;
  if (!BUNDLED.has(name)) {
    const supported = [...BUNDLED].sort().join(", ") || "(none)";
    throw new SoonError(
      `unknown tokenizer ${JSON.stringify(name)}; supported (bundled offline): ${supported}`,
    );
  }
  const { Tiktoken } = loadJsTiktoken();
  const ranks = loadRanks(name);
  const encoder = new Tiktoken(ranks);
  CACHE.set(name, encoder);
  return encoder;
}

/** Character cost or, if an encoder is passed, real token count. */
export function textCost(text: string, encoder: Encoder | null): number {
  if (encoder === null) return text.length;
  return encoder.encode(text).length;
}
