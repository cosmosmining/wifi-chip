"""Theoretical BER curves for BarkerLink under the on-chip chip-flip noise model.

The on-chip noise injector flips transmitted chips with probability p (a binary
symmetric channel at the chip level), NOT AWGN. So the reference curve is the
combinatorial probability that Barker despreading produces the wrong symbol:

  After an 11-chip Barker despread with equal-magnitude (hard) chips, the decision
  sign flips iff a strict majority of the 11 chips are flipped:
      p_sym(p) = sum_{k=6}^{11} C(11,k) p^k (1-p)^(11-k)
  Differential (DBPSK) detection turns one symbol error into (typically) two bit
  errors, so:
      BER_DBPSK(p) = 2 * p_sym * (1 - p_sym)

DQPSK (P1) is modeled as two orthogonal BPSK dimensions (I, Q), each with the same
11-chip processing gain and independent chip flips, so per-bit BER tracks DBPSK
under this chip-flip BSC; the 2x throughput is the differentiator (the AWGN Eb/N0
gap is out of scope because this noise model has no soft/analog component). This is
a documented model, finalized in Phase 5 when the DQPSK datapath exists.

Run `python3 model/ber_theory.py` to (re)generate docs/img/ber_dbpsk.png and
model/ber_curve.csv and print the table.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import barkerlink_model as bl

N = bl.N_CHIPS  # 11


def p_symbol_error_bsc(p: float, n: int = N) -> float:
    """P(majority of n chips flipped) = P(>= floor(n/2)+1 flips)."""
    thr = n // 2 + 1
    return sum(math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(thr, n + 1))


def ber_dbpsk_bsc(p: float, n: int = N) -> float:
    ps = p_symbol_error_bsc(p, n)
    return 2 * ps * (1 - ps)


def ber_dqpsk_bsc(p: float, n: int = N) -> float:
    # Per-dimension model (see module docstring): same processing gain as DBPSK.
    ps = p_symbol_error_bsc(p, n)
    return 2 * ps * (1 - ps)


def simulate_ber_dbpsk(p: float, n_bits: int, seed: int = 1,
                       target_errors: int = 120) -> tuple[float, int, int]:
    """Monte-Carlo PHY BER via the golden model. Returns (ber, errors, bits_run)."""
    rng = random.Random(seed)
    chunk = 4000
    errors = 0
    run = 0
    while run < n_bits and errors < target_errors:
        bits = [rng.getrandbits(1) for _ in range(chunk)]
        rx = bl.phy_dbpsk_loopback(bits, p, rng)
        errors += sum(1 for a, b in zip(bits, rx) if a != b)
        run += chunk
    return (errors / run if run else 0.0), errors, run


def _curve_points():
    # Theory across the spec's region of interest; MC overlay where errors are
    # statistically observable with a feasible bit budget (BER >~ 1e-3).
    p_theory = [0.02 + 0.005 * i for i in range(0, 67)]          # 0.02 .. 0.35
    p_mc = [0.10, 0.13, 0.16, 0.20, 0.24, 0.28, 0.32]
    return p_theory, p_mc


def generate(out_png: Path, out_csv: Path, mc_bits: int = 200_000) -> list[dict]:
    p_theory, p_mc = _curve_points()
    theory = [ber_dbpsk_bsc(p) for p in p_theory]

    rows = []
    mc_ber = []
    for i, p in enumerate(p_mc):
        ber, errs, bits = simulate_ber_dbpsk(p, mc_bits, seed=100 + i)
        mc_ber.append(ber)
        rows.append({"p_chip": p, "ber_theory": ber_dbpsk_bsc(p),
                     "ber_mc": ber, "mc_errors": errs, "mc_bits": bits})

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["p_chip", "ber_theory", "ber_mc",
                                           "mc_errors", "mc_bits"])
        w.writeheader()
        w.writerows(rows)

    _plot(out_png, p_theory, theory, p_mc, mc_ber)
    return rows


def _plot(out_png, p_theory, theory, p_mc, mc_ber):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.semilogy(p_theory, theory, "-", color="C0",
                label="DBPSK theory  2·p_sym(1−p_sym), Barker-11")
    # MC points may contain zeros (no errors observed); mask those for the log plot.
    xs = [p for p, b in zip(p_mc, mc_ber) if b > 0]
    ys = [b for b in mc_ber if b > 0]
    ax.semilogy(xs, ys, "o", color="C3", label="golden-model Monte-Carlo")
    ax.set_xlabel("injected chip-flip probability  p_chip")
    ax.set_ylabel("bit error rate (PHY, post-differential)")
    ax.set_title("BarkerLink DBPSK BER vs injected chip-flip noise")
    ax.set_ylim(1e-4, 1e0)
    ax.grid(True, which="both", ls=":", alpha=0.6)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parents[1]
    png = root / "docs" / "img" / "ber_dbpsk.png"
    csvp = root / "model" / "ber_curve.csv"
    rows = generate(png, csvp)
    print(f"wrote {png.relative_to(root)} and {csvp.relative_to(root)}\n")
    print(f"{'p_chip':>8} {'BER theory':>12} {'BER MC':>12} {'errors':>8} {'bits':>9}")
    for r in rows:
        print(f"{r['p_chip']:>8.3f} {r['ber_theory']:>12.3e} "
              f"{r['ber_mc']:>12.3e} {r['mc_errors']:>8d} {r['mc_bits']:>9d}")


if __name__ == "__main__":
    main()
