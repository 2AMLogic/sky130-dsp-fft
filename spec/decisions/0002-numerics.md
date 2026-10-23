# 0002 — Numerics: widths, scaling, rounding, overflow

- **Status**: Proposed (depends on 0001).
- **Date**: 2026-10-17

## Decision

Restate the README draft and bind it to what the generator exposes (0001):

- Input 16-bit I + 16-bit Q two's complement; output 16-bit I + Q.
  Fallback 12-bit, stretch 18-bit (README, unchanged).
- **Scaling**: the generator has no per-stage schedule, so internal width
  grows and the final stage reduces to the output width. The default growth
  is one bit at the first stage, then one bit per two stages
  (`sw/fftgen.cpp`, the `nbitsout` block, at the pinned commit): for
  256-point, 8 stages, a 16-bit input gives a **21-bit** output (+5 bits,
  not +4; `fftgen -f 256 -n 16 -1 -p 0` prints "Output samples will be 21
  bits wide"). The core's gain relative to the unscaled DFT is therefore
  2^5 / 256 = 1/8. The output reduction (a rounding stage in the wrapper
  versus a `-m` width cap) is the numerics-critical choice and is fixed by
  the reference model study in `sim/`, not here.
- **Rounding**: convergent. Between stages the generator rounds
  convergently (`convround.v`) and this is not selectable at the pinned
  commit (0001: `fftgen` hard-codes `RND_CONVERGENT`, no flag). The final
  reduction from the 21-bit core output to the 16-bit spec output is
  outside the generator — a wrapper, or a `-m` cap that also rounds
  convergently — so a truncation fallback can exist only in that wrapper,
  and only if the study shows convergent rounding is the timing limiter,
  in which case this record is superseded, not edited.
- **Overflow**: none in the generator (README). The spec requires the
  input vector set to stay within the no-overflow range and the testbench to
  assert it; saturation is out of scope for v1. Operator ruling 2026-10-20
  (PR #6): vector set 2 is uniform random I/Q at **70 %** of full scale, not
  90 %, because at 90 % the pinned core at default growth overflowed
  internally in 25 of 100 frames (review run, Icarus) and `-x 2` did not cure
  it; 70 % did not overflow. The `sim/` model must report the measured
  no-overflow amplitude range.
- **Reference**: double-precision FFT. RTL must match the bit-accurate model
  in `sim/` exactly; SQNR is the model's, simulated, never "measured".

## SQNR targets by width

Simulated (generated RTL vs. double precision, convergent reduction of the
21-bit core output, set 1, per-set minimum over 100 frames; PR #6 review
run, not a `sim/` model result): 16-bit ≈ 65.6 dB, 12-bit ≈ 41.5 dB. The
spec's cells follow: target ≥ 60 dB at 16-bit, **fallback ≥ 40 dB at 12-bit**
(was ≥ 50 dB, which the 12-bit figure contradicted; operator ruling
2026-10-20), stretch ≥ 70 dB at 18-bit. These are targets until the `sim/`
model reports them.

## Consequences

SQNR ≥ 60 dB at 16-bit output is a **target**, not a result: the 16-bit
output quantisation alone bounds SQNR for full-scale tones, and the value
depends on the amplitude set. The vector set is fixed in `spec/spec.md`.
