"""Lockstep: bl_dbpsk RTL vs the golden model (V-TX-DBPSK)."""
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
    decode = os.environ.get("BL_DECODE", "0") == "1"
    bits = [random.Random(5 if decode else 6).getrandbits(1) for _ in range(2000)]
    got = await _run_stream(dut, bits)
    exp = bl.dbpsk_decode(bits) if decode else bl.dbpsk_encode(bits)
    diff = next((i for i, (x, y) in enumerate(zip(got, exp)) if x != y), -1)
    assert got == exp, f"decode={decode} first mismatch at bit {diff}"


def _build_and_run(decode: int):
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir(f"dbpsk_d{decode}")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_dbpsk.v"],
                 hdl_toplevel="bl_dbpsk", parameters={"DECODE": decode},
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_dbpsk", test_module="test_dbpsk",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      extra_env={"BL_DECODE": str(decode)},
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0


def test_encode():
    _build_and_run(0)


def test_decode():
    _build_and_run(1)
