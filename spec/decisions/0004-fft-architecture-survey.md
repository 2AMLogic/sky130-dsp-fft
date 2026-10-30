# 0004 — FFT architecture survey and choice

- **Status**: Proposed. Agents do not ratify it.
- **Date**: 2026-10-29
- **Scope**: the architecture of the project's own Apache-2.0 FFT generator
  (0001, operator ruling 2026-10-29, #27). First deliverable of #27, issue #28.
  It feeds the generator issue (#29) and the model issue (#31) through the
  parameter table below. No generator, model or RTL is written here.
- **Numbering**: `origin/main` has no `spec/decisions/`; PR #6
  (`feature/issue-2`) holds 0001-0003, read 2026-10-29, so 0004 is the next
  free number. If #6 adds a record first, renumber this file, not #6's.
- **Not changed**: no spec row is relaxed. 0001, 0002, 0003 and `spec.md`
  (PR #6) are not edited; where this record states a figure it replaces one of
  their reference points, that is carried to #27's "Then" step.

## Method and limits of the evidence

The survey was a short desk review on 2026-10-29, not a systematic one. The
only checks possible in the build environment were: bibliographic records
resolved through the Crossref API (title, authors, venue, year), and web
search snippets. **No paper's full text was read.** Consequences:

- "Record checked" below means the identifier resolves to the stated title,
  authors and venue. It does not mean the claim attributed to the work was
  checked against the paper's body.
- Claims attributed to a work are marked **(from memory, unverified)** unless
  the record's abstract states them. They are design inputs, not facts, and
  the `sim/` model (#31) and synthesis decide each one.
- Items I could not resolve are listed as **unverified** and are not relied
  on.

## Spec rows this choice is judged against

From `spec/spec.md` on `feature/issue-2` (proposed, not ratified): 256-point
complex, forward, natural output (fallback bit-reversed), 16-bit I/Q in and out,
SQNR ≥ 60 dB simulated, 1 sample/clock streaming valid/ready, 50 MHz at
`ss_100C_1v60`, `tt_025C_1v80`, `ff_n40C_1v95`, flop-only storage, area budget
set after first synthesis (0003 estimate ~30k flops).

## Citations

| Id | Work | Status |
|---|---|---|
| doi:10.1007/s11265-021-01655-1 | M. Garrido, "A Survey on Pipelined FFT Hardware Architectures", J. Signal Process. Syst. 94(11):1345-1364, 2022 (online 2021) | Record checked (Crossref). Abstract: surveys 50 years of pipelined FFT architectures for complex input, power-of-two sizes, classified serial/parallel. |
| doi:10.1109/IPPS.1996.508145 | S. He, M. Torkelson, "A new approach to pipeline FFT processor", IPPS-96 | Record checked (Crossref): title, authors, venue. Year not in the record; "1996" is inferred from the conference name. Radix-2² SDF attribution: from memory, unverified. |
| doi:10.1109/TVLSI.2011.2178275 | M. Garrido, J. Grajal, M. A. Sánchez, O. Gustafsson, "Pipelined Radix-2^k Feedforward FFT Architectures", IEEE TVLSI 21:23-32, 2013 | Record checked (Crossref): title, first author, venue, year, volume, pages. Co-authors from memory, unverified. |
| doi:10.1109/DCIS62603.2024.10769116 | F. Albertuz, M. Garrido, "A Serial Low-Switching FFT Architecture Specifically Tailored for Low Power Consumption", DCIS 2024 | Record checked (Crossref). The reported ≈ one-third power reduction comes from a search snippet of the author repository page (oa.upm.es/87358), which returned HTTP 403 to the fetch: **unverified**, and its technology and activity assumptions are unknown. |
| Volder, "The CORDIC trigonometric computing technique", IRE Trans. Electronic Computers, 1959 | Not resolved through Crossref this session | **Unverified**; cited only as the name of a method. |
| Twiddle symmetry, block floating point, CSD constants | Textbook techniques, no single source cited | **Unverified** as to any quantitative claim; used qualitatively. |
| ZipCPU/dblclockfft `3378b77d83a98b06184656a5cb9b54e50dfe4485`; ucb-bar/sdf-fft `10874b3f…`; milovanovic/sdf-fft `d1978a9b284ee1bd4e09ab3fa58e223cd15a5ae9` | Read for 0001 | Reference points only, as 0001 records; not re-read here. Not used as a generator (operator ruling). |

Gap: the issue asks for reduced-switching work from about 2022 onward. One
paper was found (Albertuz/Garrido, 2024). A second was seen only in a search
snippet (Liu, Zhao, Wu, Parhi, Zeng, Chen, 2021, low-power twiddle addressing
for split-radix, University of Minnesota experts page): not resolved to an
identifier, **unverified, not cited as fact**. The survey is therefore thin on
2022+ work and #29 should treat switching reduction as an option to measure,
not as a result.

## Alternatives considered

### Radix-2^k SDF versus MDC / feedforward

At one sample per clock, a single-path delay feedback (SDF) pipeline needs
N − 1 = 255 complex words of delay storage, which is the minimum for a
streaming FFT (from memory, unverified; consistent with the Garrido survey
scope). Multi-path delay commutator (MDC) and feedforward forms
(Garrido 2013) are aimed at 2, 4 or more samples per clock; at one sample per
clock they gain no throughput and use more storage or muxing.

Radix-2² SDF (He and Torkelson) keeps the radix-2 butterfly but pairs stages so
the intermediate twiddle is the trivial rotation by −j. For N = 256 = 4^4 that
gives 8 radix-2 butterflies, 4 trivial-rotation stages and 3 general complex
multipliers (log4 N − 1), against 7 for a plain radix-2 SDF (from memory,
unverified; the stage counts follow from the structure and the model will
confirm them).

### Multiplier-light twiddle rotation

- **Trivial-twiddle stages**: kept. The −j rotation is a swap and negate, no
  multiplier.
- **Twiddle ROM reduction by symmetry**: kept. Eighth-circle symmetry
  reduces the table to about N/8 + 1 = 33 entries of (cos, sin) for 256-point;
  the table is combinational logic (no memory), so flop-only storage holds.
- **CORDIC**: rejected for v1. At one sample per clock a pipelined CORDIC
  needs about one stage per output bit, each with three adders, per general
  multiplier; the area comparison against a 16×16 multiplier is unmeasured
  and left to synthesis, but no source found says it wins at 16 bits.
- **Shift-add / CSD constants**: rejected for the SDF stages. The twiddle
  index changes every clock, so the multiplicand is not a constant; CSD helps
  only fixed-coefficient filters (the FIR, not this record).
- **Complex multiply form**: 3-real-multiplier versus 4-multiplier is a
  generator parameter; 3-multiplier trades one multiplier for three adders
  and a precomputed twiddle sum.

### Scaling

- **Per-stage unconditional 1/2**: rejected as the only mechanism. Over 8
  radix-2 stages it divides by 256, so a random input at rms level r yields
  an output at about r/16: a 4-bit (≈ 24 dB) loss of effective dynamic range
  against an unscaled core, aimed at the 60 dB row. Arithmetic, not a
  measurement.
- **Block floating point**: rejected for v1. A frame-wide exponent needs
  the whole frame stored before scaling or a second pass; at one sample per
  clock streaming that adds latency and storage beyond the flop budget
  (reasoning, unmeasured).
- **Chosen**: a fixed per-stage growth schedule with a final
  rounding reduction to the output width. Widths grow where the bounded
  amplitude range needs them (0002 keeps the no-overflow vector set rule) and
  the schedule is a model-selected parameter list, not a rule.

### Low-power / reduced switching (2022+)

Serial low-switching architecture (Albertuz/Garrido 2024): rejected as the
base because its reported gain is unverified here and the spec has no power
row (`spec.md` open item). Two options stay open for #29 as measurable
switches, not commitments: gating of idle SDF stage registers and holding
trivial-twiddle stages out of the multiplier path.

## Decision

**Radix-2² single-path delay feedback, 4 radix-2² stages, 256-point, one
sample per clock, forward, fixed per-stage width schedule, convergent rounding
at the final reduction (and at any stage that reduces width), natural output
via a reorder buffer placed after the 16-bit reduction.**

Rejected, one line each:

- Radix-2 SDF: 7 general multipliers against 3 (from memory, unverified).
- Radix-4 SDF / R4SDF: same multiplier count as radix-2², more adders in the
  butterfly (from memory, unverified).
- Radix-2^k MDC / feedforward: aimed at multi-sample-per-clock; no gain here.
- CORDIC rotation: more area per sample is expected; unmeasured.
- CSD/shift-add multipliers: twiddles are not constants in SDF.
- Block floating point: frame storage and latency against the flop budget.
- Per-stage unconditional 1/2: costs about 24 dB for noise-like input.
- Low-switching serial architecture: gain unverified; no power row.
- Memory-based (in-place, single butterfly) FFT: cannot sustain 1 sample/clock.

## What it buys against the spec rows

All figures are **estimated** (arithmetic from the structure) or
**unmeasured**; none is a result. The measured values come from `sim/`
(SQNR, overflow range), Yosys/OpenROAD (area, timing) and cocotb (latency).

| Row | Effect |
|---|---|
| FFT size, direction | 256, forward: fixed by generator parameters, no runtime selection. |
| Output order | Natural needs a reorder buffer (the SDF output is bit-reversed); bit-reversed fallback omits it. |
| Input/output width | 16-bit in, 16-bit out; reduction by convergent rounding before the reorder buffer. |
| SQNR ≥ 60 dB | **Unmeasured.** No SQNR figure is claimed. The reference point is 65.6 dB (set 1, 16-bit) simulated on the superseded dblclockfft core (0002); it does not transfer. The model (#31) reports the new number against the double-precision FFT and the spec vector set, or "unmeasured". |
| Clock 50 MHz | Per-stage pipelining depth is a generator parameter; each general multiplier is the expected critical path. Closure at `ss_100C_1v60` is **unknown** until STA. |
| Storage | SDF delays 255 complex words at a mean ≈ 18 bits ≈ 255 × 2 × 18 ≈ 9.2k flops; reorder buffer 256 words (single, in-place schedule) to 512 (ping-pong) × 2 × 16 bits ≈ 8.2k to 16.4k flops. Estimated total ≈ 17k to 26k flops for storage only, against 0003's ≈ 31k reference. Pipeline registers in butterflies and multipliers add to it; 0003 found ≈ 2× storage-only in generic synthesis of the other core. The estimate does not close the area budget; synthesis does. |
| Multipliers | 3 general complex multipliers (6 to 12 real, depending on 3/4-multiplier form), none in the trivial stages. |
| Latency | About N for the delay fill plus N for reordering plus pipeline stages: order of 500 clocks, **unmeasured**. |
| Streaming interface | Valid/ready with frame markers wraps the pipeline; back-pressure needs stall of all stage registers (a stall-enable parameter). |
| Power | No spec row; not claimed. |

No spec row is relaxed by this choice.

## Generator parameters implied (input to #29 and #31)

| Parameter | Value / candidates | Notes |
|---|---|---|
| `size` | 256 (fallback 64, stretch 1024) | Power of 4 for pure radix-2²; 64 and 1024 are also powers of 4 and 2^k. |
| `architecture` | `r22sdf` | Others rejected above. |
| `direction` | `forward` | Inverse is stretch; conjugate-trick or twiddle-sign parameter. |
| `output_order` | `natural` (target), `bitrev` (fallback) | Reorder buffer after the output reduction. |
| `input_width` | 16 (I and Q each) | 12 fallback, 18 stretch. |
| `output_width` | 16 | Matches spec rows. |
| `stage_widths` | list of 8 per-stage data widths | Selected by the model study (#31) against the no-overflow vector set and SQNR; starts from growth ≈ 1 bit per radix-2² stage and widens only where the study shows overflow. |
| `twiddle_width` | model-selected, candidates 14 to 18 | Quantisation noise of the twiddles is a model result. |
| `twiddle_rom` | eighth-circle symmetry, combinational | No memory macro. |
| `complex_mult` | `3mult` or `4mult` | Choose from synthesis. |
| `scaling` | fixed schedule via `stage_widths`; no per-stage unconditional shift, no BFP | |
| `rounding` | `convergent` at every width reduction; `truncate` allowed only at the final reduction (0002) | |
| `overflow` | none; model reports the measured no-overflow amplitude range | Saturation is out of scope for v1. |
| `pipeline` | registers per butterfly and per multiplier | Choose against STA. |
| `stall` | enable on all stage registers | For valid/ready back-pressure. |
| `storage` | flops only | No memory inferred. |

## Consequences and open questions

1. SQNR, no-overflow range, area, latency and timing are all unmeasured
   until #31 and the synthesis issues report them.
2. The unverified citations above must not be promoted to fact in later
   records without a primary-source read.
3. Whether the reorder buffer can be single (in-place) rather than ping-pong
   at one sample per clock is a generator design question for #29.
4. 0002 and 0003 still quote dblclockfft reference points; replacing them is
   #27's "Then" step, not done here.
