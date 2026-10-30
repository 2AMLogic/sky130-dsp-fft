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
  `key=value` parameter file (0004 key names; the arithmetic contract the RTL
  must match is in the module docstring). Reports per-stage overflow counts
  and peak values rather than wrapping silently. CLI, from the repo root:
  `python3 -m sim.fixedpoint_model <params-file>` prints the config, the
  parameter file's sha256, the model identity and the **simulated** SQNR of
  each vector set. The format is assumed until the generator (#29) commits its
  own `rtl/params/*.params`; reconcile there, do not fork it.
- `test_fixedpoint_model.py`: tests; `FXP_MUTANT=floor_ties` runs them against
  a flooring rounder for the negative control.

Run from a fresh clone (see `verification/README.md`):

```sh
python3 -m venv .venv && .venv/bin/pip install -r verification/requirements.txt
make -C verification sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl
```
