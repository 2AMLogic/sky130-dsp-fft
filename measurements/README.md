# measurements

Recorded results, append-only evidence. Every record names its liberty corner.

- `synth-placeholder.json`: retained history (2026-11-06): flow smoke on the retired placeholder module (not a design result). Unchanged; no longer in the live item 10 inventory.
- `fft256-smoke.json`: `{"records": [...]}`; each `make smoke-fft256` run appends one dated
  record (generator commit, parameter file and hash, model configuration, vector-set
  identity, RTL-vs-model result, simulated SQNR, Yosys cell count/area at `tt_025C_1v80`,
  tool versions and drift against the pins). Never edit or drop an earlier record.
- `overflow-range.json`: `{"records": [...]}`; each `python3 -m sim.overflow_range <params> --record measurements/overflow-range.json`
  run appends one dated record (params file and sha256, model id, seeds, step, frames, per-kind
  max no-overflow amplitude fraction and first overflowing stage). SIMULATED, on the placeholder
  schedule. Never edit or drop an earlier record.
