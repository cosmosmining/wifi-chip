"""Lockstep: bl_scrambler RTL vs the golden model (V-TX-SCRAM).

Builds the module twice (TX scramble, RX descramble). A single cocotb test selects the
reference direction from BL_DESCRAMBLE so no per-testcase filtering is needed.
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS


async def _run_stream(dut, bits):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.clear.value = 0
    dut.in_valid.value = 0
    dut.in_bit.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    out = []
    for b in bits:
        dut.in_valid.value = 1
        dut.in_bit.value = b
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if int(dut.out_valid.value):
            out.append(int(dut.out_bit.value))
    dut.in_valid.value = 0
    return out


@cocotb.test()
async def matches_model(dut):
    descramble = os.environ.get("BL_DESCRAMBLE", "0") == "1"
    bits = [random.Random(1 if descramble else 2).getrandbits(1) for _ in range(2000)]
    got = await _run_stream(dut, bits)
    if descramble:
        exp = bl.Descrambler(bl.SCRAMBLER_SEED).descramble(bits)
    else:
        exp = bl.Scrambler(bl.SCRAMBLER_SEED).scramble(bits)
    diff = next((i for i, (x, y) in enumerate(zip(got, exp)) if x != y), -1)
    assert got == exp, f"descramble={descramble} first mismatch at bit {diff}"


def _build_and_run(descramble: int):
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir(f"scrambler_d{descramble}")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_scrambler.v"],
                 hdl_toplevel="bl_scrambler",
                 parameters={"DESCRAMBLE": descramble},
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_scrambler", test_module="test_scrambler",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      extra_env={"BL_DESCRAMBLE": str(descramble)},
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0


def test_scramble():
    _build_and_run(0)


def test_descramble():
    _build_and_run(1)
