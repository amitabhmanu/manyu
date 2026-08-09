"""Is "revision ripples" a finding, or a consequence of mandatory provenance?

Offline, `n=1`.

Results §1 states the headline with a heavy qualification: revision ripples
rather than collapses, **but the architecture could not have produced the
alternative**. `BeliefUpdater._rejection_reason` refuses any candidate without
`evidence_ids`, so every belief holds independent grounding, `support_share`
can never exceed 1/(1+1), and no belief can collapse with its supporter. A
graded ripple is not evidence for Quine when foundationalism is
unrepresentable.

`RevisionConfig.ignore_own_evidence` lifts that for propagation arithmetic
only — the write-path rule is untouched — so the foundationalist limb becomes
reachable and the comparison has two possible outcomes instead of one.

Without this file the experiment's central claim rests on an untested
counterfactual: *if* collapse were representable, the engine would produce it.
These tests check that it does.
"""

from __future__ import annotations

import pytest

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.revision import RevisionConfig, RevisionEngine

AGENT = "agent_demo"


def _chain() -> tuple[ManyuCore, dict[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="d", proposition="D.", confidence=0.8),
            BeliefSpec(key="c", proposition="C.", confidence=0.8, supports=("d",)),
            BeliefSpec(key="b", proposition="B.", confidence=0.8, supports=("c",)),
            BeliefSpec(key="a", proposition="A.", confidence=0.8, supports=("b",)),
        ],
    )
    return core, ids


def _footprint(config: RevisionConfig | None = None) -> dict[str, float]:
    core, ids = _chain()
    engine = RevisionEngine(core.store, FrozenClock(), config=config)
    result = engine.retract(AGENT, ids["a"], to_confidence=0.0)
    by_id = {bid: key for key, bid in ids.items()}
    return {by_id[s.belief_id]: round(abs(s.delta), 6) for s in result.moved if s.depth > 0}


def test_the_substrate_forecloses_collapse() -> None:
    """The constraint, stated as a measurement rather than an argument."""
    grounded = _footprint()
    assert grounded == {"b": 0.4, "c": 0.2, "d": 0.1}
    assert max(grounded.values()) < 0.8, "nothing can collapse with its supporter"


def test_lifting_provenance_makes_foundationalist_collapse_appear() -> None:
    """The counterfactual the headline depends on.

    With no independent grounding, each node's sole supporter carries all of
    it, share is 1.0 at every hop, and the retraction transmits undiminished
    to depth 3 — a chain collapse, from the same engine and the same fixture.
    """
    derivative = _footprint(RevisionConfig(ignore_own_evidence=True))
    assert derivative == {"b": 0.8, "c": 0.8, "d": 0.8}


def test_the_two_regimes_are_the_two_hypotheses() -> None:
    """Same engine, same topology, same retraction — opposite epistemologies.

    This is what licenses the narrower claim in results §1: the ripple follows
    from the provenance requirement, not from the propagation rule. Had the
    rule been doing the work, lifting provenance would not have changed the
    shape.
    """
    grounded, derivative = _footprint(), _footprint(RevisionConfig(ignore_own_evidence=True))

    assert grounded["b"] > grounded["c"] > grounded["d"], "grounded: attenuates (Quinean)"
    assert len(set(derivative.values())) == 1, "derivative: does not attenuate (foundationalist)"
    for key in ("b", "c", "d"):
        assert derivative[key] > grounded[key]


def test_partial_grounding_sits_between_the_two() -> None:
    """The regimes are endpoints of a continuum, not a switch.

    A belief with some independent evidence and some inherited support decays
    at a rate its own provenance sets, so the architecture represents the
    space *between* the two classical positions rather than picking one.
    """
    thin = _footprint()["d"]
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="d", proposition="D.", confidence=0.8, evidence_count=4),
            BeliefSpec(key="c", proposition="C.", confidence=0.8, evidence_count=4, supports=("d",)),
            BeliefSpec(key="b", proposition="B.", confidence=0.8, evidence_count=4, supports=("c",)),
            BeliefSpec(key="a", proposition="A.", confidence=0.8, supports=("b",)),
        ],
    )
    result = RevisionEngine(core.store, FrozenClock()).retract(AGENT, ids["a"], 0.0)
    well_grounded = abs({s.belief_id: s for s in result.steps}[ids["d"]].delta)

    assert well_grounded < thin, "more of its own evidence means less inherited shock"
    assert well_grounded > 0, "but it is still part of the web"


def test_the_write_path_rule_is_untouched_by_the_ablation() -> None:
    """The ablation changes propagation arithmetic, not what may be stored.

    If it relaxed the write path it would be a different system, and the
    comparison would no longer be about propagation at all.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    rejected = core.update_beliefs({"agent_id": AGENT, "candidates": [{
        "candidate_id": "bc_1", "agent_id": AGENT, "proposition": "Rests on nothing.",
        "belief_type": "world_model", "scope": "general", "confidence": 0.8,
        "source_mix": {"operator_note": 1.0}, "evidence_ids": [],
    }]})
    assert rejected["rejected"], "provenance is still mandatory at the write path"
