# dv/formal/ — formal proofs (Phase 4)

Run with `make formal`. Engine: `yosys write_smt2` + `yosys-smtbmc` + **z3** — the same
machinery SymbiYosys orchestrates (sby itself isn't installable in the sandbox; this flow
is portable and runs locally and in CI). Properties live in `*_props.v` wrappers that
drive the DUT with free (`anyseq`/`anyconst`) inputs and a one-cycle reset at t0.

## Proofs and bounded-depth justification
| Proof | Property | Result | Why it suffices |
|---|---|---|---|
| `fifo_props` | `bl_fifo` level∈[0,DEPTH]; full/empty flag consistency; a tracked symbolic value reads out in FIFO order (no loss/reorder/dup) | **BMC depth 14 PASS** | Proved at DEPTH=4: the pointer/count logic is depth-parametric (identical for any DEPTH), and 14 steps enqueue at full occupancy then dequeue through all entries ahead of the tracked one. DEPTH=16 is also exercised exhaustively by the random regression. |
| `scrambler_props` | descramble(scramble(x)) == x (matched-seed self-sync inverse) | **BMC 20 + induction PASS (unbounded)** | Both 7-bit LFSRs start aligned and stay aligned; k-induction (k=20) proves the inverse for all time. |
| `plcp_props` | `bl_rx` FSM legal transitions; DONE→SEARCH next cycle (no hang) | **BMC 16 + induction PASS (unbounded)** | 4-state FSM; k-induction (k=16) proves every transition is legal for all reachable states. |

All proofs assert-only (no covers needed for the gate). `make formal` exits non-zero on
any BMC failure; induction results are reported as a (stronger, unbounded) bonus.
