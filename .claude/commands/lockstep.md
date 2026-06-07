---
description: Run a module's RTL-vs-golden-model lockstep bench and report first divergence
argument-hint: "<module> (e.g. scrambler, correlator, plcp)"
---
Run the lockstep bench for module `$ARGUMENTS`, comparing RTL to the Python golden model.

1. Build + run that module's cocotb lockstep bench under `dv/cocotb`.
2. On mismatch: report the first cycle/packet of divergence with the inputs and the RTL
   vs model values. The spec arbitrates — never edit the golden model to force a pass.
3. On pass: report how many cycles/packets were compared and which coverage points hit.
