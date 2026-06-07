"""End-to-end Phase 2 gate: full-packet TX -> internal loopback -> RX (V-LOOP).

Drives a PSDU into bl_tx, the chip stream loops into bl_rx, and the recovered PSDU /
header / CRC are checked against both the input and the golden model.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS


async def _run_one(dut, psdu, signal=bl.SIGNAL_DBPSK_1M):
    dut.start.value = 0
    dut.tx_wr.value = 0
    dut.tx_wr_data.value = 0
    dut.signal.value = signal
    dut.service.value = bl.SERVICE_DEFAULT
    dut.length.value = len(psdu)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Push the whole PSDU into the TX FIFO (length <= 16 here).
    for b in psdu:
        dut.tx_wr.value = 1
        dut.tx_wr_data.value = b
        await ClockCycles(dut.clk, 1)
    dut.tx_wr.value = 0

    dut.start.value = 1
    await ClockCycles(dut.clk, 1)
    dut.start.value = 0

    got = bytearray()
    # ~50 cycles/logical-bit; logical bits = 192 + len*8 (SYNC+SFD+HDR+CRC+PSDU).
    budget = (192 + len(psdu) * 8) * 60 + 3000
    for _ in range(budget):
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if int(dut.byte_valid.value):
            got.append(int(dut.byte_data.value))
        if int(dut.rx_done.value):
            break
    return bytes(got)


@cocotb.test()
async def loopback_packets(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    for length in (1, 4, 9):
        psdu = bytes(random.Random(length).getrandbits(8) for _ in range(length))
        got = await _run_one(dut, psdu)
        assert int(dut.sfd.value) == 0  # pulse already passed; just sanity read
        assert int(dut.crc_ok.value) == 1, f"len {length}: RTL CRC not OK"
        assert int(dut.rx_length.value) == length, "rx_length mismatch"
        assert got == psdu, f"len {length}: got {got.hex()} exp {psdu.hex()}"
        # cross-check the golden model agrees end-to-end
        res = bl.loopback_dbpsk(psdu, p_chip=0.0)
        assert res.crc_ok and res.psdu == psdu, "model loopback disagrees"
        dut._log.info("loopback OK len=%d", length)


def test_loopback():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("loopback")
    sources = sorted((bl_paths.RTL_DIR / "core").glob("*.v")) + \
        [bl_paths.COCOTB_DIR / "tb_loopback.v"]
    runner = get_runner("icarus")
    runner.build(sources=sources, hdl_toplevel="tb_loopback",
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="tb_loopback", test_module="test_loopback",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
