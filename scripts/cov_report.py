#!/usr/bin/env python3
"""Render the functional-coverage report and gate on a target (default 95%).

Reads build/cov/coverage.json (written by the regression), prints the per-bin table,
writes docs/COVERAGE.md (committed artifact), and exits non-zero if coverage < COV_TARGET.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dv" / "cocotb"))
from bl_coverage import Coverage  # noqa: E402


def main():
    cov = Coverage()
    pct, hit, total, rows = cov.report()
    target = float(os.environ.get("COV_TARGET", "95"))

    md = ["# BarkerLink — Functional Coverage Report", "",
          f"**Coverage: {pct:.1f}%** ({hit}/{total} bins) — target {target:.0f}% "
          f"({'PASS' if pct + 1e-9 >= target else 'FAIL'})", "",
          "| Group | Bin | Hits |", "|-------|-----|------|"]
    for g, b, h in rows:
        md.append(f"| {g} | {b} | {h} |")
    (ROOT / "docs" / "COVERAGE.md").write_text("\n".join(md) + "\n")

    print(f"functional coverage: {pct:.1f}% ({hit}/{total} bins), target {target:.0f}%")
    misses = [f"{g}.{b}" for g, b, h in rows if h == 0]
    for m in misses:
        print(f"  MISS {m}")
    if pct + 1e-9 < target:
        print(f"COVERAGE GATE FAIL: {pct:.1f}% < {target:.0f}%")
        return 1
    print("COVERAGE GATE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
