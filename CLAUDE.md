# CLAUDE.md — BarkerLink flow brain

BarkerLink is an **802.11b-class DSSS baseband transceiver IP** (TX + RX) targeting
**Tiny Tapeout TTSKY26c** (sky130A, 2×2 tiles, ~320×200 µm, ≤6–8k cells; design to
~70%). This repository **is** the project — treat it as memory. RF/ADC/DAC are out of
scope: the chip exposes a digital chip-stream interface plus internal loopback so it
is fully characterizable standalone.

Top module `tt_um_barkerlink` (standard TT interface). Single clock domain, f_clk
target 50 MHz; chip-rate logic designed for 44 MHz (4× oversample of 11 Mchip/s).

## Session-start ritual (every session)
1. Read this file, `STATUS.md`, `DECISIONS.md`, and the last 10 lines of `METRICS.md`.
2. Run `make tools` to see the live toolchain.
3. Resume at the phase / next action in `STATUS.md`. **Stop at every phase gate** and
   present a gate report; do not start the next phase until the operator says continue.

## Build / test / harden
| Task | Command | Notes |
|---|---|---|
| Smoke (Phase 0 gate) | `make smoke` | lint + cocotb/Icarus hello sim |
| Lint (zero-warning) | `make lint` | verilator `-Wall`; verible in CI |
| Full sim | `make sim` | pytest over `dv/cocotb` |
| Synthesizability | `make synth` | yosys elaborate + generic cell count |
| Regression | `make regress` | Phase 3 |
| Coverage | `make cov` | Phase 3 |
| Formal | `make formal` | Phase 4 (SymbiYosys) |
| DFT | `make dft` | Phase 6 (Fault) |
| Harden / DSE | `make harden` / `make sweep` | Phase 7 |
| Predictions | `make predict` | Phase 7 |
| Metrics row | `make metrics` | appends `METRICS.md` |

## Quality bars — immutable (never lower to pass a gate)
- **Lint clean** every commit (zero verilator/verible warnings; a waiver needs a
  site comment **and** a DECISIONS entry).
- **Golden model is law**: never edit it to make RTL pass; the spec arbitrates a
  disagreement. Model changes need a spec citation + DECISIONS entry.
- Every spec feature → a **named test** and **named coverage point** in `VPLAN.md`.
- **Lockstep**: every datapath module compared to the golden model (cycle/packet).
- Functional coverage **≥95%** (Phase 3); ATPG stuck-at **≥95%** on scanned logic
  (Phase 6). Always report the real number.
- f_clk **≥44 MHz** post-route, **WNS ≥0** at tt corner (Phase 7).
- Synchronous **active-low reset**; no latches; no combinational loops; one clock.
- No SRAM macros (flop storage); no FIFO >16 deep without operator approval.

## Toolchain (this environment)
Installed locally: **iverilog 12, verilator 5.020, yosys 0.33, cocotb 2.0.1, pytest,
yosys-smtbmc**. Deferred to CI (sandbox blocks GitHub releases / some apt PPAs):
**verible, sby (SymbiYosys), OpenSTA, OpenROAD/LibreLane, magic, klayout, netgen**.
See `DECISIONS.md` (D-0002). CI installs these via apt + oss-cad-suite + the TT action.

## DV conventions (cocotb 2.0)
- Use `cocotb_tools.runner.get_runner("icarus")` + pytest (not the legacy Makefile
  flow). Assert on `get_results` so pytest fails when the sim fails.
- `Clock(dut.clk, 20, unit="ns")` — kwarg is `unit` (singular), `units` is removed.
- Build with `timescale=("1ns","1ps")`.
- Sample **registered** outputs one delta after the edge (`await Timer(1, unit="ns")`).
- Shared paths/constants: `dv/cocotb/bl_paths.py`.

## File map
- `rtl/core/` — bus-facing IP (`barkerlink_core`; APB3 CSRs + TX/RX from Phase 2)
- `rtl/tt_top/` — `tt_um_barkerlink` TT wrapper (+ SPI→APB bridge from Phase 2)
- `regs/` — SystemRDL single source (PeakRDL → RTL/headers/docs)
- `model/` — Python fixed-point golden model + BER theory (Phase 1)
- `dv/cocotb/` — per-module + top benches; `dv/formal/` SymbiYosys; `regression.list`
- `dft/ synth/ pnr/ fw/` — DFT, synthesis, PnR/DSE, RP2040 bring-up
- `docs/` — `SPEC.md VPLAN.md INTEGRATION.md ERRATA.md`
- `scripts/` — `metrics.py`, `hook_rtl_check.sh`
- `.github/workflows/` — `lint test formal gds nightly`

## Feature ladder (implement strictly in order)
- **P0:** TX scrambler (z⁻⁷+z⁻⁴+1) / DBPSK / Barker-11 spreader; RX soft 11-tap
  correlator / peak detect / differential demod / descrambler; long-PLCP framing
  (SYNC, SFD 0xF3A0, header SIGNAL/SERVICE/LENGTH + CRC-16); SPI→APB3 CSRs + TX/RX
  FIFOs (8–16) + IRQ; internal digital loopback.
- **P1:** DQPSK 2 Mbps; early-late timing recovery; on-chip LFSR noise injector
  (CSR probability); CCA/energy-detect + RSSI-proxy CSR; scan + ATPG.
- **P2 (if area/schedule):** TX header CRC-16 gen; per-block clock gating; ss/ff closure.
- **Area fallback (if >70% util):** drop P2 → coarsen timing recovery → soft bits
  4→2 → DQPSK documented-but-untaped → **never** drop noise injector / CCA / scan.

## Hard rules
- TT interface signature is fixed; pin map lives in `SPEC.md` (operator-approved).
- Stop and ask **exactly one** question only when blocked on: the spec, a quality
  gate, area >70%, or the pin map. Otherwise make the smallest reasonable assumption,
  log it in `DECISIONS.md`, and continue.
- Conventional commits, one logical change each. Never commit with failing lint or a
  broken smoke test. Develop on `claude/upbeat-hypatia-eqKXz`. No PR unless asked.
- Reporting style: evidence over adjectives. Bad news first.
