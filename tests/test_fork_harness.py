"""Stage 3: D2's mechanism, offline.

**Nothing here is a D2 result.** Belief valences are authored, so merged's
numbers are our authorship (design §6.1); split's come from a rule table we did
not write but did choose to lean on (design §6.2). What these tests establish
is that the plumbing works — the conditions separate, the diagnostics are
present, the gates are satisfied — so that the one paid run in Stage 4 is
spent on a question rather than on debugging.

No provider is constructed. Without one `process_reflective_turn` never
composes an inner voice, so split has no `MoodState` at all and its affect is
read from `AffectState`. That asymmetry is why every comparison here is
within-build.
"""

from __future__ import annotations

import pytest

from manyu.architecture import Arch
from manyu.core import ManyuCore
from manyu.fork import (
    D2_CONDITIONS,
    D2_SHAPE_KEYS,
    INTER_EVENT_SECONDS,
    run_d2_condition,
    uncertainty_events,
)
from manyu.gate import assert_iv_moves, assert_shape_comparable, assert_substantive
from manyu.schemas import NormalizedEvent

AGENT = "agent_demo"


@pytest.fixture(scope="module")
def records() -> dict[tuple[str, str], object]:
    return {
        (arch.value, condition): run_d2_condition(arch=arch, condition=condition)
        for arch in (Arch.MERGED, Arch.SPLIT)
        for condition in D2_CONDITIONS
    }


# --- the blocking gate: split's route to object-less affect -------------------

def test_tool_result_yields_fear_without_negative_goal_impact():
    """**D2's split arm depends on this behaviour. Changing it invalidates the
    D2 result rather than merely breaking a test.**

    `FastAppraiser` groups `TOOL_RESULT` with `GOAL_OBSTRUCTION` and defaults
    `negative = 0.45` when `goal_impact >= 0`, so an ambiguous tool result
    produces fear with no negative impact anywhere in the event — which is
    precisely the object-less affect D2 looks for, arriving by an accident of
    the rule table.

    Left as-is deliberately (design §6.2): auditing the table would ripple into
    experiment 1's committed artifacts, and hand-writing a principled
    uncertainty branch would make split's arm circular in the same way merged's
    already is. The finding inherits whatever this rule is, and results.md says
    so.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    event = uncertainty_events(1, condition="uncertainty")[0]
    assert event.links == [], "the object-less event must carry no goal link"
    assert event.claims == [], "and no claim that could name a threat"

    appraisal = core.submit_event(event).appraisal
    assert appraisal.emotion_deltas["fear"] == pytest.approx(0.036, abs=1e-6)
    assert "goal_obstruction" in appraisal.reason_codes


def test_neutral_condition_produces_no_fear():
    """The baseline has to be a baseline. `goal_progress` yields joy and trust
    and never touches the fear channel, so split's neutral sits at its
    configured floor rather than at some small positive drift.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    appraisal = core.submit_event(uncertainty_events(1, condition="neutral")[0]).appraisal
    assert "fear" not in appraisal.emotion_deltas


def test_control_condition_produces_more_fear_than_uncertainty():
    """The positive control must be unambiguously stronger, or it cannot rule
    out a broken instrument when the main condition comes back null.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    deltas = {
        condition: core.submit_event(uncertainty_events(1, condition=condition)[0]).appraisal.emotion_deltas
        for condition in ("uncertainty", "control")
    }
    assert deltas["control"]["fear"] > deltas["uncertainty"]["fear"]


# --- the ramp gate (methodology §4.2 item 2) ---------------------------------

def test_split_fear_accumulates_across_the_event_stream():
    """Split's half of the ramp. Merged's half is in `test_merged_arch.py`.

    Run with the clock advancing `INTER_EVENT_SECONDS` between events, so
    `fear`'s 900s half-life is genuinely working against accumulation. A
    `FrozenClock` with no advance would switch decay off and flatter split by
    removing the only thing opposing it.
    """
    levels = []
    for count in range(1, 9):
        record = run_d2_condition(arch=Arch.SPLIT, condition="uncertainty", n_events=count)
        levels.append(record.affect)
    assert levels == sorted(levels), f"split fear not monotone in event count: {levels}"
    assert len(set(levels)) == 8, f"ties in the split ramp: {levels}"


def test_decay_is_actually_running():
    """Guards the ramp above. If the clock were not advancing, the ramp would
    still be monotone — trivially — and would prove nothing about a system that
    decays.
    """
    assert INTER_EVENT_SECONDS > 0
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    events = uncertainty_events(2, condition="uncertainty")
    core.submit_event(events[0])
    first = core.store.latest_state(AGENT).emotions["fear"]
    core.clock.advance(INTER_EVENT_SECONDS)
    core.submit_event(events[1])
    second = core.store.latest_state(AGENT).emotions["fear"]
    # Two identical events, but the second is applied to a decayed state, so
    # the increment must be strictly smaller than the first.
    assert (second - first) < first - core.profile.emotions["fear"].baseline


# --- conditions separate, on both builds -------------------------------------

@pytest.mark.parametrize("arch", ["merged", "split"])
def test_conditions_are_ordered_control_uncertainty_neutral(records, arch):
    by_condition = {c: records[(arch, c)] for c in D2_CONDITIONS}
    assert (
        by_condition["control"].affect
        > by_condition["uncertainty"].affect
        > by_condition["neutral"].affect
    ), {c: r.affect for c, r in by_condition.items()}


@pytest.mark.parametrize("arch", ["merged", "split"])
def test_independent_variable_moves_the_outcome(records, arch):
    """Instrument gate #4. Experiment 1 ran an eleven-point sweep whose axis was
    three system-message sentences; before reading any effect, confirm the axis
    is real at its endpoints.
    """
    assert_iv_moves(
        records[(arch, "neutral")].affect,
        records[(arch, "uncertainty")].affect,
        label=f"{arch}: uncertainty vs neutral",
    )


@pytest.mark.parametrize("arch", ["merged", "split"])
def test_conditions_are_shape_comparable(records, arch):
    """Instrument gate #7, on shape keys the measured channel actually depends on.

    `evidence_count` differs across conditions (51/54/58) because reflection
    generates evidence at a rate the treatment influences. It is *not* a shape
    key here, because merged reads the belief window and split reads
    `event_type` deltas — neither is a function of evidence count. Admissibility
    rule in `D2_SHAPE_KEYS`: a key counts only if the channel is a function of
    it, declared before the run.
    """
    rows = [records[(arch, c)].as_dict() for c in D2_CONDITIONS]
    comparable = assert_shape_comparable(
        rows, shape_keys=D2_SHAPE_KEYS[arch], condition_key="condition"
    )
    assert comparable == set(D2_CONDITIONS)


# --- diagnostics that keep a null readable -----------------------------------

@pytest.mark.parametrize("arch", ["merged", "split"])
@pytest.mark.parametrize("condition", list(D2_CONDITIONS))
def test_every_record_carries_the_fr_d2_6_diagnostics(records, arch, condition):
    """A null is only interpretable if it can be told apart from an empty
    instrument. These are the fields that do it.
    """
    row = records[(arch, condition)].as_dict()
    for field in ("window_belief_count", "authored_in_window", "sum_stake", "arousal_floored", "evidence_count", "untrusted_count"):
        assert field in row, field
    assert row["window_belief_count"] > 0, "an empty window is M-0, not M-a"


def test_merged_window_is_dominated_by_the_fixture_carriers(records):
    """If reflection beliefs filled the window, merged's measure would be noise
    rather than the treatment.
    """
    for condition in D2_CONDITIONS:
        row = records[("merged", condition)]
        assert row.authored_in_window >= row.window_belief_count - 1


def test_merged_influence_vector_is_substantive_on_the_uncertainty_stream(records):
    """Instrument gate #6 at the consumer, on the D2 path specifically."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, arch=Arch.MERGED)
    from manyu.fork import _carrier_candidate

    for index, event in enumerate(uncertainty_events(6, condition="uncertainty")):
        evidence = core.capture_belief_evidence(
            {
                "agent_id": AGENT,
                "source_type": "event",
                "source_id": event.event_id,
                "summary": event.summary,
                "trust_class": event.source.trust_class.value,
            }
        )
        core.process_reflective_turn(
            {
                "event": event.model_dump(mode="json"),
                "belief_candidates": [_carrier_candidate(event, evidence["evidence_id"], "uncertainty", index)],
            }
        )
        core.clock.advance(INTER_EVENT_SECONDS)

    mood = core.moods.active_mood(AGENT)
    assert_substantive(mood.influence.model_dump(), label="merged influence on D2 stream", min_nonzero=3)


# --- what this stage is not --------------------------------------------------

def test_merged_arousal_does_not_separate_the_conditions(records):
    """Recorded as a finding, not worked around.

    Merged's arousal is `1 - exp(-sum(stake)/tau)` and neither term depends on
    valence, so it measures how much is on the agent's mind rather than how bad
    any of it is — the standard circumplex separation. A store of pleasant
    beliefs is as aroused as one of dreadful ones, which is why D2's merged
    channel is negative valence and not arousal.
    """
    arousals = [records[("merged", c)].arousal for c in D2_CONDITIONS]
    assert max(arousals) - min(arousals) < 0.25, arousals

    affects = [records[("merged", c)].affect for c in D2_CONDITIONS]
    assert max(affects) - min(affects) > 0.6, affects
