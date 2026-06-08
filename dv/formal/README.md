# dv/formal/ — formal proofs (Phase 4)

Run with `make formal`. Engine: `yosys write_smt2` + `yosys-smtbmc` + **z3** — the same
machinery SymbiYosys orchestrates (sby itself isn't installable in the sandbox; this flow
is portable and runs locally and in CI). Properties live in `*_props.v` wrappers that
drive the DUT with free (`anyseq`/`anyconst`) inputs and a one-cycle reset at t0.

## Proofs and bounded-depth justification
| Proof | Property | Mode / depth | Why the bound suffices |
|---|---|---|---|
| `fifo_props` | `bl_fifo` level∈[0,16]; full/empty flag consistency; a tracked symbolic value reads out in FIFO order (no loss/reorder/dup) | BMC, **depth 32** | 16-deep FIFO: 32 steps let the tracked element be enqueued at full occupancy and dequeued through all 16 ahead of it, covering every in-flight position; safety is an inductive invariant exercised within this window. |
| `scrambler_props` | descramble(scramble(x)) == x (matched-seed self-sync inverse) | BMC **20** + induction | From reset both 7-bit LFSRs are aligned; the inverse is a local function of ≤7 past bits + the 2-cycle pipe, so 20 steps exercise the LFSR through many states; induction (k=20) closes it unbounded where it holds. |
| `plcp_props` | `bl_rx` FSM legal transitions; DONE→SEARCH next cycle (no hang) | BMC **16** + induction | 4-state FSM; 16 steps reach and leave every state from reset, exhaustively exercising the next-state function. |

All proofs assert-only (no covers needed for the gate). `make formal` exits non-zero on
any BMC failure; induction results are reported as a (stronger, unbounded) bonus.
