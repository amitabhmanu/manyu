"""Working alternatives to the counterfactual pricer, each wrong in one way.

Experiment 5's battery is the precedent and its lesson is the reason this file
exists: a check that passes half the time goes green on the run that matters. So
every mutant here is a *working* mechanism — it produces plausible numbers on the
happy path — and every check that catches one is itself verified to pass on the
real pricer and to be trippable by some mutant.

Each mutant reproduces a defect family this sequence has actually shipped:

- `ConstantPrice` — experiment 1's gate #3, a truncation constant read as a
  curve. A pricer returning a plausible fixed number passes every fixture whose
  correct answer is nonzero, and fails only where the answer is exactly zero.
- `IgnoresNewEvidenceGuard` — the family `_revise`'s guard exists to stop.
  Without it, re-derivation looks like corroboration and stability measures
  elapsed turns rather than support.
- `DoseIgnoresStability` — experiment 3's `attenuation`, where a constant *was*
  the hypothesis. A dose that does not read entrenchment is a dose about the
  record alone.
- `EnumeratorReturnsEverything` — the degenerate rule requirements section 13
  names, wearing the enumerator's clothes. Precision equal to the base rate,
  presented as a list.

No mutant here is documented as equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from manyu.counterfactual import (
    DEFAULT_DOSE_BOUND,
    Dose,
    Enumeration,
    HypotheticalEvidence,
    Mechanism,
    Price,
    STABILITY_STEP,
    _blend,
    _rival_overlap_after,
)
from manyu.revision import RevisionConfig
from manyu.schemas import BeliefType, CounterfactualItem
from manyu.underdetermination import EXPRESSION_THRESHOLD


@dataclass(frozen=True)
class Mutant:
    name: str
    caught_by: str
    defect_family: str


CATALOGUE: tuple[Mutant, ...] = (
    Mutant("constant_price", "test_already_held_prices_exactly_zero", "a plausible constant read as a measurement"),
    Mutant("ignores_new_evidence_guard", "test_already_held_prices_exactly_zero", "corroboration confused with re-derivation"),
    Mutant("dose_ignores_stability", "test_dose_rises_with_entrenchment", "a free constant standing in for the hypothesis"),
    Mutant("enumerator_returns_everything", "test_enumerator_declines_the_non_separating_candidate", "the degenerate rule wearing an enumerator's clothes"),
)


def price_constant(store: Any, belief: Any, hypothetical: HypotheticalEvidence, *, config: RevisionConfig | None = None) -> Price:
    """Always moves the belief by a plausible amount.

    Chosen to sit near the real pricer's output on `symmetric_rivals`, so it
    passes anything that checks the number is "about right" and fails only an
    exact-zero check.
    """
    predicted = max(0.0, belief.confidence - 0.1533)
    return Price(predicted, predicted - belief.confidence, Mechanism.OVERLAP, predicted)


def price_ignoring_guard(store: Any, belief: Any, hypothetical: HypotheticalEvidence, *, config: RevisionConfig | None = None) -> Price:
    """Prices already-held evidence as if it were new.

    Identical to the real pricer except that the `new_evidence` short-circuit is
    absent, so a record the belief already cites still produces movement.
    """
    config = config or RevisionConfig()
    overlap = _rival_overlap_after(store, belief, hypothetical)
    if overlap is not None:
        predicted = _blend(belief.confidence, belief.stability, overlap, config)
        return Price(predicted, predicted - belief.confidence, Mechanism.OVERLAP, overlap)
    predicted = _blend(belief.confidence, belief.stability, hypothetical.confidence, config)
    return Price(predicted, predicted - belief.confidence, Mechanism.BLEND, hypothetical.confidence)


def dose_ignoring_stability(
    shared: int,
    *,
    start: float = 1.0,
    stability: float = 0.10,
    threshold: float = EXPRESSION_THRESHOLD,
    bound: int = DEFAULT_DOSE_BOUND,
    arrival_ratio: float | None = None,
    config: RevisionConfig | None = None,
) -> Dose:
    """Prices every belief at the same inertia, whatever its entrenchment.

    The trajectory still falls and still crosses, so the shape looks right; only
    the dependence on entrenchment is gone. This is `attenuation = 0.6` in a new
    place — a constant sitting where the hypothesis should be.

    Note the first version of this mutant was *not* a mutant: it held inertia at
    the belief's own starting stability, which still varies with entrenchment, so
    it rose exactly as the real dose does and the battery caught it. A mutant that
    reproduces the behaviour it is meant to break tests nothing.
    """
    config = config or RevisionConfig()
    stability = 0.10  # the defect: entrenchment is read and then discarded
    numerator = denominator = shared
    confidence = start
    trajectory: list[float] = []
    separating = held = 0

    for step in range(1, bound + 1):
        if arrival_ratio is None or separating < arrival_ratio * held:
            separating += 1
            denominator += 1
        else:
            held += 1
            numerator += 1
            denominator += 1
        overlap = numerator / denominator if denominator else 0.0
        confidence = _blend(confidence, stability, overlap, config)  # stability never advances
        trajectory.append(confidence)
        if confidence < threshold:
            return Dose(step, bound, tuple(trajectory), threshold, arrival_ratio)
    return Dose(None, bound, tuple(trajectory), threshold, arrival_ratio)


def enumerate_everything(store: Any, belief: Any, *, threshold: float = EXPRESSION_THRESHOLD, bound: int = DEFAULT_DOSE_BOUND, config: RevisionConfig | None = None) -> Enumeration:
    """Emits every attachment pattern, including the one that cannot separate.

    Recall is perfect, which is what makes it dangerous: a report showing recall
    1.00 and no precision figure would read as a success.
    """
    out = Enumeration()
    if belief.belief_type is not BeliefType.UNDERDETERMINATION or len(belief.rivals) != 2:
        return out
    rivals = sorted(belief.rivals)
    out.consulted = list(rivals) + list(belief.evidence_ids)
    for pattern in ([rivals[0]], [rivals[1]], list(rivals)):
        hypothetical = HypotheticalEvidence(
            summary=f"An observation cited by {', '.join(pattern)}.",
            confidence=belief.confidence,
            attaches_to=tuple(pattern),
        )
        out.items.append(
            CounterfactualItem(
                hypothetical_id=hypothetical.hypothetical_id,
                summary=hypothetical.summary,
                attaches_to=pattern,
                edge_intent="none",
                predicted_confidence=belief.confidence,
                delta=0.0,
                mechanism=Mechanism.OVERLAP.value,
                dose=None,
                dose_bounded_at=bound,
            )
        )
    return out
