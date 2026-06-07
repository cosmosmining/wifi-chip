# dft/ — Design for Test

Lands in **Phase 6**. DFT is a feature: scan-chain insertion + ATPG with **Fault**, test
mode muxed onto `uio` under a test-enable CSR bit. Target **≥95% stuck-at** coverage on
scanned logic; the real number is reported in the committed ATPG report regardless.
Functional regression must still pass with scan inserted. Run via `make dft`.
