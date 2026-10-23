"""cocotb test for the placeholder adder, plus the runner entry point.

Run through the Makefile (verification/README.md). DUT source is selected by
the DUT environment variable so the negative control reuses the same test.
"""

import os
import random
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

WIDTH = 8
N_VECTORS = 2000
SEED = 20261017

HERE = Path(__file__).resolve().parent
DUTS = {
    "placeholder": HERE.parent / "rtl/placeholder/placeholder_add.sv",
    "mutant": HERE / "mutants/placeholder_add_mutant.sv",
}


def model(a: int, b: int) -> int:
    """Reference model: full-width unsigned sum."""
    return a + b


async def reset(dut):
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    dut.a.value = 0
    dut.b.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


@cocotb.test()
async def random_vectors(dut):
    """Random operands with random valid/ready stalls vs the Python model."""
    rng = random.Random(SEED)
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset(dut)

    # Vectors are biased towards carry-producing operands.
    vectors = [
        (rng.choice([rng.randrange(1 << WIDTH), (1 << WIDTH) - 1]),
         rng.choice([rng.randrange(1 << WIDTH), (1 << WIDTH) - 1]))
        for _ in range(N_VECTORS)
    ]
    expected = [model(a, b) for a, b in vectors]
    got = []
    sent = 0
    cycles = 0

    # Stimulus changes on the falling edge; handshakes are sampled on the rising edge.
    while len(got) < len(expected):
        cycles += 1
        assert cycles < 50 * N_VECTORS, "handshake stalled"
        await RisingEdge(dut.clk)
        in_fire = int(dut.in_valid.value) and int(dut.in_ready.value)
        if int(dut.out_valid.value) and int(dut.out_ready.value):
            got.append(int(dut.sum.value))
        if in_fire:
            sent += 1
        await FallingEdge(dut.clk)
        if int(dut.in_valid.value) and not in_fire:
            pass  # hold operands until accepted
        elif sent < len(vectors) and rng.random() < 0.7:
            dut.a.value, dut.b.value = vectors[sent]
            dut.in_valid.value = 1
        else:
            dut.in_valid.value = 0
        dut.out_ready.value = int(rng.random() < 0.6)

    assert got == expected, "DUT output differs from Python model"


def run():
    from cocotb_tools.runner import get_results, get_runner

    dut_name = os.environ.get("DUT", "placeholder")
    build_dir = HERE / "sim_build" / dut_name
    runner = get_runner("icarus")
    runner.build(
        sources=[DUTS[dut_name]],
        hdl_toplevel="placeholder_add",
        build_dir=build_dir,
        always=True,
        build_args=["-g2012"],
        timescale=("1ns", "1ps"),
    )
    results = runner.test(
        hdl_toplevel="placeholder_add",
        test_module="test_placeholder",
        build_dir=build_dir,
        test_dir=HERE,
    )
    # The runner does not raise on test failures; gate on the results file.
    passed, failed = get_results(results)
    if failed or not passed:
        sys.exit(f"cocotb: {failed} failed, {passed} passed")


if __name__ == "__main__":
    run()
