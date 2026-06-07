# STATUS

**Phase:** 0 — Scaffold (complete; awaiting operator gate approval)
**Branch:** `claude/upbeat-hypatia-eqKXz`
**Last updated:** 2026-06-07

## Last results (evidence)
- `make smoke` → `LINT CLEAN` + 1 cocotb test passed + `SMOKE PASS` (local, rc=0).
- **CI green** on push `0cc392a`: `test` workflow (smoke + sim + synth) ✓ and `lint`
  workflow (verilator + **Verible**) ✓ — Verible is enforced and clean in CI.
- `make synth` → 8 generic cells (registered `ui_in`→`uo_out` placeholder).
- RTL: `verilator --lint-only -Wall` clean; `iverilog -g2012 -Wall` elaborates clean.
- Toolchain installed locally: iverilog 12, verilator 5.020, yosys 0.33, cocotb 2.0.1,
  pytest, yosys-smtbmc. Deferred to CI: verible, sby, OpenSTA/LibreLane/magic/klayout/netgen.
- PostToolUse RTL hook verified: pass on good edit, silent-skip on non-RTL, exit 2 on
  broken RTL.

## What exists
- Full repo tree per SPEC §3.
- `tt_um_barkerlink` + `barkerlink_core` Phase 0 placeholders (registered passthrough;
  validates clock / sync reset / hierarchy / pin wiring).
- `Makefile`: `smoke`/`lint`/`sim`/`synth` live; `regress`/`cov`/`formal`/`dft`/
  `harden`/`sweep`/`predict` honest phase-tagged stubs.
- cocotb smoke bench (runner + pytest); `scripts/metrics.py`; `scripts/hook_rtl_check.sh`.
- CI workflows: `lint`, `test`, `formal`, `gds` (manual until Phase 7), `nightly`.
- Slash commands: `/regress /lockstep /timing /status`.
- Doc skeletons: `SPEC.md`, `VPLAN.md`, `INTEGRATION.md`, `ERRATA.md`; `regs/barkerlink.rdl` stub.

## Next actions — Phase 1 (after gate approval)
1. Freeze the **pin map** and **register map** in `docs/SPEC.md` (datasheet-grade:
   interfaces, timing diagrams, state machines, performance targets).
2. Write the Python **fixed-point golden model** + unit tests; plot theoretical
   DBPSK/DQPSK BER curves.
3. Build the `VPLAN.md` feature→test→coverage skeleton.
4. **Gate:** operator freezes `SPEC.md` before any P0 RTL.

## Open gate
**Phase 0 → awaiting operator "continue" to begin Phase 1.**
