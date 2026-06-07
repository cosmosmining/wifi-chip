"""Lockstep: bl_spreader RTL vs the golden model (V-TX-BARKER)."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS


@cocotb.test()
async def matches_model(dut):
    symbits = [random.Random(11).getrandbits(1) for _ in range(40)]
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.in_valid.value = 0
    dut.in_sym.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    await Timer(1, unit="ns")

    out, idx, guard = [], 0, 0
    need = len(symbits) * 44
    while len(out) < need and guard < need * 2 + 200:
        can_feed = int(dut.ready.value) == 1 and idx < len(symbits)
        dut.in_valid.value = 1 if can_feed else 0
        if can_feed:
            dut.in_sym.value = symbits[idx]
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if can_feed:
            idx += 1
        if int(dut.out_valid.value):
            out.append(int(dut.out_chip.value))
        guard += 1

    exp = bl.oversample(bl.spread_chiprate(symbits))
    assert out == exp, f"spreader mismatch: got {len(out)} chips, exp {len(exp)}"


def test_spreader():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("spreader")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_spreader.v"],
                 hdl_toplevel="bl_spreader", timescale=bl_paths.TIMESCALE,
                 build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_spreader", test_module="test_spreader",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
