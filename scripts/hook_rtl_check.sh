#!/usr/bin/env bash
# PostToolUse hook: fast lint + compile-check after any edit under rtl/.
#
# Reads the hook JSON payload on stdin, extracts the edited file path, and if it
# is a Verilog source under rtl/ runs verilator --lint-only (zero-warning gate)
# plus an iverilog elaboration check. Anything else exits 0 immediately so the
# hook never gets in the way of non-RTL edits. Exit 2 surfaces a blocking error
# back to Claude (Claude Code hook convention) so a broken edit is caught at the
# moment it is made, not at the next manual build.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0
ROOT="$(pwd)"

# Extract tool_input.file_path from the hook payload (robust to schema drift).
FILE="$(python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)
ti = d.get("tool_input", {}) or {}
print(ti.get("file_path") or ti.get("path") or "")
' 2>/dev/null)"

# Only act on Verilog files under rtl/.
case "$FILE" in
  *"/rtl/"*.v|rtl/*.v) ;;
  *) exit 0 ;;
esac

command -v verilator >/dev/null 2>&1 || exit 0
RTL=$(find rtl -name '*.v' 2>/dev/null)
[ -z "$RTL" ] && exit 0

LOG="$(mktemp)"
# shellcheck disable=SC2086
if ! verilator --lint-only -Wall --top-module tt_um_barkerlink $RTL >"$LOG" 2>&1 \
   || grep -qE '%(Warning|Error)' "$LOG"; then
  echo "RTL hook: verilator lint failed after editing $FILE" >&2
  sed -n '1,40p' "$LOG" >&2
  rm -f "$LOG"
  exit 2
fi
rm -f "$LOG"

if command -v iverilog >/dev/null 2>&1; then
  # shellcheck disable=SC2086
  if ! iverilog -g2012 -Wall -tnull -s tt_um_barkerlink $RTL >/dev/null 2>&1; then
    echo "RTL hook: iverilog elaboration failed after editing $FILE" >&2
    exit 2
  fi
fi
exit 0
