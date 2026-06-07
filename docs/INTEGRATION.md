# BarkerLink — Integration & Bring-up Guide (DRAFT)

> _TBD — completed in Phase 1 (interface details) and Phase 8 (silicon bring-up)._

## 1. Bus interface
SPI slave → APB3 → CSRs. SPI mode, framing, and the APB3 timing are specified in Phase 1
alongside the pin map (`SPEC.md` §3.2) and register map (`SPEC.md` §5).

## 2. Register-map usage
Generated from `regs/barkerlink.rdl` (PeakRDL). C/Python headers ship under `fw/`.
Typical flows (poke sequences) — _TBD-P1_:
- Configure mode (DBPSK/DQPSK), enable core.
- TX: write PSDU bytes to TX FIFO; start; poll/IRQ on done.
- RX: enable; wait SFD/header IRQ; drain RX FIFO.
- Characterization: set `NOISE_PROB`, run loopback, read BER counters.

## 3. Bring-up checklist (silicon) — _TBD-P8_
1. Clock + reset sanity; read `ID` register over SPI.
2. Internal loopback of a known packet (`fw/` script).
3. BER sweep vs `NOISE_PROB`; compare to `PREDICTIONS.md`.
4. CCA/RSSI readback under noise-only vs signal.

## 4. Test mode
Scan/test mode is muxed onto `uio` under the test-enable CSR bit — _TBD-P6_.
