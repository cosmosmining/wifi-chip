"""BarkerLink RP2040 (MicroPython) host driver.

SPI mode 0, MSB-first. Transaction = 1 command byte + 4 data bytes (32-bit, big-endian):
  cmd[7] = write(1)/read(0), cmd[6:0] = register word address (byte_addr >> 2).
Register map: regs/barkerlink.rdl (see docs/SPEC.md sec 5).
"""
from machine import Pin, SPI  # type: ignore

# byte addresses
ID, CTRL, STATUS, IRQ_EN, IRQ_STATUS = 0x00, 0x04, 0x08, 0x0C, 0x10
TX_FIFO, RX_FIFO, FIFO_LVL, TXCFG, RXSTAT = 0x14, 0x18, 0x1C, 0x20, 0x24
NOISE, CCA_CFG, RSSI, TEST = 0x28, 0x2C, 0x30, 0x34

# CTRL bits
EN, TX_START, RX_EN, LOOPBACK, MODE, NOISE_EN, SOFT_RST = \
    1 << 0, 1 << 1, 1 << 2, 1 << 3, 1 << 4, 1 << 5, 1 << 8


class BarkerLink:
    def __init__(self, spi, csn_pin):
        self.spi = spi
        self.csn = csn_pin
        self.csn.init(Pin.OUT, value=1)

    def _xfer(self, cmd, data):
        tx = bytes([cmd, (data >> 24) & 0xFF, (data >> 16) & 0xFF,
                    (data >> 8) & 0xFF, data & 0xFF])
        rx = bytearray(5)
        self.csn.value(0)
        self.spi.write_readinto(tx, rx)
        self.csn.value(1)
        return (rx[1] << 24) | (rx[2] << 16) | (rx[3] << 8) | rx[4]

    def wr(self, addr, val):
        self._xfer(0x80 | (addr >> 2), val)

    def rd(self, addr):
        return self._xfer(addr >> 2, 0)

    # convenience
    def ident(self):
        return self.rd(ID)

    def rx_level(self):
        return (self.rd(FIFO_LVL) >> 8) & 0x1F

    def tx_frame(self, psdu, signal=0x0A, service=0x00, loopback=True, noise_prob=0):
        ctrl = EN | RX_EN | (LOOPBACK if loopback else 0) | (NOISE_EN if noise_prob else 0)
        self.wr(NOISE, noise_prob & 0xFFFF)
        self.wr(TXCFG, (len(psdu) << 16) | (service << 8) | signal)
        self.wr(CTRL, ctrl)
        for b in psdu:
            self.wr(TX_FIFO, b)
        self.wr(CTRL, ctrl | TX_START)

    def rx_drain(self, n, timeout=200000):
        out = bytearray()
        for _ in range(timeout):
            if self.rx_level() >= 1 and len(out) < n:
                out.append(self.rd(RX_FIFO) & 0xFF)
            if len(out) >= n:
                break
        return bytes(out)


def make(spi_id=0, sck=2, mosi=3, miso=4, csn=5, baud=2_000_000):
    spi = SPI(spi_id, baudrate=baud, polarity=0, phase=0, bits=8,
              sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
    return BarkerLink(spi, Pin(csn))
