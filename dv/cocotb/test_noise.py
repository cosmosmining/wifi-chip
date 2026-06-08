"""P1 noise injector + CCA/RSSI (V-NOISE, V-CCA).

Drives barkerlink_core over APB with the on-chip LFSR noise injector enabled and checks
the RX result is bit-accurate to the golden model with the matching LfsrNoise applied
(lockstep under on-chip noise), plus CCA asserts and RSSI is nonzero on a present signal.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS
CTRL, STATUS, TX_FIFO, RX_FIFO, FIFO_LVL, TXCFG, NOISE, CCA_CFG, RSSI = \
    0x04, 0x08, 0x14, 0x18, 0x1C, 0x20, 0x28, 0x2C, 0x30


async def apb_write(dut, addr, data):
    dut.psel.value, dut.penable.value, dut.pwrite.value = 1, 0, 1
    dut.paddr.value, dut.pwdata.value = addr, data
    await ClockCycles(dut.clk, 1)
    dut.penable.value = 1
    await ClockCycles(dut.clk, 1)
    dut.psel.value, dut.penable.value, dut.pwrite.value = 0, 0, 0


async def apb_read(dut, addr):
    dut.psel.value, dut.penable.value, dut.pwrite.value = 1, 0, 0
    dut.paddr.value = addr
    await ClockCycles(dut.clk, 1)
    dut.penable.value = 1
    await Timer(1, unit="ns")
    v = int(dut.prdata.value)
    await ClockCycles(dut.clk, 1)
    dut.psel.value, dut.penable.value = 0, 0
    return v


async def _run(dut, psdu, prob):
    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.rx_chip_ext.value = 0
    dut.rx_chip_valid_ext.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    await apb_write(dut, CCA_CFG, 0x20)
    await apb_write(dut, NOISE, prob)
    await apb_write(dut, TXCFG,
                    (len(psdu) << 16) | (bl.SERVICE_DEFAULT << 8) | bl.SIGNAL_DBPSK_1M)
    # en | rx_en | loopback | noise_en
    await apb_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3) | (1 << 5))
    for b in psdu:
        await apb_write(dut, TX_FIFO, b)
    await apb_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3) | (1 << 5) | (1 << 1))

    for _ in range(20000):
        await ClockCycles(dut.clk, 1)
        st = await apb_read(dut, STATUS)
        if st & (1 << 1) == 0 and (st & 1) == 0:   # tx/rx idle
            await ClockCycles(dut.clk, 50)
            break
    status = await apb_read(dut, STATUS)
    rx_lvl = (await apb_read(dut, FIFO_LVL) >> 8) & 0x1F
    got = bytearray()
    for _ in range(rx_lvl):
        got.append(await apb_read(dut, RX_FIFO) & 0xFF)
    return status, bytes(got)


def _model(psdu, prob):
    stream, _ = bl.tx_dbpsk(psdu)                       # SYNC_LEN=128 (core default)
    if prob:
        stream = bl.LfsrNoise(bl.NOISE_SEED).apply(stream, prob)
    return bl.rx_dbpsk(stream)


@cocotb.test()
async def noise_lockstep_and_cca(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    for prob in (0x0000, 0x0600, 0x1800):
        psdu = bytes(random.Random(prob + 1).getrandbits(8) for _ in range(4))
        status, got = await _run(dut, psdu, prob)
        m = _model(psdu, prob)
        crc_ok = bool(status & (1 << 3))
        assert crc_ok == m.crc_ok, f"prob {prob:#x}: crc rtl {crc_ok} != model {m.crc_ok}"
        if m.crc_ok:
            assert got == m.psdu, f"prob {prob:#x}: {got.hex()} != {m.psdu.hex()}"
        # signal present in loopback -> CCA asserted and RSSI nonzero
        assert status & (1 << 4), f"prob {prob:#x}: CCA not asserted on present signal"
        assert (await apb_read(dut, RSSI)) > 0, "RSSI zero on present signal"
        dut._log.info("noise prob=%#06x crc_ok=%d -> lockstep OK", prob, crc_ok)


def test_noise():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("noise")
    sources = sorted((bl_paths.RTL_DIR / "core").glob("*.v"))
    runner = get_runner("icarus")
    runner.build(sources=sources, hdl_toplevel="barkerlink_core",
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="barkerlink_core", test_module="test_noise",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
