# verification

RTL lint, cocotb simulation and a Yosys smoke synthesis, proven on a
**placeholder** module (`rtl/placeholder/placeholder_add.sv`, a registered
adder with valid/ready handshakes). The placeholder is not part of the design;
generated RTL replaces it once the generator is chosen.

## Cold start

Prerequisites (versions pinned in [`toolchain.json`](toolchain.json)):
Icarus Verilog, Verilator, Yosys, Python, `make`, and the sky130 PDK at the
pinned `ciel` revision (`ciel enable --pdk sky130 f6eeac7d...`, installed under
`$PDK_ROOT/ciel/sky130/versions/<revision>/`; default `PDK_ROOT=~/.ciel`).

```sh
python3 -m venv .venv
.venv/bin/pip install -r verification/requirements.txt
cd verification
make all      # check-tools, lint, sim, negctl, sqnr-ref, sqnr-ref-negctl, fxp-model, fxp-model-negctl, fft-bench, fft-bench-negctl
make fft-bench fft-bench-negctl   # the streaming FFT cocotb bench on its own (~30 s)
make synth    # Yosys smoke -> ../measurements/synth-placeholder.json
```

| Target | What it does |
|---|---|
| `check-tools` | fails unless installed versions equal the pins in `toolchain.json` |
| `lint` | `verilator --lint-only -Wall` on `rtl/placeholder/`; any warning fails |
| `sim` | cocotb test: 2000 random vectors with random valid/ready stalls, checked against the Python model |
| `negctl` | runs the same test on `mutants/placeholder_add_mutant.sv` (carry dropped); succeeds only if the test **fails with** `DUT output differs from Python model` (`NEGCTL_EXPECT`), so a compile error or crash does not count |
| `sqnr-ref` | `sim/test_reference.py`: seeded SQNR vector sets, double-precision reference FFT and SQNR function (pure Python + numpy; needs no simulator) |
| `fxp-model` | `sim/test_fixedpoint_model.py`: bit-accurate fixed-point FFT model (impulse, DC, tone, convergent ties, overflow reporting, determinism; pure Python + numpy) |
| `fxp-model-negctl` | same tests with a flooring rounder; succeeds only if they **fail with** `convergent tie rounding wrong` (`FXP_NEGCTL_EXPECT`) |
| `sqnr-ref-negctl` | same tests with a wrong reference (I/Q swapped); succeeds only if they **fail with** `Reference FFT differs from numpy.fft.fft` (`SQNR_NEGCTL_EXPECT`) |
| `lint-wrapper` | `verilator --lint-only -Wall` on `rtl/wrapper/fft256_stream.sv` against a port-only stub of the generated core (`stubs/fft256_stub.sv`) |
| `fft-bench` | cocotb bench `test_fft256_stream.py` on `fft256_stream` (wrapper over the generated core, Icarus): every output component bit-exact against `sim/fixedpoint_model.py` loaded from `rtl/params/fft256.params`, on the `sim/vectors.py` sets (all 100 frames of each set back to back; `FFT_BENCH_FRAMES`, default 4, per set under stalls). Also: random and long-burst `in_valid`/`out_ready` stalls, reset during the fill and mid output frame, first output after exactly 523 accepted inputs, the wrapper equations `in_ready = out_ready | ~core_valid` and `out_valid = core_valid & in_valid` on every cycle, `out_first`/`out_last` positions, one input per output after the fill (no drop or duplicate), and zero model overflow on every set. A mismatch reports the count and first differing frame/bin |
| `fft-bench-negctl` | same bench with one captured output bit flipped (`FFT_BENCH_PERTURB`, on the short `both_stalls_random` test only); succeeds only if it **fails with** `stream output differs from bit-accurate model` (`FFT_BENCH_NEGCTL_EXPECT`), writes no record |
| `synth` | Yosys maps to `sky130_fd_sc_hd` at the `tt_025C_1v80` liberty corner and writes the cell count with tool versions and PDK revision |
| `smoke-fft256` | regenerates `rtl/generated` (must equal the committed tree), runs Icarus on the generated top against `sim/fixedpoint_model.py` over the `sim/vectors.py` sets (any mismatch exits non-zero with count and first index), maps it in Yosys at `tt_025C_1v80` (fails on any non-`sky130_fd_sc_hd__` or SRAM cell), and **appends** a record to `../measurements/fft256-smoke.json`. Tool-version drift is recorded in the record, not fatal. SQNR in the record is simulated (model vs double precision) at the placeholder widths; no timing claim |
| `smoke-fft256-negctl` | same run with one DUT output bit flipped (`PERTURB`); succeeds only if it **fails with** `RTL output differs from bit-accurate model` (`SMOKE_NEGCTL_EXPECT`) and writes no record |

`synth` is manual (not in CI). The record in `measurements/` is evidence of the
flow, not a design result; do not overwrite it for a different module, add a
new record.

## CI

`.github/workflows/rtl-ci.yml` runs `fft-bench`, `fft-bench-negctl`, `lint`, `lint-wrapper`, `sim`, `negctl`, `sqnr-ref`, `sqnr-ref-negctl`, `fxp-model` and `fxp-model-negctl` on every push
and pull request. CI installs the runner's packaged Icarus and Verilator, which
may differ from the pinned versions, so it skips `check-tools`; the version pin
is enforced by `make all` and `make synth` locally.
