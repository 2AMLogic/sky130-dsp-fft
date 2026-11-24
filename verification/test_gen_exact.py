"""Bit-exact check of the generated FFT against the fixed-point model (issue #90).

For each configuration below: generate the RTL into a temp dir
(rtl/gen/emit.py), drive it in Icarus with a streaming stimulus and compare
every captured output component against sim/fixedpoint_model.py for the same
parameter file -- exact equality, no tolerance, no permutation, no rescale
(the model's run() returns RTL stream order for both output_order settings).

Grades the six configurations the generator's loose-tolerance smoke test
covered before #90 removed it: sizes 4/16/64/256, natural/bitrev,
pipeline 0/1, with the stimulus shape (4 frames fed, first 2 graded,
random.Random(7)) inherited from it -- plus, since issue #162, the two
equal-width growth schedules it was first reported on ("0002 reference
point" and "half bit/stage" from measurements/schedule-sweep.json), whose
stage-width transitions drop a growth bit mid-pipeline. A directed
stimulus (run_directed) stresses the reduction with near-limit and tie
values, and a standalone multiplier check (run_cmul_unit) pins the single
combined rounding of twiddle fraction plus stage drop against two
successive rounds. Run through `make gen-exact`. Exits non-zero on any
mismatch, naming the configuration, frame and bin.
Environment: GEN_EXACT_PERTURB=<i> flips the LSB of one captured output
component per configuration (negative control, used by gen-exact-negctl).
Environment: GEN_EXACT_ROWS=<file> (e.g. measurements/schedule-sweep.json)
replaces the built-in list with every schedule row recorded in the file's
first record (256-point, natural, pipeline 1) -- the issue #162 acceptance
sweep; nothing in CI sets it.
Environment: GEN_EXACT_PARAMS=<file> (issue #160) restricts the run to the
single (256, natural, pipeline=1) configuration and takes every parameter --
size, widths, output order -- from that parameter file instead of
BASE/STAGE_WIDTHS: the decision-0006 candidate check, whose clean and
perturbed runs are recorded in measurements/fft256-candidate.json.
GEN_EXACT_ROWS and GEN_EXACT_PARAMS are mutually exclusive.
"""

import json
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
from sim.fixedpoint_model import round_shift

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

MISMATCH_TEXT = "generated RTL output differs from bit-accurate model"

# Same configurations the removed generator smoke test exercised, plus the
# two equal-width schedules issue #162 reported (each drops growth bits:
# the 0002 reference point on its stage A's, half bit/stage on its stage
# B's including the final stage). Entries are (size, output_order,
# pipeline, stage_widths, twiddle_width); None takes STAGE_WIDTHS[size]
# and BASE, so the module globals stay a live override for callers.
CONFIGS = ((16, "natural", 1, None, None), (16, "bitrev", 0, None, None),
           (64, "natural", 1, None, None), (256, "natural", 1, None, None),
           (256, "bitrev", 1, None, None), (4, "natural", 1, None, None),
           (256, "natural", 1, "17,18,18,19,19,20,20,21", 16),
           (256, "natural", 1, "17,17,18,18,19,19,20,20", 16))
STAGE_WIDTHS = {4: "17,18", 16: "17,18,19,20", 64: "17,18,19,20,21,22",
                256: "17,18,19,20,21,22,23,24"}
BASE = dict(size=256, architecture="r22sdf", direction="forward",
            input_width=16, output_width=16,
            stage_widths="17,18,19,20,21,22,23,24", twiddle_width=16,
            complex_mult="3mult", rounding="convergent",
            output_order="natural", pipeline=1, stall=1)
# With GEN_EXACT_PARAMS set, only this configuration runs, from that file.
PARAMS_FILE = os.environ.get("GEN_EXACT_PARAMS")
CANDIDATE_CONFIG = (256, "natural", 1, None, None)
NFRAMES_FED = 4     # frames streamed into the DUT
NFRAMES_GRADED = 2  # frames captured and compared

# Directed-stress configurations (issue #162): zero growth drops a bit at
# every stage boundary (first, intermediate and final drops included),
# half bit/stage drops on its twiddled stage B's and the final stage.
DIRECTED = (("16,16,16,16,16,16,16,16", 16),
            ("17,17,18,18,19,19,20,20", 16))

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

# Standalone multiplier bench (issue #162): drives the generated fft_cmul
# combinationally (PIPE=0) vector by vector; the expected values and the
# vector set itself are computed in Python (see run_cmul_unit).
CMUL_TB = """
module tb;
  reg signed [%(w)d-1:0] a_re, a_im;
  reg signed [%(tw)d-1:0] w_re, w_im;
  wire signed [%(ow)d-1:0] p_re, p_im;
  fft_cmul #(.W(%(w)d), .OW(%(ow)d), .TW(%(tw)d), .MULT3(%(m3)d), .PIPE(0)) dut (
      .clk(1'b0), .en(1'b1), .a_re(a_re), .a_im(a_im),
      .w_re(w_re), .w_im(w_im), .p_re(p_re), .p_im(p_im));
  initial begin
%(vecs)s
    $finish;
  end
endmodule
"""


def params_text(size, order, pipeline, widths=None, tw=None):
    d = dict(BASE)
    d.update(size=size, output_order=order, pipeline=pipeline,
             stage_widths=widths if widths is not None else STAGE_WIDTHS[size])
    if tw is not None:
        d["twiddle_width"] = tw
    return "".join("%s=%s\n" % kv for kv in d.items())


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def simulate(size, order, pipeline, data, perturb, widths=None, tw=None):
    """Generate the RTL for one configuration, simulate it in Icarus.

    Returns (model, captured) where captured is the DUT output stream as
    [(out_re, out_im), ...] in stream order. Exits non-zero on a compile or
    simulation failure or on a short capture, so a broken run never counts
    as a passing or "caught" one.
    """
    n = size
    ncap = NFRAMES_GRADED * n
    label = f"size={size} order={order} pipeline={pipeline}"
    if widths is not None:
        label += f" widths={widths} tw={tw}"
    with tempfile.TemporaryDirectory() as d:
        text = (Path(PARAMS_FILE).read_text() if PARAMS_FILE is not None
                else params_text(size, order, pipeline, widths, tw))
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


def run_config(size, order, pipeline, perturb, widths=None, tw=None,
               data=None):
    """One configuration: simulate and compare bit-exactly. True on mismatch.

    `data` overrides the random stimulus (the directed frames); `widths` /
    `tw` override BASE for equal-width schedules. The captured stream is
    compared component for component against the model, so the delayed
    difference branch of every butterfly, the twiddled samples and the
    final stage pair are all graded directly.
    """
    n = size
    ncap = NFRAMES_GRADED * n
    label = f"size={size} order={order} pipeline={pipeline}"
    if widths is not None:
        label += f" widths={widths} tw={tw}"
    if data is None:
        rng = random.Random(7)
        data = [complex(rng.randint(-8000, 8000), rng.randint(-8000, 8000))
                for _ in range(NFRAMES_FED * n)]
    else:
        label += " directed"
    model, vals = simulate(size, order, pipeline, data, perturb, widths, tw)
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


# Directed stress frames for the mid-pipeline reduction (issue #162). The
# residue lists below make the first-stage butterfly outputs cover, on both
# components: sums at the extreme of the input range (65534 and -65536 --
# results that would wrap if the growth bit were narrowed away before
# rounding), and odd sums of every convergent-tie parity and sign at a
# drop-of-one boundary (5 -> 2 even/positive keeps, 7 -> 4 odd/positive
# rounds up, -3 -> -2 even/negative keeps, -1 -> 0 odd/negative rounds up).
# run_directed asserts those properties hold of the frames it feeds.
_DA = [32767, -32768, 32767, -32768, 1, -1, 3, -5,
       32767, -32768, 32767, -32768, 5, -7, -7, 9]
_DB = [32767, -32768, -32768, 32767, 1, -1, 2, 6,
       32767, -32768, 32767, -32768, 2, 4, 3, -5]


def directed_data(n):
    """NFRAMES_FED frames of the directed pattern; frames rotate the
    residues so repeated runs are not four copies of one frame."""
    frames = []
    for f in range(NFRAMES_FED):
        frame = []
        for j in range(n):
            k = (j + 4 * f) % 16
            re = _DA[k] if j < n // 2 else _DB[k]
            im = _DA[(k + 8) % 16] if j < n // 2 else _DB[(k + 8) % 16]
            frame.append(complex(re, im))
        frames.extend(frame)
    return frames


def _assert_directed_properties(data, n):
    """Pin the stress properties the directed frames exist for: butterfly
    outputs past the 16-bit range on both components, and odd values of
    every convergent-tie parity and sign at a drop-of-one boundary."""
    for getter, name in ((lambda z: int(z.real), "re"),
                         (lambda z: int(z.imag), "im")):
        wide = [getter(data[j]) + getter(data[j + n // 2]) for j in range(n // 2)]
        assert max(wide) >= 65534 and min(wide) <= -65536, \
            f"directed {name} frames lost their beyond-16-bit results"
        for want_q_odd, want_pos in ((False, True), (True, True),
                                     (False, False), (True, False)):
            hit = any(v % 2 == 1
                      and (v >> 1) % 2 == (1 if want_q_odd else 0)
                      and (v > 0) == want_pos for v in wide)
            assert hit, (f"directed {name} frames lost the "
                         f"{'odd' if want_q_odd else 'even'}-quotient "
                         f"{'positive' if want_pos else 'negative'} tie")


def run_directed(perturb):
    """Directed stress of the mid-pipeline reduction: the crafted frames
    through the same generate / Icarus / compare path as the random ones.
    True on mismatch."""
    n = 256
    data = directed_data(n)
    _assert_directed_properties(data, n)
    failed = False
    for widths, tw in DIRECTED:
        failed |= run_config(n, "natural", 1,
                             None if perturb is None
                             else perturb % (NFRAMES_GRADED * n),
                             widths, tw, data=data)
    return failed


def _wrap(v, width):
    """Two's-complement wrap to `width` bits, like the model's _check and
    the RTL's bit-slice."""
    return ((v + (1 << (width - 1))) % (1 << width)) - (1 << (width - 1))


def _cmul_expect(a_re, a_im, w_re, w_im, ow, s):
    """Model arithmetic for one multiplier vector: the exact complex
    product, one convergent rounding by s, wrapped to ow bits."""
    out = []
    for acc in (a_re * w_re - a_im * w_im, a_re * w_im + a_im * w_re):
        v = int(round_shift(np.array([acc], dtype=np.int64), s, "convergent")[0])
        out.append(_wrap(v, ow))
    return out


def run_cmul_unit():
    """Standalone check of the reduction-capable fft_cmul the equal-width
    schedules emit (issue #162): the butterfly result stays wide and the
    multiplier performs ONE combined convergent rounding of the twiddle
    fraction plus the stage drop. Fails (exits) on any mismatch with the
    model arithmetic, and first proves the vector set distinguishes that
    single rounding from two successive rounds (drop first, then twiddle
    fraction), so a double-rounding emitter cannot pass silently.
    """
    w, ow, tw = 18, 17, 16
    s = tw - 2 + w - ow  # 15: one drop bit folded into the twiddle fraction
    vectors = []
    # Distinguishing products: P = t*2^15 + 2^14 + 1 with t even rounds up
    # to t+1 in one step, but the +1 dropped first makes the intermediate
    # tie round back down to t. Solved per twiddle so the product lands
    # exactly there (the congruence is on P, so both twiddle signs take the
    # same target); w = 11585 is the TW=16 rounded cos(pi/4) table entry.
    for twiddle in (11585, -11585):
        target = (1 << 14) + 1
        a = (target * pow(twiddle, -1, 1 << 16)) % (1 << 16)
        vectors.append((a, 0, twiddle, 0))
        vectors.append((0, a, 0, twiddle))
    # Convergent ties on the combined boundary (exact half, both parities
    # of the kept bit) and near-limit operands rounded at full width.
    for t, wv in ((2, 5), (1, 3)):
        vectors.append((((2 * t + 1) << 14) // wv, 0, wv, 0))
    vectors.append(((1 << 17) - 1, -(1 << 17), 11585, -11585))
    vectors.append((-(1 << 17), (1 << 17) - 1, -11585, 11585))
    cos, sin = fixedpoint_model.twiddle_table(64, tw)
    for k in (1, 5, 9, 13):
        vectors.append((131071 - 300 * k, -131072 + 271 * k,
                        int(cos[k]), -int(sin[k])))
    for i, (ar, ai, wr, wi) in enumerate(vectors):
        single = _cmul_expect(ar, ai, wr, wi, ow, s)
        double_re = int(round_shift(np.array([round_shift(np.array(
            [ar * wr - ai * wi], dtype=np.int64), w - ow, "convergent")[0]],
            dtype=np.int64), tw - 2, "convergent")[0])
        if single[0] != _wrap(double_re, ow):
            break
    else:
        sys.exit("cmul unit check is vacuous: no vector distinguishes one "
                 "combined rounding from two successive rounds")
    with tempfile.TemporaryDirectory() as d:
        # half bit/stage emits the reduction-capable fft_cmul (a stage B
        # with a drop feeds every multiplier instance's shared module text)
        text = params_text(256, "natural", 1, "17,17,18,18,19,19,20,20", 16)
        files = generate(dict(gen_params.parse_params(text), _sha256="0" * 64))
        for name in ("fft_cmul.v", "fft_rnd.v"):
            (Path(d) / name).write_text(files[name])
        vec_lines = []
        for ar, ai, wr, wi in vectors:
            vec_lines.append(f"    a_re = {ar}; a_im = {ai}; "
                             f"w_re = {wr}; w_im = {wi}; #1;")
            vec_lines.append('    $display("%0d %0d", p_re, p_im);')
        (Path(d) / "tb.v").write_text(CMUL_TB % dict(
            w=w, ow=ow, tw=tw, m3=1, vecs="\n".join(vec_lines)))
        rc, out = run(["iverilog", "-g2005", "-s", "tb", "-o", "t.vvp"]
                      + sorted(str(p) for p in Path(d).glob("*.v")), d)
        if rc:
            sys.exit(f"iverilog failed for the cmul unit check: {out}")
        rc, out = run(["vvp", "t.vvp"], d)
        if rc:
            sys.exit(f"vvp failed for the cmul unit check: {out}")
    vals = [tuple(map(int, l.split())) for l in out.splitlines()
            if l and l[0] in "-0123456789"]
    if len(vals) != len(vectors):
        sys.exit(f"cmul unit check captured {len(vals)} of {len(vectors)} "
                 f"vectors: {out}")
    for i, ((ar, ai, wr, wi), got) in enumerate(zip(vectors, vals)):
        want = _cmul_expect(ar, ai, wr, wi, ow, s)
        if tuple(got) != tuple(want):
            sys.exit(f"{MISMATCH_TEXT}: cmul unit check vector {i} "
                     f"(a=({ar},{ai}) w=({wr},{wi})): dut={got} model={want}")
    print(f"cmul unit check: {len(vectors)} vectors bit-exact vs the "
          f"model's single combined rounding (set includes vectors where "
          f"two successive rounds diverge)")


def run_rows(path, perturb):
    """Every schedule row of the file's first record through the standard
    comparison path (issue #162 acceptance sweep). True on mismatch."""
    rows = json.loads(Path(path).read_text())["records"][0]["candidates"]
    failed = False
    for row in rows:
        print(row["name"], flush=True)
        failed |= run_config(256, "natural", 1,
                             None if perturb is None
                             else perturb % (NFRAMES_GRADED * 256),
                             ",".join(map(str, row["stage_widths"])),
                             row["twiddle_width"])
    if not failed:
        print(f"generated RTL matches the bit-accurate model exactly on all "
              f"{len(rows)} recorded sweep rows of {path}")
    return failed


def main():
    perturb = (int(os.environ["GEN_EXACT_PERTURB"])
               if "GEN_EXACT_PERTURB" in os.environ else None)
    rows_path = os.environ.get("GEN_EXACT_ROWS")
    if rows_path:
        if PARAMS_FILE is not None:
            sys.exit("Set only one of GEN_EXACT_ROWS and GEN_EXACT_PARAMS")
        if run_rows(rows_path, perturb):
            sys.exit(1)
        if perturb is not None:
            sys.exit("perturbed run unexpectedly matched the model "
                     "at every configuration")
        return
    configs = CONFIGS if PARAMS_FILE is None else (CANDIDATE_CONFIG,)
    if PARAMS_FILE is not None:
        print(f"candidate parameter file: {PARAMS_FILE}")
    failed = False
    for size, order, pipeline, widths, tw in configs:
        failed |= run_config(size, order, pipeline,
                             None if perturb is None
                             else perturb % (NFRAMES_GRADED * size),
                             widths, tw)
    if PARAMS_FILE is None:
        failed |= run_directed(perturb)
        if perturb is None:
            run_cmul_unit()
    if failed:
        sys.exit(1)
    if perturb is not None:
        sys.exit("perturbed run unexpectedly matched the model "
                 "at every configuration")
    print(f"generated RTL matches the bit-accurate model exactly at all "
          f"{len(configs)} configurations: "
          + ", ".join(f"size={s} order={o} pipeline={p}" for s, o, p, _, _ in configs))


if __name__ == "__main__":
    main()
