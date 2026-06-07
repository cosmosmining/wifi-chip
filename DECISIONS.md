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
