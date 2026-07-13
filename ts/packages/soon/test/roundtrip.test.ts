/** Property-style round-trip tests with a deterministic seeded generator. */

import { describe, expect, it } from "vitest";

import { decode, encode } from "../src/index.js";
import type { JsonValue } from "../src/types.js";

/** Mulberry32 PRNG: tiny, deterministic. */
function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CHARS = "abz09 _-.,:()[]{}\"'!?\\/\n\téü🎒";

function randomString(rnd: () => number, maxLen: number): string {
  const len = Math.floor(rnd() * maxLen);
  let out = "";
  for (let i = 0; i < len; i++) {
    out += CHARS[Math.floor(rnd() * CHARS.length)];
  }
  return out;
}

function randomValue(rnd: () => number, depth: number): JsonValue {
  const r = rnd();
  if (depth <= 0 || r < 0.45) {
    const s = rnd();
    if (s < 0.15) return null;
    if (s < 0.3) return rnd() < 0.5;
    if (s < 0.55) return Math.floor(rnd() * 2000) - 1000;
    if (s < 0.7) return Math.round((rnd() * 200 - 100) * 1000) / 1000;
    return randomString(rnd, 12);
  }
  if (r < 0.7) {
    const n = Math.floor(rnd() * 5);
    return Array.from({ length: n }, () => randomValue(rnd, depth - 1));
  }
  const n = Math.floor(rnd() * 5);
  const out: { [k: string]: JsonValue } = {};
  for (let i = 0; i < n; i++) {
    out[randomString(rnd, 8) || `k${i}`] = randomValue(rnd, depth - 1);
  }
  return out;
}

/** Shaped records: the format's sweet spot. */
function randomRecords(rnd: () => number): JsonValue {
  const n = Math.floor(rnd() * 8) + 2;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const row: { [k: string]: JsonValue } = {
      id: i,
      name: randomString(rnd, 10),
    };
    if (rnd() < 0.6) row.tags = Array.from({ length: Math.floor(rnd() * 3) }, () => randomString(rnd, 6));
    if (rnd() < 0.5) row.meta = { a: Math.floor(rnd() * 100), b: rnd() < 0.5 };
    if (rnd() < 0.4) {
      row.children = Array.from({ length: Math.floor(rnd() * 3) }, (_, j) => ({
        k: `c${j}`,
        v: Math.floor(rnd() * 10),
      }));
    }
    rows.push(row);
  }
  return { rows };
}

describe("round-trip: decode(encode(x)) equals x", () => {
  it("arbitrary JSON values (500 seeded cases)", () => {
    const rnd = prng(0x500f);
    for (let i = 0; i < 500; i++) {
      const value = randomValue(rnd, 4);
      for (const mode of ["auto", "soon"] as const) {
        expect(decode(encode(value, { mode }))).toEqual(value);
      }
    }
  });

  it("shaped records (300 seeded cases)", () => {
    const rnd = prng(42);
    for (let i = 0; i < 300; i++) {
      const value = randomRecords(rnd);
      for (const mode of ["auto", "soon"] as const) {
        expect(decode(encode(value, { mode }))).toEqual(value);
      }
    }
  });
});
