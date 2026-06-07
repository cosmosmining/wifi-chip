# DECISIONS

Dated log of non-obvious engineering decisions and their rationale. Append-only;
supersede with a new dated entry rather than rewriting an old one.

---

### D-0001 — BarkerLink lives at the root of the `wifi-chip` repo (2026-06-07)
The master spec describes a `barkerlink/` project root. The session is scoped to the
empty `cosmosmining/wifi-chip` repo (802.11b == WiFi), so the repo root **is** the
project root (Makefile, rtl/, docs/ at top level — mirrors how the sibling `asic_soc`
repo is laid out). Not a spec/gate/pin-map question, so proceeding without asking.

### D-0002 — PD/formal/lint tools deferred to CI (2026-06-07)
This sandbox's network policy returns 403 for GitHub release assets and for some apt
PPAs (deadsnakes, ondrej). Installed locally via apt/pip: iverilog 12, verilator 5.020,
yosys 0.33, cocotb 2.0.1, pytest, yosys-smtbmc. **Could not install locally** (moved to
CI, not skipped): Verible, SymbiYosys (`sby`), OpenSTA, OpenROAD/LibreLane, magic,
klayout, netgen. CI runners have full network and install these via apt + oss-cad-suite
+ the official TT GDS action. `make lint` uses verilator locally and additionally runs
Verible when present (CI).

### D-0003 — DV flow: cocotb 2.0 Python runner + pytest (2026-06-07)
cocotb 2.0.1 removed `cocotb.runner` (now `cocotb_tools.runner`) and renamed the
`Timer`/`Clock` `units` kwarg to `unit`. We standardize on the **runner + pytest** flow
rather than the legacy `Makefile.sim` include: it gives programmatic seeds, pytest
parametrization, and clean parallelism for the Phase 3 regression. Conventions: build
with `timescale=("1ns","1ps")`; assert on `get_results` so pytest fails on sim failure;
sample registered outputs one delta after the clock edge (`await Timer(1, unit="ns")`)
to read past the NBA region.

### D-0004 — Phase 0 core is a registered passthrough placeholder (2026-06-07)
`barkerlink_core` registers `ui_in`→`uo_out` (sync reset to 0). This is a deliberate
scaffold that exercises the clock edge, active-low synchronous reset, module hierarchy,
and TT pin wiring end-to-end, giving the smoke bench something real to check. The core
internals (APB3 CSRs, TX/RX datapaths) replace it in Phase 2; the port list grows then.

### D-0005 — Unused Phase 0 inputs sunk via `_unused` idiom (2026-06-07)
`ena` and the `uio_in` input path have no load in Phase 0. They are sunk with
`wire _unused = &{ena, uio_in, 1'b0};` in the TT top. Verified verilator `-Wall` clean
(verilator exempts `*unused*`-named nets) — no lint waiver pragma needed. The sink is
removed when these pins gain real loads (test-enable CSR bit, SPI slave) in Phase 2.

### D-0006 — TT GDS workflow deferred to manual trigger until Phase 7 (2026-06-07)
`gds.yml` (official TT GDS action) runs on `workflow_dispatch` and tags only, not on
every push, to avoid burning CI minutes hardening an incomplete design. The Phase 0
`info.yaml` names the real top module and source files; final TT source packaging
(canonical `src/` layout vs our `rtl/` tree) and full GDS signoff happen in Phase 7.

---

## Phase 1 — Spec, golden model, VPLAN

### D-0101 — LENGTH field is PSDU octets, not microseconds (2026-06-07)
802.11 encodes PLCP LENGTH in microseconds (decoded to octets via the rate). For a
standalone digital baseband IP with a clean streaming interface, LENGTH is defined
directly as **PSDU octet count** (16-bit). Documented deviation; simplifies RX PSDU
slicing and the host contract. Model + RTL + `regs/barkerlink.rdl` all use octets.

### D-0102 — Scrambler seed 0x6C (2026-06-07)
The self-synchronizing scrambler (z⁻⁷+z⁻⁴+1) has a lock-up state at seed 0x7F: with all
register bits 1, feedback `bit3^bit6 = 0`, so scrambling the all-ones SYNC field returns
all ones (no scrambling). A model unit test (`test_scrambler_is_not_identity`) caught it.
Seed set to **0x6C** (non-degenerate). RX descrambler is self-synchronizing, so it is
seed-independent after 7 bits; the seed only matters for TX SYNC randomization.

### D-0103 — CRC-16-CCITT, MSB-first, init 0xFFFF, final complement (2026-06-07)
PLCP header CRC uses poly 0x1021, init 0xFFFF, bits processed MSB-first, result
complemented. This is a documented, self-consistent contract between the golden model and
RTL (golden model is law). Verified by round-trip + single-bit-flip detection tests.

### D-0104 — DQPSK chip-flip BER modeled as two orthogonal BPSK dimensions (2026-06-07)
The noise model is a chip-level BSC (flip probability), not AWGN, so there is no Eb/N0
and thus no DBPSK↔DQPSK AWGN gap. DQPSK is modeled as I/Q BPSK dimensions, each with the
11-chip processing gain; per-bit BER tracks DBPSK, the 2× throughput being the
differentiator. Documented model; finalized in Phase 5 when the DQPSK datapath exists.

### D-0105 — BER measured at the post-differential PHY point (2026-06-07)
The theoretical curve `ber_dbpsk_bsc(p)` is the post-differential-decode bit error. The
Monte-Carlo harness measures BER there (pre-descramble) to validate against theory. The
self-sync descrambler multiplies a single bit error into 3 (taps at n, n+4, n+7); that
system-level PSDU effect is reported separately and is not a model/theory discrepancy.

### D-0106 — Pin map proposed, pending operator freeze (2026-06-07)
SPEC §3.2 proposes the full functional/test-mode pin allocation (SPI, IRQ, TX/RX chip
streams, CCA, scan on `uio`). Per the hard rules the pin map is an operator sign-off
item; it is presented at the Phase 1 freeze gate.
