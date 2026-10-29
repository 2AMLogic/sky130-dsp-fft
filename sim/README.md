# sim

Bit-accurate reference models and the SQNR reference. The fixed-point model
lands here once the generator is chosen (#2).

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

Run from a fresh clone (see `verification/README.md`):

```sh
python3 -m venv .venv && .venv/bin/pip install -r verification/requirements.txt
make -C verification sqnr-ref sqnr-ref-negctl
```
