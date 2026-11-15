# SPDX-License-Identifier: Apache-2.0
"""Generator tests (unittest; also collected by pytest).

Run from the repo root: python3 -m unittest discover -s rtl/gen/tests -t .
Icarus/Yosys steps are skipped, with a reason, when the tool is not on PATH.
"""
import glob
import os
import shutil
import subprocess
import tempfile
import unittest

from rtl.gen import params as P
from rtl.gen.emit import generate, write_rtl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

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


if __name__ == "__main__":
    unittest.main()
