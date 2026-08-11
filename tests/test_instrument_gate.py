"""Stage 0: the gate that has to pass before any experiment-2 number is read.

Every check in ``manyu.gate`` is tested twice — once for firing on input known
to be bad, once for staying silent on input known to be good. A gate that
cannot fail would be experiment 1's failure mode #5 (a mechanism that is
arithmetically a no-op) reappearing in the machinery built to prevent it.

Two tests replay the actual historical failures with their published numbers,
so the gate is pinned against the incidents it exists for rather than against
invented ones.
"""

from __future__ import annotations

import pytest

from manyu.gate import (
    GateFailure,
    assert_above_chance,
    assert_constants_pinned,
    assert_exclusions_not_concentrated,
    assert_has_range,
    assert_iv_moves,
    assert_not_noop,
    assert_shape_comparable,
    assert_substantive,
    partition_provider_errors,
    shape_groups,
)

PINNED = {"recency_window_turns": 8, "arousal_tau": 2.5, "dissonance_tau": 1.5, "theta": 0.20}


# --- Gate 1 ------------------------------------------------------------------

def test_pinned_constants_pass_when_unchanged():
    assert_constants_pinned(dict(PINNED), PINNED)


def test_pinned_constants_fire_on_drift():
    active = dict(PINNED, arousal_tau=3.0)
    with pytest.raises(GateFailure, match="arousal_tau pinned=2.5 active=3.0"):
        assert_constants_pinned(active, PINNED)


def test_pinned_constants_fire_when_a_constant_is_absent_from_the_run():
    active = {k: v for k, v in PINNED.items() if k != "theta"}
    with pytest.raises(GateFailure, match="absent from the run: theta"):
        assert_constants_pinned(active, PINNED)


# --- Gate 2 ------------------------------------------------------------------

def test_provider_errors_are_partitioned_out():
    records = [
        {"kind": "affect_probe", "condition": "uncertainty"},
        {"kind": "provider_error", "condition": "uncertainty"},
        {"kind": "affect_probe", "condition": "neutral"},
    ]
    clean, errors = partition_provider_errors(records)
    assert len(clean) == 2
    assert len(errors) == 1


def test_evenly_spread_exclusions_pass():
    records = [{"kind": "provider_error", "condition": c} for c in ("a", "b", "c", "d")]
    assert_exclusions_not_concentrated(records, condition_key="condition")


def test_no_exclusions_passes():
    assert_exclusions_not_concentrated([{"kind": "affect_probe", "condition": "a"}], condition_key="condition")


def test_v4_provider_errors_would_have_been_caught():
    """The actual v4 incident: all 6 failures on `attachment_pressure` were the
    last 6 calls of the run and landed on sweep endpoint 1.0, which is exactly
    the shape of a threshold effect. results.md reported them as a cliff —
    aggregate 0.623, 1.2 citations — and v4.1 retracted it. Corrected, the
    endpoint reads 0.975 at 3.0 citations.
    """
    records = [{"kind": "provider_error", "condition": 1.0} for _ in range(6)]
    with pytest.raises(GateFailure, match="6/6 .100%. fall in condition 1.0"):
        assert_exclusions_not_concentrated(records, condition_key="condition")


# --- Gate 3 ------------------------------------------------------------------

def test_range_passes_on_a_spread_metric():
    assert_has_range([0.13, 0.40, 0.67, 0.94], label="arousal ramp")


def test_range_fires_on_a_saturated_metric():
    with pytest.raises(GateFailure, match="pinned at the ceiling"):
        assert_has_range([0.97, 0.98, 0.99, 0.995], label="dissonance ladder")


def test_range_fires_on_a_floored_metric():
    with pytest.raises(GateFailure, match="pinned at the floor"):
        assert_has_range([0.0, 0.001, 0.002], label="merged arousal")


def test_range_fires_when_resolution_is_below_the_floor():
    with pytest.raises(GateFailure, match="resolution floor"):
        assert_has_range([0.50, 0.51, 0.52], label="relative magnitude")


def test_range_fires_on_no_values():
    with pytest.raises(GateFailure, match="no values"):
        assert_has_range([], label="empty")


# --- Gate 4 ------------------------------------------------------------------

def test_iv_moves_passes_when_the_axis_is_real():
    assert_iv_moves(0.13, 0.94, label="uncertainty vs neutral")


def test_iv_moves_fires_on_a_flat_axis():
    with pytest.raises(GateFailure, match="does not move the outcome"):
        assert_iv_moves(0.5, 0.5, label="affect_influence")


# --- Gate 5 ------------------------------------------------------------------

def test_not_noop_passes_when_outputs_differ():
    assert_not_noop([1, 2, 3], [3, 2, 1], label="dissonance query")


def test_not_noop_fires_on_identical_output():
    """The `rank_causes` shape: a uniform multiplier cannot reorder anything,
    so the ranked list is identical for every input.
    """
    ranked = [("bev_1", "a", 0.9), ("bev_2", "b", 0.4)]
    with pytest.raises(GateFailure, match="no-op"):
        assert_not_noop(ranked, list(ranked), label="mood-congruent re-ranking")


# --- Gate 6 ------------------------------------------------------------------

def test_substantive_passes_on_a_populated_vector():
    influence = {"caution": 0.85, "skepticism": 0.85, "risk_aversion": 0.85, "curiosity": 0.25}
    assert_substantive(influence, label="MoodInfluenceVector", min_nonzero=3)


def test_substantive_fires_on_the_seed_mood_blank_substance_bug():
    """The v5 incident. `seed_mood` set valence/arousal — the projections the
    summary shows — and left the influence vector at its default. Every
    consumer reads the vector, so four different seeded moods produced
    byte-identical appraisals. Asserting on the summary would have passed.
    """
    blank = {name: 0.0 for name in ("caution", "curiosity", "trust_openness", "skepticism", "repair_orientation", "risk_aversion", "response_pacing")}
    with pytest.raises(GateFailure, match="substance is blank"):
        assert_substantive(blank, label="MoodInfluenceVector", min_nonzero=1)


# --- Gate 7 ------------------------------------------------------------------

def test_shape_groups_partitions_by_log_shape():
    records = [
        {"condition": "anxious", "evidence_count": 9, "untrusted_count": 6},
        {"condition": "skeptical", "evidence_count": 9, "untrusted_count": 6},
        {"condition": "curious", "evidence_count": 8, "untrusted_count": 5},
    ]
    groups = shape_groups(records, shape_keys=("evidence_count", "untrusted_count"), condition_key="condition")
    assert groups == {(9, 6): {"anxious", "skeptical"}, (8, 5): {"curious"}}


def test_v6_shape_matching_reproduces_the_published_grouping():
    """v6's `broken_promise_repair` looked like an effect at 1.47x noise. The
    two low scorers were the two with shallower logs, so the conditions were
    not comparable; results.md reports the shape-matched pair as
    anxious+skeptical, and every ratio fell below 1 once restricted.
    """
    records = [
        {"condition": "anxious", "evidence_count": 9, "untrusted_count": 6, "mean_agg": 0.913},
        {"condition": "skeptical", "evidence_count": 9, "untrusted_count": 6, "mean_agg": 0.930},
        {"condition": "curious", "evidence_count": 8, "untrusted_count": 5, "mean_agg": 0.863},
        {"condition": "content", "evidence_count": 7, "untrusted_count": 4, "mean_agg": 0.839},
    ]
    comparable = assert_shape_comparable(
        records, shape_keys=("evidence_count", "untrusted_count"), condition_key="condition"
    )
    assert comparable == {"anxious", "skeptical"}


def test_shape_comparable_fires_when_no_two_conditions_share_a_shape():
    records = [
        {"condition": "a", "evidence_count": 9},
        {"condition": "b", "evidence_count": 8},
        {"condition": "c", "evidence_count": 7},
    ]
    with pytest.raises(GateFailure, match="no 2 conditions share a shape"):
        assert_shape_comparable(records, shape_keys=("evidence_count",), condition_key="condition")


def test_shape_comparable_fires_on_no_records():
    with pytest.raises(GateFailure, match="no records"):
        assert_shape_comparable([], shape_keys=("evidence_count",), condition_key="condition")


# --- Gate 8: an effect must clear its own null -------------------------------

def test_above_chance_passes_when_the_observation_clears_its_null():
    null = [0.5 + index * 0.01 for index in range(50)]
    p = assert_above_chance(0.40, null, label="spread")
    assert p == 0.0


def test_above_chance_fires_on_a_mid_distribution_observation():
    """Experiment 4 Stage 3, reproduced exactly.

    `spread` was 0.400 against a derangement null averaging 0.476 — below the
    mean, and at the 48th percentile. Comparing to the mean said "more specific
    than chance"; the empirical p says it is not distinguishable at all.
    """
    null = [0.2 + index * 0.012 for index in range(50)]
    with pytest.raises(GateFailure) as caught:
        assert_above_chance(0.40, null, label="spread")
    assert "not distinguishable from chance" in str(caught.value)
    assert "0.4" in str(caught.value)


def test_above_chance_reads_the_other_tail_when_larger_is_better():
    null = [0.1 * index for index in range(10)]  # 0.0 .. 0.9
    # Nothing in the null reaches 1.0, so p is 0.0 — not 0.1. The upper tail is
    # counted with `>=`, and the null's own maximum is 0.9.
    assert assert_above_chance(1.0, null, label="hit rate", lower_is_better=False) == 0.0
    # Half the null is at or above 0.45, so this is squarely mid-distribution.
    with pytest.raises(GateFailure):
        assert_above_chance(0.45, null, label="hit rate", lower_is_better=False)


def test_above_chance_fires_on_an_empty_null():
    with pytest.raises(GateFailure):
        assert_above_chance(0.1, [], label="spread")
