"""Experiment 7 — every published figure re-derived from the artifacts.

On experiment 5's and 6's pattern: the JSONL is read, and every headline claim is
**recomputed** rather than looked up. So a number cannot drift from its evidence
without something here going red.

`test_the_derivability_check_can_itself_fail` is the positive control, and it is
not decoration. Experiment 5's best catch was a check in its own battery that was
itself random and went green about half the time; experiment 6 shipped two checks
that passed for the wrong reason, and this experiment's own stage 2 produced a
vacuous null -- comparing a null reading to a null reading -- before its positive
control caught it. A derivability check that cannot fail is the same family.

Skipped rather than failed when the runners have not been run: a fresh clone has no
artifacts and a red suite there would say nothing about the code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STAGE_MINUS1 = REPO / "evals" / "analysis" / "exp07" / "stage_minus1.jsonl"
STAGES = REPO / "evals" / "analysis" / "exp07" / "stages.jsonl"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"{path.name} not produced yet; run evals/analysis/exp07/")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _by_check(path: Path) -> dict[str, dict]:
    return {row["check"]: row for row in _rows(path)}


# --- stage -1 -----------------------------------------------------------------


def test_stage_minus1_gate_passed_and_the_count_is_recomputed() -> None:
    """The verdict is recomputed from the rows, not read off the verdict row."""
    rows = _rows(STAGE_MINUS1)
    verdict = rows[-1]
    assert verdict["check"] == "verdict"

    checks = [row for row in rows if "agrees" in row and row["check"] != "verdict"]
    failed = [row["check"] for row in checks if not row["agrees"]]

    assert len(checks) == verdict["checks_run"], "the verdict's own count disagrees with the rows"
    assert failed == verdict["failed"]
    assert verdict["gate_passed"] is (not failed)
    assert verdict["gate_passed"], f"stage -1 gate failed: {failed}"


def test_six_channels_confirmed_and_one_retracted() -> None:
    """The census total, recomputed from the per-channel rows."""
    by_check = _by_check(STAGE_MINUS1)
    channels = [row for check, row in by_check.items() if check.startswith("channel_reproduces__")]

    # `honest_web` is the negative control, not a channel.
    real = [row for row in channels if row["channel"] != "negative_control"]
    assert len(real) == 5, "five belief-level channels have a fixture row"
    assert all(row["agrees"] for row in channels)

    # The sixth is the rewrite channel, which is recorded in its own row because it
    # is only detectable against a snapshot.
    assert by_check["provenance_is_immutable_only_where_snapshotted"]["agrees"]
    assert by_check["verdict"]["channels_confirmed"] == 6
    assert by_check["verdict"]["channels_retracted"] == 1
    assert by_check["deprecated_is_unreachable"]["agrees"], "the retraction must be asserted, not asserted-about"


def test_the_substrate_agent_split_is_three_and_three() -> None:
    """Pre-registration section 1.7's headline, recomputed from the rows.

    Three channels reachable only by an agent, three by the substrate alone. This
    is the claim the results quote, so it is derived here rather than trusted.
    """
    rows = _rows(STAGE_MINUS1)
    sides: dict[str, set[str]] = {"agent": set(), "substrate": set()}
    for row in rows:
        if row["check"].startswith("channel_reproduces__") and row.get("reachable_by") in sides:
            sides[row["reachable_by"]].add(row["channel"])

    # The rewrite channel is agent-reachable and lives in its own row.
    sides["agent"].add("in_place_evidence_rewrite")

    assert sides["agent"] == {"status_suppression", "weight_deflation", "in_place_evidence_rewrite"}
    assert sides["substrate"] == {"stale_assertion", "one_of_n_stance_prose", "receipt_mismatch"}
    assert len(sides["agent"]) == 3 and len(sides["substrate"]) == 3


def test_status_channel_base_rate_is_zero_and_the_corpus_is_declared_fit() -> None:
    """The measurement the headline rests on, with its fitness claim attached."""
    row = _by_check(STAGE_MINUS1)["census_status_channel_base_rate"]
    assert row["below_expression_threshold"] == 0
    assert row["statuses"].get("tentative", 0) == 0
    assert row["min_confidence"] > 0.45
    assert row["beliefs"] > 0
    assert row["fit_to_decide"] is True, "a base rate from an unfit corpus cannot carry the headline"
    assert "agrees" not in row, "a census is not a prediction that can pass"


def test_prose_loss_exceeds_the_registered_line_on_every_web() -> None:
    """Why the prose criterion was retired (amendment A1), recomputed per web."""
    row = _by_check(STAGE_MINUS1)["census_prose_loss_per_web"]
    webs = row["webs"]
    assert webs, "no stored webs were measured"

    recomputed = [round(1 - web["themes"] / web["beliefs"], 6) for web in webs]
    assert recomputed == [web["prose_loss"] for web in webs], "the per-web loss does not follow from its own counts"

    assert min(recomputed) > 2 / 3, "the registered 2/3 line was not cleared by every web"
    assert row["webs_above_the_line"] == len(webs)
    assert row["fit_to_decide"] is True


def test_theme_ceiling_is_seven_from_eight_belief_types() -> None:
    """The corrected ceiling. Registered as six in the first draft, by miscounting."""
    row = _by_check(STAGE_MINUS1)["theme_ceiling"]
    assert row["belief_type_members"] == 8
    assert row["distinct_themes"] == 7
    assert row["registered"] == 7
    assert len(row["themes"]) == 7
    assert row["agrees"]


def test_the_status_trajectory_matches_the_hand_derivation() -> None:
    """Pre-registration section 0.1, and the two halves reported separately."""
    row = _by_check(STAGE_MINUS1)["status_trajectory_driven"]
    assert row["predicted"] == [0.6516, 0.7609, 0.8193, 0.8516, 0.8700]
    assert row["max_abs_error"] < row["tolerance"]
    assert row["confidences_agree"]
    assert row["status_never_promoted"], "the load-bearing half"
    assert set(row["statuses"]) == {"tentative"}
    assert row["observed"][-1] > 0.86, "and it climbs while staying tentative"


def test_snapshot_coverage_is_reported_as_unfit_rather_than_answered() -> None:
    """Pre-registration section 1.5 registered coverage below 0.10. It came out 1.0.

    The corpus is dominated by experiment 1's runs, which exist *because* they
    snapshot, so the number describes what experiment 1 was built to do. The
    registered prediction is therefore neither confirmed nor refuted, and the row
    must say so rather than reporting 1.0 as a finding -- which would be experiment
    4's Stage 0a defect with the sign flipped.
    """
    row = _by_check(STAGE_MINUS1)["census_snapshot_coverage"]
    assert row["fit_to_decide"] is False
    assert row["why_not"], "an unfit census must record why"
    assert "agrees" not in row


# --- stage 0 ------------------------------------------------------------------


def test_honest_web_is_clean_and_that_is_the_specificity_gate() -> None:
    by_check = _by_check(STAGES)
    assert by_check["detector__honest_web"]["divergences"] == 0
    assert by_check["detector_summary"]["specificity_flags_on_honest_web"] == 0
    assert by_check["detector_summary"]["agrees"]


def test_every_criterion_row_agrees_with_the_registered_matrix() -> None:
    """Amendment A5's corrected matrix, checked row by row from the artifact."""
    rows = [row for row in _rows(STAGES) if row["check"].startswith("detector__")]
    assert len(rows) == 6

    for row in rows:
        assert row["criteria"] == row["registered_criteria"], f"{row['check']} drifted from the registered matrix"
        assert row["agrees"]

    caught = [row for row in rows if row["criteria"]]
    missed = [row for row in rows if not row["criteria"] and row["check"] != "detector__honest_web"]
    assert len(caught) == 3, "three fixture rows fire: two channels plus the receipt web's second channel"
    assert {row["check"] for row in missed} == {"detector__crowded_theme", "detector__weight_deflated"}


def test_every_sensitivity_row_carries_its_own_base_rate() -> None:
    """FR-7, and it is about the *row* rather than the file.

    A base rate one table away from the number it qualifies is a base rate nobody
    reads, which is how experiment 4's Stage 0a produced a finding that described
    its instrument.
    """
    for row in _rows(STAGES):
        if not row["check"].startswith("detector__"):
            continue
        assert "prose_loss_base_rate" in row, f"{row['check']} reports sensitivity with no base rate"
        assert row["beliefs"] > 0
        recomputed = round(1 - row["themes"] / row["beliefs"], 6)
        assert recomputed == pytest.approx(row["prose_loss_base_rate"]), f"{row['check']}: base rate not derivable"


def test_every_mutant_still_differs_from_the_real_detector() -> None:
    """The battery in the scored run, not only in the test suite."""
    rows = [row for row in _rows(STAGES) if row["check"].startswith("mutant__")]
    assert len(rows) == 5
    for row in rows:
        assert row["differs_from_real_detector"], f"{row['check']} stopped differing and is no longer a mutant"
        assert row["agrees"]


def test_the_attribution_mutant_changes_no_count() -> None:
    """The dangerous one: identical divergences, inverted attribution.

    It is caught by cause comparison alone, so its row must show equal counts --
    otherwise it is being caught for the wrong reason and FR-10 is untested.
    """
    row = _by_check(STAGES)["mutant__reports_substrate_filter_as_agent"]
    assert row["real_divergences"] == row["mutant_divergences"] > 0
    assert row["differs_from_real_detector"], "it differs only in `cause`, and that must be enough"


# --- stage 1 ------------------------------------------------------------------


def test_fixture_attribution_is_labelled_a_regression_test() -> None:
    """Amendment A3. Perfect by construction, and it must say so."""
    row = _by_check(STAGES)["attribution_on_fixtures"]
    assert row["role"] == "regression_test_never_evidence"
    assert row["rate"] == 1.0
    assert row["attributed"] == row["total"] > 0


def test_stored_web_attribution_is_declared_unavailable_offline() -> None:
    """The honest consequence of A3: the figure that would mean something is not
    obtainable from a corpus with no public surfaces, and the row says so instead
    of substituting the fixture number."""
    row = _by_check(STAGES)["attribution_on_stored_webs"]
    assert row["fit_to_decide"] is False
    assert "why_not" in row and row["why_not"]
    assert "agrees" not in row
    assert row["webs"] > 0, "the shapes are still measured even though the rate is not"
    assert row["webs_with_a_status_channel"] == 0, "consistent with the zero base rate at stage -1"


# --- stage 2 ------------------------------------------------------------------


def test_composition_null_is_readable_rather_than_vacuous() -> None:
    """The null, plus the thing that makes it mean anything.

    An earlier draft of this stage compared two webs that each had no dissonance
    signal, so "identical" was true of nothing. `reading_is_readable` is what
    distinguishes a null from an absence.
    """
    row = _by_check(STAGES)["composition_changes_no_substrate_reading"]
    assert row["identical"], "something downstream reads whether a belief was composed"
    assert row["reading_is_readable"], "the null is vacuous unless there was a reading to change"
    assert row["uncomposed"]["signal_present"] and row["composed"]["signal_present"]
    assert row["uncomposed"]["magnitude_raw"] is not None
    assert row["stances_built"] > 0, "and a stance was actually built between the two reads"


def test_the_positive_control_moved_the_same_measurement() -> None:
    row = _by_check(STAGES)["positive_control_the_reading_can_move"]
    assert row["assertion_status"] == "ok", "an error dict produces no change and would fake this"
    assert row["moved"]
    assert row["before"] != row["after"]
    assert row["agrees"]


def test_no_row_anywhere_reads_the_barred_channels() -> None:
    """FR-8: `magnitude` is concave in raw tension and `stake_of` averages rather
    than sums, so neither may carry a reading."""
    for path in (STAGE_MINUS1, STAGES):
        for row in _rows(path):
            flat = json.dumps(row)
            assert '"magnitude"' not in flat, f"{row['check']} reads DissonanceSignal.magnitude"
            assert '"stake"' not in flat, f"{row['check']} reads stake_of"


# --- the positive control on this file ----------------------------------------


def test_the_derivability_check_can_itself_fail() -> None:
    """Proof that the recomputation above is not vacuous.

    Corrupt a row's counts in memory and confirm the derivation notices. Without
    this, every assertion in this file could be comparing a number to itself.
    """
    row = dict(_by_check(STAGES)["detector__crowded_theme"])
    recomputed = round(1 - row["themes"] / row["beliefs"], 6)
    assert recomputed == pytest.approx(row["prose_loss_base_rate"])

    corrupted = dict(row, themes=row["themes"] + 1)
    assert round(1 - corrupted["themes"] / corrupted["beliefs"], 6) != pytest.approx(row["prose_loss_base_rate"])

    # And the matrix check must notice a drifted criterion set.
    drifted = dict(row, criteria=["within_group"])
    assert drifted["criteria"] != drifted["registered_criteria"]
