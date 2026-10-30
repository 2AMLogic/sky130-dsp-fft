# measurements

Recorded results, append-only evidence. Every record names its liberty corner.

- `synth-placeholder.json`: flow smoke on the placeholder module (not a design result).
- `fft256-smoke.json`: `{"records": [...]}`; each `make smoke-fft256` run appends one dated
  record (generator commit, parameter file and hash, model configuration, vector-set
  identity, RTL-vs-model result, simulated SQNR, Yosys cell count/area at `tt_025C_1v80`,
  tool versions and drift against the pins). Never edit or drop an earlier record.
