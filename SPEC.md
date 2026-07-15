# SOON Specification

**Shape-Oriented Object Notation** — spec version **0.1.0**

SOON is a compact, human-readable, lossless encoding of the JSON data model,
designed to minimize LLM input tokens for **nested** JSON. Its core mechanism:
declare the *shape* (keys + structure) of repeated objects once, then stream
only positional values.

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as
described in RFC 2119.

---

## 1. Data model

SOON encodes exactly the JSON data model: objects, arrays, strings, numbers,
booleans, and `null`.

- Object member order is significant for encoding output but not for value
  equality.
- Non-finite numbers (NaN, ±Infinity) MUST be rejected at encode time.
- For objects encoded via shapes, decoded member order follows shape field
  order. This is a permitted canonicalization.

## 2. Document structure

A SOON document is a sequence of `\n`-separated lines:

```
document   = *shape-decl body
shape-decl = "SHAPE " name " = " shape-expr
body       = root-object | root-array | json-fallback
```

- `name` matches `[A-Za-z_][A-Za-z0-9_]*`.
- All shape declarations appear before the body.
- Encoders MUST NOT emit blank lines. Decoders SHOULD skip blank lines between
  entries (but not inside table rows) and tolerate a trailing newline.
- **Comment lines** (v0.2) start with `#` (optionally after leading spaces) and
  MUST be ignored by decoders — including when they appear between the rows of
  a table. Encoders MUST NOT emit comment lines by default; they appear only
  when an explicit option asks for them (currently `shape_hint_rows`, which
  re-emits the relevant SHAPE declaration mid-table so the reader can
  re-anchor). A comment line MUST NOT be the whole document.

### 2.1 JSON fallback

A SOON document MAY be a single compact JSON value. Decoders MUST first
attempt to parse the entire document as JSON; on success, that value is the
result. Encoders in `auto` mode MUST fall back to compact JSON whenever the
SOON encoding would not be strictly smaller (the *never-worse guarantee*),
and MUST use the fallback for root scalars and the empty object.

## 3. Shape expressions

```
shape-expr = "{" [field ("," field)*] "}"
field      = ["?"] field-name [":" field-type]
field-type = shape-expr            ; nested object  → tuple value
           | "[" shape-expr "]"   ; table array     → list of tuples
           | "[]"                  ; primitive array → inline list
           | "!"                   ; raw             → inline JSON value
```

- A bare `field-name` denotes a **scalar** field.
- `?` marks the field **optional**: it MAY be absent from an instance.
- `field-name` is either a token matching `[A-Za-z0-9_\-]+` or a JSON string
  (double-quoted, JSON escaping) for any other name.
- No whitespace is emitted inside shape expressions.

## 4. Body forms

### 4.1 Root object

Each member is one *entry*, indented two spaces per nesting depth:

```
entry = key ": " scalar-value        ; scalar member
      | key ": !" json-value         ; raw member (compact JSON, single line)
      | key ":"                      ; nested object; children at depth+1
      | key "[" N "]:" [" " values]  ; primitive array, comma-joined
      | key "[" N "]<" name ">:"     ; table array header
```

- `key` is a token matching `[A-Za-z0-9_\-]+` or a JSON string otherwise.
- `N` is the exact element count. Decoders MUST verify it. For **table**
  arrays (i.e. `[N]<name>:`) v0.2 permits N to be omitted (`[]<name>:`)
  as an ablation for the retrieval-accuracy harness (`row_count_guardrail`
  encoder option). When N is absent, the table extends until the next
  non-row line (a row begins with `(`; blanks and comment lines are
  skipped between rows). Primitive arrays MUST always carry N — their
  values are inlined on the header line and N is the only length signal.
- After a table header, the next `N` lines are rows (§6), **without
  indentation**, regardless of the entry's depth.
- Empty objects are encoded as raw members: `key: !{}`.

### 4.2 Root array

```
"[" N "]:" [" " values]      ; primitive root array
"[" N "]<" name ">:" rows    ; table root array
```

## 5. Scalars

Scalar literal encoding, in order:

| Value | Encoding |
|---|---|
| `null`, `true`, `false` | keyword |
| integer | decimal digits |
| float | shortest JSON number representation |
| string | unquoted if *safe* (§5.1), else JSON string |

### 5.1 Safe unquoted strings

A string MAY be unquoted iff all hold:

1. Non-empty and not exactly `_`.
2. Not exactly `null`, `true`, or `false`.
3. Every character is in `[A-Za-z0-9_.+\-@/ ]` (note: includes space).
4. Does not start or end with a space.
5. Does not match the number pattern
   `[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?`.

### 5.2 Literal decoding

A bare token decodes as: keyword → keyword value; `-?\d+` → integer; number
pattern (§5.1.5) → float; otherwise → string.

## 6. Rows and tuples

Each table row is one line containing a tuple for the declared shape:

```
tuple       = "(" [field-value ("," field-value)*] ")"
field-value = "_"                        ; absent (optional fields only)
            | "null"                     ; JSON null (any field type)
            | scalar-literal             ; scalar field
            | tuple                      ; object field
            | "[" [t ("," t)*] "]"      ; table field (t = tuple)
            | "[" [s ("," s)*] "]"      ; primitive-array field (s = scalar)
            | "!" json-value             ; raw field (always "!"-prefixed)
```

- Values are joined with `,` and no spaces. Decoders SHOULD skip spaces
  before a value.
- Tuples contain exactly one value per shape field, in shape order.
- `_` MUST only appear for optional fields; decoders MUST reject it for
  required fields. Absent means the key is omitted from the decoded object.
- Raw fields always carry the `!` prefix, even for scalars and `null`
  (`!null`), so raw `null` (value present) is distinguishable from field
  omission.

### 6.1 Labeled tuples (v0.2)

Encoders MAY emit tuples with explicit field labels
(`(id=1,customer=(name=Ada,city=Boulder))`) when `mode="labeled"` is
requested. Labeled tuples exist as an accuracy-insurance variant for LLM
retrieval; per-array table-vs-fallback decisions still follow the local
cost model (§7).

Grammar:

```
labeled-tuple = "(" [labeled-field ("," labeled-field)*] ")"
labeled-field = field-name "=" field-value
```

Rules:

- The label MUST equal a `field-name` in the declared shape.
- Labels MUST NOT repeat within a tuple.
- Fields MAY appear in any order and MAY be omitted; a required field
  that is absent is a decode error.
- `_` MUST NOT appear inside a labeled tuple — omission expresses
  absence.
- Nested object, table, and primitive-array fields carry the same
  labeled/positional convention as their enclosing tuple.

Decoders MUST accept both forms. A tuple is labeled iff the first
non-whitespace token after `(` matches `field-name "="` for some field
of the declared shape; otherwise it is positional. Empty tuples `()`
are only legal in labeled form (all fields optional).

### 6.2 ELIDE — default-value elision (v0.2)

Real-world payloads often have columns dominated by one value (e.g.
`status=active` in 95% of rows). ELIDE removes such columns from the
table body, declaring their default once in the shape declaration and
emitting only the exceptions inline.

Shape-declaration grammar (extends §3):

```
shape-decl-with-defaults = shape-decl [" | defaults: " default-list]
default-list             = default ("," default)*
default                  = field-name "=" scalar-literal
```

Row-override grammar (extends §6):

```
row = tuple *(" +" field-name "=" field-value)
```

Rules:

- An elided field MUST NOT appear in the shape's field list AND MUST
  appear in the defaults clause. It MUST have been present in every
  original row (i.e. non-optional) — this preserves the "absent" vs
  "defaulted" distinction.
- Encoders MAY elide any required scalar field whose most common value
  appears in a strict majority of rows (recommended threshold ≥ 80%),
  and MUST use the cost model to confirm elision is net-positive.
- Row overrides use the same value grammar as tuple field values.
  Multiple overrides on a single row are joined by `" +"` (space,
  plus, no comma).
- Decoders MUST reject a default whose field also appears in the shape,
  and MUST reject an override for a field not in the defaults list.
- Hydration on decode: for each elided field, set to the row's override
  value if present, otherwise the default.

## 7. Shape inference (encoding)

For an array where every element is an object and length ≥ 2, encoders
SHOULD attempt table encoding:

1. Fields are the union of keys in first-appearance order.
2. A field is optional iff absent from at least one element.
3. Field type is derived from the non-null values observed:
   - all scalars → scalar
   - all objects → nested object; infer recursively over those values
   - all arrays-of-objects (non-empty) and/or empty arrays → table; infer
     recursively over the concatenated elements
   - all arrays of scalars and/or empty arrays → primitive array
   - anything mixed → raw (`!`)
4. `null` observations are compatible with every field type.

Encoders MUST compare the local cost of the table encoding (rows plus shape
declaration if new) against the compact-JSON encoding of the same array and
use table encoding only when strictly cheaper. Structurally identical shapes
MUST be declared once and reused across arrays.

Shape names SHOULD be derived from the member key (sanitized to
`[A-Za-z0-9_]+`, prefixed with `s` if starting with a digit, `shape` if
empty), with numeric suffixes on collision. Root array shapes SHOULD be
named `item`.

## 8. Determinism

Given identical input and options (including any configured tokenizer), an
encoder MUST produce byte-identical output. A single cost function measures
every local decision (shape declarations, table-vs-fallback, root array,
document-level compare); character length is the default, and a configured
tokenizer replaces it uniformly. Because BPE token counts diverge from
character counts, two encoders with the same input but different tokenizers
MAY produce different output, and this is a permitted (deterministic-per-
tokenizer) choice.

## 9. Errors

Decoders MUST reject, with an error: element-count mismatches against `[N]`,
references to undeclared shapes, `_` for required fields, malformed tuples or
shape expressions, inconsistent indentation, and trailing non-blank content.
Decoders MUST treat input as untrusted.

## 10. Conformance

An implementation is conformant when it passes every fixture in
[`conformance/`](conformance/): `encode/` (input JSON + options →
expected SOON text), `decode/` (SOON text → expected JSON value),
`roundtrip/` (decode(encode(x)) equals x in `auto` and `soon` modes), and
`errors/` (inputs that MUST raise a decode error).

## 11. Media type & extension

File extension `.soon`; provisional media type `text/soon` (UTF-8).

## 12. Versioning

The spec uses semantic versioning, independent of implementation package
versions. Additions of new mechanisms (e.g. REF, ELIDE, DICT — planned for
0.2) are minor bumps; changes to existing encoding rules are major bumps.
