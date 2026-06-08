# PREDICTIONS — FROZEN 2026-06-08 (Rev 1.0)

Pre-registered silicon/closure predictions for BarkerLink v1.0, committed **before** the
sky130 hardening/STA results are known. **Do not edit after freeze** — corrections go in a
dated addendum at the bottom. Methodology is stated per prediction so each is falsifiable.

Tools note: OpenSTA / OpenROAD / LibreLane are not installable in the dev sandbox
(GitHub releases blocked, DECISIONS D-0002); timing/area/GDS are produced by the CI
signoff path (`gds.yml`, the official TT action) and OpenSTA. The numbers below are
predictions to be checked against that flow.

## Area
- **Generic synth (measured):** 2763 cells (yosys generic, `make synth`).
- **Prediction (sky130 std cells):** 3.0k–4.5k cells after tech mapping; **utilization < 60%**
  on the TT 2×2 tile (≈ within the ~6–8k budget, design-to-70% target met with margin).
- Method: generic→sky130 mapping typically 1.1–1.6× cell count for flop-heavy control logic;
  the design is flop-dominated (FIFOs 2×16×8b, LFSRs, FSMs) with light combinational logic.

## Timing (tt corner, f_clk = 50 MHz target)
- **Prediction: WNS ≥ +5 ns at 50 MHz; Fmax ≥ 80 MHz.**
- Method/rationale: single clock domain; the longest combinational paths are the 11-tap
  correlator accumulator (sequential adds of ±7, 8-bit) and the CRC-16 XOR chain — both
  short. No multi-cycle compute, no wide multipliers. The chip-rate datapath is budgeted
  for 44 MHz but runs comfortably at 50. To be validated by OpenSTA in CI.

## RX BER vs injected chip-flip noise
- **Prediction: RTL BER == golden-model BER (exactly), within ±1 dB-equivalent of theory
  across p_chip giving BER 1e-4 … 1e-1** (`docs/img/ber_dbpsk.png`, `model/ber_curve.csv`).
- Method: `test_noise` already shows the RTL RX is bit-accurate to `model.LfsrNoise` +
  `rx_dbpsk` under on-chip noise, and the model MC tracks analytic theory within ~10%.
  Therefore the silicon BER curve (firmware sweep, `fw/`) will match the model curve up to
  RNG variance. Strong prediction (lockstep already demonstrated).

## SFD false-detect (noise-only stimulus)
- **Prediction: < 1e-6 per slot.** Method: SFD is a 16-bit exact match (0xF3A0) on the
  descrambled stream; under noise-only the descrambled bits are ~uniform, so a false match
  is ~2⁻¹⁶ per bit-offset ≈ 1.5e-5 per offset, but the subsequent 48-bit header CRC-16 must
  also pass (≈ 2⁻¹⁶), giving a combined accepted-false-frame rate ≪ 1e-6 per slot.

## GDS / DFT (validated in CI / future)
- **GDS:** green TT precheck + routed GDSII via the official TT GDS Action (`gds.yml`),
  sky130, 2×2. DRC = 0, LVS = 0 predicted (digital-only, flop-based, no macros).
- **ATPG:** ≥ 95% stuck-at on scanned logic once scan + Fault ATPG run in CI (Phase 6,
  Fault not installable in sandbox). The design is flop-based and scan-friendly.
