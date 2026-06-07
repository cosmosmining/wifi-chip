"""Pytest configuration for BarkerLink cocotb benches.

Guarantees this directory is importable (so ``import bl_paths`` and sibling
bench helpers resolve regardless of where pytest is invoked from).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
