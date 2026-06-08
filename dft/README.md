# dft/ — Design for Test (Phase 6)

**Status:** scan infrastructure specified + reserved in RTL; **ATPG is tool-deferred to CI**
(Fault is not installable in the dev sandbox — GitHub releases blocked, DECISIONS D-0002).

## Scan architecture (specified)
- `TEST.SCAN_EN` (CSR 0x34 bit 0) enables test mode; `TEST.TEST_MODE` (bit 1) routes the
  scan chain onto `uio` per the SPEC §3.2 pin map: `uio[0]=SCAN_IN`, `uio[1]=SCAN_EN`,
  `uio[2]=SCAN_CLK` (optional), `uio[3]=SCAN_OUT` (`uio_oe[3]=1` in test mode).
- All storage is flop-based (no SRAM macros), single clock, synchronous active-low reset —
  i.e. fully scan-friendly: every flop joins one scan chain after insertion.

## Flow (CI)
1. Synthesize to sky130 (yosys/TT flow).
2. Scan-chain insertion (Fault `verilog_to_scan` / equivalent) on the mapped netlist.
3. ATPG (Fault) → stuck-at vectors + coverage report under `dft/`.
4. Re-run the functional regression with scan inserted (must still pass).

## Target
**≥95% stuck-at** coverage on scanned logic; the *real* number is reported in the
committed ATPG report regardless. Prediction (PREDICTIONS.md): ≥95% achievable given the
flop-based, macro-free design. `make dft` runs this flow once Fault is provisioned in CI.
