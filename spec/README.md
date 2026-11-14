# spec

- [`spec.md`](spec.md) — target specification (proposed, awaiting ratification)
- [`decisions/`](decisions/) — append-only decision records
  - [0001 generator](decisions/0001-generator.md)
  - [0002 numerics](decisions/0002-numerics.md)
  - [0003 timing and storage](decisions/0003-timing-and-storage.md)
  - [0004 FFT architecture survey](decisions/0004-fft-architecture-survey.md)
  - [0005 FIR source](decisions/0005-fir-source.md)

Records are not edited after ratification; a change is a new record that
supersedes the old one.

## Regenerating the RTL

```
rtl/regen.sh
```

Regenerates `rtl/generated/` from `rtl/params/fft256.params` (or the
parameter file given as the first argument) using the project's own
generator (`python3 -m rtl.gen`). Never hand-edit `rtl/generated/`.
