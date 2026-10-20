# Target specification

Status: **proposed**, not ratified. Ratification = this spec merged after
review, with the licence ruling in `decisions/0001-generator.md` resolved.
After that, agents may not relax it. Values depart from the README draft only
where a decision record says so; none do yet.

Every timing row binds at a named liberty corner (`decisions/0003`). SQNR is
always a *simulated* figure.

| Parameter | Target | Fallback | Stretch | Verification method |
|---|---|---|---|---|
| FFT size | 256-point complex | 64-point | 1024-point | `sim/` model run per size; RTL bit-exact vs. model (cocotb + Icarus) |
| Direction | forward | forward | forward + inverse (`-i` build) | model vs. RTL, both directions |
| Output order | natural (bit-reversal stage in) | bit-reversed (`-s`) | natural | index check in testbench |
| Size selection | fixed at generation | fixed | runtime-selectable | not runtime in v1; stretch needs a new decision |
| Input / output width | 16-bit I + 16-bit Q | 12-bit | 18-bit | width asserted in the testbench; model bit-exact |
| Internal growth and scaling | generator default: +1 bit at the first stage, then 1 bit per 2 stages (21-bit core output for the target), final reduction to output width in a wrapper (0002) | same | same | model bit-exact; overflow assertion on the vector set |
| Rounding | convergent (0002; the generator's inter-stage rounding is convergent and not selectable) | truncation at the wrapper's final reduction only (0002) | convergent | model bit-exact |
| Overflow | none; vector set must not overflow | same | saturation (new record) | testbench asserts the no-overflow range |
| SQNR vs. double precision | ≥ 60 dB | ≥ 50 dB | ≥ 70 dB | simulated, model vs. double-precision FFT, vector set below |
| FIR taps | 32 | 16 | 64 or decimating | FIR source undecided (see open items); coefficient-by-coefficient model |
| FIR coefficient width | 16-bit | 12-bit | 18-bit | model bit-exact |
| FIR coefficient load | register-bus write (below) | same | same | cocotb register-bus test |
| FIR options | none | none | symmetric, decimating | per-option model |
| Streaming interface | valid/ready handshake, 1 sample/clock, frame start/last markers | `i_ce` enable (generator's native handshake) behind a wrapper | — | cocotb protocol test; back-pressure test |
| Latency | stated after first generation (generator-defined) | — | — | measured in simulation, recorded |
| Control interface | register bus for configuration and coefficients | — | — | cocotb register test |
| Clock | 50 MHz at all `sky130_fd_sc_hd` corners | 25 MHz | 100 MHz | Yosys + OpenROAD STA per corner; binding corner named in the result |
| Area budget | set after first synthesis (estimate ~30k flops, 0003) | — | — | OpenROAD area report |
| Storage | flops | flops | flops | no SRAM macros in the netlist |
| Signoff | DRC + LVS clean | — | — | klayout-tools `klt` |

## SQNR vector set

Reference precision: IEEE double-precision FFT of the same input.
Vectors (frames of N complex samples, 100 frames per set):

1. Uniform random I/Q at 50 % of full scale, seeds 1-10.
2. Uniform random I/Q at 90 % of full scale, seeds 11-20.
3. Single complex tone at bin N/8 + 0.3 (non-coherent), amplitude 50 % and
   90 % of full scale.

SQNR is the reported per-set minimum. The set is part of the spec; changing
it needs a decision record.

## Statistical rows

None. No Monte Carlo or process-variation row exists in v1.

## Open items (not claims)

- **Generator licence ruling** (0001): blocks ratification.
- **FIR source**: no surveyed generator emits a FIR. Needs its own decision
  record before the FIR rows can be verified.
- **Timing closure**: whether the shift-add multiplier mapping closes 50 MHz
  at the binding corner is unknown until synthesis.
- **Flop vs. SRAM crossover**: estimate only (0003); SRAM stays out of scope.
- **Vector set 2 overflows the proposed core**: with the pinned generator at
  its default growth (`-f 256 -n 16 -1 -p 0`), uniform random I/Q at 90 % of
  full scale overflowed internally in 25 of 100 frames (Icarus, 2026-10-20,
  PR #6 review); at 70 % no frame overflowed. The overflow row and set 2
  cannot both hold as written; the amplitude or the growth policy is a spec
  change for the operator, not a result to be fitted.
- **Fallback SQNR vs. fallback width**: the same run gave ≈ 42 dB on set 1
  after a 12-bit output reduction, below the ≥ 50 dB fallback; the two
  fallback cells are not mutually consistent as written.
- **Corner set**: "all corners" is 16 corners including `ss_n40C_1v28`
  (0003), about 7.5× slower than typical, versus the three signoff corners
  open_pdks configures. Which set the clock row means is undecided.
- **PDK pin**: the corner list and every timing figure depend on the
  open_pdks revision; `verification/toolchain.json` (on `main`) is the pin
  this spec should cite once merged.
- **Power**: no row exists. Decide whether v1 reports power (which tool,
  which activity, which corner) or states that it does not.
