"""Experiment 4 §5.1 — what the substrate forces, before any mechanism exists.

Written *before* `salience.py` exists, and deliberately so. Experiment 3's
retrospective §3.1 recorded that its own suite caught none of sixteen defects,
and named the cause as structural: every test was written minutes after the
mechanism it covered, by the author who had just written it, so it agreed with
the code precisely where the code was wrong.

These tests cover no mechanism of this experiment's. They pin properties of the
*substrate* that decide what experiment 4 can possibly observe — the same
category that produced experiment 3 §11.1, where mandatory provenance turned out
to foreclose foundationalist collapse before any run happened.

The finding they encode:

    `contradicts` edges are only ever added — `BeliefUpdater.update` unions them
    (`services.py`, pass 2) and `_revise` does not touch the field at all, while
    `RevisionEngine.assert_contradiction` also only unions. `_leaf_conflicts`
    therefore never shrinks, and `magnitude_raw` sums `min(stake_a, stake_b)`
    over those leaves.

    So **tension can only fall by weakening a party — a conflict can never be
    retired** — and because the rule is `min`, the only move that changes
    anything is weakening whichever side is *already weaker*.

Consequence for the experiment: "tension fell" is never evidence that anything
was resolved. §5.8's criterion tests depend on that being true, and
`test_a_conflict_is_still_named_when_its_tension_reads_zero` below is what makes
resolution and capitulation separable at all.

If any test here fails, experiment 4's headline is re-openable rather than
quietly wrong.

Entirely offline. No provider is constructed anywhere in this file.
"""

from __future__ import annotations

import pytest

from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery, _tension, stake_of
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.schemas import BeliefStatus

AGENT = "agent_demo"


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _seeded(specs: list[BeliefSpec]) -> tuple[ManyuCore, dict[str, str]]:
    core = _core()
    return core, seed_beliefs(core, specs)


def _evidence(core: ManyuCore, key: str, *, count: int = 1, salience: float = 0.5) -> list[str]:
    ids = []
    for index in range(count):
        record = core.capture_belief_evidence(
            {
                "agent_id": AGENT,
                "source_type": "operator_note",
                "source_id": f"{key}_{index}",
                "summary": f"evidence {index} for {key}",
                "affective_salience": salience,
                "epistemic_weight": 0.7,
            }
        )
        ids.append(record["evidence_id"])
    return ids


def _ingest(
    core: ManyuCore,
    key: str,
    proposition: str,
    *,
    evidence_ids: list[str],
    confidence: float = 0.7,
    valence: float = 0.0,
    contradicts: tuple[str, ...] = (),
) -> dict:
    """Ingest through the production path — `update_beliefs`, not the seeder.

    `fork.seed_beliefs` writes edges straight to the store with `model_copy`,
    replacing rather than unioning, precisely so experiment 2 could vary
    `status` and `contradicts` independently. Claims about what production code
    can do to an edge must therefore go through the updater.
    """
    return core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": f"bcand_{key}_{len(evidence_ids)}",
                    "agent_id": AGENT,
                    "proposition": proposition,
                    "belief_key": key,
                    "belief_type": "world_model",
                    "scope": "general",
                    "confidence": confidence,
                    "stability": 0.1,
                    "valence": valence,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": evidence_ids,
                    "contradicts": list(contradicts),
                }
            ],
        }
    )


def _by_key(core: ManyuCore, key: str):
    for belief in core.store.list_beliefs(AGENT, include_inactive=True):
        if belief.belief_key == key:
            return belief
    raise KeyError(key)


def _set_confidence(core: ManyuCore, belief_id: str, value: float) -> None:
    """Move confidence without invoking propagation.

    The claims in this file are about the *arithmetic* of `_tension`, so the
    revision engine's ripple would be a confound rather than a help.
    """
    belief = core.store.get_belief(belief_id)
    core.store.save_belief(belief.model_copy(update={"confidence": value}))


def _raw(core: ManyuCore) -> float:
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "substrate")
    return 0.0 if signal is None else signal.magnitude_raw


#: One conflicting pair, equal on both sides. The base fixture for the
#: arithmetic claims below.
_PAIR = [
    BeliefSpec(key="pos", proposition="The claim holds.", valence=0.6, salience=0.8, confidence=0.8),
    BeliefSpec(
        key="neg",
        proposition="The claim does not hold.",
        valence=-0.6,
        salience=0.8,
        confidence=0.8,
        contradicts=("pos",),
    ),
]


# --- the edge is permanent ---------------------------------------------------

def test_contradicts_edges_are_never_cleared() -> None:
    """No production path removes a `contradicts` edge, so no conflict retires.

    Exercises every path that writes the field: ingest that declares one, ingest
    that does *not* declare one on an existing belief, and full retraction of
    both parties. This is the load-bearing fact for the whole experiment — if it
    ever stops holding, "the loop converged" becomes a claim that needs checking
    again rather than one that was never available.
    """
    core = _core()
    _ingest(core, "pos", "The claim holds.", evidence_ids=_evidence(core, "pos"), confidence=0.8)
    _ingest(
        core,
        "neg",
        "The claim does not hold.",
        evidence_ids=_evidence(core, "neg"),
        confidence=0.8,
        contradicts=("pos",),
    )
    pos_id = _by_key(core, "pos").belief_id
    assert _by_key(core, "neg").contradicts == [pos_id]

    # Re-ingest the same belief with fresh evidence and *no* declared edge.
    # `_revise` does not carry `contradicts` in its update dict, and pass 2
    # only unions when the candidate declares something, so the edge survives.
    _ingest(
        core,
        "neg",
        "The claim does not hold.",
        evidence_ids=_evidence(core, "neg_more"),
        confidence=0.4,
    )
    assert _by_key(core, "neg").contradicts == [pos_id], "re-ingestion without an edge cleared one"

    # Retract both parties to nothing. Retraction collapses confidence and
    # keeps provenance; it does not touch the graph.
    for key in ("pos", "neg"):
        result = core.retract_belief({"agent_id": AGENT, "belief_id": _by_key(core, key).belief_id, "arm": "direct"})
        assert result["status"] == "ok", result
    assert _by_key(core, "neg").contradicts == [pos_id], "retraction cleared an edge"


def test_a_retired_conflict_is_unrepresentable() -> None:
    """There is no reachable state with the edge gone and the beliefs present.

    The companion to the test above, stated as the property rather than as a
    walk through the paths: whatever is done to the pair, the conflict is still
    in `_leaf_conflicts` and still named by a carrier.
    """
    core, ids = _seeded(_PAIR)
    for value in (0.8, 0.4, 0.0):
        _set_confidence(core, ids["neg"], value)
        signal = MergedDissonanceQuery(core.store).detect(AGENT, "substrate")
        assert signal is not None, f"the conflict vanished entirely at confidence {value}"
        named = {tuple(sorted((c.belief_id_a, c.belief_id_b))) for c in signal.carriers}
        assert tuple(sorted((ids["pos"], ids["neg"]))) in named


# --- tension falls only one way ----------------------------------------------

def test_tension_falls_only_by_weakening_a_party() -> None:
    """Every path to a lower `magnitude_raw` runs through a lowered stake.

    Nothing else in the substrate is an input to it: the edge set cannot shrink,
    valences are untouched by revision (pinned in experiment 3's
    `test_the_valences_are_untouched_by_revision`), and `stake_of` is
    `mean(salience) x confidence`.
    """
    core, ids = _seeded(_PAIR)
    before = _raw(core)
    assert before > 0.0, "the base fixture registers no tension, so nothing below is readable"

    _set_confidence(core, ids["neg"], 0.4)
    after = _raw(core)
    assert after < before, f"weakening a party did not lower tension ({before} -> {after})"

    _set_confidence(core, ids["neg"], 0.0)
    assert _raw(core) == pytest.approx(0.0), "a zero-stake party should leave no tension to read"


def test_the_min_rule_forces_movement_onto_the_weaker_side() -> None:
    """Weakening the *stronger* party changes `magnitude_raw` by exactly zero.

    `_tension` takes `min(stake_a, stake_b)`, so above that floor the signal is
    blind — experiment 3 retrospective §3.3 measured this as raw tension moving
    identically under both contradiction arms. Stated here as what it means for
    a *control* loop: there is only ever one side worth acting on, and the
    substrate has already chosen it.
    """
    core, ids = _seeded(
        [
            BeliefSpec(key="strong", proposition="The claim holds.", valence=0.6, salience=0.8, confidence=0.9),
            BeliefSpec(
                key="weak",
                proposition="The claim does not hold.",
                valence=-0.6,
                salience=0.3,
                confidence=0.3,
                contradicts=("strong",),
            ),
        ]
    )
    baseline = _raw(core)

    # Halve the stronger party. It stays above the weaker one, so nothing moves.
    _set_confidence(core, ids["strong"], 0.45)
    assert _raw(core) == pytest.approx(baseline), "the min rule should have made this a no-op"

    # Touch the weaker party by a fraction of that, and the signal responds.
    _set_confidence(core, ids["weak"], 0.2)
    assert _raw(core) < baseline, "weakening the weaker side left the signal unmoved, so nothing can move it"


def test_stake_is_blind_to_grounding_count() -> None:
    """Five evidence records and one produce the same stake.

    `stake_of` averages salience rather than summing it, so corroboration does
    not register. This is the fact the adversarial fixture exploits: the loop's
    only available move is decided by stake, and stake cannot see how
    well-grounded a belief is. Experiment 3 §12.1 made grounding count for
    *contradiction pricing*; it does not count here.
    """
    core, ids = _seeded(
        [
            BeliefSpec(key="thin", proposition="Thinly grounded.", salience=0.6, confidence=0.7, evidence_count=1),
            BeliefSpec(key="thick", proposition="Thickly grounded.", salience=0.6, confidence=0.7, evidence_count=5),
        ]
    )
    thin = core.store.get_belief(ids["thin"])
    thick = core.store.get_belief(ids["thick"])
    assert len(thick.evidence_ids) == 5 * len(thin.evidence_ids), "the fixture does not differ in grounding"
    thin_stake, thick_stake = stake_of(core.store, thin), stake_of(core.store, thick)
    assert thin_stake == pytest.approx(thick_stake), (
        f"stake can see grounding count after all: thin={thin_stake}, thick={thick_stake}. "
        f"If this is now true, the adversarial fixture's premise has changed"
    )


# --- the discriminator this leaves available ---------------------------------

def test_a_conflict_is_still_named_when_its_tension_reads_zero() -> None:
    """Carriers survive what magnitude does not, and that is the whole opening.

    `MergedDissonanceQuery.detect` builds carriers from the closure and bails
    only when there are none; the tension figure is computed separately. So a
    conflict whose party has been driven to zero stake reports
    `magnitude_raw == 0` while still *naming* both beliefs.

    That is what makes capitulation distinguishable from resolution at all: a
    web that quieted itself by hollowing out one side looks silent in the
    magnitude channel and remains fully visible in the carrier channel.
    Requirements §12 says to read carriers rather than magnitude; this is the
    mechanical reason it is possible.
    """
    core, ids = _seeded(_PAIR)
    _set_confidence(core, ids["neg"], 0.0)

    signal = MergedDissonanceQuery(core.store).detect(AGENT, "substrate")
    assert signal is not None, "the signal went silent and took the conflict with it"
    assert signal.magnitude_raw == pytest.approx(0.0), f"a zero-stake party still priced at {signal.magnitude_raw}"
    assert signal.carriers, "no carrier named the conflict that is still in the store"
    named = {tuple(sorted((c.belief_id_a, c.belief_id_b))) for c in signal.carriers}
    assert tuple(sorted((ids["pos"], ids["neg"]))) in named


def test_confidence_collapse_does_not_remove_a_belief_from_the_query() -> None:
    """A confound I suspected and ruled out, pinned so it cannot arrive later.

    `MergedDissonanceQuery` reads `list_beliefs`, which excludes only
    `deprecated`, and `RevisionEngine._apply` downgrades no further than
    `TENTATIVE`. So retraction does not make a belief vanish from the query.

    Were that ever to change, tension would fall because a *party disappeared*
    rather than because anything was weakened — and it would read identically to
    convergence in every channel this experiment records.
    """
    core, ids = _seeded(_PAIR)
    result = core.retract_belief({"agent_id": AGENT, "belief_id": ids["neg"], "arm": "direct"})
    assert result["status"] == "ok", result

    retracted = core.store.get_belief(ids["neg"])
    assert retracted.confidence == pytest.approx(0.0), f"retraction left confidence at {retracted.confidence}"
    assert retracted.status is not BeliefStatus.DEPRECATED, (
        "retraction now deprecates, so the belief leaves list_beliefs and tension falls because a "
        "party vanished — indistinguishable from convergence in every recorded channel"
    )
    visible = {belief.belief_id for belief in core.store.list_beliefs(AGENT)}
    assert ids["neg"] in visible, "a retracted belief dropped out of the dissonance query's input"


# --- the arithmetic these rest on --------------------------------------------

def test_tension_is_symmetric_in_its_arguments() -> None:
    """`_tension(a, b) == _tension(b, a)`, or every claim above is order-dependent.

    Cheap, and it is the kind of thing experiment 3 found by adversarial probing
    rather than by testing: `_relieve_contradictions` treated a directional
    relation as symmetric and paid the wrong belief.
    """
    core, ids = _seeded(_PAIR)
    pos = core.store.get_belief(ids["pos"])
    neg = core.store.get_belief(ids["neg"])
    forward, backward = _tension(core.store, pos, neg), _tension(core.store, neg, pos)
    assert forward == pytest.approx(backward), f"tension is order-dependent: {forward} vs {backward}"


def test_a_belief_with_no_evidence_has_zero_stake() -> None:
    """The zero-valued operand case from experiment 3's adversarial checklist.

    Mandatory provenance means this should be unreachable through ingest, so the
    branch exists for stores assembled another way. Pinned because a stake that
    silently defaulted to something non-zero would manufacture tension out of an
    unprovenanced belief.
    """
    core, ids = _seeded(_PAIR)
    pos = core.store.get_belief(ids["pos"])
    unprovenanced = stake_of(core.store, pos.model_copy(update={"evidence_ids": []}))
    assert unprovenanced == 0.0, f"an unprovenanced belief carries stake {unprovenanced} and can manufacture tension"
