#!/usr/bin/env node
/**
 * `soon` CLI.
 *
 *   npx @soon-format/cli encode data.json
 *   cat data.json | npx @soon-format/cli encode - --stats
 *   npx @soon-format/cli decode doc.soon
 *   npx @soon-format/cli stats data.json
 *   npx @soon-format/cli check data.json
 */

import { readFileSync, readSync, writeFileSync } from "node:fs";
import process from "node:process";

import { SoonError, decode, encode, stats } from "@soon-format/soon";
import type { JsonValue } from "@soon-format/soon";

const USAGE = `Usage: soon <command> [input] [options]

Commands:
  encode [file|-]   encode JSON as SOON
  decode [file|-]   decode SOON back to compact JSON
  stats  [file|-]   report SOON vs JSON size for a JSON input
  check  [file|-]   verify decode(encode(x)) == x, exit code 0/1

Options:
  -o, --output <file>   output file (default: stdout)
  --mode <auto|soon|json>   encoding mode (default: auto)
  --stats               (encode) print a savings report to stderr
  --pretty              (decode) indent JSON output
  -h, --help            show this help
  --version             show version
`;

interface Args {
  command: string;
  input: string;
  output?: string;
  mode: "auto" | "soon" | "json";
  stats: boolean;
  pretty: boolean;
}

function parseArgs(argv: string[]): Args {
  if (argv.includes("-h") || argv.includes("--help") || argv.length === 0) {
    process.stdout.write(USAGE);
    process.exit(0);
  }
  if (argv.includes("--version")) {
    process.stdout.write("@soon-format/cli 0.1.0\n");
    process.exit(0);
  }
  const [command, ...rest] = argv;
  if (!command || !["encode", "decode", "stats", "check"].includes(command)) {
    process.stderr.write(`error: unknown command ${JSON.stringify(command)}\n\n${USAGE}`);
    process.exit(2);
  }
  const args: Args = { command, input: "-", mode: "auto", stats: false, pretty: false };
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i] as string;
    if (a === "-o" || a === "--output") {
      const v = rest[++i];
      if (v === undefined) {
        process.stderr.write("error: --output requires a value\n");
        process.exit(2);
      }
      args.output = v;
    } else if (a === "--mode") {
      const m = rest[++i];
      if (m !== "auto" && m !== "soon" && m !== "json") {
        process.stderr.write(`error: invalid --mode ${JSON.stringify(m)}\n`);
        process.exit(2);
      }
      args.mode = m;
    } else if (a === "--stats") {
      args.stats = true;
    } else if (a === "--pretty") {
      args.pretty = true;
    } else if (a.startsWith("-") && a !== "-") {
      process.stderr.write(`error: unknown option ${JSON.stringify(a)}\n`);
      process.exit(2);
    } else {
      args.input = a;
    }
  }
  return args;
}

function readStdin(): string {
  // Synchronous stdin read that tolerates EAGAIN on non-blocking pipes.
  const sleeper = new Int32Array(new SharedArrayBuffer(4));
  const chunks: Buffer[] = [];
  const buf = Buffer.alloc(1 << 16);
  for (;;) {
    let n: number;
    try {
      n = readSync(0, buf, 0, buf.length, null);
    } catch (exc) {
      const code = (exc as NodeJS.ErrnoException).code;
      if (code === "EAGAIN") {
        Atomics.wait(sleeper, 0, 0, 5);
        continue;
      }
      if (code === "EOF") break;
      throw exc;
    }
    if (n === 0) break;
    chunks.push(Buffer.from(buf.subarray(0, n)));
  }
  return Buffer.concat(chunks).toString("utf-8");
}

function read(path: string): string {
  if (path === "-") return readStdin();
  return readFileSync(path, "utf-8");
}

function write(text: string, out?: string): void {
  if (out === undefined || out === "-") process.stdout.write(text + "\n");
  else writeFileSync(out, text + "\n", "utf-8");
}

function main(): number {
  const args = parseArgs(process.argv.slice(2));
  try {
    if (args.command === "encode") {
      const data = JSON.parse(read(args.input)) as JsonValue;
      write(encode(data, { mode: args.mode }), args.output);
      if (args.stats) {
        process.stderr.write(JSON.stringify(stats(data)) + "\n");
      }
    } else if (args.command === "decode") {
      const value = decode(read(args.input));
      write(args.pretty ? JSON.stringify(value, null, 2) : JSON.stringify(value), args.output);
    } else if (args.command === "stats") {
      const data = JSON.parse(read(args.input)) as JsonValue;
      process.stdout.write(JSON.stringify(stats(data), null, 2) + "\n");
    } else {
      const data = JSON.parse(read(args.input)) as JsonValue;
      for (const mode of ["auto", "soon"] as const) {
        if (JSON.stringify(decode(encode(data, { mode }))) !== JSON.stringify(data)) {
          process.stderr.write(`round-trip FAILED in mode=${mode}\n`);
          return 1;
        }
      }
      process.stderr.write("round-trip OK (auto, soon)\n");
    }
  } catch (exc) {
    if (exc instanceof SoonError || exc instanceof SyntaxError || (exc as NodeJS.ErrnoException).code) {
      process.stderr.write(`error: ${(exc as Error).message}\n`);
      return 1;
    }
    throw exc;
  }
  return 0;
}

process.exit(main());
