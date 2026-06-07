---
description: Run the constrained-random regression and summarize pass/fail + coverage
argument-hint: "[seeds] (default per regression.list; Phase 3+)"
---
Run the BarkerLink regression and report results as evidence (not adjectives).

1. Run `make regress` ($ARGUMENTS seeds if given). If it is still a Phase 0 stub, say so
   and run `make sim` instead.
2. Summarize: total / pass / fail, the first failing seed with the first point of
   divergence vs the golden model, and functional coverage % with the report path.
3. If anything failed, lead with it, show the minimal repro (`SEED=...`), and propose a
   fix. Never delete or weaken a failing test to make the gate pass.
