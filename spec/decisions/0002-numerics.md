# 0002 — Numerics: widths, scaling, rounding, overflow

- **Status**: Proposed (depends on 0001).
- **Date**: 2026-10-17

## Decision

Restate the README draft and bind it to what the generator exposes (0001):

- Input 16-bit I + 16-bit Q two's complement; output 16-bit I + Q.
  Fallback 12-bit, stretch 18-bit (README, unchanged).
- **Scaling**: a generator parameter. The generator is the project's own
  (0001, operator ruling 2026-10-29) and #27's architecture record sets the
  growth and scaling schedule. The spec keeps the targets: input and output
  widths above, SQNR below. Reference point only, from the superseded
  dblclockfft candidate (`fftgen -f 256 -n 16 -1 -p 0` at `3378b77d`): no
  per-stage schedule, 21-bit core output for a 16-bit input (+1 bit at the
  first stage, then 1 per two stages). Not a property of the chosen generator.
  The output reduction (a rounding stage versus a width cap) is the
  numerics-critical choice and is fixed by the reference model study in
  `sim/`, not here.
- **Rounding**: convergent is the target, and a generator parameter. A
  truncation fallback may exist only at the final reduction, and only if the
  study shows convergent rounding is the timing limiter, in which case this
  record is superseded, not edited.
- **Overflow**: none in the generator (README). The spec requires the
  input vector set to stay within the no-overflow range and the testbench to
  assert it; saturation is out of scope for v1. Operator ruling 2026-10-20
  (PR #6): vector set 2 is uniform random I/Q at **70 %** of full scale, not
  90 %, because at 90 % the dblclockfft core at its default growth overflowed
  internally in 25 of 100 frames (review run, Icarus, superseded candidate) and
  extra internal bits did not cure it; 70 % did not overflow. The amplitude is
  kept as ruled; the `sim/` model re-measures it for the new generator. The `sim/` model must report the measured
  no-overflow amplitude range.
- **Reference**: double-precision FFT. RTL must match the bit-accurate model
  in `sim/` exactly; SQNR is the model's, simulated, never "measured".

## SQNR targets by width

Simulated on the superseded dblclockfft candidate (generated RTL vs. double
precision, convergent reduction of its 21-bit core output, set 1, per-set minimum over 100 frames; PR #6 review
run, not a `sim/` model result; reference points for the new generator, not
its results): 16-bit ≈ 65.6 dB, 12-bit ≈ 41.5 dB. The
spec's cells follow: target ≥ 60 dB at 16-bit, **fallback ≥ 40 dB at 12-bit**
(was ≥ 50 dB, which the 12-bit figure contradicted; operator ruling
2026-10-20), stretch ≥ 70 dB at 18-bit. These are targets until the `sim/`
model reports them.

## Consequences

SQNR ≥ 60 dB at 16-bit output is a **target**, not a result: the 16-bit
output quantisation alone bounds SQNR for full-scale tones, and the value
depends on the amplitude set. The vector set is fixed in `spec/spec.md`.
