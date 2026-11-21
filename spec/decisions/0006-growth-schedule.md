# 0006 — FFT growth schedule: confirm the placeholder (1 bit/stage)

- **Status**: Proposed. Agents do not ratify it.
- **Date**: 2026-11-20
- **Scope**: select the growth schedule for the spec's "Internal growth and
  scaling" row (`spec/spec.md`), the one FFT row still marked **open target:
  schedule not selected**. The measurement half was done (#76's
  `sim/schedule_sweep.py` and `measurements/schedule-sweep.json`; #77's
  `measurements/model-sizes.json`); this record is the selection. It is
  **Proposed status only**: no spec row is edited here, nothing is relaxed,
  and the swap (if any) is #163, after the ruling.
- **Numbering**: `spec/decisions/` holds 0001-0005; 0006 is the next free
  number (re-checked at write time on `feature/issue-160` from
  `origin/main` @ `761f763`).
- **Not changed**: `rtl/params/fft256.params`, `rtl/generated/`, `netlist/`,
  `synth/` and every `spec/spec.md` row. The recommended schedule is committed
  as a separate ruling-ready artifact, `rtl/params/fft256.candidate.params`
  (same widths as the placeholder file; its own sha256 keys the evidence).

## Method and limits of the evidence

Every figure below is **simulated** (the bit-accurate model against a
double-precision reference; Icarus runs of generated RTL; Yosys `klt
synthesize` runs at `tt_025C_1v80`, clock unconstrained), never measured on
silicon. Sources, all committed or filed with this record:

- `measurements/schedule-sweep.json` (2026-11-14 record): the nine
  generator-legal candidate rows, per-set minimum SQNR over 100 frames and
  overflow counts on the spec's vector sets (`random50`, `random70`,
  `tone50`, `tone90`).
- `measurements/fft256-candidate.json` (this PR): the recommended row and the
  runner-up, each re-run from a parameter file keyed by its own sha256 —
  model figures, no-overflow amplitude range, bit-exact RTL-vs-model check
  (`verification/test_gen_exact.py` style, zero tolerance) and `klt
  synthesize` figures against the placeholder baseline.
- `measurements/overflow-range.json` (record 2, this PR): the recommended
  schedule's no-overflow amplitude sweep.
- `synth/fft256.synth.report.json`: the placeholder baseline (60715 cells,
  1078566.9312 um², 781969.9712 um² sequential, `tt_025C_1v80`).

The sweep records per-set minimum SQNR, overflow counts and summed stage
widths only; the amplitude range, bit-exact check and synthesis figures are
this record's additions. The spec defines **no margin threshold** — margins
over the 60 dB row are reported as figures, and the argument below owns how
much margin the recommendation keeps.

## The candidates and their margins

Margin = the candidate's worst per-set minimum SQNR minus the spec's 60 dB
target (`measurements/schedule-sweep.json`, re-derived; all nine rows):

| Row | stage_widths | tw | sum | worst set | min SQNR (dB) | margin (dB) | meets 60 dB + no-overflow rows |
|---|---|---|---|---|---|---|---|
| zero growth | 16×8 | 16 | 128 | random50 | 61.5785 | +1.5785 | yes |
| flat at input+1 | 17×8 | 16 | 136 | random50 | 63.4453 | +3.4453 | yes |
| half bit/stage | 17,17,18,18,19,19,20,20 | 16 | 148 | random50 | 65.4672 | +5.4672 | yes |
| 0002 reference point | 17,18,18,19,19,20,20,21 | 16 | 152 | random50 | 65.6179 | +5.6179 | yes |
| 0002 reference point, tw=14 | 17,18,18,19,19,20,20,21 | 14 | 152 | random50 | 65.3157 | +5.3157 | yes |
| **placeholder (1 bit/stage)** | **17..24** | **16** | **164** | random50 | **65.6481** | **+5.6481** | **yes** |
| placeholder, tw=12 | 17..24 | 12 | 164 | random50 | 63.2524 | +3.2524 | yes |
| placeholder, tw=20 | 17..24 | 20 | 164 | random50 | 65.6626 | +5.6626 | yes |
| front-loaded growth | 18,20,21,22,22,22,22,22 | 16 | 169 | random50 | 53.4264 | −6.5736 | **no** (SQNR) |

`random50` is the worst set for every row. Eight of nine rows meet the 60 dB
row with zero overflow components on the spec's sets, so the selection is a
trade-off, not a filter. Two readings the table forces: minimum SQNR is **not
monotone in the width sum** (front-loaded growth has the largest sum and the
only failing margin), and the twiddle axis has its knee at 16 (tw=12 costs
2.4 dB, tw=20 buys 0.0145 dB) — every row here keeps tw=16.

The amplitude criterion does not separate the rows: the measured no-overflow
amplitude range of the placeholder, the runner-up, and every other
twiddle-16 contender measured is the same — random I/Q no overflow up to
**0.92** of full scale (first overflow at 0.93, in stage 1), tone no overflow
up to the **1.00** sweep end (`measurements/overflow-range.json`;
`measurements/fft256-candidate.json`). No candidate narrows the placeholder's
range, and none widens it.

## Two findings that decide the record

**1. Only the placeholder stage-width schedule (17..24) is realizable by
the generator as tested for this record.** Realizability keys on the
stage-width vector, not the sweep row: three of the nine rows — tw=12, 16
and 20 — carry the placeholder's widths `17,18,19,20,21,22,23,24` and
differ only in `twiddle_width`, and the equal-width-transition defect below
is a property of that vector. The bit-exact RTL-vs-model check (zero
tolerance, 512 samples, configuration (256, natural, pipeline=1)), run on
the emitter as pinned in `measurements/fft256-candidate.json` (`rtl/gen` @
`746e8f1`, record dated 2026-11-20 — a subsequent generator fix such as PR
#168 changes what a re-run would show, not what was tested here), covered
the tw=16 row and two failing controls: it **passes** for the placeholder
widths (512/512, bit-exact) and **fails for every narrower schedule**, the
RTL diverging from the model by a **nominal** factor of 2^(number of
equal-width stage transitions) — the runner-up at a nominal 2⁴ (512/512
samples differ), the 0002 reference point at a nominal 2³ (8×). Nominal,
not sample-exact: the runner-up's first recorded sample `(-10470,3329)` is
the model pair `(-654,208)` times 16 — `(-10464,3328)` — with a `(-6,+1)`
residual, the un-rounded low bits the emitter keeps, and individual samples
may carry rounding or wrap residual (`fft256-candidate.json` words its own
finding the same way: "dut is the model scaled by 2^4"). The tw=12 and tw=20
rows were **not** bit-exact-checked; their realizability is inferred from
the shared width vector, not measured. Root cause, filed as **#162**:
`rtl/gen` emits no mid-pipeline width reduction — the model drops
`max(0, w[i-1]+1 − w[i])` LSBs with convergent rounding after each stage,
but the emitted `fft_sdf_stage` wraps a sum that needs that bit instead of
scaling. The placeholder (17,18,…,24) is the unique sweep schedule whose
every transition grows by exactly one bit, which is why every committed
figure on main is consistent. A narrower schedule is adoptable only after
#162, plus the full swap and re-verification that #163 sequences.

**2. The area saving the narrower rows promise is measured at a fraction of
the width-sum proxy.** `klt synthesize` on the runner-up's generated RTL
(top `fft256_stream`, `sky130_fd_sc_hd`, `tt_025C_1v80`, clock
unconstrained): **58433 cells, 1053978.3488 um², 770679.1424 um²
sequential** against the placeholder's committed **60715 / 1078566.9312 /
781969.9712** — a saving of **3.76 % of cells, 2.28 % of area, 1.44 % of
sequential area** for a 9.8 % cut in summed stage width
(`measurements/fft256-candidate.json`). The reorder buffer, control and
wrapper — which stage widths do not touch — hold most of the area. These are
also **lower bounds**: they exclude the mid-pipeline rounders the #162 fix
must add before the runner-up can exist at all.

## Decision

**Recommendation: confirm the placeholder schedule — `stage_widths=
17,18,19,20,21,22,23,24`, `twiddle_width=16` ("1 bit/stage") — as the
selected schedule for the spec's Internal growth and scaling row.** The
recommended schedule keeps **+5.6481 dB** of margin over the 60 dB row, zero
overflow on the spec's sets, and the measured no-overflow amplitude range
random 0.92 / tone ≥ 1.00, identical to every contender. The margin is not
the largest on the realizable schedule: its own tw=20 row reads +5.6626 dB
in the sweep — 0.0145 dB more — at the cost of a wider multiplier, the same
trade the twiddle-axis reading above rejects, so the recommendation keeps
tw=16. Its netlist **is** the committed netlist: a fresh `klt
synthesize` of its generated RTL reproduces the committed report's figures
exactly (60715 cells, 1078566.9312 um², 781969.9712 um² sequential), and its
bit-exact check passes 512/512. Confirming it costs nothing and unblocks #17
to route the committed netlist unchanged.

Why that much margin, and not less: the spec sets no margin threshold, so the
record argues. The margin is not headroom against a softer target — 60 dB is
the ratified target row — it is robustness of the evidence: every committed
figure (smoke record, spec status cells, #17's route inputs) rests on
+5.6481 dB, and a schedule that thins it to +1.5785 dB (zero growth) would
re-base all of those for a one-off area saving measured at 2-4 % for the best
narrower row. Nothing in the target (256-point at 50 MHz) or the fallback
(64-point, same schedule family per `measurements/model-sizes.json`) needs
the thinner margin.

**Runner-up: "half bit/stage" (17,17,18,18,19,19,20,20, tw=16).** It is the
best narrower row: +5.4672 dB (0.1809 dB below the recommendation), the same
amplitude range, and the largest measured area saving of any legal row. It
lost on two measured grounds: (1) it is **not realizable today** — the
bit-exact check fails at a nominal factor of 2⁴: the DUT is the model times
16, with rounding or wrap residual in individual samples (#162), so adopting
it means a generator numerics change, a full swap and re-verification
before any netlist exists;
(2) its measured saving — 2282 cells, 24588.5824 um² total, 11290.8288 um²
sequential, before the rounders the fix adds — does not justify that path
for the target design. If a future ruling needs every um² (for example a
#17 floorplan retry that fails on area), the path back is #162 then the swap
in #163; the row and its evidence stay recorded.

The other meet-the-rows rows are named, not adopted: the 0002 reference
point (+5.6179 dB, sum 152) loses to the runner-up on the same two grounds
with less area saved; "flat at input+1" (+3.4453 dB) and "zero growth"
(+1.5785 dB) trade margin no measured pressure asks for; the twiddle-14
variant saves nothing the schedule axis doesn't and loses 0.3 dB; tw=20
costs multiplier width for 0.0145 dB. Front-loaded growth fails the 60 dB
row outright (−6.5736 dB) despite the largest width sum.

## Consequences and open questions

1. On the ruling, #163 updates the spec row from **open target** to the
   selected schedule (citing this record) and disposes of
   `rtl/params/fft256.candidate.params`; nothing else moves — the committed
   RTL, netlist, smoke and overflow evidence already describe the
   recommended schedule.
2. Generator defect #162 stays open regardless of the ruling: the parser
   accepts schedules the emitter cannot realize, and
   `sim/schedule_sweep.py` records them as `generator_legal: true` on parse
   legality alone. Any future schedule study inherits that trap until #162
   is fixed.
3. #17's operator decision (floorplan retry, batch routing, or the 64-point
   fallback) is untouched by this record: confirming the placeholder leaves
   #17 routing the committed netlist; ruling for the runner-up would instead
   sequence #17 behind #162 and the swap.
4. The stretch sizes are not re-judged here: `measurements/model-sizes.json`
   shows the 1024-point figures on this schedule family land below 60 dB —
   a stretch-size/width pairing question, not a schedule question
   (its own reading note says the same).

## Citations

| Id | What it establishes | Status |
|---|---|---|
| `measurements/schedule-sweep.json` (2026-11-14 record) | the nine candidate rows, per-set minimum SQNR and overflow; `generator_legal` verdicts | committed |
| `measurements/fft256-candidate.json` (this PR) | both finalists' model, amplitude, bit-exact and synthesis evidence, keyed by parameter-file sha256; the #162 failure and its controls | this record's evidence |
| `measurements/overflow-range.json` (record 2, this PR) | the recommended schedule's no-overflow amplitude range (random 0.92 / tone ≥ 1.00) | this record's evidence |
| `synth/fft256.synth.report.json` | the placeholder baseline: 60715 cells, 1078566.9312 um², 781969.9712 um² sequential at `tt_025C_1v80` | committed |
| `verification/test_gen_exact.py` (`GEN_EXACT_PARAMS`) | the bit-exact check path used for both finalists and the #162 controls; the six committed configurations unchanged | this PR |
| `sim/fixedpoint_model.py` (`_reduce`) | the arithmetic contract the RTL must match: one convergent reduction per stage of `max(0, w[i-1]+1−w[i])` LSBs plus twiddle fraction | committed |
| #162 | the generator defect: no mid-pipeline width reduction; 2^drops divergence | filed |
| #163 | the post-ruling follow-up (spec-row update; swap path if ruled otherwise) | filed |
| `spec/decisions/0002-numerics.md` | the 60 dB row, the vector set, the overflow row this selection is judged against | committed |
