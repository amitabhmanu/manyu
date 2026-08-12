"""Every published number comes from the run.

Experiment 3 re-derived 26 published figures from a running store and found 0
mismatches — by hand, once, so the guarantee expired the moment the document was
next edited. Experiment 4 automated it. This does the same for experiment 5.

Two directions, and both matter:

- every figure quoted in `results.md` appears in the stored JSONL;
- every headline claim is **recomputed** here rather than read, so a verdict
  cannot drift from its evidence without something going red.

Skips cleanly when a stage has not been run, so a fresh clone is not failed by
the absence of artifacts it never generated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "docs" / "experiments" / "05-underdetermination" / "results.md"
STAGE0 = REPO / "evals" / "analysis" / "exp05" / "stage0.jsonl"
STAGES = REPO / "evals" / "analysis" / "exp05" / "stages.jsonl"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"{path.name} has not been generated")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _text() -> str:
    if not RESULTS.exists():
        pytest.skip("results.md does not exist yet")
    return RESULTS.read_text(encoding="utf-8")


def _verdict(path: Path) -> dict:
    for row in _rows(path):
        if row["kind"] == "verdict":
            return row
    pytest.fail(f"{path.name} carries no verdict row")


def _by_kind(path: Path, kind: str) -> list[dict]:
    return [row for row in _rows(path) if row["kind"] == kind]


# --- stage 0 -----------------------------------------------------------------


def test_the_published_gaps_match_the_run() -> None:
    verdict = _verdict(STAGE0)
    assert verdict["mutual_gap"] == 0.0
    assert verdict["oneway_gap"] == pytest.approx(0.233333, abs=1e-6)
    text = _text()
    assert "0.0000" in text and "0.2333" in text


def test_the_standoff_and_collapse_verdicts_are_recomputed() -> None:
    """The pre-registered bands, applied here rather than trusted from the runner."""
    verdict = _verdict(STAGE0)
    assert verdict["mutual_gap"] <= 0.01, "mutual pair is not a standoff by the pre-registered band"
    assert verdict["oneway_gap"] >= 0.10, "one-way pair is not a collapse by the pre-registered band"
    assert verdict["mutual_verdict"] == "standoff"
    assert verdict["oneway_verdict"] == "collapse"


def test_the_priced_pair_is_inert_and_the_unpriced_one_is_not() -> None:
    """§1's claim that the alphabetical tie-break is unreachable on a live web,
    with the positive control that stops "inert" meaning "the loop is broken".
    """
    verdict = _verdict(STAGE0)
    assert verdict["priced_pair_is_inert"] is True
    assert verdict["unpriced_pair_moves"] is True


def test_the_base_rate_is_recorded_as_unanswerable_offline() -> None:
    verdict = _verdict(STAGE0)
    assert verdict["generation_path_can_contradict"] is False
    assert verdict["offline_base_rate_answerable"] is False
    assert "unanswerable offline" in _text()


def test_the_confidences_in_the_topology_table_match_the_run() -> None:
    rows = {r["fixture"]: r for r in _by_kind(STAGE0, "stage0") if r["path"] == "priced_ingest"}
    mutual = rows["symmetric_rivals"]["confidences"]
    oneway = rows["symmetric_rivals_oneway"]["confidences"]

    assert mutual["reading_a"] == mutual["reading_b"] == pytest.approx(0.466667, abs=1e-6)
    assert oneway["reading_a"] == pytest.approx(0.7)
    assert oneway["reading_b"] == pytest.approx(0.466667, abs=1e-6)
    text = _text()
    assert "0.4667" in text and "0.7000" in text


# --- stage 2 -----------------------------------------------------------------


def test_the_control_set_table_matches_the_run() -> None:
    rows = {row["fixture"]: row for row in _by_kind(STAGES, "stage2")}
    assert rows["symmetric_rivals"]["rival_sets"] == 1
    assert rows["symmetric_rivals_oneway"]["rival_sets"] == 1
    assert rows["near_miss"]["rival_sets"] == 1
    assert rows["shared_evidence_no_conflict"]["rival_sets"] == 0
    assert rows["conflict_disjoint_evidence"]["rival_sets"] == 0
    assert rows["three_way"]["rival_sets"] == 3
    for name in ("symmetric_rivals", "symmetric_rivals_oneway", "near_miss", "three_way"):
        assert all(value == 1.0 for value in rows[name]["confidences"])


def test_the_near_miss_delta_is_recomputed_not_read() -> None:
    """The load-bearing claim: a ratio cancels cardinality, so three times the
    evidence gives the identical value.
    """
    rows = {row["fixture"]: row for row in _by_kind(STAGES, "stage2")}
    delta = abs(rows["near_miss"]["confidences"][0] - rows["symmetric_rivals"]["confidences"][0])
    assert delta == 0.0
    assert delta <= 0.05, "pre-registered near-miss tolerance"
    assert _verdict(STAGES)["near_miss_delta"] == 0.0


def test_both_negatives_decline() -> None:
    assert _verdict(STAGES)["negatives_declined"] is True


def test_the_collapse_figures_match_and_meet_the_pre_registered_minimum() -> None:
    collapse = _by_kind(STAGES, "stage2_collapse")[0]
    assert collapse["phase_1_confidence"] == 1.0
    assert collapse["phase_2_overlap"] == pytest.approx(0.666667, abs=1e-6)
    assert collapse["phase_2_confidence"] == pytest.approx(0.846667, abs=1e-6)
    assert collapse["moved"] == pytest.approx(0.153333, abs=1e-6)
    assert collapse["moved"] >= 0.15, "pre-registration §2 minimum"

    text = _text()
    for figure in ("0.6667", "0.8467", "0.1533"):
        assert figure in text, f"{figure} is published but not derivable from the run"


def test_the_state_is_still_expressed_after_one_separating_record() -> None:
    """The uncomfortable half of §3.1, asserted so it cannot quietly disappear
    from the write-up.
    """
    collapse = _by_kind(STAGES, "stage2_collapse")[0]
    assert collapse["still_expressed"] is True
    assert "still expressed afterwards" in _text()


def test_the_collapse_trajectory_matches_and_is_monotone() -> None:
    rows = sorted(_by_kind(STAGES, "stage2_trajectory"), key=lambda r: r["separating_records"])
    values = [row["meta_confidence"] for row in rows]
    assert values == sorted(values, reverse=True), f"the trajectory is not monotone: {values}"

    expected = [0.847, 0.694, 0.571, 0.476, 0.404, 0.348]
    assert [round(value, 3) for value in values] == expected

    retired = [row["separating_records"] for row in rows if not row["still_expressed"]]
    assert min(retired) == 5, "the published 'five observations' figure does not match the run"
    assert _verdict(STAGES)["separating_records_to_stop_expressing"] == 5
    assert "five separating observations" in _text()

    text = _text()
    for figure in ("0.847", "0.694", "0.571", "0.476", "0.404", "0.348"):
        assert figure in text


def test_the_ablation_is_shown_to_diverge() -> None:
    rows = {row["mode"]: row for row in _by_kind(STAGES, "stage2_ablation")}
    assert rows["strict"]["admits_after_separation"] == 0
    assert rows["graded"]["admits_after_separation"] == 1
    assert _verdict(STAGES)["ablation_diverges"] is True


# --- stage 3 -----------------------------------------------------------------


def test_the_meta_belief_does_not_move_under_any_attention_budget() -> None:
    rows = _by_kind(STAGES, "stage3_budget")
    assert rows, "the budget sweep produced no rows"
    assert {row["budget"] for row in rows} == {1, 2, 3, 4, 8}
    assert {row["arm"] for row in rows} == {"driven", "inverted"}
    assert all(row["meta_moved"] == 0.0 for row in rows)
    assert _verdict(STAGES)["loop_stability_meets_prereg"] is True


def test_non_separating_evidence_does_not_move_the_meta_belief() -> None:
    rows = _by_kind(STAGES, "stage3_evidence")
    assert len(rows) == 4
    assert all(row["overlap"] == 1.0 for row in rows), "overlap moved; the added evidence was not shared"
    assert all(row["meta_confidence"] == 1.0 for row in rows)
    assert all(row["still_expressed"] for row in rows)


def test_the_stability_pass_is_published_with_its_caveat() -> None:
    """§4 calls its own result weak because the loop never reaches the
    meta-belief. Pinned so the caveat cannot be dropped while the number stays.
    """
    assert _verdict(STAGES)["max_meta_moved_by_loop"] == 0.0
    assert _verdict(STAGE0)["priced_pair_is_inert"] is True
    assert "weak pass" in _text()


# --- stage 4 -----------------------------------------------------------------


def test_expression_holds_and_the_averaged_stance_survives() -> None:
    rows = _by_kind(STAGES, "stage4")
    assert {row["fixture"] for row in rows} == {"symmetric_rivals", "near_miss"}
    for row in rows:
        assert row["names_both_rivals"] is True
        assert row["cites_shared_evidence"] is True
        assert row["asserts_neither"] is True
        assert row["expresses_the_state"] is True
        assert row["meta_stance_emitted"] is True
        assert row["rival_stance_still_averaged"] is True, "§5.1's averaged stance was suppressed"


# --- the document as a whole -------------------------------------------------


def test_every_decimal_in_results_is_derivable_from_the_run() -> None:
    """The blunt direction: no figure may appear in the write-up that is not
    present in, or roundable from, the stored rows.

    Thresholds quoted from the pre-registration and from other experiments are
    exempted by name, because they are inputs rather than measurements.
    """
    published = set(re.findall(r"\d+\.\d+", _text()))

    known: set[str] = set()
    for path in (STAGE0, STAGES):
        for row in _rows(path):
            for value in _walk(row):
                known.add(str(value))
                known.add(f"{value:.3f}")
                known.add(f"{value:.4f}")
                known.add(f"{value:.6f}")

    exempt = {
        "0.15",  # pre-registration §2 minimum
        "0.05",  # pre-registration §3 tolerance
        "0.01",  # pre-registration §4 tolerance
        "0.10",  # pre-registration §0 collapse band
        "0.45",  # the substrate's TENTATIVE threshold
        "0.1",  # quoted from the Stage -1 status finding
        "0.0033",  # the published margin, stated as arithmetic in prose
        "67.9",  # experiment 1's SC-5
        "5.1", "5.2", "5.3", "6.1", "3.1", "3.2", "0.4", "0.7",  # section refs and fixture inputs
        "1.0", "0.0",
    }
    unexplained = sorted(published - known - exempt)
    assert not unexplained, f"figures in results.md with no source in the run: {unexplained}"


def test_the_derivability_check_would_catch_a_fabricated_figure() -> None:
    """The positive control for the check above.

    A guard that passes on everything catches nothing, and this one has a large
    exemption list — which is exactly the shape that quietly stops working.
    Rather than trusting the list, a figure that appears in no row is fed through
    the same comparison and must come out flagged.
    """
    known: set[str] = set()
    for path in (STAGE0, STAGES):
        for row in _rows(path):
            for value in _walk(row):
                known.update({str(value), f"{value:.3f}", f"{value:.4f}", f"{value:.6f}"})

    fabricated = "0.7391"
    assert fabricated not in known, "the fabricated control figure now appears in the run; pick another"
    published = set(re.findall(r"\d+\.\d+", _text() + f"\n\nA fabricated figure: {fabricated}."))
    assert fabricated in published - known, "the check cannot see a figure with no source"


def _walk(value) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk(child)]
    return []
