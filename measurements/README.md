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
- `schedule-sweep.json`: `{"records": [...]}`; each `python3 -m sim.schedule_sweep <params> --record measurements/schedule-sweep.json`
  run appends one dated record surveying candidate growth schedules for the spec's
  "Internal growth and scaling" row (model id, base params file and sha256, vector sets,
  frames/set, and per candidate the `stage_widths`, `twiddle_width`, width sum, the
  generator's legality verdict, and per vector set the minimum SQNR and overflow
  component count). SIMULATED, never measured. The record **reports and selects
  nothing**: a schedule is chosen by a decision record, not here. Two reading notes:
  the sha256 names the **base** parameter file (each candidate overrides
  `stage_widths`/`twiddle_width` only, so no file holds a candidate and no candidate
  has a hash of its own), and minimum SQNR is **not** monotone in the width sum, so
  the rows must not be ranked by `width_sum`. An exact SQNR match is written as the
  string `"inf"` and any other non-finite value as `null`, because strict JSON cannot
  carry a non-finite number. Never edit or drop an earlier record.
