# 0001 — FFT generator

- **Status**: Proposed. Not ratified: the licence question below needs a
  human ruling (see "Open licence question"). Agents do not ratify it.
- **Date**: 2026-10-17
- **Scope**: the FFT datapath generator. The FIR source is a separate open
  item (see `spec/spec.md`, FIR row; no surveyed candidate generates a FIR).

## Method

Each candidate was cloned at its default-branch head on 2026-10-17 and
read locally. Every cell below is taken from a file in that clone; anything
not read is marked "not checked".

## Candidates

| Criterion | ZipCPU/dblclockfft | ucb-bar/dsptools | ucb-bar/sdf-fft |
|---|---|---|---|
| Commit read | `3378b77d83a98b06184656a5cb9b54e50dfe4485` (2024-04-18) | `fb3b3c6523c3d807316effa1531b7f623d8d9316` (2024-04-29) | `10874b3f1507dc11ebba2567dee65b40bb329dad` (2024-03-13) |
| Generator licence | `sw/fftgen.cpp` header: GNU GPL v3 or later | `LICENSE`: Apache-2.0; README: "Released under the Apache-2.0 license" | `LICENSE`: Apache-2.0 |
| Output licence | Generated files carry an LGPL v3 header (`sw/legal.cpp` lines 52-68, same text as `rtl/fftmain.v`): "License: LGPL, v3". README offers other licences for purchase from Gisselquist Technology, LLC | n/a, no FFT found (`grep -rli fft --include=*.scala` finds nothing) | n/a |
| Architectures | Pipelined FFT, radix-2 style stages (`butterfly.v`, `hwbfly.v`, `qtrstage.v`, `laststage.v`); `-1`/`-k` one sample per clock or one per k clocks (README); `-f` any size (README: "arbitrary sized"); real-FFT mode is a placeholder (usage text) | Chisel DSP library, no FFT generator | Repository holds only `LICENSE`; no source |
| Fixed-point controls | `-n` input width, `-c` coefficient extra bits, `-x` extra internal bits, `-m` maximum width (usage text: wider values "will be truncated"), `-p` hardware multiplies (default none: shift-add), forward/inverse (`-i`), bit reversal on/off (`-s`/`-S`). Width grows 1 bit at the first stage, then 1 bit per two stages by default (`fftgen.cpp`, `nbitsout` block: 16-bit in → 21-bit out at 256 points). Rounding: `rounding.cpp` can emit `truncate.v`, `roundhalfup.v`, `roundfromzero.v` or `convround.v`, but `fftgen` hard-codes convergent (`sw/fftgen.cpp` line 1167, `rounding = RND_CONVERGENT`; **no command-line flag**), and `-m` caps growth with the same convergent rounding at the capped stages rather than truncating. **No per-stage scaling schedule found**; README: "does not contain any overflow protection" | not applicable | not applicable |
| Plain Verilog for Yosys/Icarus | Emits Verilog files (`rtl/*.v`). Acceptance by Yosys and Icarus: **not checked** (needs a run; verified in the smoke test of the RTL-bring-up issue) | not applicable | not applicable |
| Bit-accurate model | `bench/cpp/*_tb.cpp` are Verilator testbenches with C++ helpers (`twoc.cpp`). README: the FFT testbench "doesn't yet have a threshold" for pass/fail. Whether any model is bit-accurate to the RTL: **not checked** | not applicable | not applicable |
| Reproducible from commit + parameters | `fftgen` is a standalone C++ program driven by command-line flags (README: "completely portable C++"), so a flag list is the parameter file. Byte-for-byte determinism: **not checked** until `rtl/regen.sh` runs it twice | not applicable | not applicable |

## Choice (proposed)

**ZipCPU/dblclockfft at `3378b77d83a98b06184656a5cb9b54e50dfe4485`.** It is the
only surveyed candidate that generates an FFT at all, and it covers the
target: 256-point, one sample per clock (`-1`), 16-bit input (`-n 16`),
forward, bit-reversed or natural output, multipliers as shift-add
(`-p 0`, which suits a library with no hard multipliers).

Survey limits: three candidates, found by a name search of the places the
project could plausibly look. Generators not found this way were not
evaluated; the open list below is the place to add them.

## Alternative evaluated: milovanovic/sdf-fft (operator ruling 2026-10-20)

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

What this changes: it removes the licence question if its output is
unencumbered, and offers per-stage scaling that dblclockfft lacks (0002's
"no per-stage schedule"). Its cost is a Scala/Chisel/sbt toolchain with a
multi-repo pin set (against "reproducible from a pinned generator commit and
a committed parameter file"), the SRAM default, and no evidence yet that its
Verilog runs in Icarus/Yosys. It is not chosen; the Choice above stands as
proposed. A smoke run (generate 256-point, Icarus, Yosys, determinism) on a
machine with the toolchain is the next step, in parallel with the counsel
questions on the `dblclockfft` output. Ratification waits on one of the two
clearing.

## Open licence question (needs a human ruling)

The generator is GPLv3, which does not reach its output. The output carries
an LGPLv3 header chosen by the author. This repo is Apache-2.0 and
CLAUDE.md requires the output licence to be compatible. LGPLv3 files can sit
in an Apache-2.0 tree as separately licensed files, but whether that is
"compatible" for a chip design that ships as GDS is a legal judgement
this record does not make. Per the edge case in the issue, the output licence
is recorded as **unclear**, not accepted. Options, for the operator:

1. Accept LGPLv3 for the generated RTL files only, keep their headers
   intact, and state it in `rtl/README.md` and the root README.
2. Buy the alternative licence the README offers.
3. Reject dblclockfft and widen the survey.

## What this choice rules out

- A per-stage scaling schedule from the generator (none found). Scaling is
  therefore a width policy (`-n`, `-x`, `-m`); see 0002.
- A hardware real-FFT mode (placeholder only).
- A FIR from the same tool. The FIR source is undecided.

## Open questions carried to the spec

1. Does the shift-add multiplier mapping close timing at the target corner?
   Answered only by Yosys/OpenROAD per corner; recorded as a risk.
2. Is any model shipped with the generator bit-accurate to its RTL? Unknown;
   `sim/` gets an independent model regardless (CLAUDE.md).
3. Verify with a first `fftgen` run that `-m` truncation behaviour matches
   0002 before any width is frozen.
