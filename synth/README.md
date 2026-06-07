# synth/ — Yosys synthesis

`synth.ys` — technology-independent elaborate + `stat` (synthesizability check + generic
cell count for trend tracking). Run via `make synth`. No PDK liberty required.

Real **sky130** cell mapping, area, and timing closure happen in **Phase 7**
(LibreLane / OpenROAD-flow-scripts under `pnr/`), with OpenSTA Fmax/WNS feeding
`PREDICTIONS.md`.
