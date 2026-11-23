# verification

RTL lint, cocotb simulation and a Yosys smoke synthesis of the generated
256-point FFT (`rtl/generated/`) and its streaming wrapper. (The flow-bring-up
placeholder adder and its `sim`/`negctl`/`synth` targets were retired once the
generated design was covered; see `measurements/README.md`.)

## Cold start

Prerequisites (versions pinned in [`toolchain.json`](toolchain.json)):
Icarus Verilog, Verilator, Yosys, Python, `make`, and the sky130 PDK at the
pinned `ciel` revision (`ciel enable --pdk sky130 f6eeac7d...`, installed under
`$PDK_ROOT/ciel/sky130/versions/<revision>/`; default `PDK_ROOT=~/.ciel`).

```sh
python3 -m venv .venv
.venv/bin/pip install -r verification/requirements.txt
cd verification
make all      # check-tools, lint, lint-negctl, lint-wrapper, sqnr-ref, sqnr-ref-negctl, fxp-model, fxp-model-negctl, fft-bench, fft-bench-negctl, gen-exact, gen-exact-negctl, gen-unit, gen-unit-negctl
make fft-bench fft-bench-negctl   # the streaming FFT cocotb bench on its own (~30 s)
make smoke-fft256 smoke-fft256-negctl   # regen check, Icarus vs model, Yosys (appends to ../measurements/fft256-smoke.json)
```

| Target | What it does |
|---|---|
| `check-tools` | fails unless installed versions equal the pins in `toolchain.json` |
| `lint` | `verilator --lint-only -Wall --top-module fft256` on `rtl/generated/*.v`; any warning not waived fails. The only waivers are in [`lint_waivers.vlt`](lint_waivers.vlt), scoped to `rtl/generated` and each with a stated reason (`WIDTHEXPAND`, `UNUSEDSIGNAL`: generator width-extension and discarded-bit idioms) |
| `lint-negctl` | lints a copy of the generated tree under `sim_build/`: the clean copy must pass, then a seeded defect (8-bit constant into a 4-bit wire, not waived) must fail with `%Warning-WIDTHTRUNC` (`LINT_NEGCTL_EXPECT`), so a missing file or crash does not count. `rtl/generated` is never modified |
| `sqnr-ref` | `sim/test_reference.py`: seeded SQNR vector sets, double-precision reference FFT and SQNR function (pure Python + numpy; needs no simulator) |
| `fxp-model` | `sim/test_fixedpoint_model.py`: bit-accurate fixed-point FFT model (impulse, DC, tone, convergent ties, overflow reporting, determinism; pure Python + numpy) |
| `fxp-model-negctl` | same tests with a flooring rounder, run through `negctl.sh`; succeeds only if they **fail with** `convergent tie rounding wrong` (`FXP_NEGCTL_EXPECT`) |
| `sqnr-ref-negctl` | same tests with a wrong reference (I/Q swapped), run through `negctl.sh`; succeeds only if they **fail with** `Reference FFT differs from numpy.fft.fft` (`SQNR_NEGCTL_EXPECT`) |
| `lint-wrapper` | `verilator --lint-only -Wall` on `rtl/wrapper/fft256_stream.sv` against a port-only stub of the generated core (`stubs/fft256_stub.sv`) |
| `fft-bench` | cocotb bench `test_fft256_stream.py` on `fft256_stream` (wrapper over the generated core, Icarus): every output component bit-exact against `sim/fixedpoint_model.py` loaded from `rtl/params/fft256.params`, on the `sim/vectors.py` sets (all 100 frames of each set back to back; `FFT_BENCH_FRAMES`, default 4, per set under stalls). Also: random and long-burst `in_valid`/`out_ready` stalls, reset during the fill and mid output frame, first output after exactly 523 accepted inputs, the wrapper equations `in_ready = out_ready | ~core_valid` and `out_valid = core_valid & in_valid` on every cycle, `out_first`/`out_last` positions, one input per output after the fill (no drop or duplicate), and zero model overflow on every set. A mismatch reports the count and first differing frame/bin |
| `fft-bench-negctl` | same bench with one captured output bit flipped (`FFT_BENCH_PERTURB`, on the short `both_stalls_random` test only), run through `negctl.sh`; succeeds only if it **fails with** `stream output differs from bit-accurate model` (`FFT_BENCH_NEGCTL_EXPECT`), writes no record |
| `fv-reports` | `klt functional-verification` evidence for the same bench (`fv_rtl.request.json`, `fv_gatelevel.request.json`, `fv_negctl.request.json` → `reports/`): the RTL leg runs all seven tests on the wrapper + generated core; the gate-level leg runs the same tests on the committed netlist `netlist/fft256_stream.sky130_fd_sc_hd.v` with the `sky130_fd_sc_hd` Verilog cell models from the pinned PDK revision (`toolchain.json`), zero-delay (`FUNCTIONAL` define, no SDF block, so `environment.sdf` is `null`); the negative-control leg is the RTL leg with `FFT_BENCH_PERTURB=1000` (via `request.env`), asserted to fail with the mismatch text. Manual, not in CI — see [`reports/README` section](#klt-functional-verification-evidence-issue-159) |
| `gen-exact` | `test_gen_exact.py`: the generated FFT vs `sim/fixedpoint_model.py` **bit-exactly** at eight configurations — the six the generator's removed loose-tolerance smoke covered (sizes 4/16/64/256, natural/bitrev, pipeline 0/1, issue #90) plus the two equal-width growth schedules issue #162 first reported on ("0002 reference point" and "half bit/stage" from `measurements/schedule-sweep.json`), whose stage-width transitions drop a growth bit mid-pipeline. Two directed drop configurations (`run_directed`, zero growth and half bit/stage) stress the mid-pipeline reduction with near-limit and convergent-tie values, and a standalone 12-vector `fft_cmul` unit check (`run_cmul_unit`) pins the single combined rounding of twiddle fraction plus stage drop against two successive rounds. Each configuration is regenerated into a temp dir, driven in Icarus, and every captured output component is compared with `FixedPointFFT.run` for the same parameter file — no tolerance, no permutation, no rescale (the model's `run()` returns RTL stream order for both `output_order` settings). A mismatch names the configuration, frame and bin and exits non-zero. `GEN_EXACT_ROWS=<file>` replaces the built-in list with every schedule row recorded in the file's first record (the issue #162 acceptance sweep; from the repo root `GEN_EXACT_ROWS=../measurements/schedule-sweep.json make -C verification gen-exact` grades every candidate row of the first sweep record); nothing in CI sets it |
| `smoke-fft256` | regenerates `rtl/generated` (must equal the committed tree), runs Icarus on the generated top against `sim/fixedpoint_model.py` over the `sim/vectors.py` sets (any mismatch exits non-zero with count and first index), maps it in Yosys at `tt_025C_1v80` (fails on any non-`sky130_fd_sc_hd__` or SRAM cell), and **appends** a record to `../measurements/fft256-smoke.json`. Tool-version drift is recorded in the record, not fatal. SQNR in the record is simulated (model vs double precision) at the placeholder widths; no timing claim |
| `smoke-fft256-negctl` | same run with one DUT output bit flipped (`PERTURB`), run through `negctl.sh`; succeeds only if it **fails with** `RTL output differs from bit-accurate model` (`SMOKE_NEGCTL_EXPECT`) and writes no record |
| `gen-exact-negctl` | same exact check with one captured output component flipped per configuration (`GEN_EXACT_PERTURB`), run through `negctl.sh`; succeeds only if it **fails with** `generated RTL output differs from bit-accurate model` (`GEN_EXACT_NEGCTL_EXPECT`) |
| `gen-unit` | `rtl/gen/tests/test_gen.py`: the generator's unit tests — regen byte-determinism, committed `rtl/generated` vs fresh regen from `rtl/params/fft256.params`, SPDX headers, parameter variations and invalid-parameter rejection. Pure Python; the Icarus/Yosys acceptance class skips, with a reason, when a tool is absent |
| `gen-unit-negctl` | one byte appended to a copy of the whole `rtl/` tree, shadowing the committed package via `PYTHONPATH` (make runs from `verification/`, which has no `rtl/` package), run through `negctl.sh`; succeeds only if the copy's committed-vs-regen check **fails with** the byte-compare assertion text `: fft256.v` (`GEN_UNIT_NEGCTL_EXPECT`) — proving the comparison fired, not an import error or crash. `rtl/generated` is never modified |

`smoke-fft256` is manual (not in CI). Records in `measurements/` are append-only
evidence; add a new record, never overwrite one.

## klt functional-verification evidence (issue #159)

`make fv-reports` builds the three reports in `reports/`; `make fv-reports-force`
(`make -B fv-reports`) re-runs all three simulations regardless of file
timestamps (the plain targets skip a report newer than its inputs). Each report
is written to a temporary file and moved into place only after the run meets
that leg's success criterion, so a failed run leaves the previous report
untouched. **Committed today: `fv-rtl.report.json` and
`fv-negctl.report.json` only.** The gate-level report is **pending under #159**
(the ~2 h run has not been committed); the gate-level description below is the
request's design, and only the measured probe supports any gate-level claim.

- `fv-rtl.report.json` — all seven bench tests on the RTL sources, per-test
  pass/fail.
- `fv-gatelevel.report.json` (pending under #159, not yet committed) — the same tests on the committed gate-level
  netlist, zero-delay: the request defines `FUNCTIONAL` (the PDK's
  zero-delay behavioural cell models) and carries no SDF block, so the
  report's `environment.sdf` is `null` — that null is what distinguishes
  this run from the later T1 item 7 SDF-annotated re-run once a routed
  netlist exists (#17). The cell models are the `sky130_fd_sc_hd` Verilog
  files from the PDK revision pinned in `toolchain.json`, materialised under
  `sim_build/pdk-verilog/` by the target so the committed request holds only
  repo-relative paths.
- `fv-negctl.report.json` — the recorded negative control: the RTL leg with
  `FFT_BENCH_PERTURB=1000` in `request.env` (echoed as
  `environment.env`), asserted to fail with the bit-exact mismatch text.

Pinned command (klt **0.9.0**, the lowest released `klayout-tools` whose
`functional-verification` runs this bench — it needs `request.env`
(klayout-tools #4338) for the negative control's stimulus; 0.8.0, the older
repo pin, has no `request.env`):

```sh
make -C verification fv-reports-force   # regenerate all three: RTL + negative control ~1 min; gate-level ~2 h
```

The bench runs unmodified, including its one internal probe: the handshake
equations are asserted against `dut.core_valid`, an internal net of the
wrapper rather than a port. The committed netlist keeps a `core_valid` wire,
so the probe resolves on the gate-level leg and every handshake check runs
there; that the net survives is not guaranteed by synthesis, so a future
netlist may drop it — if it does, the run must say so here and in the report
rather than silently skipping the check.

The requests pin no `requires_tools` entry for iverilog: the 0.9.0
`requires_tools` probe matches against `--version` output, which iverilog
rejects, so a version pin there can never match
(2AMLogic/klayout-tools#7094); the engine version is instead recorded by
the run itself as `environment.engine_version`.

These are the T1 item 5 functional artifacts. They are **uncited** in
`manifests/sky130-dsp-fft.json` pending ratification of `spec/spec.md`: the
tiers doc makes a verdict against a draft spec provisional, so citation
waits for the spec. No test is waived on either leg; a gate-level
disagreement with the RTL run would be filed as its own issue and reported
as measured, not waived.


## CI

`.github/workflows/rtl-ci.yml` runs `fft-bench`, `fft-bench-negctl`, `gen-exact`,
`gen-exact-negctl`, `gen-unit`, `gen-unit-negctl`, `lint`, `lint-negctl`,
`lint-wrapper`, `sqnr-ref`, `sqnr-ref-negctl`, `fxp-model` and
`fxp-model-negctl` on every push
and pull request. CI installs the runner's packaged Icarus and Verilator, which
may differ from the pinned versions, so it skips `check-tools`; the version pin
is enforced by `make all` and `make smoke-fft256` locally.
