# DECISIONS

Dated log of non-obvious engineering decisions and their rationale. Append-only;
supersede with a new dated entry rather than rewriting an old one.

---

## Phase 5 — P1 features

### D-0114 — DQPSK and early-late timing: documented-but-untaped (2026-06-08)
Per the SPEC area-fallback ladder, under the shuttle schedule the P1 must-keeps are the
**noise injector, CCA/RSSI, and scan** — all implemented/verified (bl_noise + CCA/RSSI
lockstep; scan in Phase 6). **DQPSK 2 Mbps** and **early-late chip-timing recovery** are
*documented-but-untaped*: the golden model carries the DQPSK Gray dibit↔phase mapping
(unit-tested) and the RX uses genie/fixed chip timing (loopback-aligned). The CSR
`CTRL.MODE` bit and `SIGNAL=0x14` are reserved; the DQPSK datapath and early-late loop are
specified for a future revision, not in the v1.0 tapeout. This is the spec-sanctioned
fallback, taken deliberately to protect schedule + the must-keep characterization features.

## Phase 4 — Formal

### D-0113 — Formal via yosys+smtbmc+z3; FIFO proved at DEPTH=4 (2026-06-08)
`sby` isn't installable in the sandbox, so `make formal` runs the engine SymbiYosys
orchestrates: yosys `write_smt2` + `yosys-smtbmc` + **z3** (`pip install z3-solver`). Same
flow in CI (formal.yml). The FIFO proof instantiates DEPTH=4 — the pointer/count logic is
depth-parametric, so a small instance proves the property while keeping BMC fast under z3;
DEPTH=16 is additionally exercised exhaustively by the Phase 3 regression. Results:
scrambler-inverse and PLCP-FSM pass by **k-induction (unbounded)**; FIFO by BMC depth 14.

## Phase 3 — DV closure

### D-0112 — Regression caught a TX FIFO-head race (fixed) (2026-06-07)
The constrained-random regression found a real RTL bug: `bl_tx` read the next PSDU byte's
MSB directly from the FIFO head one cycle before `psdu_pop` advanced it, so each byte k>0
took its first bit from byte k-1 (visible only when consecutive MSBs differ). The directed
loopback/core/top tests had masked it by accidentally generating all-identical PSDU bytes
(`random.Random(seed).getrandbits(8)` *per byte* re-seeds each call). Fixes: bl_tx now
latches each byte into `tx_byte` at the byte boundary (head settled); benches use one RNG
per packet. This is exactly why constrained-random + the model-as-law matter.

### D-0111 — Regression shortens SYNC_LEN for sim throughput (2026-06-07)
`bl_tx` has a `SYNC_LEN` parameter (default 128 = taped-out). The regression builds it at
SYNC_LEN=24 (model `sync_len` matched) purely for simulation speed; preamble length does
not change the scramble/spread/correlate/demod/framing logic under test. The full 128-bit
preamble is exercised by the directed `test_top`/`test_core`/`test_loopback` benches.

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

### D-0107 — SPEC Rev 1.0 frozen; pin map approved (2026-06-07)
Operator approved the Phase 1 gate: "Freeze & start Phase 2." SPEC.md Rev 1.0 is frozen
including the §3.2 pin map. Phase 2 (P0 RTL + lockstep) begins. Any spec change now needs
a new dated revision + a DECISIONS entry (quality gate: spec is law for RTL).

---

## Phase 2 — P0 RTL + lockstep

### D-0108 — Verible house-style waivers; RTL is Verilog-2001 (2026-06-07)
BarkerLink RTL targets portable **Verilog-2001** (clean across iverilog/verilator/yosys),
not Google-SystemVerilog style. Three Verible default rules conflict with that and are
waived project-wide via `dv/lint/verible.rules` (`make lint` passes `--rules_config`):
`parameter-name-style` (we use universal UPPER_SNAKE_CASE constants/states),
`explicit-parameter-storage-type` (untyped localparams with explicit width are standard
V2001), and `always-comb` (we use `always @*`). All other Verible rules stay enforced
(zero-warning gate). verilator `-Wall` remains the always-on local gate. Caught by the
first CI run of the Phase 2 RTL (lint workflow); functional `test` workflow was green.

### D-0109 — CSR RTL hand-written in Verilog-2001; RDL stays the map source (2026-06-07)
PeakRDL-regblock emits SystemVerilog with packages + packed-struct hwif ports, which would
pull SV (and yosys `-sv`, struct flattening) into the otherwise clean V2001 open-flow. So
`bl_csr.v` is hand-written V2001 implementing `regs/barkerlink.rdl`; the RDL remains the
single source for the register **map** (documentation + C header via `make regs`), and the
CSR RTL is held to it by `test_csr` (V-CSR). A future CI equivalence check vs the generated
regblock can tighten this. Net: one map definition (RDL), portable RTL implementation.

### D-0110 — SPI is oversampled in the clk domain (no 2nd clock) (2026-06-07)
The SPI slave samples SCLK/CSn/MOSI through 2-FF synchronizers and detects SCLK edges in
the 50 MHz `clk` domain (f_clk >> f_sclk), so there are no SCLK-clocked flops and the
single-clock-domain rule holds. The synchronizers are the CDC structures for the async
SPI inputs. (bl_spi_apb.)
