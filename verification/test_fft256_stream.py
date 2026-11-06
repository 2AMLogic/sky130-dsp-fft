"""cocotb bench for the streaming FFT wrapper (issue #21), plus the runner entry point.

Drives `fft256_stream` (rtl/wrapper, around the generated core) with the
sim/vectors.py sets and checks every output component bit-exactly against
sim/fixedpoint_model.py loaded from rtl/params/fft256.params. Also checks the
valid/ready protocol under stalls, a reset mid-frame and back-to-back frames.

Run through `make fft-bench` (verification/README.md). Environment:
  FFT_BENCH_PERTURB=<i>  flip one bit of captured output sample i in every run
                         (negative control: the bench must then fail on
                         MISMATCH_TEXT)
  FFT_BENCH_FRAMES=<n>   frames per vector set in the stalled runs (default 4)
"""

import os
import random
import sys
from pathlib import Path

import numpy as np

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sim"))

import fixedpoint_model  # noqa: E402
import vectors  # noqa: E402

PARAMS = ROOT / "rtl/params/fft256.params"
MISMATCH_TEXT = "stream output differs from bit-accurate model"
LATENCY = 523  # accepted input samples before the first valid output (spec.md, Latency row)
PAD = 3 * 256  # zero samples after the last frame: the tail leaves only while input is accepted
STALL_FRAMES = int(os.environ.get("FFT_BENCH_FRAMES", "4"))
PERTURB = int(os.environ["FFT_BENCH_PERTURB"]) if "FFT_BENCH_PERTURB" in os.environ else None

_MODEL = fixedpoint_model.FixedPointFFT.from_file(PARAMS)
P = _MODEL.p
_cache = {}


def vector_set(name):
    """(input frames as int64 re/im arrays, expected re, expected im, overflow count)."""
    if name not in _cache:
        z = vectors.generate_frames(name, n=P.size, width=P.input_width)
        re, im = z.real.astype(np.int64), z.imag.astype(np.int64)
        model = fixedpoint_model.FixedPointFFT.from_file(PARAMS)  # fresh stats per set
        res = model.run(re, im)
        _cache[name] = (re, im, res.re, res.im, int(sum(model.stats.overflow)))
    return _cache[name]


class Pattern:
    """Per-cycle 'active' decision for in_valid / out_ready."""

    def __init__(self, mode, rng, p=0.5):
        self.mode, self.rng, self.p = mode, rng, p
        self.left, self.on = 0, True

    def next(self):
        if self.mode == "always":
            return True
        if self.mode == "random":
            return self.rng.random() < self.p
        # bursty: alternating runs, active 1..64 cycles, idle 1..300 cycles
        if self.left == 0:
            self.on = not self.on
            self.left = self.rng.randint(1, 64) if self.on else self.rng.randint(1, 300)
        self.left -= 1
        return self.on


def s16(v):
    return int(v) & 0xFFFF


async def reset(dut):
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    dut.in_re.value = 0
    dut.in_im.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


async def drive(dut, re, im, in_pat, out_pat, stop_out=None, stop_in=None, label=""):
    """Stream samples (re, im) in, return (out_re, out_im) lists of transferred outputs.

    Stimulus changes on the falling edge, handshakes are sampled on the rising
    edge. in_valid and its data are held until accepted. Protocol checks run on
    every cycle; they assert with a message naming the cycle and sample index.
    """
    samples = list(zip(re, im)) + [(0, 0)] * PAD
    sent = 0
    holding = False
    outs_re, outs_im = [], []
    filled = False
    cycles = 0
    while True:
        await FallingEdge(dut.clk)
        if not holding and sent < len(samples) and (stop_in is None or sent < stop_in) and in_pat.next():
            dut.in_re.value = s16(samples[sent][0])
            dut.in_im.value = s16(samples[sent][1])
            dut.in_valid.value = 1
            holding = True
        elif not holding:
            dut.in_valid.value = 0
        dut.out_ready.value = int(out_pat.next())
        await RisingEdge(dut.clk)
        cycles += 1
        iv, orr = int(dut.in_valid.value), int(dut.out_ready.value)
        ir, ov = int(dut.in_ready.value), int(dut.out_valid.value)
        first, last = int(dut.out_first.value), int(dut.out_last.value)
        in_fire, out_fire = iv & ir, ov & orr
        n = len(outs_re)
        where = f"{label} cycle {cycles}, accepted inputs {sent}, transferred outputs {n}"
        # wrapper equations (rtl/wrapper/fft256_stream.sv header), against the core's valid
        cv = int(dut.core_valid.value)
        assert ir == (orr | (1 - cv)), f"in_ready != out_ready | ~core_valid ({where})"
        assert ov == (cv & iv), f"out_valid != core_valid & in_valid ({where})"
        if ov:
            if not filled:
                assert sent == LATENCY, f"first out_valid after {sent} accepted inputs, expected {LATENCY} ({where})"
                filled = True
            assert first == (n % P.size == 0), f"out_first wrong ({where})"
            assert last == (n % P.size == P.size - 1), f"out_last wrong ({where})"
        else:
            assert not first and not last, f"out_first/out_last without out_valid ({where})"
        if filled:
            # one input and one output move together: nothing dropped or duplicated
            assert in_fire == out_fire, f"in_fire {in_fire} != out_fire {out_fire} ({where})"
        if out_fire:
            outs_re.append(dut.out_re.value.to_signed())
            outs_im.append(dut.out_im.value.to_signed())
        if in_fire:
            sent += 1
            holding = False
        if stop_out is not None and len(outs_re) >= stop_out:
            break
        if stop_in is not None and sent >= stop_in:
            break
        assert cycles < 200 * len(samples), f"handshake stalled ({where})"
    dut.in_valid.value = 0
    return np.array(outs_re, dtype=np.int64), np.array(outs_im, dtype=np.int64), sent


def check_exact(got_re, got_im, exp_re, exp_im, label):
    """Bit-exact comparison; reports the count and the first differing frame/bin."""
    exp_re, exp_im = exp_re.reshape(-1)[:len(got_re)], exp_im.reshape(-1)[:len(got_im)]
    got_re, got_im = got_re.copy(), got_im.copy()
    if PERTURB is not None and PERTURB < len(got_re):
        got_re[PERTURB] ^= 0x10  # negative control: one wrong output bit
    bad = np.nonzero((got_re != exp_re) | (got_im != exp_im))[0]
    if len(bad):
        i = int(bad[0])
        raise AssertionError(
            f"{MISMATCH_TEXT} ({label}): {len(bad)} of {len(got_re)} samples differ; first at index {i} "
            f"(frame {i // P.size}, bin {i % P.size}): dut=({got_re[i]},{got_im[i]}) "
            f"model=({exp_re[i]},{exp_im[i]})")


async def run_set(dut, name, frames, in_mode, out_mode, seed, p_in=0.5, p_out=0.5):
    re, im, exp_re, exp_im, _ = vector_set(name)
    rng = random.Random(seed)
    await reset(dut)
    n = frames * P.size
    got_re, got_im, _ = await drive(
        dut, re[:frames].reshape(-1), im[:frames].reshape(-1),
        Pattern(in_mode, rng, p_in), Pattern(out_mode, rng, p_out),
        stop_out=n, label=f"{name}/{in_mode}-{out_mode}")
    assert len(got_re) == n
    check_exact(got_re, got_im, exp_re[:frames], exp_im[:frames], f"{name}, in {in_mode}, out {out_mode}")


def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


@cocotb.test()
async def model_no_overflow(dut):
    """The model reports zero overflow components on every vector set."""
    for name in vectors.VECTOR_SETS:
        overflow = vector_set(name)[4]
        assert overflow == 0, f"model overflows on vector set {name}: {overflow} component(s)"


@cocotb.test()
async def back_to_back_full_sets(dut):
    """No stalls: every frame of every vector set, frames back to back."""
    start_clock(dut)
    for name in vectors.VECTOR_SETS:
        await run_set(dut, name, vectors.FRAMES_PER_SET, "always", "always", 1)


@cocotb.test()
async def input_stalls(dut):
    """Random in_valid gaps, out_ready always high."""
    start_clock(dut)
    for k, name in enumerate(vectors.VECTOR_SETS):
        await run_set(dut, name, STALL_FRAMES, "random", "always", 10 + k, p_in=0.6)


@cocotb.test()
async def output_stalls(dut):
    """Random out_ready back-pressure, in_valid always high."""
    start_clock(dut)
    for k, name in enumerate(vectors.VECTOR_SETS):
        await run_set(dut, name, STALL_FRAMES, "always", "random", 20 + k, p_out=0.4)


@cocotb.test()
async def both_stalls_random(dut):
    """Random stalls on both sides at once."""
    start_clock(dut)
    for k, name in enumerate(vectors.VECTOR_SETS):
        await run_set(dut, name, STALL_FRAMES, "random", "random", 30 + k, p_in=0.7, p_out=0.5)


@cocotb.test()
async def long_idle_and_blocked_tail(dut):
    """Long in_valid-low and out_ready-low runs (up to 300 cycles), including the tail."""
    start_clock(dut)
    for k, name in enumerate(vectors.VECTOR_SETS):
        await run_set(dut, name, 2, "bursty", "bursty", 40 + k)


@cocotb.test()
async def reset_mid_frame(dut):
    """Reset during the fill, then mid output frame; the next run is bit-exact from sample 0."""
    start_clock(dut)
    name = "tone50"
    re, im, exp_re, exp_im, _ = vector_set(name)
    rng = random.Random(50)
    flat_re, flat_im = re[:3].reshape(-1), im[:3].reshape(-1)

    # (a) reset in the middle of an input frame, before any output
    await reset(dut)
    o_re, _, sent = await drive(dut, flat_re, flat_im, Pattern("random", rng, 0.8), Pattern("random", rng),
                                stop_in=300, label="reset-a")
    assert len(o_re) == 0 and sent == 300

    # (b) reset after 1.5 output frames; the partial run itself must be exact
    await reset(dut)
    o_re, o_im, _ = await drive(dut, flat_re, flat_im, Pattern("random", rng, 0.8), Pattern("random", rng),
                                stop_out=P.size + P.size // 2, label="reset-b")
    check_exact(o_re, o_im, exp_re[:3], exp_im[:3], "before reset mid-frame")

    # (c) after the reset, markers and data restart: three frames bit-exact
    await run_set(dut, name, 3, "random", "random", 51, p_in=0.8, p_out=0.7)


def run():
    from cocotb_tools.runner import get_results, get_runner

    build_dir = HERE / "sim_build" / "fft256_stream_bench"
    runner = get_runner("icarus")
    runner.build(
        sources=[ROOT / "rtl/wrapper/fft256_stream.sv", *sorted((ROOT / "rtl/generated").glob("*.v"))],
        hdl_toplevel="fft256_stream",
        build_dir=build_dir,
        always=True,
        build_args=["-g2012"],
        timescale=("1ns", "1ps"),
    )
    kw = {}
    if PERTURB is not None:
        kw["test_filter"] = "both_stalls_random"  # negative control: one short, bit-exact test
    results = runner.test(
        hdl_toplevel="fft256_stream",
        test_module="test_fft256_stream",
        build_dir=build_dir,
        test_dir=HERE,
        **kw,
    )
    # The runner does not raise on test failures; gate on the results file.
    passed, failed = get_results(results)
    if failed or not passed:
        sys.exit(f"cocotb: {failed} failed, {passed} passed")


if __name__ == "__main__":
    run()
