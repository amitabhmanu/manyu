"""Stage 3: is dissonance coupled to revision, or merely reported alongside it?

Entirely offline — no provider is constructed in this file.

**What this stage claims, precisely.** Experiment 2 established that merged's
dissonance falls out of graph structure. But its D2 numbers were labelled
plumbing rather than a result, because the belief valences were authored and
`_tension` reads `|a.valence - b.valence|` directly: the measured channel ran
straight back through what the author typed.

The same trap is available here and is avoided by moving a different quantity.
`stake_of` is `mean(evidence salience) * belief.confidence`, and **confidence
is what the revision engine moves**. So a retraction changes the dissonance
magnitude through a pathway nobody authored, while valence is left untouched
throughout. Every test below asserts on a *change* in magnitude across a
retraction, never on its absolute value.

**What this stage does not claim.** The contradiction itself is still an
authored `contradicts` edge, and the valences are still authored. This is not
"dissonance arose spontaneously". It is the narrower, checkable claim that
dissonance is dynamically coupled to belief revision — which is the property
experiment 4 needs before it can ask whether the signal *controls* anything.
"""

from __future__ import annotations

import pytest

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.revision import ContradictionArm, RevisionEngine

AGENT = "agent_demo"


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


ARMS = [ContradictionArm.EVIDENTIAL, ContradictionArm.DIRECT]


def _engine(core: ManyuCore, arm: ContradictionArm = ContradictionArm.EVIDENTIAL) -> RevisionEngine:
    return RevisionEngine(core.store, FrozenClock(), arm)


def _magnitude(core: ManyuCore) -> float:
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "revision")
    return signal.magnitude if signal else 0.0


def _contested_web(core: ManyuCore, arm: ContradictionArm = ContradictionArm.EVIDENTIAL) -> dict[str, str]:
    """P contradicts Q. S grounds P, and nothing grounds Q.

    Valences are opposed so a signal exists at all, but no test reads that
    opposition — they read how the magnitude *moves* when confidence does.
    """
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="p", proposition="The tool result is trustworthy.", confidence=0.8, valence=0.6),
            BeliefSpec(key="q", proposition="The tool result is unreliable.", confidence=0.8, valence=-0.6, contradicts=("p",)),
            BeliefSpec(key="s", proposition="The tool passed its self-check.", confidence=0.8, valence=0.4, supports=("p",)),
        ],
    )
    # Priced through the engine, not merely seeded — see the Stage 2 harness.
    RevisionEngine(core.store, FrozenClock(), arm).assert_contradiction(AGENT, ids["q"], ids["p"])
    return ids


# --- the coupling ------------------------------------------------------------


def test_a_web_with_a_contradiction_registers_dissonance_at_all() -> None:
    """Positive control. A null below is only meaningful if this passes."""
    core = _core()
    _contested_web(core)
    assert _magnitude(core) > 0.0


@pytest.mark.parametrize("arm", ARMS)
def test_retracting_a_supporter_reduces_dissonance(arm: ContradictionArm) -> None:
    """SC-5, and the whole point of the stage.

    Retracting S lowers P's confidence by propagation, which lowers P's stake,
    which lowers the tension P carries with Q. Nobody edited a valence and
    nobody edited P — the signal moved because the web was revised.
    """
    core = _core()
    ids = _contested_web(core)

    before = _magnitude(core)
    _engine(core, arm).retract(AGENT, ids["s"], to_confidence=0.0)
    after = _magnitude(core)

    assert after < before, f"dissonance should ease as the contested claim weakens: {before} -> {after}"
    assert after > 0.0, "the contradiction is still there — easing is not resolving"


def test_saturation_not_mechanism_is_what_separates_the_arms_here() -> None:
    """Re-look after `DIRECT` became real. The answer has two halves.

    **The mechanism is masked.** `_tension` is `min(stake_a, stake_b) * (1 +
    |dv|)/2`, and the propagation delta depends on the shock and the support
    share, never on P's starting confidence. So the *raw* tension drop is
    identical under both arms — 0.2200 — even though `DIRECT` has charged P
    for the dispute and `EVIDENTIAL` has not.

    **Saturation un-masks it, for a reason unrelated to the mechanism.**
    `magnitude` is concave in raw tension, so the same raw drop taken from
    `DIRECT`'s lower baseline (0.308 against 0.440) sits on a steeper part of
    the curve and reads as a *larger* observable change.

    The warning for experiment 4: a magnitude delta confounds "how much
    tension changed" with "where on the saturation curve the web was sitting."
    Read as a measure of belief dynamics it will attribute to the mechanism
    what is actually curve position — experiment 1's gate #3, a truncation
    constant read as a curve, in a new place.

    An earlier version of this test asserted the two arms were
    indistinguishable here. That was an artifact: the fixture priced its
    contradiction under a hardcoded arm, so `DIRECT` was never suppressing.
    """
    def _both(core: ManyuCore) -> tuple[float, float]:
        signal = MergedDissonanceQuery(core.store).detect(AGENT, "revision")
        return (signal.magnitude_raw, signal.magnitude) if signal else (0.0, 0.0)

    evidential_core = _core()
    e_ids = _contested_web(evidential_core, ContradictionArm.EVIDENTIAL)
    e_raw_before, e_before = _both(evidential_core)
    _engine(evidential_core, ContradictionArm.EVIDENTIAL).retract(AGENT, e_ids["s"], 0.0)
    e_raw_after, e_after = _both(evidential_core)
    e_raw_drop, e_drop = e_raw_before - e_raw_after, e_before - e_after

    direct_core = _core()
    d_ids = _contested_web(direct_core, ContradictionArm.DIRECT)
    d_raw_before, d_before = _both(direct_core)
    _engine(direct_core, ContradictionArm.DIRECT).retract(AGENT, d_ids["s"], 0.0)
    d_raw_after, d_after = _both(direct_core)
    d_raw_drop, d_drop = d_raw_before - d_raw_after, d_before - d_after

    # The baseline really is lower under DIRECT — that is what moves the
    # measurement onto a steeper part of the curve.
    assert d_raw_before < e_raw_before

    # Half one: the underlying tension change is the same under both arms.
    assert d_raw_drop == pytest.approx(e_raw_drop), "the mechanism is not masked after all"

    # Half two: the observable magnitude still separates them, via curve
    # position rather than via anything about contradiction.
    assert d_drop > e_drop

    # And the arms really are in different states underneath.
    assert direct_core.store.get_belief(d_ids["p"]).confidence < evidential_core.store.get_belief(e_ids["p"]).confidence


@pytest.mark.parametrize("arm", ARMS)
def test_the_valences_are_untouched_by_revision(arm: ContradictionArm) -> None:
    """Guards the claim above against the trap experiment 2's D2 fell into.

    If revision moved valence, the magnitude change could be our authorship
    resurfacing rather than the confidence pathway. Run under both arms
    because `DIRECT` writes to a belief `EVIDENTIAL` never touches.
    """
    core = _core()
    ids = _contested_web(core)
    before = {b.belief_id: b.valence for b in core.store.list_beliefs(AGENT, include_inactive=True)}

    _engine(core, arm).retract(AGENT, ids["s"], to_confidence=0.0)

    after = {b.belief_id: b.valence for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    assert before == after


@pytest.mark.parametrize("arm", ARMS)
def test_retracting_an_unrelated_belief_leaves_dissonance_alone(arm: ContradictionArm) -> None:
    """SC-4 in the dissonance channel.

    Without this, "retraction changes dissonance" is passable by any mechanism
    that recomputes a global number whenever anything at all moves.
    """
    core = _core()
    ids = _contested_web(core)
    ids |= seed_beliefs(core, [BeliefSpec(key="unrelated", proposition="Unrelated.", confidence=0.8, valence=0.1)])

    before = _magnitude(core)
    _engine(core, arm).retract(AGENT, ids["unrelated"], to_confidence=0.0)

    assert _magnitude(core) == pytest.approx(before)


def test_dissonance_tracks_the_depth_of_the_retraction() -> None:
    """A deeper supporter should move the signal less than a direct one.

    This is SC-2's shape read through the dissonance channel rather than
    through confidence, so it checks that attenuation survives the hand-off
    to the affect layer instead of being flattened by it.
    """
    near = _core()
    near_ids = _contested_web(near)
    near_before = _magnitude(near)
    _engine(near).retract(AGENT, near_ids["s"], 0.0)
    near_drop = near_before - _magnitude(near)

    far = _core()
    far_ids = seed_beliefs(
        far,
        [
            BeliefSpec(key="p", proposition="The tool result is trustworthy.", confidence=0.8, valence=0.6),
            BeliefSpec(key="q", proposition="The tool result is unreliable.", confidence=0.8, valence=-0.6, contradicts=("p",)),
            BeliefSpec(key="s", proposition="The tool passed its self-check.", confidence=0.8, valence=0.4, supports=("p",)),
            BeliefSpec(key="deep", proposition="The self-check harness is sound.", confidence=0.8, valence=0.3, supports=("s",)),
        ],
    )
    far_before = _magnitude(far)
    _engine(far).retract(AGENT, far_ids["deep"], 0.0)
    far_drop = far_before - _magnitude(far)

    assert far_drop > 0.0, "a distant retraction must still be felt"
    assert far_drop < near_drop, f"distance must attenuate: near {near_drop}, far {far_drop}"


def test_the_signal_names_the_beliefs_carrying_it_after_revision() -> None:
    """SC-6 in the dissonance channel — the eased signal is still auditable."""
    core = _core()
    ids = _contested_web(core)
    _engine(core).retract(AGENT, ids["s"], to_confidence=0.0)

    signal = MergedDissonanceQuery(core.store).detect(AGENT, "revision")
    assert signal is not None
    carried = {bid for carrier in signal.carriers for bid in (carrier.belief_id_a, carrier.belief_id_b)}
    assert {ids["p"], ids["q"]} <= carried
