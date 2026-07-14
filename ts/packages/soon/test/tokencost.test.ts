/** TS tokenizer parity: real token cost via js-tiktoken, no network. */

import { describe, expect, it } from "vitest";

import { decode, encode, stats } from "../src/index.js";
import { getEncoder, textCost } from "../src/tokencost.js";

describe("tokenizer support (o200k_base)", () => {
  it("stats reports jsonTokens/soonTokens when tokenizer set", () => {
    const data = {
      users: Array.from({ length: 5 }, (_, i) => ({ id: i, name: `user${i}` })),
    };
    const report = stats(data, { tokenizer: "o200k_base" });
    expect(report.jsonTokens).toBeGreaterThan(0);
    expect(report.soonTokens).toBeGreaterThan(0);
    // Never-worse guarantee in the tokenizer unit.
    expect(report.soonTokens!).toBeLessThanOrEqual(report.jsonTokens!);
    // Saving must be computed from tokens, not chars.
    expect(report.saving).toBeCloseTo(1 - report.soonTokens! / report.jsonTokens!, 3);
  });

  it("stats without tokenizer stays char-based (backwards compatible)", () => {
    const report = stats({ a: 1, b: 2 });
    expect(report.jsonTokens).toBeUndefined();
    expect(report.soonTokens).toBeUndefined();
  });

  it("encode threads the tokenizer through every local decision", () => {
    // Same input that flips a decision under token cost on the Python side.
    const data = {
      items: [
        { emoji: "🌟", name: "star" },
        { emoji: "🔥", name: "fire" },
        { emoji: "✨", name: "spark" },
      ],
    };
    const charDoc = encode(data);
    const tokenDoc = encode(data, { tokenizer: "o200k_base" });
    // Round-trip both regardless of which candidate won.
    expect(decode(charDoc)).toEqual(data);
    expect(decode(tokenDoc)).toEqual(data);
  });

  it("never-worse guarantee holds in tokens", () => {
    const cases: unknown[] = [
      { a: [1, [2], { b: 3 }] },
      {},
      [],
      { x: {} },
      [{ only: "one" }],
      { k: "v" },
      { rows: Array.from({ length: 20 }, (_, i) => ({ id: i, v: i * 2 })) },
    ];
    const encoder = getEncoder("o200k_base")!;
    for (const value of cases) {
      const doc = encode(value as never, { tokenizer: "o200k_base" });
      const cj = JSON.stringify(value);
      expect(textCost(doc, encoder)).toBeLessThanOrEqual(textCost(cj, encoder));
    }
  });

  it("unknown tokenizer throws a helpful error", () => {
    expect(() => encode({ a: 1 }, { tokenizer: "not-a-real-encoding" })).toThrow(/unknown tokenizer/);
  });
});
