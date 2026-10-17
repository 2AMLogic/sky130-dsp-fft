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
| Fixed-point controls | `-n` input width, `-c` coefficient extra bits, `-x` extra internal bits, `-m` maximum width (usage text: wider values "will be truncated"), `-p` hardware multiplies (default none: shift-add), forward/inverse (`-i`), bit reversal on/off (`-s`/`-S`). Width grows 1 bit per two stages by default. Rounding: `rounding.cpp` builds `truncate.v` or `convround.v` (convergent). **No per-stage scaling schedule found**; README: "does not contain any overflow protection" | not applicable | not applicable |
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
