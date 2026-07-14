/**
 * Browser-safe stub for tokenizer support.
 *
 * Selected by the ``"browser"`` conditional export in ``package.json``.
 * It exposes the same public surface as the Node build (``getEncoder``,
 * ``textCost``, ``CostFn``) but never touches ``node:module`` or the
 * ``js-tiktoken`` peer dependency, so a browser bundle can import
 * ``@soon-format/soon`` without failing at load.
 *
 * Callers that never pass a tokenizer (``getEncoder(null)`` /
 * ``getEncoder(undefined)``) get the same character-cost behaviour as the
 * Node build. Any attempt to *use* a tokenizer on the browser side raises
 * a clear ``SoonError`` naming the constraint — never a mysterious
 * bundler-resolution failure.
 */

import { SoonError } from "./errors.js";

export type CostFn = (s: string) => number;

interface Encoder {
  encode(text: string): number[];
}

/**
 * Return an encoder for ``name``, or ``null`` for character costing.
 *
 * In the browser build any non-null name raises — tokenizer support
 * requires a Node-compatible runtime with ``js-tiktoken`` installed.
 */
export function getEncoder(name: string | null | undefined): Encoder | null {
  if (name == null) return null;
  throw new SoonError(
    "tokenizer support is Node-only; browser/Deno/Workers consumers must " +
      "either avoid passing a tokenizer or run under a Node-compatible runtime " +
      "with js-tiktoken installed",
  );
}

/** Character cost. The browser build never has a real encoder to consult. */
export function textCost(text: string, _encoder: Encoder | null): number {
  return text.length;
}
