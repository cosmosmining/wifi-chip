"""barkerlink_core APB-driven end-to-end loopback (V-CSR + V-FIFO + V-LOOP).

Configures the core over APB3, pushes a PSDU via TX_FIFO, starts TX with internal
loopback, then drains RX_FIFO and checks the recovered PSDU + status + IRQ.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS

# register byte addresses
CTRL, STATUS, IRQ_EN, IRQ_STATUS = 0x04, 0x08, 0x0C, 0x10
TX_FIFO, RX_FIFO, FIFO_LVL, TXCFG = 0x14, 0x18, 0x1C, 0x20


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
    val = int(dut.prdata.value)
    await ClockCycles(dut.clk, 1)
    dut.psel.value, dut.penable.value = 0, 0
    return val


@cocotb.test()
async def apb_loopback(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.paddr.value = 0
    dut.pwdata.value = 0
    dut.rx_chip_ext.value = 0
    dut.rx_chip_valid_ext.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    _rng = random.Random(42)
    psdu = bytes(_rng.getrandbits(8) for _ in range(5))

    # enable core + rx + loopback; enable all IRQs
    await apb_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3))
    await apb_write(dut, IRQ_EN, 0x3F)
    await apb_write(dut, TXCFG, (len(psdu) << 16) | (bl.SERVICE_DEFAULT << 8) | bl.SIGNAL_DBPSK_1M)
    for b in psdu:
        await apb_write(dut, TX_FIFO, b)

    # pulse TX_START (keep en|rx_en|loopback set)
    await apb_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3) | (1 << 1))

    # wait until RX FIFO holds the whole PSDU
    got = bytearray()
    for _ in range(20000):
        await ClockCycles(dut.clk, 1)
        lvl = await apb_read(dut, FIFO_LVL)
        rx_lvl = (lvl >> 8) & 0x1F
        if rx_lvl >= len(psdu):
            break

    assert (await apb_read(dut, STATUS)) & (1 << 3), "STATUS.CRC_OK not set"
    irq = await apb_read(dut, IRQ_STATUS)
    assert irq & (1 << 1), "IRQ rx_done not set"
    assert irq & (1 << 2), "IRQ sfd not set"

    for _ in range(len(psdu)):
        got.append(await apb_read(dut, RX_FIFO) & 0xFF)
    assert bytes(got) == psdu, f"got {got.hex()} exp {psdu.hex()}"
    dut._log.info("APB loopback OK: %s", psdu.hex())


def test_core():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("core")
    sources = sorted((bl_paths.RTL_DIR / "core").glob("*.v"))
    runner = get_runner("icarus")
    runner.build(sources=sources, hdl_toplevel="barkerlink_core",
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="barkerlink_core", test_module="test_core",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
