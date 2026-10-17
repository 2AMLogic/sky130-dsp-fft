# sky130-dsp-fft — agent instructions

Open-source canary block: a streaming FFT engine and programmable FIR on
SkyWater sky130, with RTL from an open DSP generator, designed and verified
by AI agents. **Digital.**

- **PDK**: SkyWater sky130 (open PDK, google/skywater-pdk), `sky130_fd_sc_hd`
  standard cells. Digital: cocotb + Icarus, Yosys, OpenROAD. Layout, DRC,
  and LVS through klayout-tools (`klt`).
- **Generated RTL is the point, and the risk.** The datapath is not written
  here. The first decision record chooses the generator — on licence
  (of the tool *and* of its output, which must be compatible with
  Apache-2.0), parameter coverage, numerics control and how it can be
  verified. After that, every committed RTL file must be reproducible from a
  pinned generator commit and a committed parameter file. Hand edits to
  generated RTL are not allowed; a needed change is a generator parameter, a
  wrapper, or an upstream issue on the generator.
- **Numerics are a verification target, not a by-product.** A bit-accurate
  reference model in `sim/` defines the expected output for each fixed-point
  configuration; RTL must match it bit-exactly, and the reference model's
  SQNR against double precision is the accuracy claim. Never call a
  simulated SQNR measured.
- **Scope discipline.** This repo has no `consumes:` edge. It designs no
  memory compiler and no host bus fabric; v1 storage is flop/register based.
  If compiled SRAM is ever adopted, it comes from the sibling that builds it
  by pinned reference (`2am/REUSE.md`), not a second design here.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design. Generator defects go on the generator's own
  tracker, the same way.
- **Verification is the product**: no claim without a testbench. Every timing
  claim names its liberty corner; recorded results are append-only evidence.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **256-point at 50 MHz is the target.** 64-point is the fallback and
  1024-point a stretch. Do not let stretch sizes drive architecture before
  the target closes.
