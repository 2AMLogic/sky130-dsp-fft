# SPDX-License-Identifier: Apache-2.0
"""Generator tests (unittest; also collected by pytest).

Run from the repo root: python3 -m unittest discover -s rtl/gen/tests -t .
Icarus/Yosys steps are skipped, with a reason, when the tool is not on PATH.
"""
import cmath
import glob
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from rtl.gen import params as P  # noqa: E402
from rtl.gen.emit import generate, write_rtl  # noqa: E402

BASE = dict(
    size=256, architecture="r22sdf", direction="forward", input_width=16,
    output_width=16, stage_widths="17,18,19,20,21,22,23,24", twiddle_width=16,
    complex_mult="3mult", rounding="convergent", output_order="natural",
    pipeline=1, stall=1)
WIDTHS = {4: "17,18", 16: "17,18,19,20", 64: "17,18,19,20,21,22",
          256: BASE["stage_widths"]}


def text(**over):
    d = dict(BASE)
    d.update(over)
    if "size" in over and "stage_widths" not in over and d["size"] in WIDTHS:
        d["stage_widths"] = WIDTHS[d["size"]]
    return "".join("%s=%s\n" % kv for kv in d.items())


def gen(**over):
    return generate(dict(P.parse_params(text(**over)), _sha256="0" * 64))


def put(path, body):
    with open(path, "w", newline="") as f:
        f.write(body)


def have(tool):
    return shutil.which(tool) is not None


class Determinism(unittest.TestCase):
    def test_regen_twice_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            pf = os.path.join(d, "p.params")
            put(pf, text())
            outs = []
            for n in ("a", "b"):
                p = P.load_params(pf)
                write_rtl(p, os.path.join(d, n))
                outs.append(os.path.join(d, n))
            fa, fb = (sorted(os.listdir(o)) for o in outs)
            self.assertEqual(fa, fb)
            for f in fa:
                with open(os.path.join(outs[0], f), "rb") as fa_, \
                        open(os.path.join(outs[1], f), "rb") as fb_:
                    self.assertEqual(fa_.read(), fb_.read())

    def test_committed_rtl_matches_fresh_regen(self):
        p = P.load_params(os.path.join(ROOT, "rtl/params/fft256.params"))
        gdir = os.path.join(ROOT, "rtl/generated")
        fresh = generate(p)
        self.assertEqual(sorted(os.listdir(gdir)), sorted(fresh))
        for name, body in fresh.items():
            with open(os.path.join(gdir, name), newline="") as f:
                self.assertEqual(f.read(), body, name)


class Header(unittest.TestCase):
    def test_spdx_first_line_every_file(self):
        for size in (4, 16, 64, 256):
            for order in ("natural", "bitrev"):
                for name, body in gen(size=size, output_order=order).items():
                    self.assertEqual(body.splitlines()[0],
                                     "// SPDX-License-Identifier: Apache-2.0", name)
                    self.assertNotIn("\r", body)


class Variations(unittest.TestCase):
    def test_rounding_differs(self):
        a, b = gen(rounding="convergent"), gen(rounding="truncate")
        self.assertNotEqual(a["fft256.v"], b["fft256.v"])

    def test_output_order_differs(self):
        a, b = gen(output_order="natural"), gen(output_order="bitrev")
        self.assertIn("fft_reorder.v", a)
        self.assertNotIn("fft_reorder.v", b)
        self.assertNotEqual(a["fft256.v"], b["fft256.v"])

    def test_mult_and_stall(self):
        self.assertNotEqual(gen(complex_mult="3mult")["fft256.v"],
                            gen(complex_mult="4mult")["fft256.v"])
        self.assertIn("input en", gen(stall=1)["fft256.v"])
        self.assertNotIn("input en", gen(stall=0)["fft256.v"])


class Invalid(unittest.TestCase):
    def rejects(self, key, **over):
        with self.assertRaises(P.ParamError) as c:
            P.parse_params(text(**over))
        self.assertIn(key, str(c.exception))

    def test_bad_size(self):
        self.rejects("size", size=8, stage_widths="17,18,19")
        self.rejects("size", size=32, stage_widths="17,18,19,20,21")
        self.rejects("size", size=100)

    def test_bad_list_length(self):
        self.rejects("stage_widths", stage_widths="17,18,19")

    def test_bad_values(self):
        self.rejects("rounding", rounding="floor")
        self.rejects("direction", direction="inverse")
        self.rejects("output_width", output_width=30)
        self.rejects("stage_widths", stage_widths="17,16,19,20,21,22,23,24")

    def test_unknown_missing_duplicate(self):
        with self.assertRaises(P.ParamError) as c:
            P.parse_params(text() + "bogus=1\n")
        self.assertIn("bogus", str(c.exception))
        with self.assertRaises(P.ParamError) as c:
            P.parse_params("size=256\n")
        self.assertIn("architecture", str(c.exception))
        with self.assertRaises(P.ParamError) as c:
            P.parse_params(text() + "size=64\n")
        self.assertIn("size", str(c.exception))


def tool_run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


@unittest.skipUnless(have("iverilog") and have("yosys"), "iverilog/yosys not on PATH")
class ToolAcceptance(unittest.TestCase):
    def check(self, **over):
        top = "fft%d" % over.get("size", 256)
        with tempfile.TemporaryDirectory() as d:
            for name, body in gen(**over).items():
                put(os.path.join(d, name), body)
            rc, out = tool_run(["iverilog", "-g2005", "-s", top, "-o",
                                os.path.join(d, "x.vvp")] + sorted(glob.glob(d + "/*.v")), d)
            self.assertEqual(rc, 0, out)
            rc, out = tool_run(["yosys", "-q", "-p", "read_verilog %s/*.v; "
                                "hierarchy -check -top %s" % (d, top)], d)
            self.assertEqual(rc, 0, out)

    def test_sizes(self):
        for size in (4, 16, 64, 256):
            for order in ("natural", "bitrev"):
                with self.subTest(size=size, order=order):
                    self.check(size=size, output_order=order)

    def test_variants(self):
        self.check(complex_mult="4mult", rounding="truncate", pipeline=0, stall=0)


def dft(x):
    n = len(x)
    return [sum(x[j] * cmath.exp(-2j * cmath.pi * j * k / n) for j in range(n))
            for k in range(n)]


@unittest.skipUnless(have("iverilog"), "iverilog not on PATH")
class Smoke(unittest.TestCase):
    """Structural smoke only: output within a loose tolerance of a double DFT.
    Not a bit-exact check (that needs the model, #31) and no accuracy claim."""

    def run_size(self, size, order, pipeline):
        w = WIDTHS[size]
        nframes = 4
        rng = random.Random(7)
        n = size
        data = [complex(rng.randint(-8000, 8000), rng.randint(-8000, 8000))
                for _ in range(nframes * n)]
        with tempfile.TemporaryDirectory() as d:
            for name, body in gen(size=size, output_order=order, pipeline=pipeline,
                                  stage_widths=w).items():
                put(os.path.join(d, name), body)
            with open(os.path.join(d, "in.txt"), "w") as f:
                for z in data:
                    f.write("%d %d\n" % (z.real, z.imag))
            tb = """
module tb;
  reg clk = 0, rst = 1; reg en = 1;
  reg signed [15:0] ir, ii; wire signed [15:0] orr, oi; wire v;
  fft%d dut(.clk(clk), .rst(rst), .en(en), .in_re(ir), .in_im(ii),
            .out_re(orr), .out_im(oi), .out_valid(v));
  integer f, i, a, b, cnt;
  initial begin
    f = $fopen("in.txt", "r"); cnt = 0;
    ir = 0; ii = 0;
    repeat (3) @(posedge clk);
    #1 rst = 0;
    for (i = 0; i < %d; i = i + 1) begin
      a = $fscanf(f, "%%d %%d", ir, ii);
      @(posedge clk); #1;
      if (v && cnt < %d) begin $display("%%0d %%0d", orr, oi); cnt = cnt + 1; end
    end
    for (i = 0; i < %d; i = i + 1) begin
      @(posedge clk); #1;
      if (v && cnt < %d) begin $display("%%0d %%0d", orr, oi); cnt = cnt + 1; end
    end
    $finish;
  end
  always #5 clk = ~clk;
endmodule
""" % (size, nframes * n, 2 * n, 4 * n, 2 * n)
            put(os.path.join(d, "tb.v"), tb)
            rc, out = tool_run(["iverilog", "-g2005", "-s", "tb", "-o", "t.vvp"]
                               + sorted(glob.glob(d + "/*.v")), d)
            self.assertEqual(rc, 0, out)
            rc, out = tool_run(["vvp", "t.vvp"], d)
            self.assertEqual(rc, 0, out)
        vals = [tuple(map(int, l.split())) for l in out.splitlines()
                if l and l[0] in "-0123456789"]
        self.assertEqual(len(vals), 2 * n)
        shift = 2.0 ** (int(w.split(",")[-1]) - 16)
        for fr in range(2):
            ref = dft(data[fr * n:(fr + 1) * n])
            got = vals[fr * n:(fr + 1) * n]
            if order == "bitrev":
                nbits = n.bit_length() - 1
                br = lambda k: int(format(k, "0%db" % nbits)[::-1], 2)
                got = [got[j] for j in sorted(range(n), key=br)]
            for k in range(n):
                e = abs(complex(*got[k]) - ref[k] / shift)
                self.assertLess(e, 4.0, (size, order, fr, k))

    def test_smoke(self):
        for size, order, pipe in ((16, "natural", 1), (16, "bitrev", 0),
                                  (64, "natural", 1), (256, "natural", 1),
                                  (256, "bitrev", 1), (4, "natural", 1)):
            with self.subTest(size=size, order=order, pipeline=pipe):
                self.run_size(size, order, pipe)


if __name__ == "__main__":
    unittest.main()
