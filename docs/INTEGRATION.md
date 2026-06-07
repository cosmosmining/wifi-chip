# BarkerLink — Integration & Bring-up Guide

Interface details are frozen with SPEC.md (Phase 1); silicon bring-up steps are completed
in Phase 8. Register names refer to `regs/barkerlink.rdl` (SPEC §5).

## 1. SPI → APB3 bus interface
SPI slave, **mode 0** (CPOL=0, CPHA=0), **MSB-first**, framed by `CSn` (active low).
Pins: `SCLK=ui_in[0]`, `CSn=ui_in[1]`, `MOSI=ui_in[2]`, `MISO=uo_out[0]` (SPEC §3.2).

Transaction = 1 command byte + 4 data bytes (32-bit registers, big-endian on the wire):
```
cmd[7]   : 1 = write, 0 = read
cmd[6:0] : register address >> 2 (word index, 0x00..0x0D)
write:  MOSI = {cmd, data[31:24], data[23:16], data[15:8], data[7:0]}
read :  MOSI = {cmd, 0,0,0,0};  MISO returns {x, data[31:24]..data[7:0]}
```
The bridge converts each framed transfer into a single APB3 access to the PeakRDL CSR block.

## 2. Register-map usage (host flows)

**TX a frame (DBPSK, loopback or external):**
1. `CTRL.EN=1`; set `CTRL.LOOPBACK` as desired; `TXCFG` = {SIGNAL=0x0A, SERVICE=0x00, LENGTH=N}.
2. Push N bytes to `TX_FIFO` (watch `STATUS.TX_FULL` / `FIFO_LVL.TX_LVL`, ≤16 deep).
3. Pulse `CTRL.TX_START`. Poll `STATUS.TX_BUSY` or wait `IRQ.TX_DONE`; clear via `IRQ_STATUS`.
   (For N>16, refill `TX_FIFO` as it drains; underrun aborts and raises an error IRQ.)

**RX a frame:**
1. `CTRL.RX_EN=1` (and `CTRL.LOOPBACK=1` for self-test).
2. On `IRQ.SFD` / `STATUS.SFD_DET`, read `RXSTAT` (SIGNAL/SERVICE/LENGTH); check `STATUS.CRC_OK`.
3. Drain `RX_FIFO` (`FIFO_LVL.RX_LVL`) until LENGTH octets read; `IRQ.RX_DONE` on completion.

**BER characterization (P1):** `CTRL.LOOPBACK=1`, `CTRL.NOISE_EN=1`, `NOISE.PROB=p`;
loop known PSDUs; tally byte errors vs `model/ber_curve.csv` and `docs/img/ber_dbpsk.png`.

## 3. Bring-up checklist (silicon) — Phase 8
1. Clock + reset; read `ID` (expect MAGIC=0x424C) over SPI.
2. Internal loopback of a known packet (`fw/` script); confirm CRC_OK and payload match.
3. BER sweep vs `NOISE.PROB`; compare to `PREDICTIONS.md`.
4. CCA/RSSI readback under noise-only vs signal.

## 4. Test mode
`TEST.SCAN_EN=1` remaps `uio` to the scan chain (SPEC §3.2 / §13, Phase 6).
