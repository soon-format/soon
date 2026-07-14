/**
 * Tokenizer support for real token-cost measurement.
 *
 * `js-tiktoken` is loaded lazily via `createRequire` — a peer dep the user
 * opts into by installing it. Encoders are cached per tokenizer name; the
 * ranks import is the expensive part (~2 MB parse) and shouldn't repeat.
 *
 * See issue #9 for the parity story with the Python side.
 */

import { createRequire } from "node:module";

import { SoonError } from "./errors.js";

export type CostFn = (s: string) => number;

interface Encoder {
  encode(text: string): number[];
}

const require_ = createRequire(import.meta.url);

// Encodings whose ranks js-tiktoken ships. Adding a new one here just requires
// that the corresponding `js-tiktoken/ranks/<name>` submodule exists.
const BUNDLED = new Set(["o200k_base", "cl100k_base", "p50k_base", "p50k_edit", "r50k_base", "gpt2"]);

const CACHE = new Map<string, Encoder>();

function loadJsTiktoken(): {
  Tiktoken: new (ranks: unknown) => Encoder;
} {
  try {
    return require_("js-tiktoken/lite") as {
      Tiktoken: new (ranks: unknown) => Encoder;
    };
  } catch (exc) {
    throw new SoonError(
      "tokenizer support requires js-tiktoken; install with: npm install js-tiktoken",
    );
  }
}

/** Return an encoder for `name`, or `null` for character costing. */
export function getEncoder(name: string | null | undefined): Encoder | null {
  if (name == null) return null;
  const cached = CACHE.get(name);
  if (cached !== undefined) return cached;
  if (!BUNDLED.has(name)) {
    throw new SoonError(
      `unknown tokenizer ${JSON.stringify(name)}; supported: ${[...BUNDLED].join(", ")}`,
    );
  }
  const { Tiktoken } = loadJsTiktoken();
  let mod: unknown;
  try {
    mod = require_(`js-tiktoken/ranks/${name}`);
  } catch (exc) {
    throw new SoonError(
      `failed to load ranks for ${name}: ${(exc as Error).message}`,
    );
  }
  // The CJS build exports the ranks object directly; the ESM build wraps it
  // as `{ default: {...} }`. Handle both to survive whichever resolution
  // path the host (Node vs. bundler vs. Vitest) picks.
  const ranks =
    mod && typeof mod === "object" && "pat_str" in mod
      ? mod
      : (mod as { default: unknown }).default;
  const encoder = new Tiktoken(ranks);
  CACHE.set(name, encoder);
  return encoder;
}

/** Character cost or, if an encoder is passed, real token count. */
export function textCost(text: string, encoder: Encoder | null): number {
  if (encoder === null) return text.length;
  return encoder.encode(text).length;
}
