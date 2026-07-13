/**
 * SOON (Shape-Oriented Object Notation).
 *
 * Lossless, token-efficient encoding of nested JSON for LLM prompts.
 *
 * ```ts
 * import { encode, decode } from "@soon-format/soon";
 *
 * const doc = encode({ users: [{ id: 1, name: "Ada" }, { id: 2, name: "Linus" }] });
 * decode(doc); // original value
 * ```
 */

export { decode } from "./decode.js";
export { encode, type EncodeOptions } from "./encode.js";
export { SoonDecodeError, SoonEncodeError, SoonError } from "./errors.js";
export { stats, type Stats } from "./stats.js";
export type { JsonObject, JsonValue } from "./types.js";

export const VERSION = "0.1.0";
