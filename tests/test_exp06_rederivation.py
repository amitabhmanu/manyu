"""Every published figure, re-derived from the artifacts rather than read.

Experiment 5's pattern. `results.md` quotes numbers; this file recomputes each
one from `stage_minus1.jsonl` and `stages.jsonl` and from the mechanism itself,
so a figure cannot drift from its evidence without something going red.

It also carries a positive control proving the derivability check can fail —
experiment 5 found that such checks acquire exemption lists and quietly stop
working, and a check that cannot fail is not a check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manyu import counterfactual as cf

REPO = Path(__file__).resolve().parents[1]
STAGE_MINUS1 = REPO / "evals" / "analysis" / "exp06" / "stage_minus1.jsonl"
STAGES = REPO / "evals" / "analysis" / "exp06" / "stages.jsonl"

#: Experiment 5 results section 3.1.
EXP5_PUBLISHED = (0.847, 0.694, 0.571, 0.476, 0.404, 0.348)


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"{path.name} not generated; run the stage runner first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _find(rows: list[dict], **match) -> dict:
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            return row
    raise AssertionError(f"no row matching {match}")


# --- the artifacts agree with themselves -------------------------------------


def test_stage_minus1_gate_passed():
    rows = _rows(STAGE_MINUS1)
    verdict = _find(rows, check="verdict")
    assert verdict["gate_passed"], f"stage -1 gate failed: {verdict['failed']}"
    assert verdict["checks_agreeing"] == verdict["checks_run"]


def test_stages_verdict_passed():
    rows = _rows(STAGES)
    verdict = _find(rows, check="verdict")
    assert verdict["passed"], f"stages failed: {verdict['failed']}"


# --- results.md section 1: the trajectory ------------------------------------


def test_published_trajectory_is_rederivable_from_the_mechanism():
    """results.md section 1's third row, recomputed rather than read."""
    rows = _rows(STAGE_MINUS1)
    observed = _find(rows, check="substrate_vs_model")["observed"]
    for k, (got, published) in enumerate(zip(observed, EXP5_PUBLISHED), start=1):
        assert abs(got - published) < 0.001, f"k={k}: artifact {got}, experiment 5 published {published}"

    dose = cf.dose_for_standoff(2, threshold=0.45)
    assert dose.records == 5
    for k, (mech, art) in enumerate(zip(dose.trajectory, observed), start=1):
        assert abs(mech - art) < 0.001, f"k={k}: mechanism {mech}, artifact {art}"


# --- results.md section 3 / pre-registration 4.4 -----------------------------


def test_one_for_one_never_crosses():
    rows = _rows(STAGE_MINUS1)
    row = _find(rows, check="one_for_one_corroboration")
    assert row["crossed"] is False
    assert row["lowest"] >= 0.45
    assert cf.dose_for_standoff(2, arrival_ratio=1.0).records is None


def test_critical_ratio_is_a_function_of_the_threshold_alone():
    assert cf.critical_arrival_ratio(0.45) == pytest.approx(11 / 9, abs=1e-9)
    # No free constant: change the threshold and r* moves with it, by the same
    # expression. A tuned constant would not track.
    assert cf.critical_arrival_ratio(0.5) == pytest.approx(1.0, abs=1e-9)
    assert cf.critical_arrival_ratio(0.25) == pytest.approx(3.0, abs=1e-9)


def test_arrival_ratio_table_matches_the_registration():
    rows = _rows(STAGES)
    registered = {1.0: None, 1.2: None, 1.222: None, 1.25: 223, 1.3: 88, 1.5: 38, 2.0: 18, 3.0: 11}
    for ratio, expected in registered.items():
        row = _find(rows, check="arrival_ratio", arrival_ratio=ratio)
        assert row["dose"] == expected, f"r={ratio}: artifact {row['dose']}, registered {expected}"
        assert cf.dose_for_standoff(2, arrival_ratio=ratio).records == expected


# --- results.md: the dose inversion ------------------------------------------


def test_near_miss_needs_twice_the_dose():
    """The headline that inverts experiment 5's.

    Experiment 5: a ratio cancels cardinality, so near_miss lands at the
    identical confidence. Here: the marginal record does not cancel it.
    """
    rows = _rows(STAGES)
    symmetric = _find(rows, check="dose", fixture="symmetric_rivals")
    near_miss = _find(rows, check="dose", fixture="near_miss")
    assert symmetric["dose"] == 5
    assert near_miss["dose"] == 10
    assert near_miss["dose"] >= 8, "registered floor for near_miss"
    assert cf.dose_for_standoff(2).records == 5
    assert cf.dose_for_standoff(6).records == 10


def test_enumeration_is_exact_on_both_fixtures():
    rows = _rows(STAGES)
    for fixture in ("symmetric_rivals", "near_miss"):
        row = _find(rows, check="enumeration_vs_structural_truth", fixture=fixture)
        assert row["precision"] == 1.0
        assert row["recall"] == 1.0


def test_negative_controls_hold_both_halves():
    rows = _rows(STAGES)
    irrelevant = _find(rows, check="irrelevant_evidence")
    assert abs(irrelevant["predicted_delta"]) <= 0.01
    assert abs(irrelevant["observed_delta"]) <= 0.01

    held = _find(rows, check="already_held")
    assert held["predicted_delta"] == 0.0
    assert held["observed_delta"] == 0.0
    assert held["mechanism"] == "guard_noop"


def test_pricing_never_mutated_the_store():
    rows = _rows(STAGES)
    assert _find(rows, check="pricing_never_mutates")["store_identical"] is True


# --- the check on the check --------------------------------------------------


def test_the_rederivation_check_can_fail():
    """Positive control. Experiment 5's derivability check acquired an exemption
    list and would have gone quiet; this proves the comparison above is live.
    """
    dose = cf.dose_for_standoff(2, threshold=0.45)
    wrong = [v + 0.05 for v in dose.trajectory[:6]]
    with pytest.raises(AssertionError):
        for k, (got, published) in enumerate(zip(wrong, EXP5_PUBLISHED), start=1):
            assert abs(got - published) < 0.001, f"k={k}"


def test_no_published_figure_comes_from_a_constant_in_this_file():
    """The dose is read off the store's own constants, not declared here.

    Change `RevisionConfig`'s inertia and the dose must move. If it does not,
    something in the chain is hardcoded and the "no free constant" claim (FR-8)
    is false.
    """
    from manyu.revision import RevisionConfig

    baseline = cf.dose_for_standoff(2).records
    stiffer = cf.dose_for_standoff(2, config=RevisionConfig(inertia_base=0.8, inertia_span=0.15)).records
    assert stiffer is not None and baseline is not None
    assert stiffer > baseline, f"dose did not respond to inertia ({baseline} -> {stiffer}); FR-8 is not satisfied"
