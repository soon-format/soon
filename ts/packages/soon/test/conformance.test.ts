/** Run the shared, language-agnostic conformance suite. */

import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { SoonDecodeError, decode, encode } from "../src/index.js";

const ROOT = fileURLToPath(new URL("../../../../conformance", import.meta.url));

interface Fixture {
  name: string;
  input: unknown;
  options?: { mode?: "auto" | "soon" | "json"; tokenizer?: string };
  expected?: unknown;
}

function fixtures(sub: string): Fixture[] {
  const dir = join(ROOT, sub);
  const files = readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
  expect(files.length).toBeGreaterThan(0);
  return files.map((f) => ({
    name: f.replace(/\.json$/, ""),
    ...(JSON.parse(readFileSync(join(dir, f), "utf-8")) as object),
  })) as Fixture[];
}

describe("conformance: encode", () => {
  for (const c of fixtures("encode")) {
    // Tokenizer-parameterized fixtures await TS tokenizer parity (#9); the
    // Python conformance suite exercises them today.
    if (c.options?.tokenizer !== undefined) {
      it.skip(`${c.name} (awaits #9: TS tokenizer support)`, () => {});
      continue;
    }
    it(c.name, () => {
      expect(encode(c.input as never, c.options)).toBe(c.expected);
    });
  }
});

describe("conformance: decode", () => {
  for (const c of fixtures("decode")) {
    it(c.name, () => {
      expect(decode(c.input as string)).toEqual(c.expected);
    });
  }
});

describe("conformance: roundtrip", () => {
  for (const c of fixtures("roundtrip")) {
    it(c.name, () => {
      for (const mode of ["auto", "soon"] as const) {
        expect(decode(encode(c.input as never, { mode }))).toEqual(c.input);
      }
    });
  }
});

describe("conformance: errors", () => {
  for (const c of fixtures("errors")) {
    it(c.name, () => {
      expect(() => decode(c.input as string)).toThrow(SoonDecodeError);
    });
  }
});
