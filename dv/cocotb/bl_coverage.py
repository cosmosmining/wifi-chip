"""Lightweight functional coverage for the BarkerLink regression.

Defines the coverage model (groups -> expected bins), accumulates hits across sims via a
shared JSON (so the clean-loopback and noisy-RX regressions merge), and reports the hit
percentage against the *defined* bins. Coverage% = hit_bins / defined_bins. A bin only
counts as covered once observed in simulation (never assumed).
"""
import json
from pathlib import Path

# group -> ordered list of expected bin names
COV_MODEL = {
    "cp_len_class": ["1", "2-4", "5-8", "9-16", "17-40"],
    "cp_data":      ["has00", "hasFF", "hasmid"],
    "cp_service":   ["zero", "nonzero"],
    "cp_txfifo":    ["notfull", "full"],
    "cp_crc":       ["ok", "fail"],
    "cp_sfd":       ["detected"],
    "cp_noise":     ["clean", "low", "high"],
    "cx_noise_crc": ["clean_ok", "low_ok", "high_fail"],
}


def default_path():
    return Path(__file__).resolve().parents[2] / "build" / "cov" / "coverage.json"


class Coverage:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_path()
        self.hits = {}
        if self.path.exists():
            self.hits = json.loads(self.path.read_text())

    def sample(self, group, binname):
        self.hits.setdefault(group, {})
        self.hits[group][binname] = self.hits[group].get(binname, 0) + 1

    @staticmethod
    def len_class(n):
        return ("1" if n <= 1 else "2-4" if n <= 4 else "5-8" if n <= 8
                else "9-16" if n <= 16 else "17-40")

    @staticmethod
    def noise_class(p):
        return "clean" if p == 0 else "low" if p <= 0.05 else "high"

    def sample_packet(self, length, psdu, service, noise_p, crc_ok, saw_full, sfd):
        """Sample all per-packet coverage points from one observed transaction."""
        self.sample("cp_len_class", self.len_class(length))
        if any(b == 0x00 for b in psdu):
            self.sample("cp_data", "has00")
        if any(b == 0xFF for b in psdu):
            self.sample("cp_data", "hasFF")
        if any(0x00 < b < 0xFF for b in psdu):
            self.sample("cp_data", "hasmid")
        self.sample("cp_service", "zero" if service == 0 else "nonzero")
        self.sample("cp_txfifo", "full" if saw_full else "notfull")
        self.sample("cp_crc", "ok" if crc_ok else "fail")
        if sfd:
            self.sample("cp_sfd", "detected")
        nc = self.noise_class(noise_p)
        self.sample("cp_noise", nc)
        if nc == "clean" and crc_ok:
            self.sample("cx_noise_crc", "clean_ok")
        elif nc == "low" and crc_ok:
            self.sample("cx_noise_crc", "low_ok")
        elif nc == "high" and not crc_ok:
            self.sample("cx_noise_crc", "high_fail")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.hits, indent=2))

    def report(self):
        total = hit = 0
        rows = []
        for g, bins in COV_MODEL.items():
            for b in bins:
                total += 1
                h = self.hits.get(g, {}).get(b, 0)
                hit += 1 if h else 0
                rows.append((g, b, h))
        pct = 100.0 * hit / total if total else 0.0
        return pct, hit, total, rows
