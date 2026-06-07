"""Lockstep: bl_correlator RTL vs the golden model (V-RX-CORR)."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS


def _signed8(v):
    return v - 256 if v >= 128 else v


async def _run(dut, stream):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.in_valid.value = 0
    dut.in_chip.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    syms, corrs = [], []
    for c in stream:
        dut.in_valid.value = 1
        dut.in_chip.value = c
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if int(dut.out_valid.value):
            syms.append(int(dut.out_sym.value))
            corrs.append(_signed8(int(dut.out_corr.value)))
    dut.in_valid.value = 0
    return syms, corrs


@cocotb.test()
async def clean_stream(dut):
    symbits = [random.Random(20).getrandbits(1) for _ in range(60)]
    stream = bl.oversample(bl.spread_chiprate(symbits))
    syms, corrs = await _run(dut, stream)
    assert syms == symbits, "clean despread symbols differ"
    assert all(abs(c) == bl.N_CHIPS * bl.SOFT_MAX for c in corrs), "clean peak != 77"


@cocotb.test()
async def noisy_matches_model(dut):
    symbits = [random.Random(21).getrandbits(1) for _ in range(200)]
    stream = bl.oversample(bl.spread_chiprate(symbits))
    stream = bl.inject_chip_flips(stream, 0.2, random.Random(99))
    syms, corrs = await _run(dut, stream)
    soft = bl.chips_to_soft(bl.downsample_genie(stream))
    exp_sym, exp_corr = bl.despread_genie(soft)
    assert syms == exp_sym, "noisy symbol decisions differ from model"
    assert corrs == exp_corr, "noisy correlations differ from model"


def test_correlator():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("correlator")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_correlator.v"],
                 hdl_toplevel="bl_correlator", timescale=bl_paths.TIMESCALE,
                 build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_correlator", test_module="test_correlator",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
