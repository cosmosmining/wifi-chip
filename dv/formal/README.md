# dv/formal/ — SymbiYosys properties

Lands in **Phase 4**. Formal where it pays:
- **FIFOs:** no overflow/underflow; data integrity (in-order, no loss/dup).
- **PLCP FSM:** deadlock-freedom; only legal transitions; reset reachability.
- **Scrambler/descrambler:** inverse property (descramble(scramble(x)) == x).

Each `.sby` states its mode (bmc/prove) and **bounded depth with a written
justification** for why that depth suffices. Run via `make formal` (uses `sby`;
provided by CI / oss-cad-suite — see `DECISIONS.md` D-0002).
