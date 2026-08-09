"""Stage 1: the revision engine — does a retraction collapse or ripple?

Entirely offline. No provider is constructed anywhere in this file, which is
what lets the whole stage run for free and deterministically under
`FrozenClock` — hence n=1 (requirements §4).

The tests fall into four groups:

- **The ratchet** — confidence must now fall, and no belief may be
  unfalsifiable at any stability.
- **Shape** — attenuation with depth (SC-2) and fractional support (SC-3).
  These two are the discriminator: they are what makes a net absorb a shock
  that a chain transmits.
- **Negatives** (SC-4) — nothing moves without a path. Without these, a
  mechanism that moves everything passes every positive test.
- **Auditability** (SC-6) — the ripple is reconstructible from the revision
  trail alone.
"""

from __future__ import annotations

import pytest

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.revision import (
    ContradictionArm,
    DecayMode,
    RevisionConfig,
    RevisionEngine,
    blend_confidence,
)
from manyu.schemas import Belief, BeliefStatus

AGENT = "agent_demo"


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _engine(core: ManyuCore, arm: ContradictionArm = ContradictionArm.EVIDENTIAL, **kw) -> RevisionEngine:
    return RevisionEngine(core.store, FrozenClock(), arm, RevisionConfig(**kw) if kw else None)


def _belief(confidence: float = 0.8, stability: float = 0.5) -> Belief:
    return Belief(
        belief_id="bel_x",
        agent_id=AGENT,
        proposition="p",
        belief_type="world_model",
        scope="general",
        confidence=confidence,
        stability=stability,
        valence=0.0,
        source_mix={"operator_note": 1.0},
        evidence_ids=["bev_1"],
    )


# --- Group 1: the ratchet is gone -------------------------------------------


def test_confidence_falls_under_disconfirming_evidence() -> None:
    """SC-1. Previously `max(belief.confidence, blended)` made this exactly 0.

    No test covered this before: removing the ratchet broke nothing, which is
    itself the finding — the disconfirming direction was entirely uncovered.
    """
    assert blend_confidence(_belief(confidence=0.8), 0.2, RevisionConfig()) < 0.8


def test_no_belief_is_unfalsifiable_at_maximum_stability() -> None:
    """The backlog's proposed `0.5 + 0.5 * stability` reaches inertia 1.0.

    That reintroduces the ratchet under another name at exactly the point the
    experiment cares about — a maximally corroborated belief. The span is
    capped so full stability still yields.
    """
    entrenched = _belief(confidence=0.9, stability=1.0)
    assert blend_confidence(entrenched, 0.0, RevisionConfig()) < 0.9


def test_entrenched_beliefs_move_less_than_fresh_ones() -> None:
    fresh = _belief(confidence=0.8, stability=0.0)
    entrenched = _belief(confidence=0.8, stability=1.0)
    config = RevisionConfig()
    assert (0.8 - blend_confidence(entrenched, 0.0, config)) < (0.8 - blend_confidence(fresh, 0.0, config))


def test_operating_on_another_agents_belief_is_refused() -> None:
    """Found by a share value that should have been impossible.

    Grounding counts are scoped by `agent_id`, so an agent that does not own
    the belief silently returns zero supporters for everything: share collapses
    to `1/own_evidence`, and the shock propagates undiminished — the
    foundationalist regime the substrate is meant to forbid, produced by a
    caller typo rather than by the data.

    The Stage 4 runner hit exactly this, measuring 0.8/0.8/0.8 down a chain
    that should have decayed 0.8/0.4/0.2, and the run was discarded.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.8),
            BeliefSpec(key="s", proposition="S.", confidence=0.8, supports=("t",)),
        ],
        agent_id="probe_agent",
    )
    engine = RevisionEngine(core.store, FrozenClock())

    with pytest.raises(ValueError, match="belongs to agent"):
        engine.retract("agent_demo", ids["s"], 0.0)

    # The correct agent still works, and attenuates.
    result = engine.retract("probe_agent", ids["s"], 0.0)
    propagated = [s for s in result.steps if s.depth == 1]
    assert propagated and propagated[0].support_share == pytest.approx(0.5)


def test_the_contradiction_arm_defaults_to_the_decided_value() -> None:
    """Requirements §5.1 decided `DIRECT`.

    While the question was open there was deliberately no default, so it could
    not be settled by whichever branch a caller forgot about. Now that it is
    settled the default *is* the decision, and this test guards against
    reversing it by accident. The experiment surfaces still require `arm`
    explicitly, because there the choice is the point.
    """
    assert RevisionEngine(_core().store, FrozenClock()).arm is ContradictionArm.DIRECT


# --- Group 2: shape ---------------------------------------------------------


def _chain(core: ManyuCore) -> dict[str, str]:
    """A -> B -> C -> D. Each node has exactly one supporter."""
    return seed_beliefs(
        core,
        [
            BeliefSpec(key="d", proposition="D.", confidence=0.8),
            BeliefSpec(key="c", proposition="C.", confidence=0.8, supports=("d",)),
            BeliefSpec(key="b", proposition="B.", confidence=0.8, supports=("c",)),
            BeliefSpec(key="a", proposition="A.", confidence=0.8, supports=("b",)),
        ],
    )


def test_a_ripple_attenuates_with_depth() -> None:
    """SC-2. Both non-zero (a ripple reaches) and strictly decreasing (it decays)."""
    core = _core()
    ids = _chain(core)
    result = _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)

    by_id = {step.belief_id: step for step in result.steps}
    d1 = abs(by_id[ids["b"]].delta)
    d2 = abs(by_id[ids["c"]].delta)
    d3 = abs(by_id[ids["d"]].delta)

    assert d1 > 0 and d2 > 0 and d3 > 0, "the ripple must reach depth 3 at all"
    assert d1 > d2 > d3, f"must decay with distance, got {d1} {d2} {d3}"


def test_a_net_absorbs_what_a_chain_transmits() -> None:
    """SC-3 / FR-7 — the core discriminator.

    Same retraction, same target confidence. The only difference is how many
    supporters the target has, so any difference in movement is fractional
    support and nothing else.
    """
    chain_core = _core()
    chain_ids = seed_beliefs(
        chain_core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.8),
            BeliefSpec(key="s1", proposition="S1.", confidence=0.8, supports=("t",)),
        ],
    )
    chain_move = abs(
        {s.belief_id: s for s in _engine(chain_core).retract(AGENT, chain_ids["s1"], 0.0).steps}[chain_ids["t"]].delta
    )

    net_core = _core()
    net_ids = seed_beliefs(
        net_core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.8),
            BeliefSpec(key="s1", proposition="S1.", confidence=0.8, supports=("t",)),
            BeliefSpec(key="s2", proposition="S2.", confidence=0.8, supports=("t",)),
            BeliefSpec(key="s3", proposition="S3.", confidence=0.8, supports=("t",)),
        ],
    )
    net_move = abs(
        {s.belief_id: s for s in _engine(net_core).retract(AGENT, net_ids["s1"], 0.0).steps}[net_ids["t"]].delta
    )

    assert net_move > 0, "the net must still feel it — absorbing is not ignoring"
    assert net_move < chain_move, f"net {net_move} should absorb more than chain {chain_move}"


def test_retraction_collapses_confidence_without_destroying_provenance() -> None:
    core = _core()
    ids = _chain(core)
    _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)

    survivor = core.store.get_belief(ids["a"])
    assert survivor.confidence == 0.0
    assert survivor.evidence_ids, "retraction must not destroy the evidence trail"


# --- Group 3: negatives (SC-4) ----------------------------------------------


def test_an_unconnected_belief_does_not_move() -> None:
    """SC-4. A mechanism that fires without a path is keying on similarity."""
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.8),
            BeliefSpec(key="s", proposition="S.", confidence=0.8, supports=("t",)),
            BeliefSpec(key="isolated", proposition="Unrelated.", confidence=0.8),
        ],
    )
    result = _engine(core).retract(AGENT, ids["s"], 0.0)

    assert ids["isolated"] not in {s.belief_id for s in result.steps}
    assert core.store.get_belief(ids["isolated"]).confidence == pytest.approx(0.8)


def test_propagation_runs_backward_along_supports_not_forward() -> None:
    """`A.supports == [B]` means A grounds B, so retracting B must not move A.

    A rule that walked the edge in both directions would pass every depth and
    fractional-support test above while meaning something entirely different.
    """
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.8),
            BeliefSpec(key="s", proposition="S.", confidence=0.8, supports=("t",)),
        ],
    )
    _engine(core).retract(AGENT, ids["t"], 0.0)
    assert core.store.get_belief(ids["s"]).confidence == pytest.approx(0.8)


def test_a_cycle_terminates() -> None:
    """FR-4. The graph is not guaranteed acyclic."""
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="a", proposition="A.", confidence=0.8),
            BeliefSpec(key="b", proposition="B.", confidence=0.8, supports=("a",)),
        ],
    )
    a = core.store.get_belief(ids["a"])
    core.store.save_belief(a.model_copy(update={"supports": [ids["b"]]}))

    result = _engine(core).retract(AGENT, ids["a"], 0.0)
    assert len({s.belief_id for s in result.steps}) == len(result.steps), "each belief visited at most once"


def test_propagation_stops_below_epsilon() -> None:
    core = _core()
    ids = _chain(core)
    result = _engine(core, epsilon=0.2).retract(AGENT, ids["a"], to_confidence=0.0)
    assert result.max_depth_reached < 3, "a large epsilon must cut the ripple short"


# --- Group 4: auditability (SC-6) -------------------------------------------


def test_every_propagated_change_is_in_the_revision_trail() -> None:
    """SC-6. A ripple nobody can audit is not a result."""
    core = _core()
    ids = _chain(core)
    result = _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)

    for step in result.moved:
        reasons = [r.reason for r in core.store.list_belief_revisions(step.belief_id)]
        if step.depth == 0:
            assert "retraction" in reasons
        else:
            assert any(r.startswith(f"propagated_depth_{step.depth}_") for r in reasons), (
                f"depth-{step.depth} move on {step.belief_id} left no trail: {reasons}"
            )


def test_confidence_collapse_downgrades_status_but_never_upgrades_it() -> None:
    core = _core()
    ids = _chain(core)
    _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)
    assert core.store.get_belief(ids["a"]).status == BeliefStatus.TENTATIVE


def test_total_movement_excludes_the_origin() -> None:
    """Including the manipulation would let a bigger shock look like a bigger
    ripple."""
    core = _core()
    ids = _chain(core)
    result = _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)

    everything = sum(abs(s.delta) for s in result.steps)
    assert result.total_movement() == pytest.approx(everything - 0.8)


def test_aggregate_movement_is_bounded_by_the_shock() -> None:
    """Conservation, and it is derived rather than tuned.

    Mandatory provenance means every belief has at least one evidence record
    of its own, so share never exceeds 1/(1+1). A ripple therefore always sums
    to less than the retraction that caused it — no constant was chosen to
    make this true.

    The `FIXED` ablation does *not* have this property: at attenuation 0.6 the
    same chain sums to 0.941 against a 0.8 shock, which is why that arm needs
    per-depth deltas rather than totals.
    """
    core = _core()
    ids = _chain(core)
    result = _engine(core).retract(AGENT, ids["a"], to_confidence=0.0)
    assert 0.0 < result.total_movement() < 0.8

    fixed_core = _core()
    fixed_ids = _chain(fixed_core)
    fixed = _engine(fixed_core, decay_mode=DecayMode.FIXED, attenuation=0.6).retract(AGENT, fixed_ids["a"], 0.0)
    assert fixed.total_movement() > 0.8


def test_decay_needs_no_constant_under_provenance_mode() -> None:
    """The point of Option 3: SC-2 and SC-3 hold with attenuation fixed at 1.0.

    If either criterion depended on the constant, changing it would change the
    answer. Under `PROVENANCE` the constant is not consulted at all, so a wild
    value must leave both results untouched.
    """
    for attenuation in (0.1, 0.6, 1.0):
        core = _core()
        ids = _chain(core)
        result = _engine(core, attenuation=attenuation).retract(AGENT, ids["a"], 0.0)
        by_id = {s.belief_id: s for s in result.steps}
        assert abs(by_id[ids["b"]].delta) == pytest.approx(0.4)
        assert abs(by_id[ids["c"]].delta) == pytest.approx(0.2)
        assert abs(by_id[ids["d"]].delta) == pytest.approx(0.1)


def test_own_evidence_shields_a_belief_from_its_supporter() -> None:
    """Grounding counts evidence as well as supporters.

    A belief corroborated three times over should barely notice one supporter
    going; a thinly-evidenced one should feel it. Neither behaviour is
    configured — both fall out of the provenance the store already holds.
    """
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="thin", proposition="Thin.", confidence=0.8, evidence_count=1),
            BeliefSpec(key="thick", proposition="Thick.", confidence=0.8, evidence_count=5),
            BeliefSpec(key="s", proposition="S.", confidence=0.8, supports=("thin", "thick")),
        ],
    )
    steps = {s.belief_id: s for s in _engine(core).retract(AGENT, ids["s"], 0.0).steps}
    assert abs(steps[ids["thick"]].delta) < abs(steps[ids["thin"]].delta)


def test_mandatory_provenance_forecloses_full_collapse() -> None:
    """A finding about the substrate, not about this engine.

    `BeliefUpdater._rejection_reason` refuses any candidate without evidence,
    so a purely derivative belief — the foundationalist's load-bearing case —
    is unrepresentable. Share is therefore capped at 0.5 and no belief can
    collapse with its supporter. Pinned so that if the provenance rule is ever
    relaxed, this result is known to depend on it.
    """
    core = _core()
    rejected = core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": "bc_1",
                    "agent_id": AGENT,
                    "proposition": "Rests on nothing of its own.",
                    "belief_type": "world_model",
                    "scope": "general",
                    "confidence": 0.8,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": [],
                }
            ],
        }
    )
    assert rejected["rejected"], "a belief with no evidence of its own must not exist"

    ids = _chain(core)
    result = _engine(core).retract(AGENT, ids["a"], 0.0)
    assert all(s.support_share <= 0.5 for s in result.steps if s.depth > 0)
