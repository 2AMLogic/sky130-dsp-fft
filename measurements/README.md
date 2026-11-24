# measurements

Recorded results, append-only evidence. Every record names its liberty corner.

- `synth-placeholder.json`: retained history (2026-11-06): flow smoke on the retired placeholder module (not a design result). Unchanged; no longer in the live item 10 inventory.
- `fft256-smoke.json`: `{"records": [...]}`; each `make smoke-fft256` run appends one dated
  record (generator commit, parameter file and hash, model configuration, vector-set
  identity, RTL-vs-model result, simulated SQNR,
  tool versions and drift against the pins). An exact SQNR match is written as the
  string `"inf"` and any other non-finite value as `null`, because strict JSON cannot
  carry a non-finite number. Never edit or drop an earlier record. Schema note (issue #71): records written after the Yosys leg was removed carry no `cell_count`, `cells_by_type`, `area_um2`, `liberty_*` or `pdk_revision` fields; the 2026-10-30 record keeps them and is unchanged. Synthesis figures live in `synth/fft256.synth.report.json`.
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
- `model-sizes.json`: `{"records": [...]}`; each `python3 -m sim.model_sizes <params>... --record measurements/model-sizes.json`
  run appends one dated record **per parameter file** for the spec's FFT-size
  row, 64/1024 (model id, params file and sha256, size, `stage_widths`,
  twiddle width, frames/set, and per vector set the minimum SQNR and the
  overflow component count). SIMULATED, on the PLACEHOLDER one-bit-per-stage
  schedule each size's params file carries (following `fft256.params`); no
  accuracy claim, no schedule selected. Reading note: the 1024-point figures
  on the 16-bit placeholder land below the spec's 60 dB target row because ten
  radix-2 stages accumulate more rounding noise than eight -- a stretch size
  paired with the target width, not a verdict on 1024-point feasibility. An
  exact SQNR match is written as the string `"inf"` and any other non-finite
  value as `null`, because strict JSON cannot carry a non-finite number. Never
  edit or drop an earlier record.
- `fft256-candidate.json`: `{"records": [...]}`; the evidence record for the
  growth-schedule decision (`spec/decisions/0006-growth-schedule.md`, #160):
  the recommended row (confirm the placeholder, committed for the ruling as
  `rtl/params/fft256.candidate.params`) and the runner-up ("half bit/stage"),
  each with model SQNR/overflow and margins over the 60 dB row, the
  no-overflow amplitude range, the bit-exact RTL-vs-model check
  (`verification/test_gen_exact.py` with `GEN_EXACT_PARAMS`, clean and
  perturbed) and `klt synthesize` figures against the placeholder baseline,
  keyed by each parameter file's sha256, with reproduction commands. SIMULATED,
  never measured; reports, selects nothing. Reading notes: the runner-up's
  bit-exact check FAILED by exactly 2^drops — the generator defect #162 (no
  mid-pipeline width reduction) — and its synthesis figures are structural
  lower bounds that exclude the rounders the fix must add. Never edit or drop
  an earlier record.
