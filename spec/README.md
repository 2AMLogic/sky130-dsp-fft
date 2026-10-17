# spec

- [`spec.md`](spec.md) — target specification (proposed, awaiting ratification)
- [`decisions/`](decisions/) — append-only decision records
  - [0001 generator](decisions/0001-generator.md)
  - [0002 numerics](decisions/0002-numerics.md)
  - [0003 timing and storage](decisions/0003-timing-and-storage.md)

Records are not edited after ratification; a change is a new record that
supersedes the old one.

## Regenerating the RTL

```
rtl/regen.sh
```

Prints the pinned generator commit and parameter file. It exits non-zero with
"no RTL yet" until the first generation lands.
