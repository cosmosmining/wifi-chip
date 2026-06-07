# STATUS

**Phase:** 1 — Spec + golden model + VPLAN (complete; awaiting operator **SPEC freeze**)
**Branch:** `claude/upbeat-hypatia-eqKXz`
**Last updated:** 2026-06-07

## Last results (evidence)
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
**Phase 1 → awaiting operator SPEC freeze.** The one sign-off item is the **pin map**
(SPEC §3.2). On "freeze + continue" I begin Phase 2.

## Next actions — Phase 2 (P0 RTL + lockstep), after freeze
Module-by-module (model test → RTL → cocotb lockstep vs golden model → lint → commit):
scrambler → DBPSK → Barker spreader → correlator → diff-demod/descramble → PLCP FSM →
CRC → APB3 CSR (PeakRDL regblock) + SPI bridge + FIFOs + IRQ → end-to-end
TX→loopback→RX. Gate: full-packet loopback passes; lint clean.
