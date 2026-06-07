"""Lockstep: bl_crc16 RTL vs the golden model (V-PLCP-HDR)."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS


async def _crc(dut, bits):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.in_valid.value = 0
    dut.in_bit.value = 0
    dut.clear.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    dut.clear.value = 0
    for b in bits:
        dut.in_valid.value = 1
        dut.in_bit.value = b
        await ClockCycles(dut.clk, 1)
    dut.in_valid.value = 0
    await Timer(1, unit="ns")
    return int(dut.crc_out.value)


@cocotb.test()
async def matches_model(dut):
    for seed in (1, 2, 3):
        n = random.Random(seed).choice([32, 48, 64, 100])
        bits = [random.Random(seed * 7).getrandbits(1) for _ in range(n)]
        got = await _crc(dut, bits)
        exp = bl.crc16(bits)
        assert got == exp, f"CRC seed {seed}: got {got:#06x} exp {exp:#06x}"


def test_crc():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("crc16")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_crc16.v"],
                 hdl_toplevel="bl_crc16", timescale=bl_paths.TIMESCALE,
                 build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_crc16", test_module="test_crc",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
