"""bl_fifo vs a Python deque reference (V-FIFO): random push/pop, FWFT semantics."""
import collections
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths

CLK = bl_paths.CLK_PERIOD_NS
DEPTH = 16


@cocotb.test()
async def random_ops(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.clear.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    model = collections.deque()
    rng = random.Random(7)
    for _ in range(3000):
        await Timer(1, unit="ns")
        full = len(model) == DEPTH
        empty = len(model) == 0
        assert int(dut.full.value) == (1 if full else 0)
        assert int(dut.empty.value) == (1 if empty else 0)
        assert int(dut.level.value) == len(model)
        if not empty:
            assert int(dut.rd_data.value) == model[0], "head mismatch"

        we, re = rng.random() < 0.55, rng.random() < 0.45
        wd = rng.getrandbits(8)
        dut.wr_en.value = 1 if we else 0
        dut.rd_en.value = 1 if re else 0
        dut.wr_data.value = wd
        do_wr, do_rd = we and not full, re and not empty
        await ClockCycles(dut.clk, 1)
        if do_rd:
            model.popleft()
        if do_wr:
            model.append(wd)
    dut._log.info("FIFO random ops OK; final level=%d", len(model))


def test_fifo():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("fifo")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_fifo.v"],
                 hdl_toplevel="bl_fifo", timescale=bl_paths.TIMESCALE,
                 build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_fifo", test_module="test_fifo",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
