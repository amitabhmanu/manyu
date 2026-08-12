"""Plots for experiment 6, one per pre-registered question.

Methodology section 6 fixes the rule: no plot is produced for anything not
registered, and the direct arm is excluded from any calibration figure because
plotting a regression test on a calibration chart puts a perfect diagonal in the
figure carrying the headline.

**`calibration.png` is deliberately not produced offline.** The only two arms
available without a provider are the direct path (agreement by construction) and
the one-way topology proxy, and both agree to within the store's 6-decimal
rounding. A calibration chart of those would be a diagonal with no residual --
exactly the misleading figure the rule above exists to prevent. It belongs to
stage 4, where a real extractor supplies the divergence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from manyu.counterfactual import critical_arrival_ratio, dose_for_standoff  # noqa: E402

OUT = REPO / "docs" / "experiments" / "06-what-would-change-my-mind" / "plots"
STAGES = REPO / "evals" / "analysis" / "exp06" / "stages.jsonl"
THRESHOLD = 0.45


def _rows() -> list[dict]:
    return [json.loads(line) for line in STAGES.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dose_curves(plt) -> None:
    """Pre-registration section 4.1 — the k=5 versus k=10 inversion."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for shared, label, colour in ((2, "symmetric_rivals (2 shared)", "#1f77b4"), (6, "near_miss (6 shared)", "#d62728")):
        dose = dose_for_standoff(shared, threshold=THRESHOLD, bound=14)
        xs = range(1, len(dose.trajectory) + 1)
        ax.plot(xs, dose.trajectory, marker="o", ms=4, label=f"{label} — dose {dose.records}", color=colour)
        if dose.records:
            ax.axvline(dose.records, color=colour, ls=":", lw=1, alpha=0.6)

    ax.axhline(THRESHOLD, color="k", ls="--", lw=1, label=f"expression threshold {THRESHOLD}")
    ax.set_xlabel("separating records delivered")
    ax.set_ylabel("meta-belief confidence")
    ax.set_title("A ratio cancels cardinality; the marginal record does not")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "dose_curves.png", dpi=150)
    plt.close(fig)


def _arrival_ratio(plt) -> None:
    """Pre-registration section 4.4 — the phase transition.

    The analytic asymptote is drawn as a line and the simulated doses as points.
    Showing only the points would make a divergence look like a steep curve, and
    the registered claim is that it is an asymptote: the difference between
    'expensive' and 'impossible' is the finding.
    """
    r_star = critical_arrival_ratio(THRESHOLD)
    ratios = [1.25, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 6.0]
    doses = [dose_for_standoff(2, arrival_ratio=r, threshold=THRESHOLD).records for r in ratios]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.axvspan(0.9, r_star, color="#d62728", alpha=0.12)
    ax.axvline(r_star, color="#d62728", ls="--", lw=1.4, label=f"r* = 11/9 ≈ {r_star:.3f}")
    ax.plot(ratios, doses, marker="o", ms=5, color="#1f77b4", label="records to cross 0.45")
    ax.text(1.0, max(d for d in doses if d) * 0.55, "unfalsifiable\nin principle", color="#d62728", fontsize=9, ha="center")

    ax.set_yscale("log")
    ax.set_xlabel("arrival ratio r  (separating records per shared record)")
    ax.set_ylabel("records to cross the threshold (log)")
    ax.set_title("Below r* the dose is not large — it is infinite")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "arrival_ratio.png", dpi=150)
    plt.close(fig)


def _entrenchment(plt) -> None:
    """Pre-registration section 4.3 — monotonicity, where a falling point is a defect."""
    census = next(r for r in _rows() if r["check"] == "entrenchment_census")
    observations = census["observations"]
    stability = [o["meta_stability"] for o in observations]
    doses = [o["dose"] for o in observations]
    labels = [o["corroborations"] for o in observations]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(stability, doses, marker="s", ms=6, color="#2ca02c")
    for x, y, n in zip(stability, doses, labels):
        ax.annotate(f"{n} corrob.", (x, y), textcoords="offset points", xytext=(6, -10), fontsize=7)

    ax.set_xlabel("meta-belief stability reached (accumulated, not authored)")
    ax.set_ylabel("records to cross the threshold")
    ax.set_title("Dose rises with entrenchment — positive control")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "entrenchment_census.png", dpi=150)
    plt.close(fig)


def main() -> int:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed; install the `analysis` extra")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    _dose_curves(plt)
    _arrival_ratio(plt)
    _entrenchment(plt)
    print(f"  wrote 3 plots to {OUT.relative_to(REPO)}")
    print("  calibration.png deliberately not produced offline — see module docstring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
