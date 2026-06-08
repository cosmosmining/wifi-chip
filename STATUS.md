# STATUS

**Phase:** 5–8 — **release candidate v1.0.0-rc1**. P0+P1 functional complete; DV + formal
closed; PREDICTIONS frozen; firmware ready. GDS signoff + ATPG run in CI (tool-deferred).
**Branch:** `claude/upbeat-hypatia-eqKXz`
**Last updated:** 2026-06-08

## Phase 5–8 results (evidence)
- **Phase 5 (P1):** `bl_noise` LFSR chip-flip injector + CCA/RSSI implemented and
  **lockstep-verified** (`test_noise`: RX bit-accurate to `model.LfsrNoise` under on-chip
  noise; CCA/RSSI observed). DQPSK + early-late timing **documented-but-untaped** per the
  area-fallback ladder (D-0114). `make sim` 14/14.
- **Phase 6 (DFT):** scan infra specified (`TEST.SCAN_EN`, scan on `uio`); flop-based,
  macro-free → scan-friendly. ATPG via Fault **deferred to CI** (not installable; D-0002),
  target ≥95% stuck-at (`dft/README.md`).
- **Phase 7 (harden/predict):** **PREDICTIONS.md frozen** (area/timing/BER/SFD/GDS).
  OpenSTA/OpenROAD/LibreLane + TT GDS signoff run in CI (`gds.yml`, TT action) — github
  releases blocked locally (D-0002).
- **Phase 8 (release):** RP2040 MicroPython bring-up + BER-sweep firmware (`fw/`); SPEC.md
  is datasheet-grade; tag **v1.0.0-rc1**.

## Phase 4 results (evidence)
- `make formal` (yosys+smtbmc+z3; sby not installable, D-0113) → **ALL PROOFS PASSED**:
  - `fifo_props` — level bounds, full/empty consistency, tracked-value FIFO-order integrity
    (BMC depth 14, DEPTH=4 parametric).
  - `scrambler_props` — descramble(scramble(x))==x (**k-induction, unbounded**).
  - `plcp_props` — bl_rx FSM legal transitions + DONE→SEARCH no-hang (**k-induction, unbounded**).
- Depth justifications in `dv/formal/README.md`. CI `formal.yml` runs the same flow.

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
**Release candidate v1.0.0-rc1.** Done locally: P0+P1 functional (noise/CCA/RSSI), DV
closure (regress 0-fail, cov 100%), formal (FIFO/scrambler/PLCP). **Remaining to v1.0.0
(operator + CI):** run the TT GDS Action (`gds.yml`) for green sky130 signoff, run Fault
ATPG for the stuck-at number, then submit to the TTSKY26c shuttle. DQPSK/early-late are a
documented future revision (D-0114).

## Phase 2 plan (module-by-module: RTL → cocotb lockstep vs golden model → lint → commit)
scrambler → DBPSK enc/dec → Barker spreader/oversample → soft correlator + genie decision
→ descramble → CRC-16 → PLCP TX/RX FSMs → APB3 CSR (PeakRDL regblock) + SPI bridge +
TX/RX FIFOs + IRQ → wire into `tt_um_barkerlink` → end-to-end loopback.
Datapath modules share the sign-bit / fixed-point conventions in SPEC §6.
