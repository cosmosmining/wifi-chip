#!/usr/bin/env bash
# BarkerLink formal proofs via `yosys write_smt2` + `yosys-smtbmc` (+ z3) - the engine
# SymbiYosys orchestrates. Each proof runs bounded BMC to a justified depth, plus
# induction where the property is inductive. Depth justifications: dv/formal/README.md.
set -uo pipefail
cd "$(dirname "$0")/../.."
B=build/formal
mkdir -p "$B"
SOLVER="${BL_SOLVER:-z3}"
fail=0

prove() {  # name top sources bmc_depth ind_depth(0=skip)
  local name=$1 top=$2 srcs=$3 bmc=$4 ind=$5
  echo "=== $name ==="
  if ! yosys -q -p "read_verilog -formal -DFORMAL $srcs dv/formal/$name.v; \
                    prep -top $top -flatten; write_smt2 -wires $B/$name.smt2" \
                    2>"$B/$name.ys.log"; then
    echo "  yosys elaboration FAILED"; tail -8 "$B/$name.ys.log"; fail=1; return
  fi
  if yosys-smtbmc -s "$SOLVER" -t "$bmc" "$B/$name.smt2" >"$B/$name.bmc.log" 2>&1; then
    echo "  BMC(depth $bmc): PASS"
  else
    echo "  BMC(depth $bmc): FAIL"; tail -6 "$B/$name.bmc.log"; fail=1
  fi
  if [ "$ind" != 0 ]; then
    if yosys-smtbmc -s "$SOLVER" -i -t "$ind" "$B/$name.smt2" \
         >"$B/$name.ind.log" 2>&1; then
      echo "  induction(k=$ind): PASS (unbounded)"
    else
      echo "  induction(k=$ind): not k-inductive at this k (BMC bound holds)"
    fi
  fi
}

prove fifo_props      fifo_props      "rtl/core/bl_fifo.v"      14 0
prove scrambler_props scrambler_props "rtl/core/bl_scrambler.v" 20 20
prove plcp_props      plcp_props      \
  "rtl/core/bl_rx.v rtl/core/bl_correlator.v rtl/core/bl_dbpsk.v rtl/core/bl_scrambler.v rtl/core/bl_crc16.v" \
  16 16

if [ $fail -eq 0 ]; then echo "ALL FORMAL PROOFS PASSED"; else echo "FORMAL FAILURES"; exit 1; fi
