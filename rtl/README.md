# rtl

Generated FFT RTL plus the project's own Apache-2.0 generator.

- `gen/`: stdlib-only Python generator for a streaming radix-2² single-path
  delay feedback FFT (architecture: `spec/decisions/0004-fft-architecture-survey.md`).
- `params/fft256.params`: the committed parameter file.
- `generated/`: committed generator output. **Never hand-edit it**; change a
  parameter, the generator, or a wrapper, then regenerate.
- `regen.sh`: `rtl/regen.sh [PARAMS]` rebuilds `generated/` (default
  `params/fft256.params`).
- `wrapper/fft256_stream.sv`: hand-written valid/ready streaming wrapper (not generated).
- `placeholder/`: the smoke-flow placeholder module.

## Usage

```sh
rtl/regen.sh                                   # regenerate rtl/generated
python3 -m rtl.gen rtl/params/fft64.params /tmp/out   # any params file, from the repo root
python3 -m unittest rtl.gen.tests.test_gen     # tests (Icarus/Yosys steps skip if absent)
```

Output is deterministic: equal parameter files give byte-identical files. Every
emitted file starts with `// SPDX-License-Identifier: Apache-2.0`, then a line
with the sha256 of the parameter file. A test fails if `generated/` differs
from a fresh regeneration.

## Parameter file

`key=value` lines, `#` comments, lists comma-separated. Every key is required;
unknown, duplicate or invalid keys exit non-zero with a message naming the key.
This schema is the contract with the model (#31); keep key names stable.

| Key | Values | Meaning |
|---|---|---|
| `size` | power of 4, 4..1024 | FFT points (8 and 32 are rejected: no radix-2 tail stage) |
| `architecture` | `r22sdf` | only choice |
| `direction` | `forward` | inverse is not implemented |
| `input_width`, `output_width` | 4..32 | bits per I and Q; output ≤ last stage width |
| `stage_widths` | list, 2·log4(size) entries | data width after each radix-2 stage (and its twiddle multiplier); non-decreasing from `input_width` |
| `twiddle_width` | 6..24 | signed twiddle bits, 2 integer bits |
| `complex_mult` | `3mult`, `4mult` | multiplier form |
| `rounding` | `convergent`, `truncate` | final reduction (multiplier reductions are always convergent; `truncate` is floor) |
| `output_order` | `natural`, `bitrev` | `natural` adds a ping-pong reorder buffer (2·size words) |
| `pipeline` | 0, 1 | register after each butterfly and multiplier |
| `stall` | 0, 1 | `en` port gating every register |

`stage_widths` and `twiddle_width` in `params/fft256.params` are **placeholders**
until the model study (#31) selects them. The generator makes no accuracy,
overflow, area, latency or timing claim; there is no saturation, so an
undersized `stage_widths` wraps.

## Top-level interface

`fft<size>(clk, rst, [en], in_re, in_im, out_re, out_im, out_valid)`. Synchronous
active-high `rst`; frame 0 starts at the first enabled clock after reset
(one sample per clock, no frame markers or ready; `wrapper/fft256_stream.sv` adds them).
`out_valid` goes high with the first output sample and stays high. The final
reduction drops `stage_widths[-1] - output_width` LSBs, so output is scaled by
2^-(that). Tests check structure, determinism and a loose double-precision DFT
agreement in Icarus; bit-exact checking needs the model (#31).

## Streaming wrapper and netlist

`wrapper/fft256_stream.sv` (`fft256_stream`) drives the core's `en` stall port
from a valid/ready handshake: `in_ready = out_ready | ~core_valid`,
`en = in_valid & in_ready`, `out_valid = core_valid & in_valid`, with
`out_first` / `out_last` marking samples 0 / 255 of each output frame. Input
frames are delimited by sample count from reset; there is no flush, so the last
frame leaves the pipeline only while more input is accepted. The register-bus
wrapper is not here (tied to FIR coefficient load). Checks:
`make -C verification lint-wrapper fft-bench fft-bench-negctl`.

The committed gate-level netlist `netlist/fft256_stream.sky130_fd_sc_hd.v` is
the output of `klt synthesize` on `synth/fft256.synth.json` (top
`fft256_stream`, `sky130_fd_sc_hd`, liberty corner `tt_025C_1v80`, no clock
target). Regenerate it, and the report that records its hashes, with:

```sh
klt synthesize synth/fft256.synth.json --format json > synth/fft256.synth.report.json
cp synth/.klt/synthesize/<run_id>/fft256_stream_synth.v netlist/fft256_stream.sky130_fd_sc_hd.v
# freshness: cheap (hashes only) or full re-run (Yosys + PDK, about 2 minutes)
klt synthesize synth/fft256.synth.json --check synth/fft256.synth.report.json --netlist netlist/fft256_stream.sky130_fd_sc_hd.v --skip-deck
klt synthesize synth/fft256.synth.json --check synth/fft256.synth.report.json --rerun --netlist netlist/fft256_stream.sky130_fd_sc_hd.v
```

Flops only, no SRAM macros. The netlist freshness check needs a `klt` whose
`synthesize` has `--check` and `--skip-deck` (newer than the 0.8.0 pin used by
`signoff.yml`), so item 1 is re-attested locally, not in CI.
