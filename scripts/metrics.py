#!/usr/bin/env python3
"""Parse build logs into summary.json and append one row to METRICS.md.

This is the single place that turns tool output into the append-only METRICS.md
trend table. It is deliberately tolerant: any metric whose evidence is missing
is recorded as "n/a" rather than guessed. Coverage / WNS / ATPG land as evidence
appears in later phases; nothing here ever fabricates a number.

Usage:
    python3 scripts/metrics.py [--phase N] [--note "..."]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
METRICS_MD = ROOT / "METRICS.md"
SUMMARY_JSON = BUILD / "summary.json"

HEADER = (
    "| Date | Commit | Phase | Lint | Cells(generic) | Func Cov | "
    "WNS(ns) | ATPG% | Note |"
)
SEP = "|------|--------|-------|------|----------------|----------|---------|-------|------|"


def _sh(*args: str, default: str = "n/a") -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    except Exception:
        return default


def _git_commit() -> str:
    return _sh("git", "rev-parse", "--short", "HEAD", default="uncommitted")


def _phase_from_status() -> str:
    status = ROOT / "STATUS.md"
    if status.exists():
        m = re.search(r"Phase\D*([0-9]+)", status.read_text(), re.IGNORECASE)
        if m:
            return m.group(1)
    return "?"


def _lint_status() -> str:
    log = BUILD / "lint.log"
    if not log.exists():
        return "n/a"
    txt = log.read_text()
    return "FAIL" if re.search(r"%(Warning|Error)", txt) else "clean"


def _cell_count() -> str:
    log = BUILD / "synth.log"
    if not log.exists():
        return "n/a"
    hits = re.findall(r"Number of cells:\s+(\d+)", log.read_text())
    return hits[-1] if hits else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default=None)
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    row = {
        "date": _dt.date.today().isoformat(),
        "commit": _git_commit(),
        "phase": args.phase or _phase_from_status(),
        "lint": _lint_status(),
        "cells_generic": _cell_count(),
        "func_cov": "n/a",
        "wns_ns": "n/a",
        "atpg_pct": "n/a",
        "note": args.note or "-",
    }

    BUILD.mkdir(exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(row, indent=2) + "\n")

    # Ensure METRICS.md has a header, then append (never rewrite history).
    if not METRICS_MD.exists() or HEADER not in METRICS_MD.read_text():
        with METRICS_MD.open("a") as fh:
            fh.write(f"\n{HEADER}\n{SEP}\n")

    line = "| {date} | {commit} | {phase} | {lint} | {cells_generic} | {func_cov} | {wns_ns} | {atpg_pct} | {note} |".format(**row)
    with METRICS_MD.open("a") as fh:
        fh.write(line + "\n")

    print("summary.json:")
    print(json.dumps(row, indent=2))
    print(f"\nappended row to {METRICS_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
