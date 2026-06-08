# STATUS

**Phase:** 3 — DV closure. **COMPLETE** (regression 0 fail, 100% functional coverage).
**Branch:** `claude/upbeat-hypatia-eqKXz`
**Last updated:** 2026-06-08

## Phase 3 results (evidence)
- **Regression:** `make regress` SEEDS=500 (+60 noisy-RX) → **0 failures** (8m34s). Clean
  full-chip loopback (random length 1–24, data, service) exact recovery + RTL==model;
  noisy-RX lockstep vs model across clean/low/high chip-flip noise.
- **Functional coverage: 100.0% (21/21 bins)** — `docs/COVERAGE.md` (length, data,
  service, TX-FIFO occupancy, CRC ok/fail, SFD, noise, noise×crc cross). Gate ≥95% PASS.
- **Bug found + fixed:** the regression caught a `bl_tx` FIFO-head race on each PSDU
  byte's MSB (D-0112); directed tests had masked it with all-identical PSDU bytes.
- Directed suite `make sim` 13/13 (regression excluded; lives in `make regress`).
- **CI green** on `bbe5c2f`: lint ✓ test ✓ formal ✓.

## Phase 2 / P0 results (evidence)
- Full P0 chip integrated and verified: `make sim` **13/13**, `make model` **23/23**,
  `make lint` clean (verilator -Wall + Verible in CI).
- Datapath modules (lockstep vs golden model): `bl_scrambler`, `bl_dbpsk`, `bl_spreader`,
  `bl_correlator`, `bl_crc16`, `bl_tx`, `bl_rx`; infra: `bl_fifo`, `bl_csr` (APB3),
  `bl_spi_apb` (SPI mode-0, oversampled D-0110).
- Integration: `barkerlink_core` (CSR + TX/RX FIFOs + DSSS + loopback mux + IRQ) wired
  into `tt_um_barkerlink` per SPEC §3.2 pin map.
- End-to-end: `test_core` (APB-driven) and `test_top` (**pin-level SPI**) push a PSDU,
  TX→internal loopback→RX, recover it with CRC OK, read back over SPI. Cross-checked vs model.
- Full-chip synth ≈ **2743 generic cells** (budget ~4900 @ 70% of 7k) — headroom OK.
- **CI green** on `8f8a64c`: lint ✓ test ✓ formal ✓ (two Verible style nits fixed/waived).
- **P1 stubs (not yet built):** CCA/RSSI, LFSR noise injector, DQPSK datapath, scan.

## Phase 1 results (evidence)
- **Golden model:** `make model` → **23/23 passing** (`model/test_model.py`).
- **BER:** model Monte-Carlo tracks analytic theory within ~10% across p=0.10..0.32
  (`model/ber_curve.csv`); curve plotted at `docs/img/ber_dbpsk.png`.
- **Register map:** `regs/barkerlink.rdl` elaborates (14 regs, 0x00–0x37); PeakRDL
  `regblock` (APB3 SV), `c-header`, and `html` all generate cleanly (`make regs`).
- **Scrambler:** unit test caught seed 0x7F lock-up on all-ones SYNC → seed 0x6C (D-0102).
- `make smoke` still green (Phase 0 gate intact); RTL unchanged.
- **CI green** on `92ee342`: `lint` ✓, `test` ✓ (smoke + sim + **model** + synth), `formal` ✓
  (oss-cad-suite path validated; still a Phase 4 stub).

## What exists (added in Phase 1)
- `model/barkerlink_model.py` — fixed-point golden model (scrambler / DBPSK / Barker /
  genie correlator / PLCP / CRC-16 / loopback / chip-flip noise; DQPSK symbol mapping).
- `model/ber_theory.py` + curve PNG/CSV; `model/test_model.py` (23 tests).
- `regs/barkerlink.rdl` — full APB3 register map (ID..TEST), single source.
- `docs/SPEC.md` — datasheet-grade **freeze candidate** (interfaces, **pin map**, register
  map, TX/RX datapath + fixed-point, PLCP, FSMs, timing, performance targets).
- `docs/VPLAN.md` — feature→test→coverage map (model layer passing; RTL benches mapped).
- `docs/INTEGRATION.md` — SPI/APB3 protocol + register flows.
- Make targets: `model`, `ber`, `regs`. DECISIONS D-0101..D-0106.

## Open gate
**Phase 3 gate MET** — regression 0 failures over 500+ seeds, functional coverage 100%
(≥95% gate), `docs/COVERAGE.md` committed. **Next: Phase 4** — formal (SymbiYosys): FIFO
safety, PLCP FSM deadlock-freedom/legal transitions, scrambler/descrambler inverse.

## Phase 2 plan (module-by-module: RTL → cocotb lockstep vs golden model → lint → commit)
scrambler → DBPSK enc/dec → Barker spreader/oversample → soft correlator + genie decision
→ descramble → CRC-16 → PLCP TX/RX FSMs → APB3 CSR (PeakRDL regblock) + SPI bridge +
TX/RX FIFOs + IRQ → wire into `tt_um_barkerlink` → end-to-end loopback.
Datapath modules share the sign-bit / fixed-point conventions in SPEC §6.
