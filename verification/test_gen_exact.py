"""Bit-exact check of the generated FFT against the fixed-point model (issue #90).

For each configuration below: generate the RTL into a temp dir
(rtl/gen/emit.py), drive it in Icarus with a streaming stimulus and compare
every captured output component against sim/fixedpoint_model.py for the same
parameter file -- exact equality, no tolerance, no permutation, no rescale
(the model's run() returns RTL stream order for both output_order settings).

Grades the six configurations the generator's loose-tolerance smoke test
covered before #90 removed it: sizes 4/16/64/256, natural/bitrev,
pipeline 0/1, with the stimulus shape (4 frames fed, first 2 graded,
random.Random(7)) inherited from it. Run through `make gen-exact`. Exits
non-zero on any mismatch, naming the configuration, frame and bin.
Environment: GEN_EXACT_PERTURB=<i> flips the LSB of one captured output
component per configuration (negative control, used by gen-exact-negctl).
"""

import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from rtl.gen import params as gen_params
from rtl.gen.emit import generate
from sim import fixedpoint_model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

MISMATCH_TEXT = "generated RTL output differs from bit-accurate model"

# Same configurations the removed generator smoke test exercised:
# (size, output_order, pipeline). STAGE_WIDTHS follows the WIDTHS entries at
# rtl/gen/tests/test_gen.py (one width per radix-2 stage).
CONFIGS = ((16, "natural", 1), (16, "bitrev", 0),
           (64, "natural", 1), (256, "natural", 1),
           (256, "bitrev", 1), (4, "natural", 1))
STAGE_WIDTHS = {4: "17,18", 16: "17,18,19,20", 64: "17,18,19,20,21,22",
                256: "17,18,19,20,21,22,23,24"}
BASE = dict(size=256, architecture="r22sdf", direction="forward",
            input_width=16, output_width=16,
            stage_widths="17,18,19,20,21,22,23,24", twiddle_width=16,
            complex_mult="3mult", rounding="convergent",
            output_order="natural", pipeline=1, stall=1)
NFRAMES_FED = 4     # frames streamed into the DUT
NFRAMES_GRADED = 2  # frames captured and compared

# Streaming testbench moved out of the generator smoke test: feeds
# NFRAMES_FED frames back to back, captures the first NFRAMES_GRADED output
# frames, then drains the pipeline. +perturb=<i> flips the LSB of out_re on
# captured sample i (negative control only).
TB = """
module tb;
  reg clk = 0, rst = 1; reg en = 1;
  reg signed [15:0] ir, ii; wire signed [15:0] orr, oi; wire v;
  fft%(size)d dut(.clk(clk), .rst(rst), .en(en), .in_re(ir), .in_im(ii),
            .out_re(orr), .out_im(oi), .out_valid(v));
  integer f, i, a, cnt, perturb, tre, tim;
  initial begin
    if (!$value$plusargs("perturb=%%d", perturb)) perturb = -1;
    f = $fopen("in.txt", "r"); cnt = 0;
    ir = 0; ii = 0;
    repeat (3) @(posedge clk);
    #1 rst = 0;
    for (i = 0; i < %(nfeed)d; i = i + 1) begin
      a = $fscanf(f, "%%d %%d", ir, ii);
      @(posedge clk); #1;
      if (v && cnt < %(ncap)d) begin
        tre = orr; tim = oi;
        if (cnt == perturb) tre = tre ^ 1;
        $display("%%0d %%0d", tre, tim); cnt = cnt + 1;
      end
    end
    for (i = 0; i < %(ndrain)d; i = i + 1) begin
      @(posedge clk); #1;
      if (v && cnt < %(ncap)d) begin
        tre = orr; tim = oi;
        if (cnt == perturb) tre = tre ^ 1;
        $display("%%0d %%0d", tre, tim); cnt = cnt + 1;
      end
    end
    $finish;
  end
  always #5 clk = ~clk;
endmodule
"""


def params_text(size, order, pipeline):
    d = dict(BASE)
    d.update(size=size, output_order=order, pipeline=pipeline,
             stage_widths=STAGE_WIDTHS[size])
    return "".join("%s=%s\n" % kv for kv in d.items())


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def simulate(size, order, pipeline, data, perturb):
    """Generate the RTL for one configuration, simulate it in Icarus.

    Returns (model, captured) where captured is the DUT output stream as
    [(out_re, out_im), ...] in stream order. Exits non-zero on a compile or
    simulation failure or on a short capture, so a broken run never counts
    as a passing or "caught" one.
    """
    n = size
    ncap = NFRAMES_GRADED * n
    label = f"size={size} order={order} pipeline={pipeline}"
    with tempfile.TemporaryDirectory() as d:
        text = params_text(size, order, pipeline)
        pf = Path(d) / "p.params"
        pf.write_text(text)
        model = fixedpoint_model.FixedPointFFT.from_file(pf)
        for name, body in generate(dict(gen_params.parse_params(text),
                                        _sha256=model.p.sha256)).items():
            (Path(d) / name).write_text(body)
        (Path(d) / "in.txt").write_text(
            "".join("%d %d\n" % (int(z.real), int(z.imag)) for z in data))
        (Path(d) / "tb.v").write_text(
            TB % dict(size=size, nfeed=NFRAMES_FED * n, ncap=ncap,
                      ndrain=NFRAMES_FED * n))
        rc, out = run(["iverilog", "-g2005", "-s", "tb", "-o", "t.vvp"]
                      + sorted(str(p) for p in Path(d).glob("*.v")), d)
        if rc:
            sys.exit(f"iverilog failed for {label}: {out}")
        args = ["vvp", "t.vvp"] + ([f"+perturb={perturb}"]
                                   if perturb is not None else [])
        rc, out = run(args, d)
        if rc:
            sys.exit(f"vvp failed for {label}: {out}")
    vals = [tuple(map(int, l.split())) for l in out.splitlines()
            if l and l[0] in "-0123456789"]
    if len(vals) != ncap:
        sys.exit(f"Icarus run captured {len(vals)} of {ncap} output samples "
                 f"for {label}: {out}")
    return model, vals


def run_config(size, order, pipeline, perturb):
    """One configuration: simulate and compare bit-exactly. True on mismatch."""
    n = size
    ncap = NFRAMES_GRADED * n
    label = f"size={size} order={order} pipeline={pipeline}"
    rng = random.Random(7)
    data = [complex(rng.randint(-8000, 8000), rng.randint(-8000, 8000))
            for _ in range(NFRAMES_FED * n)]
    model, vals = simulate(size, order, pipeline, data, perturb)
    frames_re = np.array([int(z.real) for z in data[:ncap]],
                         dtype=np.int64).reshape(NFRAMES_GRADED, n)
    frames_im = np.array([int(z.imag) for z in data[:ncap]],
                         dtype=np.int64).reshape(NFRAMES_GRADED, n)
    res = model.run(frames_re, frames_im)
    dut_re = np.array([v[0] for v in vals], dtype=np.int64).reshape(NFRAMES_GRADED, n)
    dut_im = np.array([v[1] for v in vals], dtype=np.int64).reshape(NFRAMES_GRADED, n)
    # No permutation, no rescale: run() returns RTL stream order for both
    # output_order settings, so the captured stream is compared directly.
    bad = np.nonzero((dut_re.reshape(-1) != res.re.reshape(-1))
                     | (dut_im.reshape(-1) != res.im.reshape(-1)))[0]
    if len(bad):
        i = int(bad[0])
        fr, k = divmod(i, n)
        print(f"{MISMATCH_TEXT}: {label}: {len(bad)} of {ncap} samples differ; "
              f"first at index {i} (frame {fr}, bin {k}): "
              f"dut=({dut_re[fr, k]},{dut_im[fr, k]}) "
              f"model=({res.re[fr, k]},{res.im[fr, k]})", file=sys.stderr)
        return True
    print(f"{label}: {ncap} samples bit-exact vs the model "
          f"(total_shift={res.total_shift})")
    return False


def main():
    perturb = (int(os.environ["GEN_EXACT_PERTURB"])
               if "GEN_EXACT_PERTURB" in os.environ else None)
    failed = False
    for size, order, pipeline in CONFIGS:
        failed |= run_config(size, order, pipeline,
                             None if perturb is None
                             else perturb % (NFRAMES_GRADED * size))
    if failed:
        sys.exit(1)
    if perturb is not None:
        sys.exit("perturbed run unexpectedly matched the model "
                 "at every configuration")
    print(f"generated RTL matches the bit-accurate model exactly at all "
          f"{len(CONFIGS)} configurations: "
          + ", ".join(f"size={s} order={o} pipeline={p}" for s, o, p in CONFIGS))


if __name__ == "__main__":
    main()
