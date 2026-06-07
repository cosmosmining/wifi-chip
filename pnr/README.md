# pnr/ — Place & Route / DSE

Lands in **Phase 7**. LibreLane / OpenROAD-flow-scripts configs + a parallel DSE sweep
harness (utilization × clock target × placement density). Pick a Pareto point, pass the
TT precheck via the official GDS GitHub Action, and feed OpenSTA Fmax/WNS + area into
`PREDICTIONS.md`. Run via `make harden` / `make sweep`. Tools provided by CI / the TT
action (see `DECISIONS.md` D-0002, D-0006).
