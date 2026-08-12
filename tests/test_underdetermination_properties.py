"""Properties the criterion and the derivation must hold on any web, not just the fixtures.

The fixtures ask "does it get these six cases right." These ask "is it the kind
of thing that could be right at all" — determinism, idempotence, symmetry,
invariance under things that should not matter. Experiment 4's tie-break defect
(random because it ran on `uuid4`) was found by a property test over repeated
stores, not by a fixture, and the mutant battery in this experiment found the same
family hiding in a *test*.

Also here: the instrument gate. `assert_not_noop` on the derivation and
`assert_has_range` on the meta-belief's confidence, run before any stage's numbers
are readable — a derivation that cannot fire and a confidence pinned at one value
both make everything downstream unreadable, and neither shows up as a failure.

Entirely offline.
"""

from __future__ import annotations

import pytest

from manyu.core import ManyuCore
from manyu.gate import assert_has_range, assert_not_noop
from manyu.schemas import BeliefType
from manyu.underdetermination import (
    EXPRESSION_THRESHOLD,
    OverlapConfig,
    OverlapMode,
    apply_then,
    derive,
    evidence_overlap,
    find_rival_sets,
    is_underdetermined,
    read,
    seed_fixture,
    separating_evidence,
)

AGENT = "agent_demo"
DERIVING = ("symmetric_rivals", "symmetric_rivals_oneway", "near_miss", "three_way")
DECLINING = ("shared_evidence_no_conflict", "conflict_disjoint_evidence")


def _core(name: str) -> ManyuCore:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_fixture(core, name, agent_id=AGENT)
    return core


def _beliefs(core: ManyuCore):
    return core.store.list_beliefs(AGENT, include_inactive=True)


# --- determinism -------------------------------------------------------------


@pytest.mark.parametrize("name", DERIVING + DECLINING)
def test_the_same_web_gives_the_same_rival_sets_every_time(name: str) -> None:
    """Belief ids come from `uuid4`, so a mechanism that leaks id ordering into
    its *decisions* is random and will look deterministic in any single run.

    Compared by `belief_key` rather than by id, since the ids differ by
    construction between two independently seeded stores. What must be stable is
    *which readings* are named, not what they happen to be called.
    """
    seen = set()
    for _ in range(6):
        core = _core(name)
        keyed = {b.belief_id: b.belief_key for b in _beliefs(core)}
        found = frozenset(tuple(sorted(keyed[bid] for bid in rs.belief_ids)) for rs in find_rival_sets(_beliefs(core)))
        seen.add(found)
    assert len(seen) == 1, f"rival sets varied across identical stores: {seen}"


@pytest.mark.parametrize("name", DERIVING)
def test_the_derived_confidence_is_stable_across_identical_stores(name: str) -> None:
    values = set()
    for _ in range(6):
        core = _core(name)
        values.add(tuple(sorted(round(row["derived_overlap"], 9) for row in derive(core, AGENT).as_dict()["derived"])))
    assert len(values) == 1, f"derived confidence varied across identical stores: {values}"


# --- symmetry and invariance -------------------------------------------------


@pytest.mark.parametrize("name", DERIVING + DECLINING)
def test_the_criterion_is_symmetric_in_its_arguments(name: str) -> None:
    """Requirements §6.1: the confidence channel already inherits the accident of
    which side declared the edge. The criterion must not.
    """
    beliefs = _beliefs(_core(name))
    for left in beliefs:
        for right in beliefs:
            if left.belief_id == right.belief_id:
                continue
            assert is_underdetermined(left, right) is is_underdetermined(right, left)
            assert separating_evidence(left, right) == separating_evidence(right, left)
            assert evidence_overlap(left, right) == pytest.approx(evidence_overlap(right, left))


def test_a_belief_is_never_underdetermined_with_itself() -> None:
    """Self-reference, from the standing method's list of inputs the author did
    not have in mind. A belief trivially shares all its evidence with itself, so
    a criterion checking only the evidence half would say yes.
    """
    beliefs = _beliefs(_core("symmetric_rivals"))
    for belief in beliefs:
        assert not is_underdetermined(belief, belief)


def test_evidence_volume_does_not_change_the_verdict_or_the_value() -> None:
    """`near_miss` carries three times `symmetric_rivals`' evidence with the same
    separation structure — which is to say, none.

    Pre-registration §3 predicted the values land within 0.05. They are identical,
    and the reason is structural: the quantity is a **ratio**, so cardinality
    cancels. A criterion tracking volume would need a term that does nothing else.
    """
    small = derive(_core("symmetric_rivals"), AGENT).as_dict()["derived"]
    large = derive(_core("near_miss"), AGENT).as_dict()["derived"]
    assert len(small) == len(large) == 1
    assert small[0]["derived_overlap"] == large[0]["derived_overlap"] == 1.0


# --- idempotence -------------------------------------------------------------


@pytest.mark.parametrize("name", DERIVING)
def test_re_deriving_an_unchanged_web_moves_nothing(name: str) -> None:
    """`BeliefUpdater._revise` only moves a belief on evidence it does not already
    hold, so a second pass over an unchanged web must be a no-op.

    Without the stable `belief_key` from the sorted rival ids this would mint a
    fresh meta-belief every pass — the defect experiment 1 found when restatements
    created a new single-evidence belief each turn.
    """
    core = _core(name)
    first = derive(core, AGENT).as_dict()["derived"]
    held_after_first = read(core, AGENT)
    for _ in range(4):
        derive(core, AGENT)
    held = read(core, AGENT)

    assert len(held) == len(held_after_first) == len(first), "re-derivation minted duplicate meta-beliefs"
    assert [row["confidence"] for row in held] == [row["confidence"] for row in held_after_first]


@pytest.mark.parametrize("name", DECLINING)
def test_a_web_with_no_standoff_derives_nothing_however_often_it_is_run(name: str) -> None:
    core = _core(name)
    for _ in range(3):
        assert derive(core, AGENT).as_dict()["derived"] == []
    assert read(core, AGENT) == []


# --- the meta-belief obeys the ordinary rules (FR-2) -------------------------


def test_the_meta_belief_carries_the_evidence_it_consulted() -> None:
    """FR-3. Its provenance is the records the criterion looked at, so the claim
    carries its own receipts and the honesty scorer can be pointed at it.
    """
    core = _core("symmetric_rivals")
    derived = derive(core, AGENT).as_dict()["derived"][0]
    rivals = [core.store.get_belief(bid) for bid in derived["rivals"]]
    consulted = set(rivals[0].evidence_ids) | set(rivals[1].evidence_ids)
    assert set(derived["evidence_ids"]) == consulted


def test_the_meta_belief_is_created_above_the_expression_threshold() -> None:
    """Stage −1's trap. Below 0.45 `BeliefUpdater._create` stamps TENTATIVE and
    `WorldviewSynthesizer` drops it silently, so a Stage 4 null would measure the
    threshold rather than the experiment.
    """
    for name in DERIVING:
        for row in derive(_core(name), AGENT).as_dict()["derived"]:
            assert row["confidence"] >= EXPRESSION_THRESHOLD, (name, row["confidence"])
            assert row["below_expression_threshold"] is False


def test_the_meta_belief_is_typed_and_reachable_by_query() -> None:
    core = _core("symmetric_rivals")
    derive(core, AGENT)
    typed = core.store.list_beliefs(AGENT, belief_type=BeliefType.UNDERDETERMINATION.value, include_inactive=True)
    assert len(typed) == 1
    assert typed[0].rivals and len(typed[0].rivals) == 2


def test_nothing_but_derivation_can_produce_the_type_or_the_rivals() -> None:
    """Requirements §7, as a property of the schema rather than of our restraint.

    `BeliefCandidate` has no `rivals` field and the extractor schema does not
    offer `underdetermination`, so a fixture or a model cannot declare a standoff
    — there is nowhere to write it. An implementer's discipline is not a
    constraint; an absent field is.
    """
    from manyu.schemas import BeliefCandidate
    from manyu.services import BeliefExtractor

    assert "rivals" not in BeliefCandidate.model_fields
    schema = BeliefExtractor()._schema()
    enum = schema["properties"]["candidates"]["items"]["properties"]["belief_type"]["enum"]
    assert BeliefType.UNDERDETERMINATION.value not in enum

    # And the refusal is loud rather than silent: `ManyuModel` sets
    # `extra="forbid"`, so a smuggled `rivals` is a validation error rather than a
    # field quietly dropped on the floor. That is the better failure — a dropped
    # field would let a fixture author believe the declaration took effect.
    import pydantic

    core = _core("symmetric_rivals")
    with pytest.raises(pydantic.ValidationError):
        core.update_beliefs(
            {
                "agent_id": AGENT,
                "candidates": [
                    {
                        "candidate_id": "bcand_smuggled",
                        "agent_id": AGENT,
                        "proposition": "These readings cannot be told apart.",
                        "belief_key": "smuggled",
                        "belief_type": "world_model",
                        "scope": "general",
                        "confidence": 0.9,
                        "stability": 0.1,
                        "valence": 0.0,
                        "source_mix": {"operator_note": 1.0},
                        "evidence_ids": _beliefs(core)[0].evidence_ids,
                        "rivals": ["bel_anything", "bel_else"],
                    }
                ],
            }
        )

    # **The type itself is not fully unreachable, and pretending otherwise would
    # be the weaker claim.** `BeliefType.UNDERDETERMINATION` is a real enum
    # member, so a hand-written candidate against the API can set it and will
    # validate. What it cannot do is carry a rival set, because that field does
    # not exist on a candidate — so what it produces is a belief with the type and
    # `rivals == []`, which is not a standoff and cannot be mistaken for one by
    # anything reading `rivals`.
    #
    # Neither path §7 is about can reach even that far: the fixture format has no
    # `belief_type` key (`seed_web` writes `world_model`), and the extractor schema
    # does not offer the value.
    smuggled_type = core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": "bcand_typed",
                    "agent_id": AGENT,
                    "proposition": "A belief that merely claims the type.",
                    "belief_key": "typed",
                    "belief_type": BeliefType.UNDERDETERMINATION.value,
                    "scope": "general",
                    "confidence": 0.9,
                    "stability": 0.1,
                    "valence": 0.0,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": _beliefs(core)[0].evidence_ids,
                }
            ],
        }
    )
    typed = core.store.get_belief(smuggled_type["accepted"][0]["belief_id"])
    assert typed.belief_type is BeliefType.UNDERDETERMINATION
    assert typed.rivals == [], "a candidate managed to declare a rival set"

    # A misspelled type is refused outright, so the enum is not a free-text field.
    with pytest.raises(pydantic.ValidationError):
        core.update_beliefs(
            {
                "agent_id": AGENT,
                "candidates": [
                    {
                        "candidate_id": "bcand_typed",
                        "agent_id": AGENT,
                        "proposition": "These readings cannot be told apart.",
                        "belief_key": "typed",
                        "belief_type": "underdetermination_but_misspelled",
                        "scope": "general",
                        "confidence": 0.9,
                        "stability": 0.1,
                        "valence": 0.0,
                        "source_mix": {"operator_note": 1.0},
                        "evidence_ids": _beliefs(core)[0].evidence_ids,
                    }
                ],
            }
        )


# --- collapse ----------------------------------------------------------------

def test_separating_evidence_weakens_the_meta_belief_through_the_ordinary_path() -> None:
    """FR-2 and pre-registration §2. No bespoke rule: the separating record enters
    the meta-belief's own provenance, so `blend_confidence` treats it exactly as it
    treats disconfirming evidence for any other belief.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    minted = seed_fixture(core, "discriminating", agent_id=AGENT)
    before = derive(core, AGENT).as_dict()["derived"][0]["confidence"]

    apply_then(core, "discriminating", minted, agent_id=AGENT)
    result = derive(core, AGENT).as_dict()

    assert result["derived"] == [], "the criterion still admits the pair after separation"
    assert len(result["weakened"]) == 1
    weakened = result["weakened"][0]
    assert weakened["outcome"] == "weakened"
    assert weakened["moved"] >= 0.15, f"pre-registered collapse threshold not met: {weakened['moved']}"
    assert weakened["confidence"] < before


# --- the ablation must be able to fail --------------------------------------


def test_the_graded_ablation_admits_a_pair_strict_refuses() -> None:
    """Requirements §13. `GRADED` exists to show the result does not rest on a
    tolerance parameter, and it is only evidence of that if it can be seen
    behaving differently — a mode selector over one behaviour is the
    `ContradictionArm` defect (stored, stamped on every result, consulted by no
    branch) waiting to happen.

    Pinned as a *failure*: on the phase-2 web the tolerant criterion accepts a
    standoff that separating evidence has already retired.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    minted = seed_fixture(core, "discriminating", agent_id=AGENT)
    apply_then(core, "discriminating", minted, agent_id=AGENT)
    beliefs = _beliefs(core)

    strict = find_rival_sets(beliefs, config=OverlapConfig(mode=OverlapMode.STRICT))
    graded = find_rival_sets(beliefs, config=OverlapConfig(mode=OverlapMode.GRADED, tolerance=0.4))
    assert strict == []
    assert len(graded) == 1, "the ablation behaves identically to the mechanism, so it demonstrates nothing"


# --- the instrument gate -----------------------------------------------------


def test_gate_the_derivation_is_not_a_noop() -> None:
    """§2 flavour C: wiring that cannot fire is the same mistake as wiring that
    cannot fail. Experiment 1's mood → `rank_causes` coupling was arithmetically a
    no-op across several versions.
    """
    deriving = derive(_core("symmetric_rivals"), AGENT).as_dict()["derived"]
    declining = derive(_core("conflict_disjoint_evidence"), AGENT).as_dict()["derived"]
    assert_not_noop(len(deriving), len(declining), label="underdetermination derivation")


def test_gate_the_meta_belief_confidence_has_range() -> None:
    """A quantity pinned at one value reports its own constant, which is
    experiment 1's failure mode #3. Measured across the collapse trajectory, where
    it must move.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    minted = seed_fixture(core, "discriminating", agent_id=AGENT)
    values = [derive(core, AGENT).as_dict()["derived"][0]["confidence"]]
    apply_then(core, "discriminating", minted, agent_id=AGENT)
    values.append(derive(core, AGENT).as_dict()["weakened"][0]["confidence"])

    assert_has_range(values, label="meta-belief confidence")


def test_the_frozen_fixtures_have_not_drifted() -> None:
    """A fixture edit invalidates every result resting on it."""
    from manyu.underdetermination import verify_freeze

    freeze = verify_freeze()
    assert len(freeze["files"]) == 7
