# Target specification

Status: **proposed**, not ratified. Ratification = this spec merged after
the EE and market key reviews and an operator ruling. The generator is the
project's own Apache-2.0 generator (`decisions/0001-generator.md`, operator
ruling 2026-10-29, work in #27), so no output-licence question remains.
Rows that depended on a third-party generator's behaviour are generator
parameters, set by #27's architecture record. After ratification, agents may not relax it. Values depart from the README draft only
where a decision record says so: the fallback SQNR (0002), vector set 2
amplitude (0002) and the binding corner set (0003), per the 2026-10-20
operator ruling; the README draft table is updated to match.

The Status column separates rows with simulated evidence on the current
smoke record from targets with none. Ratifying a target row ratifies the
value, not that it is reachable.

Every timing row binds at a named liberty corner (`decisions/0003`). SQNR is
always a *simulated* figure.

| Parameter | Target | Fallback | Stretch | Verification method | Status |
|---|---|---|---|---|---|
| FFT size | 256-point complex | 64-point | 1024-point | `sim/` model run per size; RTL bit-exact vs. model (cocotb + Icarus) | evidenced: bit-exact at 256 on `measurements/fft256-smoke.json`; 64/1024 not run |
| Direction | forward | forward | forward + inverse (generator parameter) | model vs. RTL, both directions | evidenced (forward only); inverse is a stretch, not implemented |
| Output order | natural (generator parameter) | bit-reversed (generator parameter) | natural | index check in testbench | evidenced (natural, 256-point smoke) |
| Size selection | fixed at generation | fixed | runtime-selectable | not runtime in v1; stretch needs a new decision | evidenced by construction (fixed at generation) |
| Input / output width | 16-bit I + 16-bit Q | 12-bit | 18-bit | width asserted in the testbench; model bit-exact | evidenced (16-bit, 256-point smoke) |
| Internal growth and scaling | generator parameters (width growth and scaling schedule). **The schedule is open**: `rtl/params/fft256.params` (`stage_widths=17..24`, `twiddle_width=16`) is a placeholder, and SQNR and overflow evidence is on it only; no accuracy or overflow claim rests on it; final reduction to output width as 0002 states | same | same | model bit-exact; overflow assertion on the vector set | **open target**: schedule not selected |
| Rounding | convergent (0002); a generator parameter | truncation at the final reduction only (0002) | convergent | model bit-exact | evidenced (convergent, bit-exact vs model) |
| Overflow | none; the vector set (amplitudes below) must not overflow, and the model states the measured no-overflow amplitude range | same | saturation (new record) | testbench asserts the no-overflow range | evidenced on the placeholder schedule only (0 overflow components in the smoke record; `make fft-bench` asserts zero model overflow on every vector set); no-overflow amplitude range not yet reported |
| SQNR vs. double precision | ≥ 60 dB at 16-bit output | ≥ 40 dB at 12-bit output | ≥ 70 dB at 18-bit output | simulated, model vs. double-precision FFT, vector set below | evidenced, simulated (min 65.65 dB over the sets in the smoke record, on the placeholder schedule) |
| FIR taps | 32 | 16 | 64 or decimating | FIR source undecided (see open items); coefficient-by-coefficient model | **target, no evidence**: FIR source undecided |
| FIR coefficient width | 16-bit | 12-bit | 18-bit | model bit-exact | **target, no evidence** |
| FIR coefficient load | register-bus write (below) | same | same | cocotb register-bus test | **target, no evidence** |
| FIR options | none | none | symmetric, decimating | per-option model | **target, no evidence** |
| Streaming interface | valid/ready handshake, 1 sample/clock, frame start/last markers | enable-style handshake (generator parameter) behind a wrapper | — | cocotb protocol test; back-pressure test | evidenced, simulated: `make fft-bench` (cocotb, Icarus) checks the wrapper bit-exactly against the model under random and burst `in_valid`/`out_ready` stalls, reset mid-frame and back-to-back frames, with a negative control; simulation only, no timing claim |
| Latency | 523 clocks from first input to first valid output for the 256-point, natural-order, `pipeline=1` configuration with no back-pressure (267 bit-reversed); a generator parameter | — | — | measured in simulation, recorded | evidenced, simulated: 523 clocks first valid output (256-point, natural order, `pipeline=1`, no back-pressure; see row text) |
| Control interface | register bus for configuration and coefficients | — | — | cocotb register test | **target, no evidence** |
| Clock | 50 MHz at the three signoff corners `ss_100C_1v60`, `tt_025C_1v80`, `ff_n40C_1v95`; all 16 shipped corners reported, not binding | 25 MHz, same corners | 100 MHz, same corners | Yosys + OpenROAD STA at each corner; binding corner named in the result | **target, no timing evidence**: no STA yet; reachability unverified |
| Area budget | set after first synthesis (estimate ~30k flops, 0003) | — | — | OpenROAD area report | **target, no budget set**: synthesis exists (see open items) but sets no budget |
| Storage | flops | flops | flops | no SRAM macros in the netlist | evidenced (flops only, no macros in the smoke netlist) |
| Signoff | DRC + LVS clean | — | — | klayout-tools `klt` | **target, no evidence**: no layout exists |

## SQNR vector set

Reference precision: IEEE double-precision FFT of the same input.
Vectors (frames of N complex samples, 100 frames per set):

1. Uniform random I/Q at 50 % of full scale, seeds 1-10.
2. Uniform random I/Q at 70 % of full scale, seeds 11-20.
3. Single complex tone at bin N/8 + 0.3 (non-coherent), amplitude 50 % and
   90 % of full scale.

SQNR is the reported per-set minimum. The set is part of the spec; changing
it needs a decision record.

## Statistical rows

None. No Monte Carlo or process-variation row exists in v1.

## Open items (not claims)

- **Generator**: the project's own Apache-2.0 generator (0001, operator
  ruling 2026-10-29), delivered by #27: a survey of recent pipelined-FFT work,
  then the generator, a bit-accurate model and smoke evidence. Its
  architecture record sets the parameters the rows above name.
- **FIR source**: no surveyed generator emits a FIR. Needs its own decision
  record before the FIR rows can be verified.
- **Timing closure**: whether the generated multiplier mapping closes 50 MHz
  at the binding corner is unknown until synthesis.
- **Flop vs. SRAM crossover**: estimate only (0003); SRAM stays out of scope.
- **Resolved by the 2026-10-20 operator ruling (PR #6), pending the
  ratification gates above**: (1) vector set 2 is 70 % of full scale, because
  uniform random I/Q at 90 % overflowed the proposed core internally in 25 of
  100 frames (Icarus, 2026-10-20 review) and 70 % did not; the `sim/` model
  must report the measured no-overflow amplitude range. The 90 % tone in set 3
  is unaffected as an input amplitude but is only valid if the model shows it
  does not overflow. (2) The fallback SQNR is ≥ 40 dB, matching ≈ 42 dB simulated
  on set 1 at 12-bit output (review run), not ≥ 50 dB. (3) The clock row binds
  at the three signoff corners and reports all 16 (0003).
- **Clarification on the relaxations**: the 50 to 40 dB fallback SQNR and
  the 90 to 70 % vector-set-2 change altered values that were only
  *proposed*, never ratified; no ratified value is relaxed. The 12-bit
  output-quantisation floor (about 42 dB) makes 50 dB unreachable at 12-bit
  output under any growth schedule.
- **PDK pin**: the corner list and every timing figure depend on the
  open_pdks revision; `verification/toolchain.json` (on `main`) is the pin
  this spec should cite once merged.
- **Power**: no row exists. Decide whether v1 reports power (which tool,
  which activity, which corner) or states that it does not.
