"""Experiment 6 — pricing what would change Manyu's mind.

Every experiment before this one reads the store backwards: provenance says why a
belief is held, revision says what happened when evidence arrived. This module
points the same arithmetic forwards -- given a belief and a record that has *not*
arrived, what confidence would the belief take, and how many such records would
it take to cross the line where Manyu stops saying it.

**Nothing here is new arithmetic.** `blend_confidence` (experiment 3),
`evidence_overlap` (experiment 5) and `BeliefUpdater._revise`'s 0.05 stability
step are the whole model, and Stage -1 checked their composition against
experiment 5's published trajectory on the driven substrate to a maximum error of
0.0005. This module composes them without mutating anything; where it disagrees
with the store, the store is right and this is the defect.

Three constraints are structural rather than documented:

- `HypotheticalEvidence` is a frozen dataclass and deliberately **not** a
  `ManyuModel`, so `ManyuStore.save_belief_evidence` cannot accept one and FR-1's
  "pricing never mutates" is enforced by the type system (requirements 14.2).
- Its id is a content hash and never `uuid4`. Experiment 4 found a `uuid4`
  tie-break in production; experiment 5 found the same family inside a test,
  where it went green about half the time. A price that differs on re-run is
  unusable for calibration.
- Nothing here reads `stake_of`. Stake averages evidence salience rather than
  summing it and is blind to grounding (experiment 4 section 1), and requirements
  section 12 bars the pricer from that channel. Stage -1 confirmed salience does
  not reach the price by any other route.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence

from manyu.revision import RevisionConfig, blend_confidence
from manyu.schemas import Belief, BeliefType, CounterfactualItem, CounterfactualReceipt
from manyu.underdetermination import EXPRESSION_THRESHOLD, evidence_overlap

#: How far a dose search runs before reporting "not within bound". Reported as
#: `None` rather than as a large integer, because pre-registration section 4.4
#: predicts genuinely infinite doses below the critical arrival ratio and an
#: integer there would read as a measurement.
DEFAULT_DOSE_BOUND = 400

#: `BeliefUpdater._revise` adds this to stability on every revision carrying new
#: evidence. Not a constant of this module's choosing -- read off services.py.
STABILITY_STEP = 0.05


class EdgeIntent(str, Enum):
    NONE = "none"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class Mechanism(str, Enum):
    """Which arithmetic produced a price. Stamped on every item.

    Analysis must be able to separate a real movement from the `new_evidence`
    guard returning the belief untouched -- FR-11's distinction between "found
    nothing" and "found something and priced it at zero".
    """

    #: `blend_confidence` against the record's own confidence.
    BLEND = "blend"
    #: `blend_confidence` against a recomputed Jaccard overlap. Meta-beliefs only.
    OVERLAP = "overlap"
    #: `BeliefUpdater._revise` returns the belief untouched -- delta exactly 0.
    GUARD_NOOP = "guard_noop"


@dataclass(frozen=True)
class HypotheticalEvidence:
    """A record that has not arrived.

    Not a `BeliefEvidence` and not a `ManyuModel`, so it cannot be handed to
    `ManyuStore.save_belief_evidence`. That is the point: a counterfactual that
    can be written is one exception handler away from being written.

    `evidence_id` is set only when the hypothetical stands for a record the store
    already holds -- the `already_held` case, where the correct price is exactly
    0.000 rather than approximately it.
    """

    summary: str
    confidence: float
    attaches_to: tuple[str, ...] = ()
    salience: float = 0.5
    weight: float = 0.7
    edge_intent: EdgeIntent = EdgeIntent.NONE
    evidence_id: str | None = None

    @property
    def hypothetical_id(self) -> str:
        """Content-derived and stable across processes.

        `uuid4` here would make a price differ between the run that predicted it
        and the run that checked it, which is the one thing calibration cannot
        survive.
        """
        payload = json.dumps(
            {
                "summary": self.summary,
                "confidence": round(self.confidence, 9),
                "attaches_to": sorted(self.attaches_to),
                "edge_intent": self.edge_intent.value,
                "evidence_id": self.evidence_id,
            },
            sort_keys=True,
        )
        return "hyp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Price:
    """One priced counterfactual. `delta` is signed; negative weakens."""

    predicted_confidence: float
    delta: float
    mechanism: Mechanism
    candidate_confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "predicted_confidence": round(self.predicted_confidence, 6),
            "delta": round(self.delta, 6),
            "mechanism": self.mechanism.value,
            "candidate_confidence": round(self.candidate_confidence, 6),
        }


# --- the pricer ---------------------------------------------------------------


def _blend(confidence: float, stability: float, candidate: float, config: RevisionConfig) -> float:
    """`blend_confidence` without needing a `Belief` to call it.

    The real function takes a Belief and reads two attributes off it. Rebuilding
    one to price a hypothetical would mean constructing a schema object that
    looks storable, which is exactly what requirements 14.2 removed.
    """

    class _Stub:
        pass

    stub = _Stub()
    stub.confidence = confidence  # type: ignore[attr-defined]
    stub.stability = stability  # type: ignore[attr-defined]
    return blend_confidence(stub, candidate, config)  # type: ignore[arg-type]


def _rival_overlap_after(store: Any, belief: Belief, hypothetical: HypotheticalEvidence) -> float | None:
    """The Jaccard overlap the rivals would show once the record arrives.

    Returns None when the belief is not a standoff or its rivals are unreadable.

    A record entering **one** rival raises the union alone and lowers the
    overlap; entering **both** raises numerator and denominator together and
    barely moves it. That asymmetry is the entire content of the enumeration, and
    it is arithmetic rather than judgement.
    """
    if belief.belief_type is not BeliefType.UNDERDETERMINATION or len(belief.rivals) != 2:
        return None
    try:
        left, right = (store.get_belief(bid) for bid in sorted(belief.rivals))
    except (KeyError, ValueError):
        return None

    left_ids = set(left.evidence_ids)
    right_ids = set(right.evidence_ids)
    token = hypothetical.evidence_id or hypothetical.hypothetical_id
    if left.belief_id in hypothetical.attaches_to:
        left_ids.add(token)
    if right.belief_id in hypothetical.attaches_to:
        right_ids.add(token)

    union = left_ids | right_ids
    if not union:
        return 0.0
    return len(left_ids & right_ids) / len(union)


def price(
    store: Any,
    belief: Belief,
    hypothetical: HypotheticalEvidence,
    *,
    config: RevisionConfig | None = None,
) -> Price:
    """What `belief` would become if `hypothetical` arrived. Never writes.

    FR-1 is verified by comparing `export_agent` either side of a call rather
    than by inspection -- see `tests/test_counterfactual_reference.py`.
    """
    config = config or RevisionConfig()

    # The `new_evidence` guard, and it comes first because it overrides
    # everything: `BeliefUpdater._revise` returns the belief untouched when the
    # candidate carries no evidence the belief does not already hold, so the
    # correct price is exactly 0.000 (FR-9).
    if hypothetical.evidence_id is not None and hypothetical.evidence_id in set(belief.evidence_ids):
        return Price(belief.confidence, 0.0, Mechanism.GUARD_NOOP, belief.confidence)

    overlap = _rival_overlap_after(store, belief, hypothetical)
    if overlap is not None:
        token = hypothetical.evidence_id or hypothetical.hypothetical_id
        if token in set(belief.evidence_ids) or not hypothetical.attaches_to:
            return Price(belief.confidence, 0.0, Mechanism.GUARD_NOOP, belief.confidence)
        predicted = _blend(belief.confidence, belief.stability, overlap, config)
        return Price(predicted, predicted - belief.confidence, Mechanism.OVERLAP, overlap)

    if belief.belief_id not in hypothetical.attaches_to:
        # It would not enter this belief's provenance, so `_revise` never sees it.
        return Price(belief.confidence, 0.0, Mechanism.GUARD_NOOP, belief.confidence)

    predicted = _blend(belief.confidence, belief.stability, hypothetical.confidence, config)
    return Price(predicted, predicted - belief.confidence, Mechanism.BLEND, hypothetical.confidence)


# --- the dose -----------------------------------------------------------------


@dataclass(frozen=True)
class Dose:
    """How many records it would take, and the trajectory getting there.

    `records` is None when the threshold is not reached within `bound`. It is
    never a large integer standing in for "never" -- pre-registration section 4.4
    predicts genuinely unreachable thresholds below the critical arrival ratio,
    and an integer there would read as a measurement.
    """

    records: int | None
    bound: int
    trajectory: tuple[float, ...]
    threshold: float
    arrival_ratio: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "bound": self.bound,
            "threshold": self.threshold,
            "arrival_ratio": self.arrival_ratio,
            "trajectory_head": [round(v, 6) for v in self.trajectory[:12]],
            "final": round(self.trajectory[-1], 6) if self.trajectory else None,
        }


def dose_for_standoff(
    shared: int,
    *,
    start: float = 1.0,
    stability: float = 0.10,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    arrival_ratio: float | None = None,
    config: RevisionConfig | None = None,
) -> Dose:
    """Records needed to retire a standoff resting on `shared` records.

    With `arrival_ratio = r`, `r` separating records arrive per shared record and
    the Jaccard overlap converges to `1/(1 + r)`. Against a threshold `t` that
    puts a phase transition at `r* = (1 - t)/t`: below it the overlap's limit
    never falls under the threshold and the dose is **infinite**, not merely
    large (pre-registration section 4.4).

    `arrival_ratio = None` means pure separating evidence -- the experiment 5
    collapse arm, and the r -> infinity limit of the same expression.
    """
    config = config or RevisionConfig()
    numerator = shared
    denominator = shared
    confidence = start
    trajectory: list[float] = []
    separating = held = 0

    for step in range(1, bound + 1):
        if arrival_ratio is None or separating < arrival_ratio * held:
            separating += 1
            denominator += 1  # enters one rival: union only
        else:
            held += 1
            numerator += 1  # enters both: numerator and denominator
            denominator += 1
        overlap = numerator / denominator if denominator else 0.0
        confidence = _blend(confidence, stability, overlap, config)
        stability = min(1.0, stability + STABILITY_STEP)
        trajectory.append(confidence)
        if confidence < threshold:
            return Dose(step, bound, tuple(trajectory), threshold, arrival_ratio)

    return Dose(None, bound, tuple(trajectory), threshold, arrival_ratio)


def dose_for_belief(
    belief: Belief,
    candidate_confidence: float,
    *,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    config: RevisionConfig | None = None,
) -> Dose:
    """Records needed to carry an ordinary belief past `threshold`.

    Inertia is `0.5 + 0.4 * stability` capped at 0.9, and stability rises 0.05
    per revision, so the distance to the candidate shrinks by at least 10% each
    time and the sequence always converges. Every belief is movable; the dose is
    what varies, and nothing bounds it.
    """
    config = config or RevisionConfig()
    confidence = belief.confidence
    stability = belief.stability
    trajectory: list[float] = []

    for step in range(1, bound + 1):
        confidence = _blend(confidence, stability, candidate_confidence, config)
        stability = min(1.0, stability + STABILITY_STEP)
        trajectory.append(confidence)
        if confidence < threshold:
            return Dose(step, bound, tuple(trajectory), threshold, None)

    return Dose(None, bound, tuple(trajectory), threshold, None)


def critical_arrival_ratio(threshold: float = EXPRESSION_THRESHOLD) -> float:
    """`r* = (1 - t)/t`, below which a standoff cannot be retired at all.

    Derived, not chosen: the overlap's limit under interleaved arrival is
    `1/(1 + r)`, and the transition is where that equals the threshold. The only
    input is the threshold itself, which is registered in advance.
    """
    return (1.0 - threshold) / threshold


# --- the enumerator -----------------------------------------------------------


@dataclass
class Enumeration:
    items: list[CounterfactualItem] = field(default_factory=list)
    declined: list[dict[str, Any]] = field(default_factory=list)
    consulted: list[str] = field(default_factory=list)


def enumerate_changers(
    store: Any,
    belief: Belief,
    *,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    config: RevisionConfig | None = None,
) -> Enumeration:
    """What would change Manyu's mind about `belief`, priced, with what it declined.

    The rule is structural and carries no constant (requirements section 13): a
    hypothetical is a mind-changer when it would enter the belief's own
    provenance *and* the store's structure implies it. For a standoff the
    structure is the rival pair -- a record entering one rival separates them,
    a record entering both does not -- and that is read off the store rather than
    chosen.

    **What is declined is recorded** (FR-11), because "the enumerator found
    nothing" and "the enumerator found things and priced them at zero" are
    different results and analysis must be able to tell them apart.
    """
    config = config or RevisionConfig()
    out = Enumeration()

    if belief.belief_type is BeliefType.UNDERDETERMINATION and len(belief.rivals) == 2:
        rivals = sorted(belief.rivals)
        out.consulted = list(rivals) + list(belief.evidence_ids)

        for rival_id in rivals:
            hypothetical = HypotheticalEvidence(
                summary=f"An observation cited by {rival_id} and not by the other reading.",
                confidence=belief.confidence,
                attaches_to=(rival_id,),
                edge_intent=EdgeIntent.NONE,
            )
            priced = price(store, belief, hypothetical, config=config)
            shared = len(set.intersection(*(set(store.get_belief(r).evidence_ids) for r in rivals)))
            dose = dose_for_standoff(shared, start=belief.confidence, stability=belief.stability, threshold=threshold, bound=bound, config=config)
            out.items.append(
                CounterfactualItem(
                    hypothetical_id=hypothetical.hypothetical_id,
                    summary=hypothetical.summary,
                    attaches_to=[rival_id],
                    edge_intent=hypothetical.edge_intent.value,
                    predicted_confidence=round(priced.predicted_confidence, 6),
                    delta=round(priced.delta, 6),
                    mechanism=priced.mechanism.value,
                    dose=dose.records,
                    dose_bounded_at=dose.bound,
                )
            )

        # The non-separating candidate, declined on arithmetic rather than taste.
        both = HypotheticalEvidence(
            summary="An observation cited by both readings.",
            confidence=belief.confidence,
            attaches_to=tuple(rivals),
        )
        both_price = price(store, belief, both, config=config)
        out.declined.append(
            {
                "hypothetical_id": both.hypothetical_id,
                "summary": both.summary,
                "attaches_to": list(rivals),
                "reason": "non_separating",
                "predicted_delta": round(both_price.delta, 6),
                "note": (
                    "Enters both rivals, so it raises numerator and denominator together and cannot "
                    "retire the standoff. Declined because the arithmetic says so, not because it "
                    "looked irrelevant."
                ),
            }
        )
        return out

    if belief.supports:
        out.consulted = list(belief.supports) + list(belief.evidence_ids)
        for supporter_id in sorted(belief.supports):
            hypothetical = HypotheticalEvidence(
                summary=f"Evidence retracting {supporter_id}.",
                confidence=0.0,
                attaches_to=(belief.belief_id,),
                edge_intent=EdgeIntent.CONTRADICTS,
            )
            priced = price(store, belief, hypothetical, config=config)
            dose = dose_for_belief(belief, 0.0, threshold=threshold, bound=bound, config=config)
            out.items.append(
                CounterfactualItem(
                    hypothetical_id=hypothetical.hypothetical_id,
                    summary=hypothetical.summary,
                    attaches_to=[belief.belief_id],
                    edge_intent=hypothetical.edge_intent.value,
                    predicted_confidence=round(priced.predicted_confidence, 6),
                    delta=round(priced.delta, 6),
                    mechanism=priced.mechanism.value,
                    dose=dose.records,
                    dose_bounded_at=dose.bound,
                )
            )
        return out

    out.consulted = list(belief.evidence_ids)
    out.declined.append(
        {
            "belief_id": belief.belief_id,
            "reason": "no_structure",
            "note": (
                "No rivals and no supporters, so the store's structure implies nothing specific and only "
                "the degenerate rule remains -- 'a disconfirming record you do not already hold', which is "
                "available for every belief and names none. Requirements section 13's weakness, recorded "
                "where it occurs rather than argued about."
            ),
        }
    )
    return out


def build_receipt(
    store: Any,
    agent_id: str,
    belief: Belief,
    *,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    config: RevisionConfig | None = None,
) -> CounterfactualReceipt:
    """An enumeration in storable form. Still does not write -- the caller does."""
    enumeration = enumerate_changers(store, belief, threshold=threshold, bound=bound, config=config)
    digest = hashlib.sha256(
        json.dumps([belief.belief_id, [i.hypothetical_id for i in enumeration.items]], sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return CounterfactualReceipt(
        receipt_id=f"cfr_{digest}",
        agent_id=agent_id,
        belief_id=belief.belief_id,
        belief_key=belief.belief_key,
        belief_type=belief.belief_type.value,
        confidence_before=belief.confidence,
        items=enumeration.items,
        declined=enumeration.declined,
        consulted=enumeration.consulted,
        threshold=threshold,
    )


def receipts_for_agent(
    store: Any,
    agent_id: str,
    *,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    config: RevisionConfig | None = None,
    persist: bool = False,
) -> list[CounterfactualReceipt]:
    """A receipt per belief. `persist` is off by default -- FR-1 is the default."""
    receipts = []
    for belief in sorted(store.list_beliefs(agent_id, include_inactive=True), key=lambda b: b.belief_id):
        receipt = build_receipt(store, agent_id, belief, threshold=threshold, bound=bound, config=config)
        receipts.append(receipt)
        if persist:
            store.save_counterfactual_receipt(receipt)
    return receipts
