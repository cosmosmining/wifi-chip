"""bl_csr APB3 register access (V-CSR): R/W regs, RO status, W1C IRQ, FIFO pulses."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths

CLK = bl_paths.CLK_PERIOD_NS


async def apb_write(dut, addr, data):
    dut.psel.value = 1
    dut.penable.value = 0
    dut.pwrite.value = 1
    dut.paddr.value = addr
    dut.pwdata.value = data
    await ClockCycles(dut.clk, 1)
    dut.penable.value = 1
    await ClockCycles(dut.clk, 1)
    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0


async def apb_read(dut, addr):
    dut.psel.value = 1
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.paddr.value = addr
    await ClockCycles(dut.clk, 1)
    dut.penable.value = 1
    await Timer(1, unit="ns")
    val = int(dut.prdata.value)
    await ClockCycles(dut.clk, 1)
    dut.psel.value = 0
    dut.penable.value = 0
    return val


@cocotb.test()
async def csr_access(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    # init all inputs
    for sig in ("psel", "penable", "pwrite", "paddr", "pwdata", "irq_set",
                "st_tx_busy", "st_rx_busy", "st_sfd_det", "st_crc_ok", "st_cca",
                "st_tx_full", "st_tx_empty", "st_rx_full", "st_rx_empty",
                "tx_level", "rx_level", "rx_fifo_rdata", "rx_signal",
                "rx_service", "rx_length", "rssi"):
        getattr(dut, sig).value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    pushes, pops = [], []

    async def mon():
        while True:
            await ClockCycles(dut.clk, 1)
            await Timer(1, unit="ns")
            if int(dut.tx_fifo_wr.value):
                pushes.append(int(dut.tx_fifo_wdata.value))
            if int(dut.rx_fifo_rd.value):
                pops.append(1)
    cocotb.start_soon(mon())

    # ID read-only
    assert await apb_read(dut, 0x00) == 0x424C0100, "ID magic/version wrong"

    # CTRL: en|rx_en|loopback|mode|noise_en persist; tx_start/soft_rst are pulses (read 0)
    await apb_write(dut, 0x04, (1 << 0) | (1 << 2) | (1 << 3) | (1 << 5))
    assert await apb_read(dut, 0x04) == 0x2D, f"CTRL readback {await apb_read(dut,0x04):#x}"

    # TXCFG round-trip
    await apb_write(dut, 0x20, (0x0123 << 16) | (0x45 << 8) | 0x0A)
    assert await apb_read(dut, 0x20) == 0x0123450A, "TXCFG readback"

    # NOISE / CCA_CFG / TEST
    await apb_write(dut, 0x28, 0x1234)
    assert await apb_read(dut, 0x28) == 0x1234
    await apb_write(dut, 0x2C, 0x55)
    assert await apb_read(dut, 0x2C) == 0x55
    await apb_write(dut, 0x34, 0x3)
    assert await apb_read(dut, 0x34) == 0x3

    # STATUS / FIFO_LVL / RXSTAT / RSSI read-only from inputs
    dut.st_tx_busy.value = 1
    dut.st_crc_ok.value = 1
    dut.st_rx_empty.value = 1
    dut.tx_level.value = 5
    dut.rx_level.value = 9
    dut.rx_signal.value = 0x14
    dut.rx_length.value = 0x00C8
    dut.rssi.value = 0x7E
    await Timer(1, unit="ns")
    assert await apb_read(dut, 0x08) == ((1 << 8) | (1 << 3) | (1 << 0)), "STATUS"
    assert await apb_read(dut, 0x1C) == ((9 << 8) | 5), "FIFO_LVL"
    assert (await apb_read(dut, 0x24) & 0xFFFF00FF) == ((0x00C8 << 16) | 0x14), "RXSTAT"
    assert await apb_read(dut, 0x30) == 0x7E, "RSSI"

    # W1C IRQ: event sets, write-1 clears
    dut.irq_set.value = 0b000101
    await ClockCycles(dut.clk, 1)
    dut.irq_set.value = 0
    await Timer(1, unit="ns")
    assert await apb_read(dut, 0x10) == 0b000101, "IRQ_STATUS set"
    await apb_write(dut, 0x10, 0b000001)          # clear bit 0
    assert await apb_read(dut, 0x10) == 0b000100, "IRQ_STATUS W1C"

    # TX_FIFO write pulses, RX_FIFO read pulses
    dut.rx_fifo_rdata.value = 0xAB
    for b in (0x11, 0x22, 0x33):
        await apb_write(dut, 0x14, b)
    assert await apb_read(dut, 0x18) == 0xAB, "RX_FIFO read returns head"
    await ClockCycles(dut.clk, 2)
    assert pushes == [0x11, 0x22, 0x33], f"tx_fifo pushes {pushes}"
    assert len(pops) >= 1, "rx_fifo_rd never pulsed"
    dut._log.info("CSR access OK")


def test_csr():
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir("csr")
    runner = get_runner("icarus")
    runner.build(sources=[bl_paths.RTL_DIR / "core" / "bl_csr.v"],
                 hdl_toplevel="bl_csr", timescale=bl_paths.TIMESCALE,
                 build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel="bl_csr", test_module="test_csr",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0
