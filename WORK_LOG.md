# Work Log

Chronological record of merged PRs and closed issues, newest first.
Maintained by the Guide triage role.

### 2026-11-07

- **PR #60**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #58**: feat(sim): report the model's no-overflow amplitude range per vector kind
- **Issue #56** (closed): Report the fixed-point model's measured no-overflow amplitude range per vector kind
- **PR #57**: refactor(verification): retire placeholder flow, lint generated fft256
- **Issue #44** (closed): Retire flow-bring-up placeholder now that generated FFT smoke exists
- **PR #54**: test: assert wrapper handshake equations in cocotb bench, retire Icarus wrapper smoke
- **Issue #52** (closed): Remove superseded Icarus wrapper smoke bench tb_fft256_stream.sv

### 2026-11-04

- **PR #51**: test: cocotb bit-exact bench for the streaming FFT wrapper, attest T1 item 9
- **Issue #21** (closed): T1 item 9 (testbenches shipped), part 2: bit-exact FFT cocotb bench, fixed-point model and attest 9 envelope
- **PR #49**: feat: add streaming wrapper, sky130 gate-level netlist and item 1 attestation for fft256
- **Issue #15** (closed): T1 item 1 (design sources): generated FFT RTL, wrappers and a sky130_fd_sc_hd gate-level netlist once the generator is ruled
- **PR #6**: docs(spec): propose target spec and generator, numerics, timing decision records
- **Issue #2** (closed): Draft and ratify the target spec

### 2026-11-01

- **PR #46**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-31

- **PR #41**: fix(package): wire check/test/lint npm scripts to verification Makefile
- **Issue #36** (closed): package.json check/test/lint scripts are always-green stubs; wire to verification Makefile

### 2026-10-30

- **PR #43**: refactor(sim): reuse the generator's parameter parser in the fixed-point model
- **Issue #39** (closed): Consolidate duplicate parameter-file parsers: sim/fixedpoint_model.py vs rtl/gen/params.py
- **Issue #27** (closed): Apache-2.0 FFT generator of our own: survey recent pipelined-FFT work, then generator + bit-accurate model
- **PR #38**: feat(verification): smoke generated fft256 vs model and map in Yosys
- **Issue #30** (closed): Smoke evidence: 256-point FFT through Icarus and Yosys sky130_fd_sc_hd (part of #27)
- **PR #34**: feat(sim): bit-accurate fixed-point radix-2^2 SDF FFT model
- **Issue #31** (closed): Bit-accurate fixed-point FFT model from generator parameters (part of #27)
- **PR #35**: feat(rtl): add radix-2^2 SDF FFT generator, params and committed RTL
- **Issue #29** (closed): Own Apache-2.0 FFT generator emitting Verilog (part of #27)
- **PR #32**: docs(spec): add 0004 FFT architecture survey choosing radix-2^2 SDF
- **Issue #28** (closed): Survey: recent pipelined-FFT work and architecture decision record (part of #27)

### 2026-10-27

- **PR #23**: feat(sim): add seeded SQNR vector sets and double-precision reference
- **Issue #16** (closed): T1 item 9 (testbenches shipped), part 1: seeded SQNR vector set and double-precision reference
- **PR #22**: feat: attest T1 item 10 with klt 0.8.0 and document reproduction
- **Issue #14** (closed): T1 item 10 (repo hygiene): README reproduction section and klt signoff --attest 10 envelope

### 2026-10-21

- **PR #12**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **PR #11**: fix(verification): require intended assertion text in negctl
- **Issue #8** (closed): Make negctl assert the mutant fails for the expected reason
- **PR #9**: ci: add T1 signoff manifest, vendored checklist and verdict-of-record check
- **Issue #3** (closed): Add the T1 signoff scaffolding: block manifest, vendored checklist and CI (item 10)
- **PR #7**: feat: add RTL lint, cocotb sim and Yosys smoke flow on a placeholder adder
- **Issue #4** (closed): Stand up the RTL lint, cocotb simulation and Yosys smoke flow on a placeholder module (T1 item 9)

### 2026-10-17

- **PR #1**: chore(loom): Install Loom 0.19.1180
