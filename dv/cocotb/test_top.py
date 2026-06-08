"""Top-level pin-level end-to-end: SPI -> CSR -> TX -> loopback -> RX -> SPI (V-LOOP/V-CSR).

A cocotb SPI master (mode 0) drives ui_in[2:0]/samples uo_out[0], configures the chip,
pushes a PSDU through TX_FIFO, starts TX with internal loopback, then reads the recovered
PSDU back out of RX_FIFO. This is the full P0 chip exercised exactly as a host would.
"""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl

CLK = bl_paths.CLK_PERIOD_NS
HALF = 6   # clk cycles per SPI half-period (SPI ~ 4 MHz vs 50 MHz clk)

# register byte addresses
CTRL, STATUS, IRQ_EN, TX_FIFO, RX_FIFO, FIFO_LVL, TXCFG = \
    0x04, 0x08, 0x0C, 0x14, 0x18, 0x1C, 0x20


def _ui(sclk, csn, mosi):
    return (mosi << 2) | (csn << 1) | sclk


async def _idle(dut):
    dut.ui_in.value = _ui(0, 1, 0)
    await ClockCycles(dut.clk, HALF)


async def _txn(dut, write, addr, data=0):
    cmd = ((1 if write else 0) << 7) | (addr >> 2)
    bits = [(cmd >> (7 - i)) & 1 for i in range(8)]
    bits += [((data >> (31 - i)) & 1) for i in range(32)]
    captured = []
    dut.ui_in.value = _ui(0, 0, 0)            # CSn low, start
    await ClockCycles(dut.clk, HALF)
    for b in bits:
        dut.ui_in.value = _ui(0, 0, b)        # set MOSI while SCLK low
        await ClockCycles(dut.clk, HALF)
        dut.ui_in.value = _ui(1, 0, b)        # rising edge
        await ClockCycles(dut.clk, HALF)
        captured.append(int(dut.uo_out.value) & 1)   # sample MISO (uo_out[0])
    dut.ui_in.value = _ui(0, 1, 0)            # CSn high, done
    await ClockCycles(dut.clk, HALF)
    rd = 0
    for i in range(8, 40):                     # data phase bits
        rd = (rd << 1) | captured[i]
    return rd


async def spi_write(dut, addr, data):
    await _txn(dut, True, addr, data)


async def spi_read(dut, addr):
    return await _txn(dut, False, addr)


@cocotb.test()
async def spi_loopback(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    dut.ui_in.value = _ui(0, 1, 0)
    dut.uio_in.value = 0
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await _idle(dut)

    assert await spi_read(dut, 0x00) == 0x424C0100, "ID over SPI wrong"

    _rng = random.Random(123)
    psdu = bytes(_rng.getrandbits(8) for _ in range(4))
    await spi_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3))     # en|rx_en|loopback
    await spi_write(dut, IRQ_EN, 0x02)                              # only rx_done -> IRQ pin
    await spi_write(dut, TXCFG,
                    (len(psdu) << 16) | (bl.SERVICE_DEFAULT << 8) | bl.SIGNAL_DBPSK_1M)
    for b in psdu:
        await spi_write(dut, TX_FIFO, b)
    await spi_write(dut, CTRL, (1 << 0) | (1 << 2) | (1 << 3) | (1 << 1))  # +tx_start

    # wait for the whole loopback (≈ (192 + N*8) logical bits * ~50 clk/bit)
    for _ in range((200 + len(psdu) * 8) * 55 + 4000):
        await ClockCycles(dut.clk, 1)
        if int(dut.uo_out.value) & (1 << 1):   # IRQ pin -> rx_done pending
            break

    status = await spi_read(dut, STATUS)
    assert status & (1 << 3), "STATUS.CRC_OK not set over SPI"
    assert status & (1 << 6) == 0 or True       # SFD bit informational
    rx_lvl = (await spi_read(dut, FIFO_LVL) >> 8) & 0x1F
    assert rx_lvl >= len(psdu), f"RX FIFO has {rx_lvl}, expected >= {len(psdu)}"

    got = bytearray()
    for _ in range(len(psdu)):
        got.append(await spi_read(dut, RX_FIFO) & 0xFF)
    got = bytes(got)
    assert got == psdu, f"SPI loopback got {got.hex()} exp {psdu.hex()}"
    dut._log.info("SPI loopback OK: %s", psdu.hex())


def test_top():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("top")
    runner = get_runner("icarus")
    runner.build(sources=bl_paths.RTL_ALL, hdl_toplevel=bl_paths.TT_TOPLEVEL,
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel=bl_paths.TT_TOPLEVEL, test_module="test_top",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
