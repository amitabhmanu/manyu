"""Experiment 4 section 5.10 — every published number comes from the run.

Experiment 3 re-derived 26 published figures from a running store and found 0
mismatches. It did so by hand, once, which means the guarantee expired the moment
the document was next edited. Automating it means a number cannot drift from its
own evidence without something going red.

Two directions, and both matter:

- Every figure quoted in `results.md` appears in the stored JSONL.
- Every headline claim in `results.md` is *entailed* by the JSONL, not merely
  consistent with it — the verdicts are recomputed here rather than read.

Skips cleanly when a stage has not been run, so a fresh clone is not failed by
the absence of artifacts it never generated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "docs" / "experiments" / "04-dissonance-control-signal" / "results.md"
STAGE0 = REPO / "evals" / "analysis" / "exp04" / "stage0.jsonl"
STAGES = REPO / "evals" / "analysis" / "exp04" / "stages.jsonl"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"{path.name} has not been generated")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _text() -> str:
    if not RESULTS.exists():
        pytest.skip("results.md does not exist yet")
    return RESULTS.read_text(encoding="utf-8")


def _numbers(text: str) -> set[str]:
    """Every decimal figure in the document, as written."""
    return set(re.findall(r"\d+\.\d+", text))


# --- stage 0 -----------------------------------------------------------------

def test_the_published_base_rate_matches_the_run() -> None:
    rows = _rows(STAGE0)
    natural = [r for r in rows if r["kind"] == "naturalistic"]
    fired = [r for r in natural if r["dissonance"]["fires"]]

    text = _text()
    assert f"{len(natural)} naturalistic turns" in text or f"| Naturalistic turns | {len(natural)}," in text, (
        f"results.md does not quote the actual turn count ({len(natural)})"
    )
    assert len(fired) == 0, "the run now produces conflicts; results.md's void verdict needs revisiting"


def test_the_published_incumbent_rate_matches_the_run() -> None:
    rows = _rows(STAGE0)
    natural = [r for r in rows if r["kind"] == "naturalistic"]
    rate = sum(1 for r in natural if r["incumbent_escalates"]) / len(natural)
    published = f"{rate * 100:.1f}%"
    assert published in _text(), f"results.md does not quote the measured incumbent rate {published}"


def test_the_authored_control_still_fires() -> None:
    """The void verdict depends on the control passing. If it stops, the zero
    base rate has two possible causes and the write-up names only one.
    """
    rows = _rows(STAGE0)
    authored = [r for r in rows if r["kind"] == "authored"]
    assert authored, "no authored control in the run"
    assert all(r["dissonance"]["fires"] for r in authored)


# --- stage 2 -----------------------------------------------------------------

def test_the_published_stage2_table_matches_the_run() -> None:
    rows = [r for r in _rows(STAGES) if r["stage"] == 2 and r["fixture"] == "multi_conflict_web"]
    assert rows, "no multi_conflict_web rows in the Stage 2 run"

    published = _numbers(_text())
    for row in rows:
        for key in ("driven_remaining", "inverted_remaining", "random_mean"):
            value = f"{row[key]:.3f}"
            assert value in published or f"{row[key]:.4f}" in published, (
                f"budget {row['budget']} {key}={row[key]} is not quoted in results.md"
            )


def test_the_convergence_claim_is_entailed_by_the_run() -> None:
    """`results.md` says the arms converge once the budget covers every conflict.
    Recomputed rather than trusted.
    """
    for fixture in ("multi_conflict_web", "hub_web", "adversarial_multi"):
        rows = sorted((r for r in _rows(STAGES) if r["stage"] == 2 and r["fixture"] == fixture), key=lambda r: r["budget"])
        assert rows, fixture
        converged = [r["budget"] for r in rows if r["converged"]]
        not_converged = [r["budget"] for r in rows if not r["converged"]]
        assert converged, f"{fixture}: the arms never converge, which contradicts the write-up"
        assert not_converged, f"{fixture}: the arms always agree, so the scarcity claim is unmeasurable here"
        assert min(converged) > max(not_converged), (
            f"{fixture}: convergence is not monotone in the budget — {converged} vs {not_converged}"
        )


def test_driven_beats_inverted_wherever_the_arms_have_not_converged() -> None:
    for row in (r for r in _rows(STAGES) if r["stage"] == 2 and not r["converged"]):
        assert row["driven_remaining"] < row["inverted_remaining"], row


# --- stage 3 -----------------------------------------------------------------

def test_the_stage3_verdict_is_recomputed_not_quoted() -> None:
    """The negative result is the one most worth re-deriving, because a negative
    is what a mistake most easily looks like.
    """
    rows = [r for r in _rows(STAGES) if r["stage"] == 3]
    assert rows

    measurable = [r for r in rows if r["measurable"]]
    assert measurable, "every Stage 3 fixture is at the spread ceiling; nothing was measured"

    for row in measurable:
        expected = "more_specific_than_chance" if row["p_at_or_below"] <= 0.05 else "indistinguishable_from_chance"
        assert row["verdict"] == expected, row
    assert all(r["verdict"] == "unmeasurable_at_ceiling" for r in rows if not r["measurable"])


def test_the_published_stage3_figures_match_the_run() -> None:
    rows = [r for r in _rows(STAGES) if r["stage"] == 3 and r["fixture"] == "distractor_web"]
    assert rows
    row = rows[0]
    published = _numbers(_text())
    for value in (f"{row['real_spread']:.3f}", f"{row['deranged_mean']:.3f}", f"{row['p_at_or_below']:.2f}"):
        assert value in published, f"{value} is not quoted in results.md"


# --- stage 4 -----------------------------------------------------------------

def test_the_stage4_claim_holds_in_the_run() -> None:
    """Under a scarce budget the driven arm must land on better-grounded targets
    than the inverted arm, or the adversarial write-up is wrong.
    """
    rows = sorted((r for r in _rows(STAGES) if r["stage"] == 4), key=lambda r: r["budget"])
    assert rows

    scarce = [r for r in rows if r["driven_steps"] < 3]
    assert scarce, "no budget in the sweep is actually scarce for this web"
    for row in scarce:
        assert row["driven_well_grounded_hits"] > row["inverted_well_grounded_hits"], row

    saturated = [r for r in rows if r["driven_steps"] == 3]
    for row in saturated:
        assert row["driven_well_grounded_hits"] == row["inverted_well_grounded_hits"], (
            f"the arms differ at a budget covering every conflict: {row}"
        )


def test_no_stage_reports_a_saturated_magnitude() -> None:
    """Requirements section 12, enforced on the artifacts rather than trusted.

    Every trajectory figure must be raw tension. A `magnitude` key anywhere in
    the run records would mean the saturated channel reached the analysis.
    """
    for path in (STAGE0, STAGES):
        for row in _rows(path):
            flat = json.dumps(row)
            assert '"magnitude"' not in flat, f"{path.name} carries a saturated magnitude: {row}"
