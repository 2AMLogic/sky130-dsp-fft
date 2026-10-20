# 0003 — Timing corners and storage

- **Status**: Proposed.
- **Date**: 2026-10-17

## Decision

- The clock target (50 MHz target / 25 fallback / 100 stretch) must hold at
  **every** `sky130_fd_sc_hd` liberty corner the PDK ships. The corner list
  is read from the pinned PDK at STA time and recorded with the result; it
  is not enumerated from memory here (not checked).
- Setup is expected to bind at the slowest corner (low voltage, high
  temperature: `ss_100C_1v60` is the expected name); hold at the fastest
  (`ff_n40C_1v95`). **Expectation only**: STA names the binding corner.
  No bare "50 MHz" appears in any result.
- Storage is flops for v1 (repo CLAUDE.md). Compiled SRAM is out of scope and
  would come from a sibling by pinned reference, not from here.

## Flop estimate (arithmetic, not a measurement)

256-point, 16-bit input growing to a 21-bit output (0002), ~19-bit mean
internal width, I+Q: delay lines hold about N−1 = 255 complex words
≈ 255 × 2 × 19 ≈ 9.7k flops; the bit-reversal buffer (`bitreverse.v`,
`brmem` of 2^(LGSIZE+1) words) holds 2N = 512 complex words at 21 bits
≈ 21.5k flops. Storage estimate ≈ 31k flops. This counts storage only: the
butterfly and shift-add multiplier pipelines add registers the estimate
does not include, and a first generic Yosys synthesis of the generated
core (`fftgen -f 256 -n 16 -1 -p 0` at the pinned commit, 2026-10-20) found
≈ 62k flops in ≈ 207k generic cells — roughly double the storage-only
figure. 1024-point is about 4× that. Where flops stop being reasonable is
decided from synthesized area, not from this estimate.
