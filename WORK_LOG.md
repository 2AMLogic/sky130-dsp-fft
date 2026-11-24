# Work Log

Chronological record of merged PRs and closed issues, newest first.
Maintained by the Guide triage role.

### 2026-11-24

- **PR #178**: verification: drop the Yosys leg from smoke-fft256, check no-macro on the committed synth report
- **Issue #71** (closed): Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow

### 2026-11-23

- **PR #176**: signoff: supersede item 10 as -15, refresh gen-exact docs and T1 citations
- **Issue #170** (closed): Refresh gen-exact and T1 item-1 evidence pointers in verification/README.md and ROADMAP.md
- **PR #168**: feat: emit the model's mid-pipeline stage-width reduction in generated FFT RTL
- **Issue #162** (closed): Implement bit-exact stage-width reduction in generated FFT RTL

### 2026-11-22

- **PR #172**: verification: run the bit-exact FFT bench through klt functional-verification (RTL + negative control; gate-level request committed, report pending under #159)

### 2026-11-21

- **Issue #169** (closed): Tighten two precision claims in decision 0006 before it is ruled on
- **PR #171**: docs: correct 0006 finding 1 to the shared 17..24 schedule and nominal 2^drops factors
- **Issue #160** (closed): Write decision record 0006 (Proposed): select the FFT growth schedule from the committed sweep, with model evidence for the candidate
- **PR #164**: docs: add decision 0006 selecting the FFT growth schedule, with candidate evidence records

### 2026-11-18

- **PR #155**: ci: add merge_group trigger to rtl-ci and signoff workflows
- **Issue #154** (closed): Merge queue: add the merge_group trigger to the required-check workflow(s)

### 2026-11-17

- **PR #152**: signoff: supersede drifted item-9 -5 pair with -6 and item-10 -11 with -12
- **Issue #151** (closed): signoff: item-9 attestation envelope is drifted on main, blocking every PR
- **PR #149**: chore(loom): resync installed Loom to v0.19.1306
- **PR #137**: fix: route the smoke record's SQNR through json_safe and reject non-finite records at the shared writer
- **Issue #135** (closed): verification/test_fft256_smoke.py writes a bare Infinity literal for an exact-match SQNR, bypassing the json_safe convention
- **PR #132**: test(sim): dual drift guard names both red causes and derives the all-ceiling keys
- **Issue #127** (closed): Drift-guard dual test tells a maintainer to fix the probe when the generator is genuinely narrower
- **PR #147**: fix: attest item 9 over the cold_start chain's transitive loads (-5 pair)
- **Issue #129** (closed): T1 item 9's inventory does not hash verification/flow_tools.py, which its cold_start argv loads
- **PR #120**: ci(signoff): gate item-9 testbench attestations; supersede item9 evidence to -4 and item10 to -10
- **Issue #85** (closed): klt signoff --attest 9 is drifted and no CI gate catches it

### 2026-11-16

- **PR #142**: chore(loom): resync installed Loom to v0.19.1302
- **Issue #138** (closed): Decide how BEHIND PRs clear main's strict required-status-checks policy
- **PR #141**: verification: assert gen-unit-negctl's clean copy passes before perturbing it
- **Issue #136** (closed): verification: gen-unit-negctl should assert the clean copy passes before perturbing it
- **PR #130**: ci: gate committed generated RTL against a fresh regen
- **Issue #124** (closed): Run rtl/gen/tests/test_gen.py in CI: nothing gates committed RTL vs fresh regen

### 2026-11-15

- **PR #134**: fix: encode -inf as null in json_safe to match the evidence convention
- **Issue #128** (closed): sim/: json_safe encodes -inf as "-inf", but measurements/README.md states null for it
- **PR #126**: refactor(sim): own the evidence JSON encoding in records.json_safe
- **Issue #116** (closed): sim/: give the evidence JSON-safety helper a public home and refresh records.py's sharer list
- **PR #122**: test: guard the generator's width ceilings against the model's _WIDTH_MAX
- **Issue #113** (closed): No drift guard ties the generator's width bounds to the model's _WIDTH_MAX
- **PR #121**: fix: raise when a sweep kind mixes scalar seed with seeds
- **PR #119**: verify(smoke): append live fft256 smoke record, supersede item10 pair to -8
- **PR #114**: docs: pin item 1 signoff recipe to klayout-tools==0.9.0 and fix T1 verdict counts in manifests/README.md
- **PR #104**: verify: replace loose-tolerance generator smoke with bit-exact RTL-vs-model check in CI
- **PR #97**: feat: record simulated model SQNR for the 64/1024-point FFT sizes
- **Issue #110** (closed): Close out #94 step 5: a live `make smoke-fft256` append, unverified because yosys/abc wedges on this worker
- **Issue #108** (closed): sweep_specs(): a kind mixing scalar `seed` with `seeds` misrecords provenance without raising
- **Issue #105** (closed): klt signoff --attest 1 --check is drifted on main: the pinned klt 0.8.0 cannot re-verify the committed item 1 envelope
- **Issue #90** (closed): Retire the loose-tolerance DFT in the generator's smoke test: the bit-accurate model it waited on now exists
- **Issue #77** (closed): Record model SQNR and overflow for the 64-point fallback and 1024-point stretch sizes
- **PR #117**: docs: defer manifests README evidence-map bullet to the signoff record
- **PR #107**: refactor: collapse the four copied sim/ test runners onto unittest
- **PR #100**: fix: cap generator stage_widths at 32, the model's verified bound
- **PR #99**: refactor: derive the overflow sweep's vector kinds from VECTOR_SETS
- **PR #98**: docs: fix two documented Python invocations in rtl/ that do not run
- **Issue #112** (closed): manifests/README.md § Files says the evidence map is "deliberately empty"; it cites items 1, 9 and 10
- **Issue #115** (closed): yosys-abc pipe wedge reproduced on fleet workers: fft256 smoke frozen in abc -liberty
- **Issue #109** (closed): T1 item 9's attestation hashes drift silently: signoff.yml re-attests only item 10
- **Issue #91** (closed): test_gen.py documents a unittest discover command that does not run
- **Issue #89** (closed): Narrow the generator's stage_widths cap from 40 to 32: widths above 32 have no reference model
- **Issue #88** (closed): Derive the overflow sweep's vector kinds from VECTOR_SETS instead of restating the seeds
- **Issue #86** (closed): Collapse the three copy-pasted test runners in sim/ onto unittest, the repo's attested runner
- **PR #103**: refactor(sim): consolidate the three append-only record writers into sim/records.py
- **Issue #94** (closed): Consolidate the three copy-pasted append-only record writers; the untested one feeds committed evidence
- **PR #96**: refactor: one score_set helper for the three SQNR/overflow scoring paths
- **Issue #92** (closed): Consolidate the three copy-pasted SQNR/overflow scoring paths onto one helper
- **PR #95**: refactor(verification): single-source the negctl must-fail contract in negctl.sh
- **Issue #81** (closed): Collapse the four copy-pasted negative-control recipes in verification/Makefile into one helper
- **Issue #102** (closed): manifests/README.md 'Current verdict' says all 11 T1 items are unmet; the record says 3 are met
- **PR #75**: docs: roadmap as of 2026-11-13

### 2026-11-14

- **PR #93**: docs: make README item 10 attestation row defer to manifests/README.md
- **Issue #79** (closed): README Reproduce table names superseded item 10 attestation -3; point it at the live one
- **PR #87**: feat: survey candidate growth schedules in the fixed-point model
- **Issue #76** (closed): Sweep candidate growth schedules in the fixed-point model and record SQNR and overflow per candidate
- **PR #84**: refactor: import sim as a package instead of patching sys.path
- **Issue #80** (closed): Retire the hand-rolled sys.path bootstraps: run sim and generator entry points as modules
- **PR #83**: docs: add decision record 0005 surveying FIR sources
- **Issue #78** (closed): Survey FIR sources and write decision record 0005 (Proposed)

### 2026-11-12

- **PR #67**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-08

- **PR #63**: docs: align README, spec index and Overflow status with evidence on main
- **Issue #62** (closed): Bring README, spec/README and the spec's Overflow status in line with what main now holds
- **PR #65**: fix: point npm test at live verification targets
- **Issue #64** (closed): Fix package.json test script: it calls retired Makefile targets sim and negctl

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
