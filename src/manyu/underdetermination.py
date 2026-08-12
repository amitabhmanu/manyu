"""Experiment 5 — underdetermination as a belief in its own right.

Two readings of the same evidence can both be defensible. Experiments 3 and 4
assumed a conflict is *resolvable*: one side is wrong, and evidence will
eventually say which. This module is about the case where it will not, and the
question it exists to make falsifiable is not "can Manyu hold that state" — a
branch we write holds whatever we tell it to — but whether the state can be
**derived from the evidence and given up when the evidence separates**.

Three things shape everything here.

**The state is a belief, not a relation** (requirements §5.3). A meta-belief
whose proposition names the standoff, whose `evidence_ids` are exactly the
records that fail to separate its rivals, and which obeys every rule any other
belief obeys — mandatory provenance, ordinary pricing, ordinary revision. It can
therefore be *wrong*, and losing confidence when separating evidence arrives is
the experiment's cleanest dependent variable. A set object has no confidence to
move.

**Nothing may declare it** (requirements §7). `Belief.rivals` exists on `Belief`
and deliberately not on `BeliefCandidate` or in the extractor schema, so no
fixture and no model can assert underdetermination — there is no field for it.
`derive` below is the only writer, and it reads the evidence off the store.

**No free constant** (requirements §13, FR-8). Experiment 3 removed `attenuation`
and `contradiction_penalty` rather than tuning them, on the ground that in a
chain the constant *was* the hypothesis. The quantity here is the **Jaccard index
of the two rivals' evidence sets** — `|shared| / |union|` — which is 1.0 exactly
when nothing separates them. It is both the detection condition and the derived
confidence, and it contains no term this author chose.

That it also settles the near-miss question is the reason to prefer it: a ratio
**cancels cardinality**, so two rivals sharing six records and two rivals sharing
two produce the identical value. A criterion tracking evidence *volume* cannot be
written this way without adding a term that is visibly doing nothing else.

`GRADED` is retained as a labelled ablation and pinned by a test showing it fail.
It is never promoted to rescue a null.

Entirely offline. Nothing here calls a provider.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from manyu.schemas import Belief, BeliefScope, BeliefStatus, BeliefType

FIXTURE_DIR = Path("evals/fixtures/exp05")
FREEZE_PATH = Path("evals/analysis/exp05/freeze.json")

#: `BeliefUpdater._create` stamps TENTATIVE below 0.45 and
#: `WorldviewSynthesizer` composes only `{ACTIVE, CONTESTED}`, so a meta-belief
#: created below this is dropped from expression *silently*. Found by Stage -1
#: (requirements §5.1) before it could produce a Stage 4 null that measured the
#: threshold rather than the experiment.
#:
#: **Not a tuning knob.** It is read from the substrate, and the derived
#: confidence is never clamped to satisfy it — `derive` records
#: `below_expression_threshold` and lets the value stand, because a meta-belief
#: too weak to be expressed is a finding rather than something to round up.
EXPRESSION_THRESHOLD = 0.45


class OverlapMode(str, Enum):
    """How "nothing separates these" is decided."""

    #: The union of the rivals' evidence equals the intersection. No constant.
    STRICT = "strict"
    #: **Ablation only.** Accepts a Jaccard index within `tolerance` of 1.0.
    #: Retained so the result can be shown not to depend on a free parameter, by
    #: running the arm that has one. Experiment 3 §§11–12's `FIXED` ablations in
    #: a new place.
    GRADED = "graded"


@dataclass(frozen=True)
class OverlapConfig:
    mode: OverlapMode = OverlapMode.STRICT
    #: Ignored unless `mode` is `GRADED`.
    tolerance: float = 0.2


# --- the criterion -----------------------------------------------------------


def separating_evidence(left: Belief, right: Belief) -> frozenset[str]:
    """Evidence held by one rival and not the other.

    The symmetric difference, and the whole of what "separates" means here: a
    record both sides cite cannot discriminate between them, whatever it says.
    A record only one side cites is the shape evidence has when it does.
    """
    return frozenset(set(left.evidence_ids) ^ set(right.evidence_ids))


def shared_evidence(left: Belief, right: Belief) -> frozenset[str]:
    return frozenset(set(left.evidence_ids) & set(right.evidence_ids))


def evidence_overlap(left: Belief, right: Belief) -> float:
    """Jaccard index of the two evidence sets — `|shared| / |union|`.

    1.0 exactly when nothing separates the rivals. **Cardinality cancels**, so
    six shared records and two shared records give the same number; a criterion
    reading evidence volume cannot be expressed in this form.

    Two beliefs with no evidence between them return 0.0 rather than dividing by
    zero, which is also the right answer: the substrate refuses a belief without
    provenance, so an empty union means something upstream is wrong and it must
    not read as perfect agreement.
    """
    union = set(left.evidence_ids) | set(right.evidence_ids)
    if not union:
        return 0.0
    return len(shared_evidence(left, right)) / len(union)


def conflicts(left: Belief, right: Belief) -> bool:
    """A stated contradiction in either direction.

    Direction is not required. Stage -1 found that a one-way edge collapses an
    otherwise symmetric pair by the full contradiction penalty, with the
    surviving side decided by which one the extractor phrased as contradicting
    the other (requirements §6.1). Reading the edge as directionless here means
    the *criterion* does not inherit that accident, even though the confidence
    channel already has.
    """
    return right.belief_id in left.contradicts or left.belief_id in right.contradicts


def is_underdetermined(left: Belief, right: Belief, *, config: OverlapConfig | None = None) -> bool:
    """Both conditions, and both are load-bearing.

    Pinned by two negatives authored before this function existed:
    `shared_evidence_no_conflict` (evidence condition alone — corroboration, the
    commonest shape in any web) and `conflict_disjoint_evidence` (conflict
    condition alone — the ordinary resolvable dispute experiments 3 and 4 were
    about). A criterion satisfying only the second would relabel every
    disagreement in the store as unresolvable.
    """
    config = config or OverlapConfig()
    if not conflicts(left, right):
        return False
    if not left.evidence_ids or not right.evidence_ids:
        return False
    overlap = evidence_overlap(left, right)
    if config.mode is OverlapMode.GRADED:
        return overlap >= 1.0 - config.tolerance
    return not separating_evidence(left, right)


# --- derivation --------------------------------------------------------------


@dataclass(frozen=True)
class RivalSet:
    """One derived standoff, before it is written."""

    belief_ids: tuple[str, ...]
    shared: tuple[str, ...]
    separating: tuple[str, ...]
    overlap: float
    belief_key: str

    @property
    def consulted(self) -> tuple[str, ...]:
        """Every record the criterion looked at — the meta-belief's provenance.

        The union rather than the intersection, and the difference matters at
        exactly one moment: when separating evidence arrives, it enters here.
        Without it the meta-belief would cite only records it already held,
        `BeliefUpdater._revise` would find no new evidence and decline to move
        anything, and the state could never be disconfirmed through the ordinary
        pathway — which is the whole of FR-2.
        """
        return tuple(sorted(set(self.shared) | set(self.separating)))


def find_rival_sets(beliefs: Iterable[Belief], *, config: OverlapConfig | None = None) -> list[RivalSet]:
    """Every pair the criterion admits, in deterministic order.

    Pairwise, and `three_way.json` exists to record what that does to a
    three-rival standoff rather than to assume it. Ordering is by sorted belief
    id throughout — experiment 4 found a tie-break running on `uuid4`, and a
    mechanism whose output depends on store iteration order cannot be re-derived
    from its own artifacts.
    """
    ordered = sorted((b for b in beliefs if b.belief_type is not BeliefType.UNDERDETERMINATION), key=lambda b: b.belief_id)
    found: list[RivalSet] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if not is_underdetermined(left, right, config=config):
                continue
            pair = tuple(sorted([left.belief_id, right.belief_id]))
            found.append(
                RivalSet(
                    belief_ids=pair,
                    shared=tuple(sorted(shared_evidence(left, right))),
                    separating=tuple(sorted(separating_evidence(left, right))),
                    overlap=evidence_overlap(left, right),
                    belief_key=_key_for(pair),
                )
            )
    return found


def _key_for(pair: tuple[str, ...]) -> str:
    """Stable identity for a standoff, so re-derivation merges rather than mints.

    `BeliefCandidate.belief_key` is how the substrate is told two candidates are
    the same belief (`_find_existing` matches on it first). Deriving the key from
    the sorted rival ids means the second pass over an unchanged web revises the
    existing meta-belief instead of creating a duplicate — the defect experiment
    1 found when restatements minted a fresh single-evidence belief every turn.
    """
    return "underdetermination/" + "|".join(pair)


def _proposition(store: Any, rival_set: RivalSet) -> str:
    left, right = (store.get_belief(bid) for bid in rival_set.belief_ids)
    return (
        f"On the evidence currently held, these readings cannot be told apart: "
        f"{left.proposition.rstrip('.')}; or {right.proposition.rstrip('.')}."
    )


@dataclass
class DerivationResult:
    """What one derivation pass did, in enough detail to audit it."""

    derived: list[dict[str, Any]] = field(default_factory=list)
    rival_sets: list[RivalSet] = field(default_factory=list)
    weakened: list[dict[str, Any]] = field(default_factory=list)
    mode: OverlapMode = OverlapMode.STRICT

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": self.mode.value,
            "derived": self.derived,
            "weakened": self.weakened,
            "rival_sets": [
                {
                    "belief_ids": list(rs.belief_ids),
                    "shared": list(rs.shared),
                    "separating": list(rs.separating),
                    "overlap": round(rs.overlap, 6),
                    "belief_key": rs.belief_key,
                }
                for rs in self.rival_sets
            ],
        }


def derive(core: Any, agent_id: str, *, config: OverlapConfig | None = None) -> DerivationResult:
    """Read the web, write a meta-belief for every standoff, weaken the rest.

    Two passes, reusing the house pattern from `fork._resolve_edges` and
    `BeliefUpdater.update`: the candidate goes through `core.update_beliefs` so
    that screening, mandatory provenance and ordinary revision all apply, and
    only then is `rivals` stamped onto the saved belief. Constructing the
    `Belief` directly and calling `save_belief` would have been shorter and would
    have bypassed the screening FR-2 requires it to face.

    **Existing meta-beliefs are re-derived, not left alone.** A standoff that no
    longer holds is re-proposed at its now-lower overlap, citing the enlarged
    evidence — so it weakens through `blend_confidence` like any other belief
    meeting disconfirming evidence, with no bespoke rule. That is the collapse
    arm's entire mechanism.
    """
    config = config or OverlapConfig()
    beliefs = core.store.list_beliefs(agent_id, include_inactive=True)
    result = DerivationResult(mode=config.mode)
    result.rival_sets = find_rival_sets(beliefs, config=config)

    for rival_set in result.rival_sets:
        result.derived.append(_write(core, agent_id, rival_set, config))

    live = {rs.belief_key for rs in result.rival_sets}
    for belief in beliefs:
        if belief.belief_type is not BeliefType.UNDERDETERMINATION or belief.belief_key in live:
            continue
        result.weakened.append(_reassess(core, agent_id, belief, config))
    return result


def _write(core: Any, agent_id: str, rival_set: RivalSet, config: OverlapConfig) -> dict[str, Any]:
    update = core.update_beliefs(
        {
            "agent_id": agent_id,
            "candidates": [
                {
                    "candidate_id": f"bcand_{rival_set.belief_key}",
                    "agent_id": agent_id,
                    "proposition": _proposition(core.store, rival_set),
                    "belief_key": rival_set.belief_key,
                    "belief_type": BeliefType.UNDERDETERMINATION.value,
                    "scope": BeliefScope.GENERAL.value,
                    "confidence": rival_set.overlap,
                    "stability": 0.1,
                    "valence": 0.0,
                    "source_mix": {"reflection": 1.0},
                    "evidence_ids": list(rival_set.consulted),
                    "uncertainty": (
                        "Holds only while no evidence separates these readings. "
                        "Evidence held by one and not the other retires it."
                    ),
                }
            ],
        }
    )
    accepted = update.get("accepted") or []
    if not accepted:
        raise RuntimeError(f"meta-belief for {rival_set.belief_key} was rejected: {update.get('rejected')}")
    stored = core.store.get_belief(accepted[0]["belief_id"])
    core.store.save_belief(stored.model_copy(update={"rivals": sorted(rival_set.belief_ids)}))
    return _record(core, stored.belief_id, rival_set.overlap, rival_set)


def _reassess(core: Any, agent_id: str, belief: Belief, config: OverlapConfig) -> dict[str, Any]:
    """Re-propose a meta-belief whose standoff no longer holds.

    The rivals are read back from `belief.rivals` rather than re-detected,
    because the pair is exactly the one this belief is *about* — re-detection
    would find nothing (that is why we are here) and there would be no way to
    price the disconfirmation.
    """
    try:
        left, right = (core.store.get_belief(bid) for bid in belief.rivals)
    except (KeyError, ValueError):
        return {"belief_id": belief.belief_id, "outcome": "rivals_unreadable", "confidence": belief.confidence}

    overlap = evidence_overlap(left, right)
    rival_set = RivalSet(
        belief_ids=tuple(sorted(belief.rivals)),
        shared=tuple(sorted(shared_evidence(left, right))),
        separating=tuple(sorted(separating_evidence(left, right))),
        overlap=overlap,
        belief_key=belief.belief_key or _key_for(tuple(sorted(belief.rivals))),
    )
    before = belief.confidence
    record = _write(core, agent_id, rival_set, config)
    record["confidence_before"] = round(before, 6)
    record["moved"] = round(before - record["confidence"], 6)
    record["outcome"] = "weakened" if record["moved"] > 0 else "unmoved"
    return record


def _record(core: Any, belief_id: str, overlap: float, rival_set: RivalSet) -> dict[str, Any]:
    belief = core.store.get_belief(belief_id)
    return {
        "belief_id": belief.belief_id,
        "belief_key": belief.belief_key,
        "rivals": list(belief.rivals),
        "confidence": round(belief.confidence, 6),
        "derived_overlap": round(overlap, 6),
        "status": belief.status.value,
        "evidence_ids": list(belief.evidence_ids),
        "shared": list(rival_set.shared),
        "separating": list(rival_set.separating),
        # Recorded rather than corrected. A meta-belief below the threshold is
        # invisible to `WorldviewSynthesizer` and that is a fact about the run.
        "below_expression_threshold": belief.confidence < EXPRESSION_THRESHOLD,
    }


def read(core: Any, agent_id: str) -> list[dict[str, Any]]:
    """Every standoff currently held, newest first."""
    return [
        {
            "belief_id": belief.belief_id,
            "belief_key": belief.belief_key,
            "proposition": belief.proposition,
            "rivals": list(belief.rivals),
            "confidence": round(belief.confidence, 6),
            "status": belief.status.value,
            "evidence_ids": list(belief.evidence_ids),
            "below_expression_threshold": belief.confidence < EXPRESSION_THRESHOLD,
        }
        for belief in core.store.list_beliefs(agent_id, belief_type=BeliefType.UNDERDETERMINATION.value, include_inactive=True)
    ]


# --- fixtures ----------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceSpec:
    key: str
    summary: str
    salience: float = 0.5
    weight: float = 0.7


@dataclass(frozen=True)
class RivalBeliefSpec:
    key: str
    proposition: str
    evidence: tuple[str, ...]
    confidence: float = 0.7
    valence: float = 0.0
    contradicts: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()


def load_web(name: str, *, directory: Path | str = FIXTURE_DIR) -> dict[str, Any]:
    return json.loads((Path(directory) / f"{name}.json").read_text(encoding="utf-8"))


def web_specs(fixture: dict[str, Any], *, phase: str = "beliefs") -> tuple[list[EvidenceSpec], list[RivalBeliefSpec]]:
    """Convert a fixture into evidence and belief specs.

    **Not `fork.BeliefSpec`, and the difference is the point.** `fork.seed_beliefs`
    mints evidence per belief (`f"{spec.key}_{index}"`), so two seeded beliefs can
    never cite the same record — pinned in
    `tests/test_underdetermination_substrate.py`. Sharing evidence is the entire
    subject of this experiment, so the fixture declares an evidence pool once at
    top level and beliefs reference records by key.

    Extending `fork.BeliefSpec` instead was the alternative, and was rejected on
    the precedent `salience.web_specs` set: experiments 2 and 3 are closed and
    their published numbers came out of that function, and a behaviour-neutral
    edit is still an edit to code a closed result rests on.
    """
    block = fixture if phase == "beliefs" else fixture.get("then", {})
    evidence = [
        EvidenceSpec(key=item["key"], summary=item["summary"], salience=item.get("salience", 0.5), weight=item.get("weight", 0.7))
        for item in block.get("evidence", [])
    ]
    beliefs = [
        RivalBeliefSpec(
            key=item["key"],
            proposition=item["proposition"],
            evidence=tuple(item["evidence"]),
            confidence=item.get("confidence", 0.7),
            valence=item.get("valence", 0.0),
            contradicts=tuple(item.get("contradicts", ())),
            supports=tuple(item.get("supports", ())),
        )
        for item in block.get("beliefs", [])
    ]
    return evidence, beliefs


def seed_web(
    core: Any,
    evidence_specs: list[EvidenceSpec],
    belief_specs: list[RivalBeliefSpec],
    *,
    agent_id: str = "agent_demo",
    evidence_ids: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build a shared-evidence web through the **priced** ingest path.

    Returns `(evidence key -> id, update result)`.

    Deliberately *not* `fork.seed_beliefs`, which writes edges straight to the
    store and therefore never prices a contradiction (`salience.SEEDS_ARE_UNPRICED`).
    That is right for experiment 4, where stake is the independent variable and a
    priced fixture would start from a state the fixture did not specify. Here the
    opposite holds: pricing is what a live web actually does to a rival pair, and
    Stage -1 showed it is the difference between a gap of zero and a gap of
    0.2333. Stage 0 runs both paths and reports them separately.

    `evidence_ids` carries the pool forward across a fixture's phases, so a
    `then` block can add a record without re-minting the ones already cited.
    """
    minted = dict(evidence_ids or {})
    for spec in evidence_specs:
        if spec.key in minted:
            continue
        captured = core.capture_belief_evidence(
            {
                "agent_id": agent_id,
                "source_type": "operator_note",
                "source_id": spec.key,
                "summary": spec.summary,
                "affective_salience": spec.salience,
                "epistemic_weight": spec.weight,
            }
        )
        minted[spec.key] = captured["evidence_id"]

    missing = sorted({key for spec in belief_specs for key in spec.evidence if key not in minted})
    if missing:
        raise ValueError(f"fixture references undefined evidence keys: {missing}")

    candidates = [
        {
            "candidate_id": f"bcand_{spec.key}",
            "agent_id": agent_id,
            "proposition": spec.proposition,
            "belief_key": spec.key,
            "belief_type": BeliefType.WORLD_MODEL.value,
            "scope": BeliefScope.GENERAL.value,
            "confidence": spec.confidence,
            "stability": 0.1,
            "valence": spec.valence,
            "source_mix": {"operator_note": 1.0},
            "evidence_ids": [minted[key] for key in spec.evidence],
            "contradicts": list(spec.contradicts),
            "supports": list(spec.supports),
        }
        for spec in belief_specs
    ]
    update = core.update_beliefs({"agent_id": agent_id, "candidates": candidates})
    rejected = update.get("rejected") or []
    if rejected:
        raise ValueError(f"seed rejected candidates: {rejected}")
    return minted, update


def seed_fixture(core: Any, name: str, *, agent_id: str = "agent_demo", directory: Path | str = FIXTURE_DIR) -> dict[str, str]:
    fixture = load_web(name, directory=directory)
    evidence_specs, belief_specs = web_specs(fixture)
    minted, _ = seed_web(core, evidence_specs, belief_specs, agent_id=agent_id)
    return minted


def apply_then(core: Any, name: str, minted: dict[str, str], *, agent_id: str = "agent_demo", directory: Path | str = FIXTURE_DIR) -> dict[str, str]:
    """Apply a fixture's `then` block — the second phase of a two-phase fixture.

    `discriminating` is the only one that has one, and it is how collapse becomes
    measurable as a *fall in confidence* rather than as a non-derivation. A
    fixture that merely failed to derive would confirm the criterion says no; it
    would not show the meta-belief can be disconfirmed once held, which is the
    thing FR-2 and pre-registration §2 are about.
    """
    fixture = load_web(name, directory=directory)
    if not fixture.get("then"):
        raise ValueError(f"fixture {name!r} has no `then` block")
    evidence_specs, belief_specs = web_specs(fixture, phase="then")
    minted, _ = seed_web(core, evidence_specs, belief_specs, agent_id=agent_id, evidence_ids=minted)
    return minted


def verify_freeze(path: Path | str = FREEZE_PATH) -> dict[str, Any]:
    """Reuses experiment 4's verifier rather than writing a second one."""
    from manyu.salience import verify_fixture_freeze

    return verify_fixture_freeze(path, experiment="5")
