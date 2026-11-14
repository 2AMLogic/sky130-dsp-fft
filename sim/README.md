# sim

Bit-accurate reference models and the SQNR reference.

- `vectors.py`: seeded, deterministic vector sets. `VECTOR_SETS` is the single
  place the draft-spec sets are defined (random I/Q at 50 % and 70 % of full
  scale, non-coherent tone at bin N/8 + 0.3 at 50 % and 90 %); `generate_frames`
  returns `(100, N)` integer-valued complex frames (default N=256, 16-bit).
- `reference.py`: `reference_fft` (double precision, forward, natural order,
  unscaled), `sqnr_db` (`10*log10(sum|Xref|^2 / sum|X-Xref|^2)`, one frame) and
  `set_sqnr_db` (minimum over frames; takes any candidate callable). Figures are
  simulated, never measured.
- `test_reference.py`: tests; `REF_MUTANT=swap_iq` runs them against a wrong
  reference for the negative control.

- `fixedpoint_model.py`: bit-accurate integer model of the radix-2^2 SDF FFT
  chosen in `spec/decisions/0004`. `load_params` reads the generator's
  `key=value` parameter file through the generator's own parser
  (`rtl/gen/params.py`), so there is one validator (0004 key names; the arithmetic contract the RTL
  must match is in the module docstring). Reports per-stage overflow counts
  and peak values rather than wrapping silently. CLI, from the repo root:
  `python3 -m sim.fixedpoint_model <params-file>` prints the config, the
  parameter file's sha256, the model identity and the **simulated** SQNR of
  each vector set. Widths outside the generator's ranges
  are an explicit opt-in: build a `Params` directly and pass it to
  `FixedPointFFT`; only the model's own invariants (power-of-4 size, one width
  per stage, int64 headroom) are then checked.
- `test_fixedpoint_model.py`: tests; `FXP_MUTANT=floor_ties` runs them against
  a flooring rounder for the negative control.
- `overflow_range.py`: amplitude sweep (0.50 to 1.00, step 0.01, 100 frames/step)
  for uniform random I/Q (seeds 1..20) and the non-coherent tone (N/8 + 0.3,
  seed 1), reusing `vectors.generate_swept_frames` (the generator behind
  `generate_frames`; `VECTOR_SETS` is unchanged). Reports, per kind, the largest
  fraction below the first overflowing step and the first overflowing stage
  (overflow need not be monotone in amplitude). From the repo root:
  `python3 -m sim.overflow_range rtl/params/fft256.params [--record measurements/overflow-range.json]`.
  Figures are **simulated** and on the **placeholder** schedule. Narrowing a
  `stage_widths` entry does not lower the range (the model drops one more LSB,
  same threshold); widening one raises it.
- `test_overflow_range.py`: tests incl. the widened-stage control; run by `make -C verification fxp-model`.
- `schedule_sweep.py`: candidate growth-schedule survey for the spec's "Internal
  growth and scaling" row, which is an open target (the committed `stage_widths`
  and `twiddle_width` are placeholders). Runs `fixedpoint_model` over the
  `CANDIDATES` table -- the single place the study is defined -- on all four
  `vectors.VECTOR_SETS`, reporting per candidate the per-set minimum SQNR, the
  per-set overflow component count, the sum of stage widths as a size proxy, and
  whether the generator's own parser (`rtl/gen/params.py`) accepts the schedule.
  Candidates override `stage_widths`/`twiddle_width` on the base `Params`; no
  parameter file is written, so the recorded sha256 is the **base** file's. From
  the repo root:
  `python3 -m sim.schedule_sweep rtl/params/fft256.params [--record measurements/schedule-sweep.json]`.
  Figures are **simulated**; the module **reports and selects nothing** -- choosing a
  schedule is a decision record's job. Two findings it makes visible: minimum SQNR
  is **not** monotone in the width sum (the widest candidate is the only one below
  the spec's SQNR target), and the overflow column is `0` for every candidate
  because overflow in this model is amplitude driven, not width driven (the
  mechanism `overflow_range.py` measures from the other direction).
- `test_schedule_sweep.py`: tests incl. both negative controls -- the SQNR column
  must separate schedules by more than 10 dB, and the overflow column is driven
  with full-scale frames to prove it is wired to the model's `Stats`; run by
  `make -C verification fxp-model`.

Run from a fresh clone (see `verification/README.md`):

```sh
python3 -m venv .venv && .venv/bin/pip install -r verification/requirements.txt
make -C verification sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl
```
