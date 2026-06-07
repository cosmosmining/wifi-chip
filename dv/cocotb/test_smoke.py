"""Phase 0 smoke bench for BarkerLink.

This is the hello-world simulation behind ``make smoke``. It does not exercise
any DSSS functionality yet (none exists in Phase 0); it proves the full DV path
is alive: cocotb 2.x + Icarus + the runner, the TT pin interface, the clock, the
active-low synchronous reset, and that data actually traverses the module
hierarchy (ui_in -> barkerlink_core -> uo_out). Real lockstep datapath benches
arrive in Phase 2.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths

SETTLE_NS = 1  # sample registered outputs one delta past the NBA region


async def _reset(dut):
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    await Timer(SETTLE_NS, unit="ns")


@cocotb.test()
async def smoke_reset_and_datapath(dut):
    """Reset behavior, output defaults, and the registered ui_in->uo_out path."""
    cocotb.start_soon(Clock(dut.clk, bl_paths.CLK_PERIOD_NS, unit="ns").start())
    await _reset(dut)

    # Out of reset every output sits at its defined zero state.
    assert int(dut.uo_out.value) == 0, f"uo_out not 0 in reset: {dut.uo_out.value}"
    assert int(dut.uio_out.value) == 0, "uio_out must be 0 in Phase 0"
    assert int(dut.uio_oe.value) == 0, "uio must be inputs (oe=0) in Phase 0"

    # Release reset; verify the registered passthrough across several values
    # including all-zeros and all-ones so stuck bits would show up.
    dut.rst_n.value = 1
    for val in (0xA5, 0x3C, 0xFF, 0x00, 0x81, 0x7E):
        dut.ui_in.value = val
        await ClockCycles(dut.clk, 1)
        await Timer(SETTLE_NS, unit="ns")
        got = int(dut.uo_out.value)
        assert got == val, f"uo_out 0x{got:02x} != ui_in 0x{val:02x}"

    dut._log.info("SMOKE OK: clock, sync reset, hierarchy, and pins verified")


def test_smoke():
    """Pytest entry point: build with Icarus via the cocotb runner and run."""
    from cocotb_tools.runner import get_runner, get_results

    bdir = bl_paths.build_dir("smoke")
    runner = get_runner("icarus")
    runner.build(
        sources=bl_paths.RTL_ALL,
        hdl_toplevel=bl_paths.TT_TOPLEVEL,
        timescale=bl_paths.TIMESCALE,
        build_dir=str(bdir),
        always=True,
    )
    results_xml = runner.test(
        hdl_toplevel=bl_paths.TT_TOPLEVEL,
        test_module="test_smoke",
        test_dir=str(bl_paths.COCOTB_DIR),
        build_dir=str(bdir),
        results_xml=str(bdir / "results.xml"),  # keep the source tree clean
    )
    total, failed = get_results(results_xml)
    assert failed == 0, f"{failed}/{total} cocotb test(s) failed"


if __name__ == "__main__":
    test_smoke()
