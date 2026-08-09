"""Deciding requirements §5: should a contradiction lower confidence directly?

Offline, `n=1`. Stage 2 established that the two arms behave differently.
Nothing there said which is *right* — and preferring one is not a result. This
file scores them against two standards neither arm gets to set.

**Standard 1 — round-trip coherence.** Assert a contradiction, then retract
the contradictor. The web must return to where it started. This is not a
matter of taste: a system whose final state depends on the order of events it
has since undone is incoherent, and it means retracting a false accusation
never restores the accused belief.

**Standard 2 — representability.** Requirements §2 named "Manyu can hold a
contested belief at 0.9" as a *defect*, before either arm existed, and made
fixing it part of the experiment's purpose. So: after a well-evidenced
contradiction, can any consumer reading `confidence` distinguish the disputed
belief from an otherwise identical undisputed one? Every downstream
consumer — `stake_of`, mood, salience, arbitration — reads confidence, not
`status`.
"""

from __future__ import annotations

import pytest

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.revision import (
    ContradictionArm,
    ContradictionPricing,
    RevisionConfig,
    RevisionEngine,
    load_topology,
    topology_specs,
)

AGENT = "agent_demo"
ARMS = [ContradictionArm.EVIDENTIAL, ContradictionArm.DIRECT]


def _seeded(name: str, arm: ContradictionArm):
    fixture = load_topology(name)
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, topology_specs(fixture))
    return fixture, ids, core, RevisionEngine(core.store, FrozenClock(), arm)


# --- standard 1: round-trip coherence ---------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_asserting_then_retracting_a_contradiction_returns_to_the_start(arm: ContradictionArm) -> None:
    """Both arms must pass. `DIRECT` did not, until suppression was written.

    Relief existed while suppression did not, so `DIRECT` credited a belief
    for the removal of a cost it had never paid: the target finished *above*
    0.8 having been contradicted and then un-contradicted. Confidence created
    from nothing.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", arm)
    start = core.store.get_belief(ids["disputed"]).confidence

    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
    engine.retract(AGENT, ids["counter"], to_confidence=0.0)

    assert core.store.get_belief(ids["disputed"]).confidence == pytest.approx(start), (
        "the web must return to where it started once the contradiction is gone"
    )


def test_the_round_trip_closes_at_partial_retraction_too() -> None:
    """Not just at zero — the relief is the exact differential of the penalty.

    A round trip that only closes on full retraction would mean the two
    formulas merely coincide at one endpoint.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.DIRECT)
    start = core.store.get_belief(ids["disputed"]).confidence
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
    suppressed = core.store.get_belief(ids["disputed"]).confidence
    charged = start - suppressed

    # Remove exactly half the contradictor's confidence.
    counter = core.store.get_belief(ids["counter"]).confidence
    engine.retract(AGENT, ids["counter"], to_confidence=counter / 2)
    refunded = core.store.get_belief(ids["disputed"]).confidence - suppressed

    # Stated as a proportion rather than a number, so the invariant survives
    # any change to how the penalty is priced.
    assert refunded == pytest.approx(charged / 2)


# --- standard 2: is a dispute representable at all? -------------------------


def test_direct_makes_a_disputed_belief_distinguishable() -> None:
    fixture, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.DIRECT)
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])

    disputed = core.store.get_belief(ids["disputed"])
    undisputed = core.store.get_belief(ids["undisputed"])
    assert disputed.confidence < undisputed.confidence
    assert disputed.confidence == pytest.approx(fixture["expect"]["direct"]["disputed_after_assert"])


# --- pricing: the constant is gone (requirements §12) ------------------------


def test_a_well_grounded_belief_resists_a_lone_objection() -> None:
    """The property that justifies removing `contradiction_penalty`.

    Two beliefs, the same objection, differing only in evidence count. A fixed
    penalty cannot represent this at any value, because it cannot see the
    target's grounding.
    """
    fixture, ids, core, engine = _seeded("resistance_to_a_lone_objection", ContradictionArm.DIRECT)
    for pair in fixture["contradictions"]:
        engine.assert_contradiction(AGENT, ids[pair["contradictor"]], ids[pair["target"]])

    thin_drop = 0.8 - core.store.get_belief(ids["thin"]).confidence
    thick_drop = 0.8 - core.store.get_belief(ids["thick"]).confidence
    assert thick_drop > 0, "corroboration is resistance, not immunity"
    assert thick_drop < thin_drop, f"thin {thin_drop:.3f} vs thick {thick_drop:.3f}"


def test_the_fixed_ablation_cannot_tell_them_apart() -> None:
    """The ablation, shown failing — otherwise the test above proves nothing
    about the *constant*, only that the new code does something."""
    fixture = load_topology("resistance_to_a_lone_objection")
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, topology_specs(fixture))
    engine = RevisionEngine(
        core.store,
        FrozenClock(),
        ContradictionArm.DIRECT,
        RevisionConfig(contradiction_pricing=ContradictionPricing.FIXED, contradiction_penalty=0.3),
    )
    for pair in fixture["contradictions"]:
        engine.assert_contradiction(AGENT, ids[pair["contradictor"]], ids[pair["target"]])

    thin = core.store.get_belief(ids["thin"]).confidence
    thick = core.store.get_belief(ids["thick"]).confidence
    assert thin == pytest.approx(thick), "a constant is blind to grounding, by construction"


def test_a_second_objection_dilutes_the_first_rather_than_stacking() -> None:
    """All contradictors sit in the denominator.

    Otherwise n objections would drive any belief to zero regardless of how
    well grounded it is, which is a majority vote rather than an epistemology.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="t", proposition="T.", confidence=0.9, evidence_count=2),
            BeliefSpec(key="c1", proposition="C1.", confidence=0.8),
            BeliefSpec(key="c2", proposition="C2.", confidence=0.8),
        ],
    )
    engine = RevisionEngine(core.store, FrozenClock(), ContradictionArm.DIRECT)
    engine.assert_contradiction(AGENT, ids["c1"], ids["t"])
    after_one = core.store.get_belief(ids["t"]).confidence
    engine.assert_contradiction(AGENT, ids["c2"], ids["t"])
    after_two = core.store.get_belief(ids["t"]).confidence

    assert after_two < after_one, "a second objection must still count for something"
    assert (after_one - after_two) < (0.9 - after_one), "but for less than the first did"


def test_evidential_leaves_a_disputed_belief_numerically_identical() -> None:
    """The defect requirements §2 set out to fix, reproduced exactly.

    Status records the dispute; every consumer that reads confidence is blind
    to it. This is what disqualifies the arm.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.EVIDENTIAL)
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])

    disputed = core.store.get_belief(ids["disputed"])
    undisputed = core.store.get_belief(ids["undisputed"])

    assert disputed.confidence == pytest.approx(undisputed.confidence) == pytest.approx(0.8)
    assert disputed.status.value == "contested", "the dispute exists — but only as a flag"


def test_evidential_hides_the_dispute_from_the_dissonance_channel_too() -> None:
    """The blindness is not confined to `confidence`.

    `stake_of` multiplies by confidence, so under `EVIDENTIAL` a belief facing
    five evidence records against it carries exactly the stake of one facing
    none. The dispute cannot reach any affect consumer either.
    """
    results = {}
    for arm in ARMS:
        _, ids, core, engine = _seeded("disputed_vs_undisputed", arm)
        engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
        signal = MergedDissonanceQuery(core.store).detect(AGENT, "dispute")
        results[arm] = (signal.magnitude if signal else 0.0, core.store.get_belief(ids["disputed"]).confidence)

    direct_magnitude, direct_conf = results[ContradictionArm.DIRECT]
    evidential_magnitude, evidential_conf = results[ContradictionArm.EVIDENTIAL]

    assert direct_conf < evidential_conf
    assert direct_magnitude < evidential_magnitude, (
        "under DIRECT the weakened belief carries less stake, so the tension it can support is lower"
    )


# --- the gate ---------------------------------------------------------------


def test_asserting_the_same_contradiction_twice_charges_once() -> None:
    """Found by adversarial audit, not by the suite.

    Before the guard, a second assertion charged again: 0.80 → 0.56 → 0.32.
    Any harness re-applying a fixture's declared edges, or any re-processing
    of the same web, compounded the penalty without bound.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.DIRECT)
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
    once = core.store.get_belief(ids["disputed"]).confidence
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
    assert core.store.get_belief(ids["disputed"]).confidence == pytest.approx(once)


def test_refunds_never_exceed_what_was_charged() -> None:
    """Found by adversarial audit.

    Relief fired on every weakening of the contradictor with no memory of the
    balance, so a contradictor that weakened, recovered, and weakened again
    refunded twice: a belief charged 0.24 finished at 0.92, above the 0.80 it
    held before it was ever contradicted. The ledger is reconstructed from the
    revision trail, so it cannot drift from the movements it accounts for.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.DIRECT)
    start = core.store.get_belief(ids["disputed"]).confidence
    engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])

    engine.retract(AGENT, ids["counter"], to_confidence=0.4)
    recovered = core.store.get_belief(ids["counter"])
    core.store.save_belief(recovered.model_copy(update={"confidence": 0.9}))
    engine.retract(AGENT, ids["counter"], to_confidence=0.0)

    assert core.store.get_belief(ids["disputed"]).confidence <= start + 1e-9


def test_a_fully_retracted_contradictor_leaves_no_suppression_behind() -> None:
    """Path-independence, and the audit case that nearly slipped through.

    When the contradictor loses grounding alongside its target, the `seen`
    guard skips that weakening — and under incremental refunds that portion
    was gone for good, leaving the target permanently suppressed by something
    that no longer existed. Since round-trip coherence is the standard the arm
    was *chosen* on, a topology where it silently fails would undercut the
    decision itself.

    Refunds now price against the contradictor's current confidence, so the
    balance is correct however it got there.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="p", proposition="P.", confidence=0.8),
            BeliefSpec(key="q", proposition="Q.", confidence=0.8),
            BeliefSpec(key="x", proposition="X.", confidence=0.8, supports=("p", "q")),
        ],
    )
    engine = RevisionEngine(core.store, FrozenClock(), ContradictionArm.DIRECT)
    engine.assert_contradiction(AGENT, ids["q"], ids["p"])

    engine.retract(AGENT, ids["x"], 0.0)  # weakens P and Q together
    engine.retract(AGENT, ids["q"], 0.0)  # then removes the contradictor

    charged, refunded = engine._suppression_ledger(ids["p"], ids["q"])
    assert refunded == pytest.approx(charged), "a departed contradictor must leave nothing behind"

    # P should be down only by what it lost in grounding, not by the charge.
    assert core.store.get_belief(ids["p"]).confidence == pytest.approx(0.4)


def test_retract_refuses_to_raise_confidence() -> None:
    """Found by adversarial audit.

    `_propagate` used `abs(shock)`, so *any* change weakened everything
    downstream regardless of direction — raising a supporter from 0.4 to 0.9
    pushed its target from 0.80 to 0.55. The propagation is now signed, and
    this entry point rejects a direction it does not model.
    """
    _, ids, core, engine = _seeded("disputed_vs_undisputed", ContradictionArm.DIRECT)
    current = core.store.get_belief(ids["disputed"]).confidence
    with pytest.raises(ValueError, match="must not raise confidence"):
        engine.retract(AGENT, ids["disputed"], to_confidence=current + 0.1)


# --- ingest prices contradictions (requirements §14) -------------------------


def _extracted(core: ManyuCore, contradicts: tuple[str, ...] = ()) -> dict:
    """Exactly the shape a live extractor emits: edges declared by belief_key."""
    def cand(cid, prop, key, edges=()):
        return {
            "candidate_id": cid, "agent_id": AGENT, "proposition": prop, "belief_key": key,
            "belief_type": "world_model", "scope": "general", "confidence": 0.8,
            "source_mix": {"operator_note": 1.0}, "evidence_ids": [f"bev_{cid}"],
            "contradicts": list(edges),
        }
    return core.update_beliefs({"agent_id": AGENT, "candidates": [
        cand("1", "The deploy succeeded.", "world_model/general/deploy-ok"),
        cand("2", "The deploy failed.", "world_model/general/deploy-bad", contradicts),
    ]})


def test_an_extractor_declared_contradiction_is_priced_on_ingest() -> None:
    """The Stage 4 blocker.

    `BeliefUpdater` records the edge and marks the *declaring* belief
    contested, which left the belief being contradicted untouched in every
    channel: confidence 0.8, status ACTIVE, no edge of its own. Under the
    adopted arm a live run would have read as a flat null that looked like a
    finding — experiment 1's v2 knob-with-nothing-to-bite-on, in a new place.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    result = _extracted(core, ("world_model/general/deploy-ok",))

    assert result["contradictions_priced"], "ingest must charge, not merely record"
    target = next(b for b in core.store.list_beliefs(AGENT, include_inactive=True) if b.belief_key == "world_model/general/deploy-ok")
    assert target.confidence < 0.8, "the contradicted belief must feel it"
    assert target.status.value == "contested", "and be marked, not just quieter"


def test_ingest_pricing_is_idempotent_across_reruns() -> None:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    _extracted(core, ("world_model/general/deploy-ok",))
    once = next(b for b in core.store.list_beliefs(AGENT, include_inactive=True) if b.belief_key == "world_model/general/deploy-ok").confidence
    _extracted(core, ("world_model/general/deploy-ok",))
    twice = next(b for b in core.store.list_beliefs(AGENT, include_inactive=True) if b.belief_key == "world_model/general/deploy-ok").confidence
    assert twice == pytest.approx(once)


def test_the_evidential_arm_still_leaves_ingested_contradictions_unpriced() -> None:
    """The ablation must remain runnable through the same pipeline."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, contradiction_arm=ContradictionArm.EVIDENTIAL)
    _extracted(core, ("world_model/general/deploy-ok",))
    target = next(b for b in core.store.list_beliefs(AGENT, include_inactive=True) if b.belief_key == "world_model/general/deploy-ok")
    assert target.confidence == pytest.approx(0.8)
    assert target.status.value == "contested", "EVIDENTIAL still records the dispute as a flag"


def test_ingest_without_contradictions_prices_nothing() -> None:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    assert _extracted(core)["contradictions_priced"] == []


def _mutual(order: tuple[str, str]) -> tuple[ManyuCore, dict[str, str]]:
    """A contradicts B and B contradicts A, emitted in the given order."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    def cand(cid, prop, key, edges):
        return {
            "candidate_id": cid, "agent_id": AGENT, "proposition": prop, "belief_key": key,
            "belief_type": "world_model", "scope": "general", "confidence": 0.8,
            "source_mix": {"operator_note": 1.0}, "evidence_ids": [f"bev_{cid}"],
            "contradicts": list(edges),
        }
    specs = {
        "x": cand("1", "X is so.", "wm/g/x", ["wm/g/y"]),
        "y": cand("2", "X is not so.", "wm/g/y", ["wm/g/x"]),
    }
    core.update_beliefs({"agent_id": AGENT, "candidates": [specs[k] for k in order]})
    return core, {b.belief_key: b.belief_id for b in core.store.list_beliefs(AGENT, include_inactive=True)}


def test_mutual_contradictions_are_priced_symmetrically() -> None:
    """Found in Stage 4 pre-flight, not by the suite.

    Charging sequentially meant the first charge weakened its target, so the
    reciprocal charge landed against a weaker opponent: the pair settled at
    0.6/0.4 with the split decided purely by which candidate the extractor
    emitted first. Pricing a batch against a snapshot makes it atomic.
    """
    for order in (("x", "y"), ("y", "x")):
        core, ids = _mutual(order)
        x = core.store.get_belief(ids["wm/g/x"]).confidence
        y = core.store.get_belief(ids["wm/g/y"]).confidence
        assert x == pytest.approx(y), f"emit order {order} produced {x} vs {y}"


def test_a_refund_never_undoes_an_explicit_retraction() -> None:
    """Also from pre-flight, and it broke the standard §5 was decided on.

    Retracting both halves of a mutual contradiction left a belief that had
    been deliberately driven to 0.0 sitting back at 0.4 — and the final state
    differed by emission order (`x=0.0,y=0.4` one way, `y=0.2,x=0.0` the
    other). A retraction is a deliberate statement about a belief; lifting its
    suppressor must not quietly reverse it.
    """
    for order in (("x", "y"), ("y", "x")):
        core, ids = _mutual(order)
        core.retract_belief({"belief_id": ids["wm/g/y"], "arm": "direct"})
        core.retract_belief({"belief_id": ids["wm/g/x"], "arm": "direct"})
        final = {k: core.store.get_belief(v).confidence for k, v in ids.items()}
        assert all(v == pytest.approx(0.0) for v in final.values()), f"order {order}: {final}"


def test_gate_the_deciding_fixture_actually_separates_the_arms() -> None:
    """A fixture on which both arms agree cannot decide anything. Checked
    before the verdict is read, per experiment 2's gate #1."""
    outcomes = set()
    for arm in ARMS:
        _, ids, core, engine = _seeded("disputed_vs_undisputed", arm)
        engine.assert_contradiction(AGENT, ids["counter"], ids["disputed"])
        outcomes.add(round(core.store.get_belief(ids["disputed"]).confidence, 6))
    assert len(outcomes) == 2, f"the arms are indistinguishable on this fixture: {outcomes}"
