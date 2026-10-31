# 0001 — FFT generator

- **Status**: Proposed. Not ratified: agents do not ratify it. The generator
  choice follows the operator ruling of 2026-10-29 (see "Decision"); the
  licence question that blocked the earlier proposal no longer arises.
- **Date**: 2026-10-17
- **Scope**: the FFT datapath generator. The FIR source is a separate open
  item (see `spec/spec.md`, FIR row; no surveyed candidate generates a FIR).

## Decision (operator ruling 2026-10-29)

**The block uses its own Apache-2.0 FFT generator**, written in this project.
It does not use ZipCPU/dblclockfft and does not use milovanovic/sdf-fft. The
ruling (rjwalters, attended `fleet:decide` round 20261029-r2-holds, question
h14) asks that the generator take advantage of recent FFT improvements. The
work is issue #27: a survey of recent pipelined-FFT work first, then the
generator, a bit-accurate model and smoke evidence. The generator's
architecture, its pinned location and its parameter file are recorded by the
architecture record that #27 produces; this record does not fix them.

This supersedes the 2026-10-20 ruling's two paths (counsel on the LGPLv3
output of dblclockfft, or an sdf-fft evaluation). Because the generator and
its output are written here under Apache-2.0, no output-licence question
remains. This is not ratification: the spec still needs the EE and market
key reviews and then the operator.

The survey, the dblclockfft reading and the sdf-fft evaluation below are
kept as history. They are the evidence behind the ruling, not the current
choice.

## Method (survey history)

Each candidate was cloned at its default-branch head on 2026-10-17 and
read locally. Every cell below is taken from a file in that clone; anything
not read is marked "not checked".

## Candidates (history)

| Criterion | ZipCPU/dblclockfft (not chosen: LGPLv3 output) | ucb-bar/dsptools | ucb-bar/sdf-fft |
|---|---|---|---|
| Commit read | `3378b77d83a98b06184656a5cb9b54e50dfe4485` (2024-04-18) | `fb3b3c6523c3d807316effa1531b7f623d8d9316` (2024-04-29) | `10874b3f1507dc11ebba2567dee65b40bb329dad` (2024-03-13) |
| Generator licence | `sw/fftgen.cpp` header: GNU GPL v3 or later | `LICENSE`: Apache-2.0; README: "Released under the Apache-2.0 license" | `LICENSE`: Apache-2.0 |
| Output licence | Generated files carry an LGPL v3 header (`sw/legal.cpp` lines 52-68, same text as `rtl/fftmain.v`): "License: LGPL, v3". README offers other licences for purchase from Gisselquist Technology, LLC | n/a, no FFT found (`grep -rli fft --include=*.scala` finds nothing) | n/a |
| Architectures | Pipelined FFT, radix-2 style stages (`butterfly.v`, `hwbfly.v`, `qtrstage.v`, `laststage.v`); `-1`/`-k` one sample per clock or one per k clocks (README); `-f` any size (README: "arbitrary sized"); real-FFT mode is a placeholder (usage text) | Chisel DSP library, no FFT generator | Repository holds only `LICENSE`; no source |
| Fixed-point controls | `-n` input width, `-c` coefficient extra bits, `-x` extra internal bits, `-m` maximum width (usage text: wider values "will be truncated"), `-p` hardware multiplies (default none: shift-add), forward/inverse (`-i`), bit reversal on/off (`-s`/`-S`). Width grows 1 bit at the first stage, then 1 bit per two stages by default (`fftgen.cpp`, `nbitsout` block: 16-bit in → 21-bit out at 256 points). Rounding: `rounding.cpp` can emit `truncate.v`, `roundhalfup.v`, `roundfromzero.v` or `convround.v`, but `fftgen` hard-codes convergent (`sw/fftgen.cpp` line 1167, `rounding = RND_CONVERGENT`; **no command-line flag**), and `-m` caps growth with the same convergent rounding at the capped stages rather than truncating. **No per-stage scaling schedule found**; README: "does not contain any overflow protection" | not applicable | not applicable |
| Plain Verilog for Yosys/Icarus | Emits Verilog files (`rtl/*.v`). Acceptance by Yosys and Icarus: **not checked** (needs a run; verified in the smoke test of the RTL-bring-up issue) | not applicable | not applicable |
| Bit-accurate model | `bench/cpp/*_tb.cpp` are Verilator testbenches with C++ helpers (`twoc.cpp`). README: the FFT testbench "doesn't yet have a threshold" for pass/fail. Whether any model is bit-accurate to the RTL: **not checked** | not applicable | not applicable |
| Reproducible from commit + parameters | `fftgen` is a standalone C++ program driven by command-line flags (README: "completely portable C++"), so a flag list is the parameter file. Byte-for-byte determinism: **not checked** until `rtl/regen.sh` runs it twice | not applicable | not applicable |

## Earlier proposal: ZipCPU/dblclockfft (not chosen: LGPLv3 output)

The earlier proposal of this record was `ZipCPU/dblclockfft` at
`3378b77d83a98b06184656a5cb9b54e50dfe4485`: the only surveyed candidate that
generates an FFT at all, covering 256-point, one sample per clock (`-1`),
16-bit input (`-n 16`), forward, with shift-add multipliers (`-p 0`). It is
**not chosen**, because its generated files carry an LGPLv3 header and this
repo requires output compatible with Apache-2.0. The numbers measured from it
(21-bit core output, convergent rounding, overflow behaviour) remain useful
as a reference point for #27's survey and are cited where 0002 and 0003 use
them.

Survey limits: three candidates, found by a name search of the places the
project could plausibly look. Generators not found this way were not
evaluated.

## Alternative evaluated: milovanovic/sdf-fft (not chosen; operator ruling 2026-10-20)

Source-level read only, no build or run. Cloned at default-branch head
`d1978a9b284ee1bd4e09ab3fa58e223cd15a5ae9` (committed 2023-07-05, as cloned
2026-10-23). Not built: it needs sbt, Verilator and a chipyard-era
submodule set (`scripts/init_submodules_and_build_sbt.sh` pins `dsptools`,
`rocket-dsp-utils`, `cde`, `rocket-chip`, `firesim`), which is not installed
here.

| Criterion | milovanovic/sdf-fft |
|---|---|
| Generator licence | `LICENSE`: Apache-2.0; `src/main/scala/SDFFFTParams.scala` carries `SPDX-License-Identifier: Apache-2.0` |
| Output licence | Not checked. The emitted Verilog comes from Chisel/FIRRTL elaboration of Apache-2.0 sources; whether the emitter or its dependencies add any notice to the output was not checked |
| Architectures | Single-path delay feedback, radix-2 and radix-2²; DIT or DIF; streaming valid/ready (`Decoupled`) with `lastIn`/`lastOut`; optional bit-reverse ping-pong module (`useBitReverse`); optional run-time size (`runTime`, `runTimeR22`) and direction (`fftDirReg`) |
| Fixed-point controls | Per-stage data types (`protoIQstages`), per-stage growth (`expandLogic`), `keepMSBorLSB`, `trimType` (eleven trim/rounding types per doc), twiddle type, 3- or 4-multiplier complex multiply, `numAddPipes`/`numMulPipes`, optional `overflowReg` status. Finer numerics control than dblclockfft |
| Storage | Delay lines above `minSRAMdepth` are emitted as SRAM (`fft_mem.conf` lists the blocks), and `useBitReverse` adds SRAM. v1 is flop-only (CLAUDE.md): this would need `minSRAMdepth` set so no memory is inferred, and the bit-reverse buffer checked. Not checked |
| Plain Verilog for Yosys/Icarus | Not checked (generator not run) |
| Bit-accurate model | Test suite includes `Radix22SQNRSpec`/`Radix2SQNRSpec` against a `DspReal` golden model; whether any model is bit-accurate to the RTL: not checked |
| Reproducible from commit + parameters | Parameters are a Scala `FFTParams` case class plus `make gen_all_*`; the toolchain pins are submodule commits in a script, not a lockfile. Byte-for-byte determinism: not checked |
| Maintenance | Last commit on the default branch read is 2023-07-05; chipyard 1.9.1 era |

What this showed: per-stage scaling that dblclockfft lacks, against a
Scala/Chisel/sbt toolchain with a multi-repo pin set, an SRAM default, and no
evidence that its Verilog runs in Icarus/Yosys. It was not built or run, and
its output licence was never checked. The 2026-10-29 ruling does not choose
it; its per-stage numerics controls are input to #27's survey.

## Licence question (closed by the 2026-10-29 ruling)

The earlier version of this record left open whether LGPLv3 output from
dblclockfft is compatible with this Apache-2.0 repo. The ruling above closes
it by not using that output: the generator and everything it emits are
written here under Apache-2.0. No counsel question, alternative-licence
purchase or LGPL exception is needed.

## What this choice leaves open

The generator does not exist yet, so nothing is ruled in or out by it.
Carried to #27 and its architecture record:

1. Which pipelined-FFT architecture, rounding and per-stage scaling policy
   the survey supports; 0002 and 0003 state targets, not generator behaviour.
2. Whether the multiplier mapping closes timing at the target corner
   (answered only by Yosys/OpenROAD per corner; recorded as a risk).
3. The bit-accurate model in `sim/` is independent of the generator
   regardless (CLAUDE.md), and RTL must match it bit-exactly.
4. The FIR source is a separate open item (see `spec/spec.md`).
5. Reproducibility: every committed RTL file must come from a pinned commit
   of the generator and a committed parameter file (CLAUDE.md).
