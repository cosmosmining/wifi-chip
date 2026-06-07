# BarkerLink — Specification (DRAFT)

> **Status: DRAFT — NOT FROZEN.** No P0 RTL datapath is written until the operator
> freezes this document (Phase 1 gate). Sections marked _TBD-P1_ are completed during
> Phase 1. The fixed hard constraints and performance targets below are authoritative now.

## 1. Overview
Digital baseband TX/RX for 802.11b-class DSSS. 1 Mbps DBPSK (P0) and 2 Mbps DQPSK (P1)
at 11 Mchip/s using the Barker-11 sequence. RF/ADC/DAC are out of scope; the chip
exposes a digital chip-stream interface (1-bit @ 4× oversample) and an internal
loopback path (TX chips → RX input) for standalone characterization.

## 2. Hard constraints (authoritative)
- Tiny Tapeout digital project, sky130A, **2×2 tiles** (~320×200 µm), **≤6–8k cells**
  (design to ~70% for routability). No SRAM macros (flop storage). No FIFO >16 deep
  without operator approval.
- Top `tt_um_barkerlink`, standard TT interface. **Single clock domain**, f_clk = 50 MHz;
  core chip-rate logic designed for 44 MHz (4× oversample of 11 Mchip/s).
- Synchronous **active-low reset**; no latches; no combinational loops.

## 3. Interfaces

### 3.1 Tiny Tapeout pins
```
input  [7:0] ui_in     output [7:0] uo_out
input  [7:0] uio_in    output [7:0] uio_out   output [7:0] uio_oe
input  ena   input  clk   input  rst_n
```

### 3.2 Pin map — _TBD-P1 (operator-approved at freeze)_
Planned allocation (to be finalized; the pin map is an operator gate item):
| Pin | Dir | Planned function |
|---|---|---|
| `ui_in[0]` | in | SPI `SCLK` |
| `ui_in[1]` | in | SPI `CSn` |
| `ui_in[2]` | in | SPI `MOSI` |
| `ui_in[3]` | in | RX chip-stream in (external) |
| `ui_in[7:4]` | in | _TBD_ |
| `uo_out[0]` | out | SPI `MISO` |
| `uo_out[1]` | out | IRQ |
| `uo_out[2]` | out | TX chip-stream out |
| `uo_out[3]` | out | CCA / carrier-sense |
| `uo_out[7:4]` | out | status / _TBD_ |
| `uio[*]` | bidir | test mode (scan) under test-enable CSR — _TBD-P1_ |

## 4. Clocking & reset
Single 50 MHz domain from the TT harness. 4× oversampling → 44 MHz chip-rate datapath
budget. Active-low synchronous reset throughout. Any second clock domain requires
operator approval + proper CDC (none planned).

## 5. Register map
Single source: `regs/barkerlink.rdl` → PeakRDL generates the APB3 CSR RTL, C/Python
headers, and this table. **_TBD-P1_** — full map: ID, CTRL, STATUS, IRQ_EN/IRQ_STATUS,
TX/RX FIFO data + level, MODE (DBPSK/DQPSK), NOISE_PROB, CCA_THRESH, RSSI, TEST_EN.

## 6. TX datapath — _TBD-P1_
Scrambler (z⁻⁷+z⁻⁴+1, self-synchronizing) → differential encode (DBPSK; DQPSK in P1)
→ Barker-11 spreader → 1-bit chip stream @ 4× oversample.

## 7. RX datapath — _TBD-P1_
4-bit soft-input 11-tap Barker correlator → peak detect (genie/fixed timing in P0;
early-late recovery in P1) → differential demod → descrambler.

## 8. PLCP framing — _TBD-P1_
Long preamble: SYNC (scrambled ones) → SFD (0xF3A0) detect → header
(SIGNAL/SERVICE/LENGTH + CRC-16 check) → PSDU streamed via FIFOs (no full-packet buffering).

## 9. Host interface, FIFOs, IRQ — _TBD-P1_
SPI slave → APB3 → CSRs; TX/RX data FIFOs (8–16 deep); status + IRQ pin.

## 10. Characterization features (P1) — _TBD-P1_
Internal digital loopback; LFSR noise injector (CSR-set chip-flip probability); CCA /
energy-detect (correlation-magnitude threshold) + RSSI-proxy CSR.

## 11. DFT (P1/P6) — _TBD_
Scan insertion + ATPG (Fault); test mode muxed onto `uio` under a test-enable CSR bit.
Target ≥95% stuck-at coverage on scanned logic.

## 12. State machines & timing diagrams — _TBD-P1_

## 13. Performance targets (authoritative; verify in DV, predict in Phase 7)
- RX BER within **1 dB-equivalent** of theoretical DBPSK/DQPSK under injected
  chip-flip noise across **1e-4 … 1e-1**.
- SFD false-detect rate **< 1e-6 per slot** in noise-only stimulus.
- f_clk **≥ 44 MHz** post-route, **WNS ≥ 0** at tt corner.

## 14. Feature ladder & area fallback
See `CLAUDE.md` (P0 → P1 → P2; fallback never drops noise injector / CCA / scan).
