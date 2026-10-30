# rtl

Generated FFT RTL plus the project's own Apache-2.0 generator.

- `gen/`: stdlib-only Python generator for a streaming radix-2² single-path
  delay feedback FFT (architecture: `spec/decisions/0004-fft-architecture-survey.md`).
- `params/fft256.params`: the committed parameter file.
- `generated/`: committed generator output. **Never hand-edit it**; change a
  parameter, the generator, or a wrapper, then regenerate.
- `regen.sh`: `rtl/regen.sh [PARAMS]` rebuilds `generated/` (default
  `params/fft256.params`).
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
(one sample per clock, no frame markers or ready; wrappers are #15).
`out_valid` goes high with the first output sample and stays high. The final
reduction drops `stage_widths[-1] - output_width` LSBs, so output is scaled by
2^-(that). Tests check structure, determinism and a loose double-precision DFT
agreement in Icarus; bit-exact checking needs the model (#31).
