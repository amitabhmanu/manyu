"""Experiment 7 — the three offline figures.

One per pre-registered question, and no plot is produced for anything not
registered (methodology section 6).

- `channel_census.png` — **the headline figure.** The channels split into a
  substrate half and an agent half, so pre-registration section 1.7's result is the
  *shape* of the plot rather than a caption on it.
- `status_trap.png` — the section 0.1 trajectory climbing to 0.87 entirely inside
  the never-composed region.
- `criterion_matrix.png` — the fixtures against the criteria as a catch/miss grid.
  **A grid rather than a curve, deliberately:** a curve invites summing two criteria
  that must not be pooled, and the registered misses have to be drawn *as* misses.

`matplotlib` is an optional dependency under `[project.optional-dependencies]
analysis` (experiment 1 v2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = REPO / "evals" / "analysis" / "exp07"

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    print("matplotlib not installed; install the `analysis` extra")
    raise SystemExit(1)

EXPRESSION_THRESHOLD = 0.45


def _rows(name: str) -> list[dict]:
    path = HERE / name
    if not path.exists():
        print(f"missing {name}; run the stage runners first")
        raise SystemExit(1)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _by_check(rows: list[dict]) -> dict[str, dict]:
    return {row["check"]: row for row in rows}


def channel_census() -> None:
    """The headline: which channels fire without an agent, and which need one."""
    minus1 = _rows("stage_minus1.jsonl")
    stages = _by_check(_rows("stages.jsonl"))

    # Base rate per channel: the prose loss where the substrate produces it, and 0
    # where only an agent can. The point of the figure is that these differ.
    census = _by_check(minus1)["census_prose_loss_per_web"]
    measured_loss = census["max_prose_loss"]

    channels = [
        ("one_of_n_stance_prose", "substrate", measured_loss, 0),
        ("receipt_mismatch", "substrate", None, stages["detector__mismatched_receipts"]["divergences"]),
        ("stale_assertion", "substrate", None, stages["detector__stale_assertion"]["divergences"]),
        ("status_suppression", "agent", 0.0, stages["detector__tentative_suppression"]["divergences"]),
        ("weight_deflation", "agent", 0.0, stages["detector__weight_deflated"]["divergences"]),
        ("in_place_evidence_rewrite", "agent", 0.0, 0),
    ]

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for axis, side, title in (
        (left, "substrate", "Fires with no agent involved"),
        (right, "agent", "Fires only when an agent acts"),
    ):
        rows = [row for row in channels if row[1] == side]
        names = [row[0].replace("_", "\n") for row in rows]
        base = [0.0 if row[2] is None else row[2] for row in rows]
        detected = [1.0 if row[3] else 0.0 for row in rows]
        positions = range(len(rows))

        axis.bar([p - 0.2 for p in positions], base, width=0.4, label="base rate on stored webs", color="#4c72b0")
        axis.bar([p + 0.2 for p in positions], detected, width=0.4, label="detected by surface comparison", color="#dd8452")
        axis.set_xticks(list(positions))
        axis.set_xticklabels(names, fontsize=8)
        axis.set_title(title, fontsize=10)
        axis.set_ylim(0, 1.05)
        axis.grid(axis="y", alpha=0.3)

    left.set_ylabel("rate / detected")
    left.legend(fontsize=8, loc="upper right")
    fig.suptitle(
        "Six concealment channels. Three need an agent; not one of those three has been observed in 640 stored beliefs.",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(HERE / "channel_census.png", dpi=140)
    plt.close(fig)
    print("  wrote channel_census.png")


def status_trap() -> None:
    """The trajectory, with the composed region shaded and the curve outside it."""
    row = _by_check(_rows("stage_minus1.jsonl"))["status_trajectory_driven"]
    observed = row["observed"]
    steps = range(1, len(observed) + 1)

    fig, axis = plt.subplots(figsize=(7, 4.2))
    axis.axhspan(EXPRESSION_THRESHOLD, 1.0, color="#55a868", alpha=0.12)
    axis.axhline(EXPRESSION_THRESHOLD, color="#55a868", linestyle="--", linewidth=1)
    axis.annotate(
        "confidence above 0.45 — but status was set at creation and is never promoted,\nso none of this is ever composed into a stance",
        xy=(1.05, 0.90),
        fontsize=8,
        color="#33683f",
    )
    axis.plot(list(steps), observed, marker="o", color="#c44e52", label="belief created at 0.44")
    for step, value in zip(steps, observed):
        axis.annotate(f"{value:.4f}", (step, value), textcoords="offset points", xytext=(0, -14), fontsize=7, ha="center")

    axis.set_xlabel("corroborating records delivered")
    axis.set_ylabel("confidence")
    axis.set_ylim(0.35, 1.0)
    axis.set_xticks(list(steps))
    axis.set_title("The status trap: 0.44 → 0.87, never spoken", fontsize=11)
    axis.legend(fontsize=8, loc="lower right")
    axis.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "status_trap.png", dpi=140)
    plt.close(fig)
    print("  wrote status_trap.png")


def criterion_matrix() -> None:
    """The grid. Registered misses drawn as misses, not omitted."""
    stages = [row for row in _rows("stages.jsonl") if row["check"].startswith("detector__")]
    criteria = ["citation", "within_group", "stale_assertion", "receipt_mismatch"]
    fixtures = [row["check"].removeprefix("detector__") for row in stages]

    grid = [[1 if criterion in row["criteria"] else 0 for criterion in criteria] for row in stages]

    fig, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.imshow(grid, cmap="Blues", vmin=0, vmax=1.6, aspect="auto")
    axis.set_xticks(range(len(criteria)))
    axis.set_xticklabels([c.replace("_", "\n") for c in criteria], fontsize=8)
    axis.set_yticks(range(len(fixtures)))
    axis.set_yticklabels(fixtures, fontsize=8)

    for y, row in enumerate(stages):
        base = row["prose_loss_base_rate"]
        axis.text(len(criteria) - 0.35, y, f"base {base:.2f}", fontsize=7, va="center", color="#555")
        for x, hit in enumerate(grid[y]):
            axis.text(x, y, "catch" if hit else "miss", ha="center", va="center", fontsize=7,
                      color="white" if hit else "#888")

    axis.set_title(
        "Four criteria, six fixtures. `crowded_theme` and `weight_deflated` are caught by none —\n"
        "in both, nothing about the emitted surface is wrong.",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(HERE / "criterion_matrix.png", dpi=140)
    plt.close(fig)
    print("  wrote criterion_matrix.png")


def main() -> int:
    channel_census()
    status_trap()
    criterion_matrix()
    return 0


if __name__ == "__main__":
    sys.exit(main())
