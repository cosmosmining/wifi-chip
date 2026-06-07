"""Make the model package importable when pytest collects from the repo root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
