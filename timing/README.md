# timing — pre-route STA evidence (issue #158)

`klt sta` (verilog mode) reports over the committed gate-level netlist
`netlist/fft256_stream.sky130_fd_sc_hd.v`. This is a first reading and a tool
probe on the **placeholder growth schedule** netlist (`stage_widths=17..24`,
`twiddle_width=16`), to be re-run when the growth-schedule decision (#160)
regenerates the netlist. It is not timing closure. Freshness of these reports
is by re-run until `klt sta` grows `--check`/`--rerun`
(klayout-tools#5841).

## Reproduce

One command, from anywhere (the script cds to the repository root; `klt sta`
resolves its scratch dir under the cwd, klayout-tools#5753):

```
./timing/run-sta.sh
```

Tool versions used for the committed reports (also recorded in
`run-sta.sh` and in each report's `provenance`):

- klayout-tools **0.9.2** (published release, via `uvx --from
  "klayout-tools==0.9.2"`). Verilog-mode `klt sta` with `pdk.corners` needs
  it — newer than the `klayout-tools==0.8.0` that `signoff.yml` pins for
  `klt signoff`; used for these reports only. The item 1/9/10 attestation
  recipes and their pins are unchanged.
- OpenROAD/OpenSTA **26Q3-1510-g6cb3f2b704** (resolved from `$PATH`).
- PDK: sky130A, open_pdks **f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7** — the
  revision `verification/toolchain.json` pins.

## Assumptions the requests carry

- `hdl_toplevel: fft256_stream` (the hand-written streaming wrapper, not the
  generated core top).
- Ideal clock, 20.0 ns (50 MHz target) on the wrapper port `clk`; no clock
  uncertainty (`clock_mode: ideal`, `clock_uncertainty.applied: false`).
- **No input/output delays set** — the 36 wrapper I/O endpoints are
  unconstrained (`constraint_completeness` in each report); every internal
  register is clocked (`unclocked_registers.count: 0`).
- Both requests omit the wire-load model and mode. The reports echo these
  omissions as `wire_load_model: null` and `wire_load_mode: null`. With no
  `set_wire_load*` override, each of the 16 `sky130_fd_sc_hd` corners uses
  its Liberty default wire-load model, `Small`, in `top` mode.
- The pre-route estimate (`geometry_source: netlist_estimate`) includes no
  extracted placement or routing parasitics.
- The netlist was synthesized with `constraints.clock_period_ns: null`
  (`synth/fft256.synth.json`) — timing-unconstrained mapping.

## Results

Every corner below has `timing_status: "constrained"`. Setup is negative at
every corner (design finding, tracked in #165; the 50 MHz target is not
changed); hold is positive at every corner.

Signoff corners (`timing/fft256.sta.report.json`):

| corner | worst setup slack | worst hold slack | fmax | setup violations |
|---|---|---|---|---|
| `ss_100C_1v60` (binding) | −427.975 ns | +0.84148 ns | 2.2323 MHz | 42543 |
| `tt_025C_1v80` | −240.615 ns | +0.40030 ns | 3.8371 MHz | 26039 |
| `ff_n40C_1v95` | −153.377 ns | +0.24158 ns | 5.7678 MHz | 26039 |

Worst setup path at the binding corner: `u_core/_311_/Q` →
`u_core/u_ro/_19572_/DE`. Hold violations: 0 at every corner.

All 16 shipped corners, reported not binding
(`timing/fft256.sta.all-corners.report.json`):

| corner | worst setup slack | worst hold slack | fmax |
|---|---|---|---|
| `tt_025C_1v80` | −240.615 ns | +0.40030 ns | 3.8371 MHz |
| `tt_100C_1v80` | −230.003 ns | +0.42305 ns | 4.0000 MHz |
| `ss_100C_1v40` | −605.762 ns | +1.20465 ns | 1.5980 MHz |
| `ss_100C_1v60` | −427.975 ns | +0.84148 ns | 2.2323 MHz |
| `ss_n40C_1v28` | −1880.740 ns | +2.04681 ns | 0.5261 MHz |
| `ss_n40C_1v35` | −1290.890 ns | +1.53684 ns | 0.7628 MHz |
| `ss_n40C_1v40` | −1047.540 ns | +1.29811 ns | 0.9367 MHz |
| `ss_n40C_1v44` | −923.332 ns | +1.15438 ns | 1.0601 MHz |
| `ss_n40C_1v60` | −584.315 ns | +0.78800 ns | 1.6548 MHz |
| `ss_n40C_1v76` | −454.454 ns | +0.60485 ns | 2.1077 MHz |
| `ff_100C_1v65` | −196.963 ns | +0.34361 ns | 4.6091 MHz |
| `ff_100C_1v95` | −148.162 ns | +0.27515 ns | 5.9466 MHz |
| `ff_n40C_1v56` | −284.446 ns | +0.35706 ns | 3.2847 MHz |
| `ff_n40C_1v65` | −237.863 ns | +0.31953 ns | 3.8780 MHz |
| `ff_n40C_1v76` | −197.516 ns | +0.28316 ns | 4.5974 MHz |
| `ff_n40C_1v95` | −153.377 ns | +0.24158 ns | 5.7678 MHz |

The spec Clock row's verification-method cell says "Yosys + OpenROAD STA";
`klt sta` drives OpenSTA (via OpenROAD), so these reports are that method
applied pre-route.
