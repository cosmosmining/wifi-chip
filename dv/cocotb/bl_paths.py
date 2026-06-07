"""Shared paths and constants for BarkerLink cocotb benches.

Centralizes RTL source discovery, the simulation timescale, and the per-bench
build directory layout so every bench (smoke today; lockstep datapath benches
from Phase 2 onward) builds the same way and stays reproducible from a clean
clone.
"""
from pathlib import Path

COCOTB_DIR = Path(__file__).resolve().parent          # dv/cocotb
REPO_ROOT = COCOTB_DIR.parents[1]                      # repo root
RTL_DIR = REPO_ROOT / "rtl"
MODEL_DIR = REPO_ROOT / "model"

# Make the golden model importable from any bench (lockstep reference).
import sys
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

# Dependencies first (core), then the TT top wrapper.
RTL_CORE = sorted((RTL_DIR / "core").glob("*.v"))
RTL_TOP = sorted((RTL_DIR / "tt_top").glob("*.v"))
RTL_ALL = RTL_CORE + RTL_TOP

# 50 MHz target clock; 1ns/1ps gives cocotb enough precision for a 20 ns period.
TIMESCALE = ("1ns", "1ps")
CLK_PERIOD_NS = 20
TT_TOPLEVEL = "tt_um_barkerlink"


def build_dir(name: str) -> Path:
    """Per-bench build directory under the gitignored build/ tree."""
    return REPO_ROOT / "build" / "sim" / name
