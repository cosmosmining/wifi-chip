# fw/ — RP2040 bring-up & characterization firmware

Lands in **Phase 8**. MicroPython on the TT carrier's RP2040:
- Register poke/peek over SPI (using PeakRDL-generated headers from `regs/`).
- Packet loopback demo (internal loopback path).
- BER sweep script (set `NOISE_PROB`, run loopback, tally errors) producing the
  standalone silicon BER-vs-injection curve compared against `PREDICTIONS.md`.
