"""Stage 1: the merged build, and the guarantees that make it a fair comparison.

Two kinds of test here. Most check that merged is what it claims to be — no
stored state, no inertia, no age-weighting — because a merged build that
quietly grows any of those is split wearing a different name, and the fork
would compare a thing to itself.

The rest check that merged and split still agree everywhere the fork is not
supposed to matter (SC-1). A difference that leaks in through the mood label
vocabulary, or through an influence vector the consumer reads as blank, would
show up in D2 as an architecture effect.
"""

from __future__ import annotations

import math

import pytest

from manyu.architecture import Arch, ArchConfig
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.gate import assert_has_range, assert_substantive
from manyu.core import ManyuCore
from manyu.schemas import BeliefType
from manyu.services import MergedMoodEngine, MoodEngine

AGENT = "agent_demo"


def _core(arch: Arch = Arch.MERGED, **config) -> ManyuCore:
    return ManyuCore.from_paths(
        db_path=":memory:", frozen=True, arch=arch, arch_config=ArchConfig(**config) if config else None
    )


def _uncertainty(n: int, *, valence: float = 0.0, salience: float = 0.5) -> list[BeliefSpec]:
    return [
        BeliefSpec(key=f"u{i}", proposition=f"Question {i} is unresolved.", valence=valence, salience=salience)
        for i in range(n)
    ]


# --- the fork is off by default ----------------------------------------------

def test_split_is_the_default():
    """Every pre-experiment caller must be untouched by the fork existing."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    assert core.arch is Arch.SPLIT
    assert isinstance(core.moods, MoodEngine)
    assert not isinstance(core.moods, MergedMoodEngine)


def test_merged_is_selected_only_when_asked():
    assert isinstance(_core(Arch.MERGED).moods, MergedMoodEngine)


# --- SC-1: the builds agree where the fork should not matter -----------------

def test_both_builds_appraise_an_event_identically_without_mood():
    """The affect->belief-formation path is shared. With no mood on either
    side, the two builds must produce byte-identical appraisals, or D2 would be
    reading a difference the fork did not cause.
    """
    from manyu.probing import load_fixture

    _, events, _ = load_fixture("evals/fixtures/everyday_collaboration_mood.json")
    event = events[0]
    traces = {}
    for arch in (Arch.MERGED, Arch.SPLIT):
        core = _core(arch)
        traces[arch] = core.submit_event(event).appraisal
    assert traces[Arch.MERGED].emotion_deltas == traces[Arch.SPLIT].emotion_deltas
    assert traces[Arch.MERGED].reason_codes == traces[Arch.SPLIT].reason_codes
    assert traces[Arch.MERGED].action_tendency == traces[Arch.SPLIT].action_tendency


def test_seed_mood_behaves_identically_in_both_builds():
    """`seed_mood` is the NFR-3 control arm: it removes the inner-voice LLM from
    split's mood path so an architecture effect can be told apart from a model
    effect. If the two builds seeded differently the arm would be worthless.
    """
    moods = {}
    for arch in (Arch.MERGED, Arch.SPLIT):
        core = _core(arch)
        moods[arch] = core.moods.seed_mood(AGENT, label="anxious", valence=-0.6, arousal=0.85, momentum=0.7)
    merged, split = moods[Arch.MERGED], moods[Arch.SPLIT]
    assert (merged.valence, merged.arousal, merged.momentum) == (split.valence, split.arousal, split.momentum)
    assert merged.influence == split.influence


# --- merged is what it claims to be ------------------------------------------

def test_merged_uses_influence_for_verbatim():
    """Merged must reuse split's own inversion rather than reimplement it.

    `MoodEngine.influence_for` exists because v5 found `seed_mood` setting the
    projections and leaving the substance blank. Reusing it means any downstream
    difference comes from the belief query and not from a second opinion about
    what an influence vector means.
    """
    core = _core()
    seed_beliefs(core, _uncertainty(3, valence=-0.4))
    projection = core.moods.project(AGENT)
    expected = MoodEngine.influence_for(projection.valence, projection.arousal)
    assert core.moods.active_mood(AGENT).influence == expected


def test_merged_momentum_is_zero():
    core = _core()
    seed_beliefs(core, _uncertainty(3, valence=-0.5))
    assert core.moods.active_mood(AGENT).momentum == 0.0


def test_merged_never_reads_prior_mood():
    """No stored state means no read of stored state. A merged build that
    consulted `latest_mood` would have inertia through the back door.
    """
    core = _core()
    seed_beliefs(core, _uncertainty(3, valence=-0.4))
    calls = []
    original = core.store.latest_mood
    core.store.latest_mood = lambda *a, **k: (calls.append(a), original(*a, **k))[1]

    core.moods.active_mood(AGENT)
    core.moods.project(AGENT)
    assert calls == []


def test_window_has_no_age_weighting():
    """OQ-1's governance line, made mechanical.

    Same two beliefs, opposite insertion orders. Any weighting by position
    would make the two stores disagree; a hard cutoff with no weighting inside
    it cannot.
    """
    heavy = BeliefSpec(key="heavy", proposition="This one is negative.", valence=-0.8)
    light = BeliefSpec(key="light", proposition="This one is neutral.", valence=0.0)

    newest_heavy = _core()
    seed_beliefs(newest_heavy, [light, heavy])
    newest_light = _core()
    seed_beliefs(newest_light, [heavy, light])

    assert newest_heavy.moods.project(AGENT).valence == newest_light.moods.project(AGENT).valence


def test_window_excludes_beliefs_beyond_the_cutoff():
    """The window is a hard cutoff. Beliefs pushed out of it contribute nothing
    — not a little, nothing.
    """
    core = _core(recency_window_beliefs=3)
    seed_beliefs(
        core,
        [BeliefSpec(key="old", proposition="An old extreme belief.", valence=-1.0)]
        + _uncertainty(3, valence=0.0),
    )
    projection = core.moods.project(AGENT)
    assert projection.window_belief_count == 3
    assert projection.valence == 0.0


def test_empty_window_yields_none_not_a_zeroed_mood():
    """"No beliefs to read" and "beliefs read, no affect" are different states.

    Collapsing them is what makes M-0 indistinguishable from M-a, and M-a is a
    loss condition for merged — so a store that never populated would score
    against the architecture. Experiment 1 lost an entire finding to this shape.
    """
    core = _core()
    assert core.moods.active_mood(AGENT) is None
    assert core.moods.project(AGENT).window_belief_count == 0


# --- the realisability constraint --------------------------------------------

def test_merged_arousal_is_floored_at_abs_valence():
    """`influence_for` cannot represent `|valence| > arousal` and silently
    clamps. Merged computes the two independently, so without a floor it would
    request an unreachable state and occupy a different one with nothing
    recording the substitution.
    """
    core = _core()
    # Strongly negative but low-salience: accumulated arousal lands well below
    # |valence|, so the floor has to engage.
    seed_beliefs(core, [BeliefSpec(key="a", proposition="A strongly negative, barely salient belief.", valence=-0.9, salience=0.15, confidence=0.5)])
    projection = core.moods.project(AGENT)
    assert projection.arousal_floored is True
    assert projection.arousal == pytest.approx(abs(projection.valence))

    mood = core.moods.active_mood(AGENT)
    assert MoodEngine.influence_for(mood.valence, mood.arousal) == mood.influence


def test_unfloored_case_is_reported_as_unfloored():
    core = _core()
    seed_beliefs(core, _uncertainty(6, valence=-0.05))
    assert core.moods.project(AGENT).arousal_floored is False


# --- gate 6: assert at the consumer ------------------------------------------

def test_fast_appraiser_sees_a_substantive_influence_vector():
    """Instrument gate #6, at the only place it matters.

    `FastAppraiser.appraise` reads *only* the influence vector — not valence,
    not arousal, not the label. v5's `seed_mood` bug made four very different
    moods produce byte-identical appraisals because the summary was populated
    and the substance was not. Asserting on `MoodState.valence` here would pass
    against that bug.
    """
    from manyu.probing import load_fixture

    core = _core()
    seed_beliefs(core, _uncertainty(5, valence=-0.6, salience=0.8))
    mood = core.moods.active_mood(AGENT)

    assert_substantive(mood.influence.model_dump(), label="merged MoodInfluenceVector", min_nonzero=3)

    _, events, _ = load_fixture("evals/fixtures/everyday_collaboration_mood.json")
    appraisal = core.fast_appraiser.appraise(events[0], 0, mood)
    assert any(code.startswith("mood_bias_") for code in appraisal.reason_codes), (
        f"merged mood did not reach the appraiser; reason_codes={appraisal.reason_codes}"
    )


# --- accumulation ------------------------------------------------------------

def test_merged_arousal_accumulates_with_belief_count():
    """Half of the D2 ramp gate. Object-less anxiety is the case where many
    low-grade items must add up, so a mean would make D2 unrunnable by
    construction.

    Note the ceiling: accumulation stops at the window size, because merged has
    no memory beyond it. That is the merged *answer* to whether affect
    accumulates indefinitely, not a defect — but it does mean the D2 ramp can
    only be read inside the window.
    """
    window = 8
    arousals = []
    for k in range(1, window + 1):
        core = _core(recency_window_beliefs=window)
        seed_beliefs(core, _uncertainty(k))
        arousals.append(core.moods.project(AGENT).arousal)

    assert arousals == sorted(arousals), f"arousal not monotone in belief count: {arousals}"
    assert len(set(arousals)) == window, f"ties in the ramp: {arousals}"
    assert_has_range(arousals, label="merged arousal ramp")


def test_merged_arousal_is_flat_beyond_the_window():
    """The other side of the same property, pinned so it is a recorded finding
    rather than a surprise during D2.
    """
    core_at = _core(recency_window_beliefs=4)
    seed_beliefs(core_at, _uncertainty(4))
    core_beyond = _core(recency_window_beliefs=4)
    seed_beliefs(core_beyond, _uncertainty(12))
    assert core_at.moods.project(AGENT).arousal == core_beyond.moods.project(AGENT).arousal


def test_arousal_matches_the_pinned_saturating_formula():
    """Arithmetic somebody can check by hand, against the pinned tau."""
    core = _core()
    seed_beliefs(core, _uncertainty(4))  # stake = 0.5 salience * 0.7 confidence = 0.35 each
    projection = core.moods.project(AGENT)
    assert projection.sum_stake == pytest.approx(1.4)
    assert projection.arousal == pytest.approx(1 - math.exp(-1.4 / 2.5), abs=1e-6)


# --- the supports edge -------------------------------------------------------

def test_supports_edge_round_trips():
    """Without an entailment edge a Quinean ripple is unrepresentable, not just
    unimplemented. Experiment #3 consumes the same field.
    """
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="ground", proposition="The tool reported a conflict."),
            BeliefSpec(key="derived", proposition="The merge is unsafe.", supports=("ground",)),
        ],
    )
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT)}
    assert beliefs[ids["derived"]].supports == [ids["ground"]]
    assert beliefs[ids["ground"]].supports == []


def test_supports_accumulates_without_contesting():
    """Lending support to another belief says nothing about this one's standing,
    so `supports` must not trip the CONTESTED flip that `contradicts` does.
    """
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="a", proposition="Ground truth holds."),
            BeliefSpec(key="b", proposition="The derived claim holds.", supports=("a",)),
        ],
    )
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT)}
    assert beliefs[ids["b"]].status.value == "active"
