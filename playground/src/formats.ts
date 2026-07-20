import { encode as soonEncode } from "@soon-format/soon";
import { encode as toonEncode } from "@toon-format/toon";
import { encodeGeneric as gcfEncode } from "@blackwell-systems/gcf";

export interface FormatResult {
  name: string;
  output: string;
  chars: number;
  error: string | null;
}

function tryEncode(
  name: string,
  fn: (data: unknown) => string,
  data: unknown,
): FormatResult {
  try {
    const output = fn(data);
    return { name, output, chars: output.length, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { name, output: "", chars: 0, error: msg };
  }
}

export function encodeAll(data: unknown): {
  json: FormatResult;
  soon: FormatResult;
  toon: FormatResult;
  gcf: FormatResult;
} {
  const jsonStr = JSON.stringify(data);
  return {
    json: { name: "JSON", output: jsonStr, chars: jsonStr.length, error: null },
    soon: tryEncode("SOON", (d) => soonEncode(d), data),
    toon: tryEncode("TOON", (d) => toonEncode(d), data),
    gcf: tryEncode("GCF", (d) => gcfEncode(d), data),
  };
}
