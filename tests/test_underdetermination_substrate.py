"""Experiment 5 Stage -1 — executing the requirements document against the substrate.

Written *before* `src/manyu/underdetermination.py` exists, and covering no
mechanism of this experiment's. Same category as
`tests/test_salience_substrate.py`, and for the same reason experiment 4 wrote
that file first: experiment 3's suite caught none of sixteen defects because
every test was written minutes after the mechanism, by the author who had just
written it, so it agreed with the code precisely where the code was wrong.

**The specific risk this file exists for.** Requirements sections 5 and 6 were
derived by *reading* code, not by running it. Three of their claims are already
quoted in the backlog as findings:

- the synthesizer averages rival confidence into one mediocre stance (section 5.1);
- a mutual conflict's direction is broken by sorted belief id (section 5.2);
- ingest prices a symmetric pair symmetrically, so it may already sit in a
  stable standoff (section 6).

The third can end the experiment. If any of them is wrong, the document is
wrong, and correcting it is this stage's output rather than a follow-up.

Every test below names the section it pins and what follows if it fails. A
failure here is never a bug in this file — it is a defect report against
`requirements.md`.

Entirely offline. No provider is constructed anywhere except the scenario
provider in the final section, which makes no network call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.salience import Arm, AttentionLoop
from manyu.schemas import BeliefRejectionReason, BeliefStatus

AGENT = "agent_demo"


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _evidence(core: ManyuCore, source_id: str, *, salience: float = 0.5, weight: float = 0.7) -> str:
    """One evidence record, addressable so several beliefs can cite it."""
    captured = core.capture_belief_evidence(
        {
            "agent_id": AGENT,
            "source_type": "operator_note",
            "source_id": source_id,
            "summary": f"observation {source_id}",
            "affective_salience": salience,
            "epistemic_weight": weight,
        }
    )
    return captured["evidence_id"]


def _candidate(key: str, evidence_ids: list[str], *, confidence: float = 0.7, valence: float = 0.0, contradicts: tuple[str, ...] = ()) -> dict:
    return {
        "candidate_id": f"bcand_{key}",
        "agent_id": AGENT,
        "proposition": f"Reading {key} of the same observations.",
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


def _symmetric_pair_through_ingest(core: ManyuCore, *, reversed_order: bool = False) -> dict:
    """Two rivals on the *same* two evidence records, each contradicting the other.

    The shape the whole experiment turns on, built through the priced ingest
    path (`update_beliefs` -> `_price_contradictions`) rather than through
    `fork.seed_beliefs`, which does not price.
    """
    shared = [_evidence(core, "shared_0"), _evidence(core, "shared_1")]
    candidates = [
        _candidate("reading_a", shared, valence=0.4, contradicts=("reading_b",)),
        _candidate("reading_b", shared, valence=-0.4, contradicts=("reading_a",)),
    ]
    if reversed_order:
        candidates.reverse()
    return core.update_beliefs({"agent_id": AGENT, "candidates": candidates})


def _by_key(core: ManyuCore) -> dict[str, object]:
    return {belief.belief_key: belief for belief in core.store.list_beliefs(AGENT, include_inactive=True)}


# --- section 5.3: can the meta-belief be stored at all? ----------------------


def test_two_beliefs_can_cite_the_same_evidence_record() -> None:
    """The precondition for everything. If evidence cannot be shared, the
    criterion in requirements section 13 is unrepresentable and the experiment
    has no subject.
    """
    core = _core()
    shared = [_evidence(core, "shared_0")]
    result = core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [_candidate("reading_a", shared), _candidate("reading_b", shared)],
        }
    )

    assert len(result["accepted"]) == 2, f"a candidate was rejected: {result['rejected']}"
    stored = _by_key(core)
    assert stored["reading_a"].evidence_ids == stored["reading_b"].evidence_ids == shared


def test_provenance_rejects_only_an_empty_evidence_list() -> None:
    """Requirements section 5.3 — the meta-belief cites the evidence that fails
    to separate its rivals, so it must pass screening on evidence somebody else
    already cited.

    If evidence that is already in use were refused, FR-3 would be
    unimplementable and the meta-belief would need an exemption — which FR-2
    makes a defect report rather than a fix.
    """
    core = _core()
    shared = [_evidence(core, "shared_0")]
    core.update_beliefs({"agent_id": AGENT, "candidates": [_candidate("reading_a", shared)]})

    result = core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [_candidate("meta", shared), _candidate("groundless", [])],
        }
    )

    accepted = {item["belief_key"] for item in result["accepted"]}
    assert "meta" in accepted, "a belief citing already-used evidence was refused"
    rejected = {item["reason"] for item in result["rejected"]}
    assert rejected == {BeliefRejectionReason.INSUFFICIENT_PROVENANCE.value}


# --- the seeder gap ----------------------------------------------------------


def test_fork_seed_beliefs_cannot_share_an_evidence_record() -> None:
    """`fork.seed_beliefs` mints evidence per spec (`f"{spec.key}_{index}"`), so
    two seeded beliefs never overlap.

    If this fails, the experiment-5 seeder planned for `underdetermination.py`
    is unnecessary and the plan simplifies to reusing `fork`.
    """
    core = _core()
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="reading_a", proposition="Reading A of the observations.", evidence_count=2),
            BeliefSpec(key="reading_b", proposition="Reading B of the observations.", evidence_count=2),
        ],
    )

    a = core.store.get_belief(ids["reading_a"])
    b = core.store.get_belief(ids["reading_b"])
    assert set(a.evidence_ids) & set(b.evidence_ids) == set(), "seed_beliefs shared a record; the exp-5 seeder is unnecessary"


# --- section 5.1: the synthesizer -------------------------------------------


def _stances(core: ManyuCore) -> list[dict]:
    from manyu.services import WorldviewSynthesizer

    return _as_dicts(WorldviewSynthesizer(core.store, core.clock).synthesize(AGENT))


def test_the_synthesizer_averages_rival_confidence_into_one_stance() -> None:
    """Requirements section 5.1, quoted in the backlog as a finding.

    Two contested rivals in the same theme group are composed into a single
    stance whose confidence is their arithmetic mean — so a standoff is not
    suppressed and not flagged, but averaged into a mediocre opinion.

    Measured on a pair that has been through ingest, which is the case section
    5.1 is about. A first version of this test used two freshly created beliefs
    at 0.8 and 0.4 and failed, for a reason that turned out to matter more than
    the test did: see `test_a_rival_created_below_the_threshold_is_never_composed`.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)
    expected = (stored["reading_a"].confidence + stored["reading_b"].confidence) / 2

    world = [item for item in _stances(core) if item["theme"] == "world_model"]
    assert len(world) == 1, f"expected one grouped stance, got {[i['theme'] for i in _stances(core)]}"
    assert len(world[0]["supporting_belief_ids"]) == 2, "a rival was dropped from composition"
    assert world[0]["confidence"] == pytest.approx(expected), "the two rivals were not averaged"


def test_a_rival_created_below_the_threshold_is_never_composed() -> None:
    """**Found by Stage -1, and it is a trap for Stage 4.**

    `BeliefUpdater._create` stamps `TENTATIVE` on any candidate created below
    0.45 confidence (`services.py:835`), and `synthesize` filters on
    `{ACTIVE, CONTESTED}`. So a rival created below the threshold is not
    averaged into a mediocre stance — it is **excluded from composition
    entirely**, silently.

    The consequence for this experiment: the meta-belief must be created at or
    above 0.45 or it is invisible to the synthesizer, and Stage 4 would measure
    nothing for a reason that has nothing to do with underdetermination.
    Requirements section 5.1 is amended rather than withdrawn.
    """
    core = _core()
    shared = [_evidence(core, "shared_0")]
    core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                _candidate("reading_a", shared, confidence=0.8),
                _candidate("reading_b", shared, confidence=0.4),
            ],
        }
    )

    stored = _by_key(core)
    assert stored["reading_a"].status is BeliefStatus.ACTIVE
    assert stored["reading_b"].status is BeliefStatus.TENTATIVE, "the 0.45 creation threshold has moved"

    world = [item for item in _stances(core) if item["theme"] == "world_model"]
    assert len(world[0]["supporting_belief_ids"]) == 1, "the tentative rival was composed after all"
    assert world[0]["confidence"] == pytest.approx(0.8), "composition did not simply drop the tentative rival"


def test_status_is_not_re_derived_from_confidence_after_creation() -> None:
    """The other half of the finding above, and it cuts the other way.

    Status is set once at creation and by contradiction, and never recomputed
    from confidence. So a belief charged all the way down to 0.1 stays
    `CONTESTED` and stays composed, while one *created* at 0.4 and never touched
    is `TENTATIVE` and is not.

    **Whether a belief is expressed is therefore a function of its creation
    confidence and its contradiction history, not of what it currently is.**
    Any Stage 3 reading that treats "still composed" as "still believed" is
    reading the wrong thing.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)

    core.retract_belief({"agent_id": AGENT, "belief_id": stored["reading_b"].belief_id, "to_confidence": 0.1, "arm": "direct"})

    after = _by_key(core)["reading_b"]
    assert after.confidence == pytest.approx(0.1)
    assert after.status is BeliefStatus.CONTESTED, "status followed confidence; the finding is withdrawn"
    named = {belief_id for item in _stances(core) for belief_id in item["supporting_belief_ids"]}
    assert after.belief_id in named, "a belief at 0.1 was dropped from composition"


def test_a_contested_belief_is_still_composed_into_a_stance() -> None:
    """Requirements section 5.1 — `synthesize` filters on `{ACTIVE, CONTESTED}`,
    so being contested does not quiet a belief.

    This is what makes the averaging above reachable for a *conflicting* pair
    rather than only for two unrelated beliefs.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)
    assert stored["reading_a"].status is BeliefStatus.CONTESTED
    assert stored["reading_b"].status is BeliefStatus.CONTESTED

    named = {belief_id for item in _stances(core) for belief_id in item["supporting_belief_ids"]}
    assert stored["reading_a"].belief_id in named
    assert stored["reading_b"].belief_id in named


def _as_dicts(results) -> list[dict]:
    return [item if isinstance(item, dict) else item.model_dump(mode="json") for item in results]


# --- section 6: what ingest does to a symmetric pair -------------------------


def test_ingest_charges_a_symmetric_pair_symmetrically() -> None:
    """Requirements section 6 — **this is the claim that can end the experiment.**

    `_price_contradictions` snapshots every contradictor's strength before
    charging any of them, and `_contradiction_share` is equal for two beliefs
    with equal grounding. So both sides should be charged the same amount and
    the pair should land on an equal, lowered confidence.

    If the gap is non-zero, the substrate breaks ties on its own and section 6's
    "may already sit in a stable standoff" is answered in the negative — which
    makes the experiment *larger*, not smaller.

    If the gap is zero, the claim shrinks: underdetermination is already stable
    in the confidence channel, and what remains is that it is indistinguishable
    from two mediocre beliefs.
    """
    core = _core()
    result = _symmetric_pair_through_ingest(core)
    stored = _by_key(core)

    a = stored["reading_a"].confidence
    b = stored["reading_b"].confidence
    assert a == pytest.approx(b), f"the substrate broke the tie on its own: {a} vs {b}"
    assert a < 0.7, "neither side was charged at all; the pair was never priced"
    assert len(result["contradictions_priced"]) == 2


def test_a_one_directional_edge_collapses_the_tie() -> None:
    """**The Stage -1 finding that decides requirements section 6.**

    The symmetric standoff above holds only because *both* rivals declared the
    contradiction. With a single edge — the same two beliefs, the same shared
    evidence, the same confidences — only the target is charged, and the pair
    separates by the full penalty.

    So which reading survives at full confidence is decided by **which one the
    extractor happened to phrase as contradicting the other**, which is not an
    epistemic fact about the evidence. That is a distinct mechanism from the
    alphabetical tie-break in section 5.2, and a worse one: the tie-break is at
    least labelled `"mutual"` where it fires.

    Consequence: section 6's "the substrate may already force the answer" is
    answered **only for mutual pairs**. Whether live webs produce mutual or
    one-way edges is an empirical question and belongs to the paid stage.
    """
    core = _core()
    shared = [_evidence(core, "shared_0"), _evidence(core, "shared_1")]
    core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                _candidate("reading_a", shared, valence=0.4, contradicts=("reading_b",)),
                _candidate("reading_b", shared, valence=-0.4),
            ],
        }
    )

    stored = _by_key(core)
    declarer = stored["reading_a"].confidence
    target = stored["reading_b"].confidence
    assert declarer == pytest.approx(0.7), "the declaring side was charged; the asymmetry is not what it seems"
    assert target < declarer, "a one-way edge left the pair symmetric after all"
    assert declarer - target == pytest.approx(0.233333, abs=1e-5)


def test_the_split_is_not_decided_by_emission_order() -> None:
    """Requirements section 6, quoting the defect the atomic snapshot was built
    to fix: mutual contradictions used to settle at 0.6/0.4 with the split
    decided by extractor emission order.

    Reversing the candidate order must change nothing.
    """
    forward = _core()
    _symmetric_pair_through_ingest(forward)
    backward = _core()
    _symmetric_pair_through_ingest(backward, reversed_order=True)

    lhs = {key: belief.confidence for key, belief in _by_key(forward).items()}
    rhs = {key: belief.confidence for key, belief in _by_key(backward).items()}
    assert lhs == rhs, f"emission order changed the outcome: {lhs} vs {rhs}"


def test_asserting_the_same_contradiction_twice_charges_once() -> None:
    """Requirements section 5.2 — `assert_contradiction` is idempotent via
    `_was_asserted`, which is what leaves an already-priced pair inert.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)
    before = core.store.get_belief(stored["reading_b"].belief_id).confidence

    core.assert_contradiction(
        {
            "agent_id": AGENT,
            "contradictor_id": stored["reading_a"].belief_id,
            "target_id": stored["reading_b"].belief_id,
            "arm": "direct",
        }
    )

    after = core.store.get_belief(stored["reading_b"].belief_id).confidence
    assert after == pytest.approx(before), "the same contradiction was charged twice"


# --- section 5.2: the attention loop ----------------------------------------


def test_a_mutual_conflict_direction_is_broken_by_sorted_belief_id() -> None:
    """Requirements section 5.2, quoted in the backlog: collapse-to-a-guess by
    alphabetical order is already shipped.

    If this fails, section 5.2 is withdrawn from `requirements.md` and from the
    backlog entry.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)
    left, right = sorted([stored["reading_a"].belief_id, stored["reading_b"].belief_id])

    loop = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT)
    contradictor, target, how = loop._direction((left, right))

    assert how == "mutual", f"a mutual pair was not labelled mutual: {how}"
    assert (contradictor, target) == (left, right), "the tie-break is not by sorted belief id"


def test_a_priced_pair_is_inert_when_the_attention_loop_arrives() -> None:
    """Requirements section 5.2 — the alphabetical tie-break bites only where
    the pair reaches the loop unpriced.

    Ingest has already charged this pair, so the loop's step must move nothing
    and be recorded as inert. If it moves something, the tie-break bites on
    every live web and section 5.2's mitigation is wrong.
    """
    core = _core()
    _symmetric_pair_through_ingest(core)
    stored = _by_key(core)
    before = {key: belief.confidence for key, belief in stored.items()}

    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)

    after = {key: belief.confidence for key, belief in _by_key(core).items()}
    assert after == before, f"the loop moved an already-priced pair: {before} -> {after}"
    assert all(step.moved == 0.0 for step in result.steps), [step.moved for step in result.steps]
    assert result.inert, "a no-op step was not recorded as inert"


def test_an_unpriced_pair_is_not_inert() -> None:
    """The positive control for the test above. Without it, "inert" could mean
    the loop is broken rather than that the pair was already charged.

    `fork.seed_beliefs` writes edges directly and does not price
    (`salience.SEEDS_ARE_UNPRICED`), so the same web reached this way *does*
    move.
    """
    core = _core()
    seed_beliefs(
        core,
        [
            BeliefSpec(key="reading_a", proposition="Reading A of the observations.", valence=0.4, contradicts=("reading_b",)),
            BeliefSpec(key="reading_b", proposition="Reading B of the observations.", valence=-0.4, contradicts=("reading_a",)),
        ],
    )
    before = {key: belief.confidence for key, belief in _by_key(core).items()}

    AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=1)

    after = {key: belief.confidence for key, belief in _by_key(core).items()}
    assert after != before, "an unpriced pair did not move either; the loop is inert for another reason"


# --- staging: can the offline path generate the shape at all? ----------------


def test_the_offline_generation_path_cannot_emit_a_contradiction() -> None:
    """Requirements section 7's corollary, and it decides the staging.

    Experiment 4's Stage 0a was voided because `ScenarioJSONProvider` hardcodes
    `"contradicts": []`, so a base rate of zero described the instrument. The
    same limit applies here: an offline base rate for shared-evidence rivals is
    not answerable, and the question belongs to the paid stage.

    Confirming it *in advance* is the whole point. Reuses experiment 4's probe
    rather than writing a second one.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "analysis" / "exp04"))
    from run_stage0 import generation_path_can_contradict

    from manyu.providers import ScenarioJSONProvider

    assert generation_path_can_contradict(ScenarioJSONProvider()) is False, (
        "the offline path can now emit a contradiction; experiment 5's base rate may be answerable offline "
        "and experiment 4's Stage 0a should be re-run"
    )
