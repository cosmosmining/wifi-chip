"""Phase 0/2 smoke bench for tt_um_barkerlink.

Hello-world sim behind ``make smoke``: proves the DV path (cocotb 2.x + Icarus +
runner) and that the full chip (SPI bridge + core) resets cleanly with all outputs
in their defined idle state. The functional end-to-end check is test_top (SPI loopback).
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths

SETTLE_NS = 1
CSN_IDLE = 0b0000_0010   # ui_in[1]=CSn held high (SPI idle), others low


@cocotb.test()
async def smoke_reset(dut):
    """Reset behavior and defined idle outputs of the full chip."""
    cocotb.start_soon(Clock(dut.clk, bl_paths.CLK_PERIOD_NS, unit="ns").start())
    dut.ui_in.value = CSN_IDLE
    dut.uio_in.value = 0
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    await Timer(SETTLE_NS, unit="ns")
    assert int(dut.uo_out.value) == 0, f"uo_out not 0 in reset: {dut.uo_out.value}"
    assert int(dut.uio_oe.value) == 0, "uio must be inputs (oe=0)"
    assert int(dut.uio_out.value) == 0

    # Release reset; with SPI idle and no TX started, outputs stay at defined 0.
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 10)
    await Timer(SETTLE_NS, unit="ns")
    assert int(dut.uo_out.value) == 0, f"uo_out not idle 0: {dut.uo_out.value}"
    assert int(dut.uio_oe.value) == 0
    dut._log.info("SMOKE OK: chip resets to defined idle state")


def test_smoke():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("smoke")
    runner = get_runner("icarus")
    runner.build(sources=bl_paths.RTL_ALL, hdl_toplevel=bl_paths.TT_TOPLEVEL,
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    results_xml = runner.test(hdl_toplevel=bl_paths.TT_TOPLEVEL, test_module="test_smoke",
                              test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                              results_xml=str(bdir / "results.xml"))
    total, failed = get_results(results_xml)
    assert failed == 0, f"{failed}/{total} cocotb test(s) failed"


if __name__ == "__main__":
    test_smoke()
