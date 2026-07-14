<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/soon-format/soon/main/assets/brand/social/readme-banner-dark.png">
    <img alt="soon — shape-oriented object notation" src="https://raw.githubusercontent.com/soon-format/soon/main/assets/brand/social/readme-banner-light.png" width="720">
  </picture>
</p>

# @soon-format/cli

`npx`-runnable CLI for **SOON (Shape-Oriented Object Notation)** — lossless,
token-efficient encoding of nested JSON for LLM prompts.

```bash
npx @soon-format/cli encode data.json --stats
cat data.json | npx @soon-format/cli encode -
npx @soon-format/cli decode doc.soon
npx @soon-format/cli decode doc.soon --pretty   # indented JSON
npx @soon-format/cli check data.json            # round-trip verification, exit 0/1
```

Library: [`@soon-format/soon`](https://www.npmjs.com/package/@soon-format/soon).
Docs and spec: https://github.com/soon-format/soon
