# 0002 — Numerics: widths, scaling, rounding, overflow

- **Status**: Proposed (depends on 0001).
- **Date**: 2026-10-17

## Decision

Restate the README draft and bind it to what the generator exposes (0001):

- Input 16-bit I + 16-bit Q two's complement; output 16-bit I + Q.
  Fallback 12-bit, stretch 18-bit (README, unchanged).
- **Scaling**: the generator has no per-stage schedule, so internal width
  grows (default 1 bit per two stages: 256-point is 8 stages, +4 bits) and
  the final stage reduces to the output width. The output reduction
  (rounding stage versus `-m` truncation) is the numerics-critical choice
  and is fixed by the reference model study in `sim/`, not here.
- **Rounding**: convergent rounding (`convround.v`) at the final reduction;
  truncation only if the study shows convergent rounding is the timing
  limiter, in which case this record is superseded, not edited.
- **Overflow**: none in the generator (README). The spec requires the
  input vector set to stay within the no-overflow range and the testbench to
  assert it; saturation is out of scope for v1.
- **Reference**: double-precision FFT. RTL must match the bit-accurate model
  in `sim/` exactly; SQNR is the model's, simulated, never "measured".

## Consequences

SQNR ≥ 60 dB at 16-bit output is a **target**, not a result: the 16-bit
output quantisation alone bounds SQNR for full-scale tones, and the value
depends on the amplitude set. The vector set is fixed in `spec/spec.md`.
