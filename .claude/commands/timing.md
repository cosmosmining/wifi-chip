---
description: Run timing analysis (OpenSTA / Yosys) and report Fmax and per-block WNS
---
Report BarkerLink timing as evidence.

1. If OpenSTA + the sky130 liberty are available, run STA at the tt corner and report
   Fmax, WNS, and the worst paths per block. Otherwise run `make synth` and report the
   generic cell count, noting that signoff STA runs in CI / Phase 7.
2. Compare against the targets: f_clk >= 44 MHz, WNS >= 0 at the tt corner. Lead with any
   violation.
