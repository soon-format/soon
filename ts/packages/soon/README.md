# @soon-format/soon

**SOON (Shape-Oriented Object Notation)** — lossless, token-efficient encoding
of nested JSON for LLM prompts. Declares the shape of repeated objects once,
then streams only values: ~60% smaller than compact JSON on realistic nested
payloads, with a never-worse-than-JSON guarantee.

```bash
npm install @soon-format/soon
```

```ts
import { encode, decode, stats } from "@soon-format/soon";

const data = { users: [{ id: 1, name: "Ada" }, { id: 2, name: "Linus" }] };
const doc = encode(data);
// SHAPE users = {id,name}
// users[2]<users>:
// (1,Ada)
// (2,Linus)

decode(doc); // deep-equals data
stats(data); // { jsonChars, soonChars, fallback, saving }
```

CLI: see [`@soon-format/cli`](https://www.npmjs.com/package/@soon-format/cli)
(`npx @soon-format/cli encode data.json`).

Docs, spec and the shared conformance suite:
https://github.com/soon-format/soon
