# 0003 — Timing corners and storage

- **Status**: Proposed.
- **Date**: 2026-10-17

## Decision

- The clock target (50 MHz target / 25 fallback / 100 stretch) must hold at
  **every** `sky130_fd_sc_hd` liberty corner the PDK ships. The corner list
  is read from the pinned PDK at STA time and recorded with the result. For
  reference, open_pdks `c6d73a35` (sky130A, read locally 2026-10-20) ships
  16 characterised corners, excluding the `_ccsnoise` variants:
  `tt_025C_1v80 tt_100C_1v80 ss_100C_1v40 ss_100C_1v60 ss_n40C_1v28
  ss_n40C_1v35 ss_n40C_1v40 ss_n40C_1v44 ss_n40C_1v60 ss_n40C_1v76
  ff_100C_1v65 ff_100C_1v95 ff_n40C_1v56 ff_n40C_1v65 ff_n40C_1v76
  ff_n40C_1v95`. The list at the revision `verification/toolchain.json`
  pins is re-read at STA time (not checked at that revision).
- The slowest shipped corner is **`ss_n40C_1v28`** (1.28 V, −40 °C), not
  `ss_100C_1v60`: in those liberty files `dfxtp_1` CLK→Q is 2.05 ns at
  `ss_n40C_1v28`, 0.57 ns at `ss_100C_1v60` and 0.27 ns at `tt_025C_1v80`,
  so "every corner" asks for a datapath about 7.5× faster than typical.
  `ss_100C_1v60` / `ff_n40C_1v95` / `tt_025C_1v80` are the slow / fast /
  typical **signoff** corners open_pdks configures for OpenLane
  (`libs.tech/openlane/sky130_fd_sc_hd/config.tcl`: `LIB_SLOWEST`,
  `LIB_FASTEST`, `LIB_TYPICAL`), and ORFS's `sky130hd` platform times at
  `tt_025C_1v80` only. Whether the spec's "every corner" means all 16 or the
  signoff three is an open spec call (`spec/spec.md`, open items). Setup is
  expected to bind at the slowest corner in force and hold at the fastest;
  **expectation only**: STA names the binding corner. No bare "50 MHz"
  appears in any result.
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
