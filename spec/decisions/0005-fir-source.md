# 0005 — FIR source survey and recommendation

- **Status**: Proposed. Agents do not ratify it.
- **Date**: 2026-11-14
- **Scope**: where the programmable FIR datapath comes from. It is the decision
  record `spec/spec.md:66-67` names as the gate on the four FIR rows
  (`spec.md:31-34`), and the open item 0001 deferred twice
  (`0001-generator.md:7-8`, `:112`). No FIR generator, model, RTL or
  register-bus specification is written here, and no spec row is edited.
- **Numbering**: re-checked at write time on `feature/issue-78` (branched from
  `origin/main` @ `2779bed`): `spec/decisions/` holds 0001-0004, and the only
  open PR (#75) touches `ROADMAP.md` alone (`gh pr diff 75 --name-only`), so
  0005 is the next free number. If another record lands as 0005 first,
  renumber this file, not the other.
- **Not changed**: no spec row is relaxed, and 0001-0004 are not edited
  (records are append-only). One inconsistency inside 0004 is noted in
  "Consequences and open questions" item 4 rather than corrected in place.

## Method and limits of the evidence

The survey follows 0001's method, not 0004's: each external candidate was
**cloned at a pinned commit on 2026-11-14 and read locally**, and the two
licence questions this repo requires — the licence of the *tool* and the
licence of its *output* — were answered from files in that clone, cited
`file:line`. Nothing here rests on a web-search snippet or on a project's
own licence badge.

What "checked" and "unverified" mean below:

- **Checked** means the cited file was read in the pinned clone at the stated
  line. It does not mean the candidate was built, elaborated, simulated or
  synthesised. **No candidate was built or run.**
- **Unverified** means the file was not read or the toolchain to produce the
  artefact is not installed here. Unverified cells are not relied on, and a
  candidate whose *output* licence is unverified is not adoptable on this
  evidence — that is 0001's rule (`0001:78`, where `sdf-fft`'s output licence
  was "Not checked"), applied unchanged.
- **Every quantity in this record is arithmetic from the structure or an
  estimate. None is measured, and none is simulated.** There is no FIR model
  and no FIR RTL, so there is nothing to measure yet. Area, timing and SQNR
  for the FIR are decided by `sim/`, Yosys/OpenROAD and cocotb in the
  follow-on issues, not here.

Survey limits: four external candidates, found by name and topic search of
the places this project could plausibly look (GitHub repository search,
plus the two leads 0001 left open). Generators not found that way were not
evaluated. A commercial or non-GitHub generator was not sought.

## Spec rows this choice is judged against

From `spec/spec.md` (proposed, not ratified). All four FIR rows are
`**target, no evidence**`:

| Row | Target | Fallback | Stretch | `spec.md` |
|---|---|---|---|---|
| FIR taps | 32 | 16 | 64 or decimating | `:31` |
| FIR coefficient width | 16-bit | 12-bit | 18-bit | `:32` |
| FIR coefficient load | register-bus write | same | same | `:33` |
| FIR options | none | none | symmetric, decimating | `:34` |

Three rows outside the FIR block bind the choice just as hard:

- **Streaming interface** (`:35`): valid/ready handshake, **1 sample per
  clock**, frame markers. A multicycle or folded FIR does not meet it.
- **Clock** (`:38`): 50 MHz at `ss_100C_1v60`, `tt_025C_1v80`,
  `ff_n40C_1v95`. No FIR timing evidence exists.
- **Storage** (`:40`): flops, no SRAM macros.

And two repo-level constraints:

- `CLAUDE.md`: every committed RTL file reproducible from a **pinned
  generator commit plus a committed parameter file**; hand edits to generated
  RTL not allowed; output licence must be compatible with Apache-2.0.
- `README.md:39`: "the FFT **and FIR** datapaths come out of an open
  generator from a parameter set". `README.md:58` puts "hand-redesigning the
  generator's datapath" out of scope.

## Citations

### External candidates (cloned and read 2026-11-14)

| Id | Work | Status |
|---|---|---|
| `ucb-bar/dsptools` @ `fb3b3c6523c3d807316effa1531b7f623d8d9316` (2024-04-29) | Chisel DSP library. FIR at `src/main/scala/examples/TransposedStreamingFIR.scala` | **Checked** (clone read). Tool licence Apache-2.0: `LICENSE:1-5`, `README.md:190`; file header `TransposedStreamingFIR.scala:1` carries `SPDX-License-Identifier: Apache-2.0`. **Output licence unverified** — see below. Default-branch head is the *same commit* 0001 read (`0001:41`), so the repository has not moved since 2024-04-29. Verification quality, **checked**: of the two FIR classes only the **fixed**-tap one has a self-checking test (`src/test/scala/examples/TransposedStreamFIRSpec.scala:14-46`, with `expect` against a recomputed answer); the **programmable**-tap one is exercised by `TransposedStreamingTester` (`:49-55`), which pokes inputs and `println`s outputs with **no `expect` at all**. |
| `ZipCPU/dspfilters` @ `16d7dc3b23af167759693da9caff7c7111805873` (2024-01-18) | 19 hand-written DSP filter cores incl. `rtl/genericfir.v`, `rtl/firtap.v`, `rtl/fastfir.v`, `rtl/slowsymf.v`, `rtl/subfildown.v` | **Checked** (clone read). **LGPLv3.** No `LICENSE` file in the repository; the grant is in each file header: `rtl/genericfir.v:18-21` (LGPL "version 3 of the License, or … any later version"), `rtl/genericfir.v:33` (`License: LGPL, v3`), identically `rtl/firtap.v:47`. All 19 `rtl/*.v` files carry the same `License: LGPL` line (tallied across the directory). `README.md:48-53` offers "other licenses terms … for a minimal purchase price". |
| `ucb-art/filter` @ `e5ae49cbf55405da834f4b9357b43495b0f14934` (2017-06-29) | Chisel decimating/multi-lane FIR (`src/main/scala/fir/FIR.scala`, `FIRBlock.scala`, `Config.scala`) | **Checked** (clone read). **No licence grant at all**: `FIRBlock.scala:1` and `FIRSpec.scala:1` say "See LICENSE for license details", and **there is no `LICENSE` file** in the repository; `README.md` makes no licence statement; `FIR.scala` and `Config.scala` have no licence header. |
| `hildebrandmw/VerilogFIR.jl` @ `994550d950b924251c96245431c4e717de604fa2` (2018-09-13) | Julia program that emits a Verilog FIR | **Checked** (clone read). Tool licence **MIT**: `LICENSE.md:1`. **Output licence checked and clean**: the committed generated output `example/filter.v` (68 lines) carries **no licence or copyright notice of any kind** (grepped for `licen`/`copyright`/`MIT`/`GPL`: no match). This is the only candidate whose output licence was actually verified. |

**The one unverified cell, and what it would take.** `dsptools`' *output*
licence is unverified because answering it means elaborating Chisel to
Verilog, and the toolchain is not installed on this host: `sbt`, `scala` and
`julia` are all absent (`command -v`; only `java` 21.0.13 is present), and
the repo's own pinned toolchain is Python 3.13 + cocotb 2.1.0 + numpy 2.3.4
(`verification/requirements.txt`) with Icarus 13.0 / Verilator 5.050 /
Yosys 0.67 (`verification/toolchain.json`). `dsptools` pins Chisel 5.1.0 and
Scala 2.13.10 (`build.sbt:8`, `:15`), so the output comes from CIRCT/firtool,
whose emitted notice (if any) was **not read**. This is the identical blocker
0001 hit with `sdf-fft` (`0001:72-73`, `:78`), and it carries the identical
consequence: not adoptable on this evidence.

### Repo-internal references (read on this branch)

| Id | What it establishes | Status |
|---|---|---|
| `rtl/gen/params.py:9-13`, `:51-53`, `:16-22` | The generator's parameter schema: 12 keys, **every key required, no defaults**, `architecture` enum is `("r22sdf",)` only | Checked |
| `rtl/gen/emit.py:2`, `:10-33`, `:159-327` | Emitter is a "pure function of the params"; 327 lines; `fft_rnd` convergent rounder at `:10-33`; per-module string templates assembled by `_top` | Checked |
| `rtl/README.md:22-25` | Output is deterministic; every emitted file carries SPDX Apache-2.0 plus the sha256 of the parameter file; a test fails if `generated/` differs from a fresh regeneration | Checked |
| `rtl/README.md:12`, `:69-70` | `wrapper/fft256_stream.sv` is hand-written and sanctioned ("not generated"); "The register-bus wrapper is not here (tied to FIR coefficient load)" | Checked |
| `sim/fixedpoint_model.py`, `sim/README.md:16-28` | The model pattern: bit-accurate integer model reading the generator's parameter file **through the generator's own parser** (`rtl/gen/params.py`), one validator; `FXP_MUTANT=floor_ties` / `REF_MUTANT=swap_iq` negative controls | Checked |
| `spec/decisions/0004-fft-architecture-survey.md:154` | The FFT core is "3 general complex multipliers (6 to 12 real)" — the scale this record is compared against | Checked |
| `spec/decisions/0004-fft-architecture-survey.md:89-90` | 0004's CSD aside, which reads the FIR as fixed-coefficient | Checked; see open question 4 |
| `spec/decisions/0002-numerics.md:22-25`, `:35-36` | Convergent rounding is the target and a generator parameter; RTL must match the `sim/` model bit-exactly | Checked |
| `README.md:3`, `:39`, `:58`, `:72`; `CLAUDE.md` | Scope: generated datapaths, no hand-redesign, pinned-commit reproducibility | Checked |
| `grep -n -i register spec/spec.md` → lines 33, 37 only | `spec.md:33`'s "register-bus write (below)" has **no register-bus section below it**; the bus is undefined repo-wide | Checked |

## Alternatives considered

### The three options, criterion by criterion

Columns are the three options AC 2 requires. Option B is represented by its
**best** candidate (`dsptools`); the other three external candidates are
disqualified outright and are tabulated separately below.

| Criterion | A: extend `rtl/gen/` | B: external generator (best: `dsptools`) | C: hand-written RTL |
|---|---|---|---|
| Commit/version read | this branch (`rtl/gen/`, 466 lines of stdlib Python excluding its tests) | `fb3b3c65…` (2024-04-29) | n/a |
| Tool licence (file + line) | Apache-2.0, repo-wide; emitted files carry SPDX (`rtl/README.md:23`) | Apache-2.0 (`LICENSE:1-5`, `README.md:190`, `TransposedStreamingFIR.scala:1`) | Apache-2.0 (written here) |
| Output licence (file + line) | Apache-2.0 by construction; no third party in the path (0001's logic at `:93-99`) | **Unverified** — needs sbt/firtool, not installed | Apache-2.0 by construction |
| 32 taps at 1 sample/clock? | Yes, by construction (direct or transposed form, one multiplier per tap) | Yes in form (`TransposedStreamingFIR.scala:61-70`), but **registers are ungated** (`:65-70` has no `when(valid)`), so no stall for back-pressure; the gated variant (`:17-47`) is the **fixed**-tap one | Yes, by construction |
| 16-bit programmable coefficients? | Yes, a parameter + a coefficient store | Taps are a **port**, not a store: `val taps = Input(Vec(numberOfTaps, tapGenerator))` (`:58`). Programmable, but the 32×16-bit store and its load path are not supplied | Yes, by construction |
| Register-bus coefficient load? | **No — nothing supplies this.** Must be specified and written as a wrapper | **No** | Yes, but the bus is undefined (`spec.md:33`, open question 3) |
| Multiplier count (arithmetic) | 32 general 16×16 for a real FIR; see the table below | 32 general (transposed, one per tap) | 32 general |
| Bit-accurate model route | `sim/fir_model.py` reading the parameter file through `rtl/gen/params.py`, **this repo defines the rounding/scaling contract** | Model must chase Chisel/`DspContext` trim and overflow semantics, which cannot be established without building the candidate (the cost 0001 recorded at `:83-84`, `:89-90`) | Model written against hand-written RTL; contract defined here, but no parameter file to read |
| Reproducible from commit + parameter file? | Yes — `regen.sh`, param sha256 in every file, regeneration-diff test (`rtl/README.md:22-25`) | Would need sbt + firtool pinned into `verification/toolchain.json`; `dsptools` pins submodule-free but Chisel 5.1.0/Scala 2.13.10 (`build.sbt:8`, `:15`) | **No** — hand-written RTL has no generator commit or parameter file; `CLAUDE.md`'s reproducibility rule does not apply to it |
| Fits "generated RTL" scope? | Yes | Yes | **Datapath: no** (`README.md:39`). **Wrapper: yes** (`rtl/README.md:12` precedent) |
| New toolchain added to the repo | None (stdlib Python, as `rtl/gen/` already is) | sbt, Scala 2.13, JDK, firtool/CIRCT | None |

### Why the other three external candidates are disqualified

| Candidate | Disqualifier | Evidence |
|---|---|---|
| `ZipCPU/dspfilters` | **LGPLv3 source.** Not compatible with this repo's Apache-2.0 output requirement. Worse than the `dblclockfft` case 0001 rejected: there the LGPL was on the *generated output*, here the LGPL is on the RTL files themselves, so there is no generation step to put distance between the licence and the committed netlist | `rtl/genericfir.v:18-21`, `:33`; `rtl/firtap.v:47`; all 19 `rtl/*.v` identical; `README.md:48-53` offers paid alternatives. The same Gisselquist pattern as `0001:43` |
| `ucb-art/filter` | **No licence grant.** Headers point at a `LICENSE` file that does not exist, so no permission is granted at all — strictly worse than an incompatible licence. Also Chisel2-era (2017) API (`Reg(next=…)`, `Reg(init=…)`, `Vec.fill`) on a `cde`/`dsp-framework` submodule set | `FIRBlock.scala:1`; absence of `LICENSE`; `README.md` silent; last commit 2017-06-29 |
| `hildebrandmw/VerilogFIR.jl` | **Licence clean, architecture wrong.** Its own docstring calls it "a **multicycle** FIR filter": a state machine counts down through taps accumulating one product per clock, so it takes N clocks per sample, not 1 sample/clock (`spec.md:35`). Coefficients are **baked into the output** by an `initial` block — fixed at generation, so the programmable-coefficient and register-bus rows (`spec.md:32-33`) cannot be met. Output reduction is a bare bit-slice (truncation), not convergent (`0002:22-25`). `initial`-initialised coefficient arrays are an FPGA idiom, not a standard-cell one. Julia 0.6/0.7-era package, last commit 2018-09-13 | `src/VerilogFIR.jl:62` ("multicycle"), `:37`, `:68-70`; `example/filter.v:24-33` (`coeff[0] = 2;` … in `initial`), `:53-62` (count-down accumulate), `:64-67` (`data_out <= acc[23:8]`) |

It is worth stating plainly that `dspfilters`' `genericfir` is, of the four,
the **closest architectural match** to what `spec.md` asks for — parameterised
`NTAPS`/`IW`/`TW`/`OW`, a `FIXED_TAPS` switch, a coefficient-write port
(`i_tap_wr`/`i_tap`) and a clock-enable (`i_ce`) for exactly the stall the
streaming row needs. The licence, not the engineering, is what rules it out.
No code, and no file from it, is used here.

### Option C, split in two (as the scope text requires)

"Hand-written RTL" is not one option, because this repo already treats the
datapath and the wrapper differently:

- **C1, hand-written FIR *datapath*.** Contradicts `README.md:39` ("the FFT
  and FIR datapaths come out of an open generator from a parameter set") and
  forfeits `CLAUDE.md`'s pinned-commit-plus-parameter-file reproducibility,
  which is the repo's stated reason for existing (`README.md:46-51`).
  Adopting it would require editing `README.md` and the spec — **a ruling, not
  an agent edit**. Rejected at this level; named for the ruling.
- **C2, hand-written *wrapper*** holding the register bus, the coefficient
  store and the valid/ready handshake, around a generated datapath. **Already
  sanctioned**: `rtl/wrapper/fft256_stream.sv` is hand-written and explicitly
  "not generated" (`rtl/README.md:12`), and `rtl/README.md:69-70` records the
  register-bus wrapper as deliberately absent *pending this decision*. C2 is
  not an alternative to A or B — **it is required under all of them**, because
  no surveyed candidate supplies a register bus.

### Rejected framings, one line each

- **A prose-only record**: 0001 and 0004 both use tables, and the table is
  what makes the checked/unverified column auditable per candidate.
- **Deferring the licence check to the implementing issue**: `0001:43` shows
  the output-licence header is precisely what disqualifies a candidate, so it
  belongs in the survey; three of four candidates here were settled on licence
  alone.
- **Surveying FIR coefficient-design tooling** (`scipy.signal`, `firdes`,
  Julia `DSP.jl` as `VerilogFIR.jl`'s `example.jl` uses): these produce
  coefficients, not RTL. They are an input to any option, not a competitor.
- **Adopting symmetry or folding to cut multipliers**: both touch rows this
  record may not edit (`spec.md:34`, `:35`); they are named as options below,
  not adopted.

## Decision

**Recommendation: Option A + C2 — extend the project's own Apache-2.0
generator (`rtl/gen/`) to emit the FIR datapath from its own parameter file,
with a hand-written wrapper supplying the register bus and the coefficient
store.** No external generator qualifies.

This is the same outcome 0001 reached for the FFT, on the same two grounds
(licence of the output, and the impossibility of establishing a candidate's
numerics contract without building it) — and `spec.md:66-67`'s premise ("no
surveyed generator emits a FIR") turns out to be *narrowly* false and
*materially* true: `dsptools` does contain a FIR, and three other candidates
exist, but none is adoptable.

Rejected, one line each:

- **`ZipCPU/dspfilters`**: LGPLv3 on the RTL itself (`rtl/genericfir.v:33`).
- **`ucb-art/filter`**: no licence grant at all; `LICENSE` referenced but absent.
- **`hildebrandmw/VerilogFIR.jl`**: multicycle and fixed-coefficient; cannot meet
  `spec.md:32`, `:33` or `:35`.
- **`ucb-bar/dsptools`**: output licence unverified (no sbt/firtool here), the
  programmable-tap variant is ungated example code with no checking test, it
  supplies no coefficient store, and it would add a Scala/sbt/firtool
  toolchain to a stdlib-Python repo.
- **C1, hand-written datapath**: contradicts `README.md:39` and forfeits
  pinned-commit reproducibility; needs a README/spec change, which is a ruling.
- **Symmetric-only or folded FIR**: cuts multipliers but breaks full
  programmability or the 1-sample/clock row; stretch-column options
  (`spec.md:34`), not the target.

**This is a recommendation, not a ratification. Agents do not ratify.** The
ruling questions are in the next-to-last section.

## What it buys against the spec rows

All figures are **arithmetic from the structure or estimates. None is
measured and none is simulated.** There is no FIR model and no FIR RTL yet.

### Multiplier count — the dominant finding

`sky130_fd_sc_hd` has no hard multipliers, so every multiply is synthesised
logic. Runtime-programmable coefficients are **not constants**, so CSD and
shift-add specialisation do not apply — the same reasoning `0004:89-91`
applies to the twiddles, here for the opposite reason (see open question 4).
At 32 taps and one sample per clock, every tap needs its own multiplier:

| Configuration | Real 16×16 multipliers | Versus the whole FFT core (6 to 12 real, `0004:154`) |
|---|---|---|
| Real data, real coefficients | **32** | 2.7× to 5.3× |
| Complex data, **real** coefficients (one filter per rail) | **64** | 5.3× to 10.7× |
| Complex data, **complex** coefficients, 3-multiplier form | **96** | 8× to 16× |
| Complex data, complex coefficients, 4-multiplier form | **128** | 10.7× to 21.3× |

**The FIR is arithmetically the larger block of the two, by between about 3×
and 20× in general multipliers, and which multiple applies is not specified
anywhere** (open questions 1 and 2). That is this record's main finding, not
a footnote. The three-way split matters: "complex FIR" is ambiguous between
real and complex *coefficients*, a further 1.5× to 2× on top of the 2× for
complex data.

Options that reduce the count, each with the spec row it touches:

- **Linear-phase symmetry**: halves 32 taps to **16** multipliers, by folding
  tap pairs before the multiply. Constrains the coefficients to be symmetric,
  so it is not compatible with unrestricted programmability, and "symmetric"
  is a **stretch**-column entry (`spec.md:34`), not the target. Named, not
  adopted.
- **Time-multiplexing / folding** one multiplier across M taps: needs the
  clock to run M× the sample rate. `spec.md:35` and `:38` ask for 1
  sample/clock *at* 50 MHz, so on the current rows there is **no headroom at
  all** and folding is unavailable. `VerilogFIR.jl` is exactly this design and
  fails the row for exactly this reason. Available only if the ruling answers
  open question 5 by separating the sample rate from the clock. Named, not
  adopted.

### Row by row

| Row | Effect |
|---|---|
| FIR taps (`:31`) | 32 is a generator parameter (`taps`); 16 fallback and 64 stretch are the same parameter. Decimating (stretch) is a different structure, not a parameter of this one. |
| FIR coefficient width (`:32`) | 16-bit is a parameter (`coeff_width`); 12 and 18 the same. Programmability is a property of the **store**, which option A must add — no surveyed candidate supplies it. |
| FIR coefficient load (`:33`) | **Not satisfiable yet, by any option.** The register bus is undefined repo-wide (open question 3). The wrapper (C2) implements whatever the bus specification says; this record does not specify it. |
| FIR options (`:34`) | Target is "none". Symmetry and decimation stay stretch; both are structural, so each needs its own parameter and its own model path. |
| Streaming interface (`:35`) | Direct or transposed form at one multiplier per tap meets 1 sample/clock natively. Back-pressure needs an `en` gate on every register — the same `stall` parameter `rtl/gen/params.py:12` already defines for the FFT, and the thing `dsptools`' programmable variant lacks (`TransposedStreamingFIR.scala:65-70`). |
| Clock 50 MHz (`:38`) | **Unknown; no timing evidence.** The critical path is one 16×16 multiply plus the adder that accumulates it. Transposed form is the better starting point: it puts one adder between tap registers, instead of direct form's depth-5 adder tree over 32 products. 20 ns at `ss_100C_1v60` for a synthesised 16×16 multiply plus an add is **not established**, and pipelining the multipliers is the obvious parameter if STA fails. This is the FIR's main risk and only STA answers it. |
| Internal width growth | Arithmetic worst case, no coefficient normalisation assumed: a 16-bit × 16-bit product is 32 bits (magnitude ≤ 2^30); 32 of them sum to ≤ 2^35, needing about a **36- to 37-bit accumulator**; then a reduction to 16-bit output. Convergent rounding at the reduction, per `0002:22-25`. The real schedule is a model study, exactly as `stage_widths` is for the FFT (`rtl/README.md:47-50`). |
| Storage (`:40`) | Flops only, and **small**: a 32-tap 16-bit data delay line ≈ 512 flops, a 32×16-bit coefficient store ≈ 512 flops, plus pipeline and accumulator registers — order **1k to 2k flops**, against the FFT's estimated 17k to 26k for storage alone (`0004:153`) and 0003's ≈ 31k reference. **The FIR's cost is multipliers and timing, not storage.** No SRAM is implied at any tap count in the spec. |
| Area budget (`:39`) | No budget is set, so none is breached. But 32 to 128 synthesised 16×16 multipliers is a large addition that the first synthesis must report before any budget is set. **Unmeasured.** |
| SQNR (`:30`) | The FIR is outside the FFT's SQNR row. Whether a combined FIR+FFT accuracy claim is needed depends on open question 2 (where the FIR sits) and is not decided here. |
| Control interface (`:37`) | Same undefined register bus as `:33`. Unchanged by this record. |

No spec row is relaxed by this recommendation, and none is edited.

### Bit-accurate model route (all options)

The existing pattern is the answer and is cited rather than re-invented:
`sim/fir_model.py` plus `sim/test_fir_model.py`, reading the FIR parameter
file **through the generator's own parser** (`rtl/gen/params.py`) so there is
one validator, as `sim/fixedpoint_model.py` does
(`sim/README.md:16-28`), and shipping a must-fail negative control selected by
an environment variable (`FIR_MUTANT=…`, mirroring `REF_MUTANT=swap_iq` and
`FXP_MUTANT=floor_ties`). RTL must match it bit-exactly (`0002:35-36`).

What differs between the options is **whose arithmetic the model must match**.
Under A and C the repo defines the rounding and scaling contract and writes
the model against this record. Under B the model must reproduce an external
generator's `DspContext` trim and overflow semantics — which `0001:83-84`
and `:89-90` record as a cost it could not even establish without building
the candidate. That asymmetry, more than the licence, is why A is recommended
over B even if `dsptools`' output licence were to come back clean.

## Generator parameters implied (input to the follow-on issues)

Offered as the shape of the parameter file a FIR emitter would read, not as
ratified values. **A separate parameter file, not an extension of
`fft256.params`**: `rtl/gen/params.py:9-13` and `:51-53` make every key in
`SCHEMA_KEYS` required with no defaults, so adding FIR keys to the shared
schema would invalidate the existing committed FFT parameter file. A second
schema keyed on `architecture` (today enumerated `("r22sdf",)` only,
`params.py:17`) with its own `rtl/params/fir32.params` is the route that keeps
the existing validator honest.

| Parameter | Value / candidates | Notes |
|---|---|---|
| `architecture` | `fir_direct` or `fir_transposed` | New enum member. Transposed is the better timing starting point (see the clock row); the choice is for the implementing issue, against STA. |
| `taps` | 32 (fallback 16, stretch 64) | `spec.md:31`. |
| `data_width` | 16 | `spec.md:26`-consistent; 12 fallback, 18 stretch. |
| `coeff_width` | 16 | `spec.md:32`. |
| `coeff_programmable` | `1` | `spec.md:32-33`. A `0` (fixed-coefficient) variant would enable CSD and is **not** what the spec asks for; see open question 4. |
| `complex` | **unset — open question 1** | Drives multiplier count by 2× to 4×. Must be answered by the ruling before any parameter file is committed. |
| `acc_width` | model-selected, candidate 36 to 37 | Arithmetic worst case above; the study narrows it as the FFT's `stage_widths` study does. |
| `output_width` | 16 | Convergent reduction from `acc_width`. |
| `rounding` | `convergent` at the reduction | `0002:22-25`; reuse `fft_rnd` (`rtl/gen/emit.py:10-33`), which is already a parameterised convergent rounder. |
| `overflow` | none; the model reports the no-overflow coefficient and input range | Matches `0002:26-34` and `sim/overflow_range.py` for the FFT. Saturation out of scope for v1. |
| `pipeline` | registers per multiplier | Choose against STA, as the FFT's `pipeline` is. |
| `stall` | `en` on all registers | For valid/ready back-pressure; the FFT already has this key (`params.py:12`). |
| `storage` | flops only | ≈ 1k to 2k flops; no SRAM at any spec tap count. |
| *(not a generator parameter)* | register-bus address map, data width, handshake | **Undefined** — a wrapper and a specification, not a parameter. Open question 3. |

## Consequences and open questions

These are gaps in the spec, carried to the ruling. Editing `spec.md` is out of
scope for this record, so none is decided here.

1. **Is the FIR real or complex — and if complex, are the coefficients real or
   complex?** No row says. It is a 2× to 4× swing in multiplier count (table
   above) and the single largest unknown in this record. Nothing downstream —
   not the parameter file, not the model, not an area estimate — can be
   committed until it is answered.
2. **Where does the FIR sit** — before the FFT, after it, in parallel, or
   bypassable? Nothing in `spec.md` or `README.md` says. It determines the
   data width the FIR sees (16-bit input, or the post-reduction 16-bit
   output), whether question 1 is even open (a FIR before a complex FFT on a
   real input stream could be real), and whether a combined accuracy claim is
   needed.
3. **The register bus is undefined, repo-wide.** `spec.md:33` says
   "register-bus write (below)" but there is no register-bus section below it
   — only the Control interface row (`spec.md:37`), itself
   `**target, no evidence**`. No address map, data width or handshake is
   specified anywhere, which is exactly why `rtl/README.md:69-70` records the
   register-bus wrapper as deliberately absent. **The bus must be specified
   before the coefficient-load row can be verified**, and no option in this
   survey supplies one. This record does not specify it. Note also that
   `CLAUDE.md` puts host bus *fabric* design out of scope, so the bus should
   be a minimal local register interface, not a bus implementation.
4. **0004's CSD aside assumes a fixed-coefficient FIR, which contradicts
   `spec.md`.** `0004:89-91` rejects CSD for the twiddles because "CSD helps
   only fixed-coefficient filters (the FIR, not this record)" — reading the
   FIR as fixed-coefficient, while `spec.md:33` and `README.md:72` make the
   coefficients runtime-programmable. Records are append-only and 0004 is not
   edited. **This record proceeds on the `spec.md` reading: programmable, so
   CSD does not apply and every multiplier is general.** If the ruling instead
   makes the coefficients fixed, the multiplier counts above are a large
   overestimate and this record must be superseded, not amended.
5. **FIR sample rate relative to the clock.** On the current rows (1
   sample/clock at 50 MHz) folding is unavailable, so the multiplier count
   cannot be traded down. If the ruling separates the two, folding becomes an
   option and the arithmetic above changes substantially.
6. **`spec.md:66-67` needs a correction at ratification.** Its premise "no
   surveyed generator emits a FIR" is narrowly false — `dsptools` contains
   `TransposedStreamingFIR` (`src/main/scala/examples/TransposedStreamingFIR.scala:49-73`),
   which 0001 did not check because it searched for an FFT (`0001:43`,
   `grep -rli fft --include=*.scala`). The conclusion is unchanged, for
   different reasons. Editing `spec.md` is out of scope here.
7. **`dsptools`' output licence stays unverified** and must not be promoted to
   fact without an sbt/firtool elaboration and a read of the emitted file's
   header. If a future issue installs that toolchain, this is the check to run;
   until then option B is closed on evidence, not on preference.
8. **No FIR timing, area or accuracy figure exists.** Everything in this
   record is arithmetic. The multiplier-heavy datapath against a 50 MHz target
   at `ss_100C_1v60` is the risk the follow-on synthesis issue must size, and
   the first thing that could invalidate the recommendation.
9. **Follow-on work, all gated on the ruling**: the register-bus
   specification; the FIR emitter in `rtl/gen/` plus its parameter file; the
   `sim/fir_model.py` model and its mutant; the hand-written register-bus
   wrapper; the cocotb coefficient-load and bit-exactness benches; and the
   `spec.md` row updates that turn `**target, no evidence**` into evidence.
