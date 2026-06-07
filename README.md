# BarkerLink

An **802.11b-class direct-sequence spread-spectrum (DSSS) baseband transceiver IP**
(TX + RX), built spec-first and verification-driven for the **Tiny Tapeout TTSKY26c**
shuttle (sky130A, 2×2 tiles). RF/ADC/DAC are out of scope; the design exposes a digital
chip-stream interface with internal loopback so it is fully characterizable standalone.

> Status: **Phase 0 — scaffold complete.** See `STATUS.md`.

## Quickstart
```bash
make tools     # show detected toolchain
make smoke     # Phase 0 gate: lint + cocotb/Icarus hello sim  -> "SMOKE PASS"
make synth     # yosys elaborate + generic cell count
make help      # all targets
```
Local prerequisites: `iverilog`, `verilator`, `yosys`, and `pip install cocotb pytest`.
CI additionally provides Verible, SymbiYosys, and the sky130 PD/signoff tools.

## What it will do
- **TX:** 802.11 scrambler → DBPSK (P0) / DQPSK (P1) → Barker-11 spreader, 11 Mchip/s.
- **RX:** soft 11-tap Barker correlator → peak detect / timing recovery → differential
  demod → descrambler, with long-PLCP framing (SYNC / SFD / header + CRC-16).
- **Host:** SPI → APB3 → PeakRDL-generated CSRs, TX/RX FIFOs, IRQ.
- **Characterization:** internal loopback + on-chip noise injector for standalone
  silicon BER curves; CCA/energy-detect + RSSI proxy.

## Repository map
| Path | Contents |
|---|---|
| `rtl/core/`, `rtl/tt_top/` | core IP and the `tt_um_barkerlink` TT wrapper |
| `regs/` | SystemRDL single-source register description |
| `model/` | Python fixed-point golden model + BER theory |
| `dv/cocotb/`, `dv/formal/` | cocotb benches; SymbiYosys properties |
| `dft/ synth/ pnr/ fw/` | DFT, synthesis, PnR/DSE, RP2040 bring-up |
| `docs/` | `SPEC.md`, `VPLAN.md`, `INTEGRATION.md`, `ERRATA.md` |

## Project memory
`CLAUDE.md` (flow brain) · `STATUS.md` (phase/next) · `DECISIONS.md` (rationale log) ·
`METRICS.md` (trend table) · `PREDICTIONS.md` (frozen at tapeout).

## License / context
A flagship RTL/DV/PD portfolio artifact developed as a commercial-grade IP-team-of-one:
spec-first, lockstep-verified, signoff-disciplined.
