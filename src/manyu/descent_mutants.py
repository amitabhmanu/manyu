"""Deliberately broken reconstructors and scorers, for testing the suite.

The suite is under test here, not the code. Experiment 3 shipped sixteen defects
and its own suite caught zero; experiment 4 caught eight, none by a test written
after the code. A test written minutes after the mechanism, by the author who has
just written it, agrees with the code precisely where the code is wrong.

Three invariants, carried from `concealment_mutants.py` and
`underdetermination_mutants.py`:

1. Every mutant is caught by at least one *named* check, or the gap is reported
   as a hole rather than omitted.
2. Every mutant is a **working mechanism** on the development fixture. One that
   merely crashes proves nothing — it would be caught by any test at all.
3. Every check **passes on the real mechanism**. A check that fires on everything
   catches nothing.

Injection, not monkeypatching: every mutant is signature-compatible with the
`descent` function it replaces and is passed in by the caller. Patching a module
attribute does not reach a caller that did `from descent import reconstruct`.

**Eight mutants where the house count is four to six, and the reason is
structural.** This experiment has *two* independently-wrong-able mechanisms —
`reconstruct` and `score` — where every prior experiment had one. A wrong graph
and a wrong ruler fail differently and are caught by different checks, so
collapsing the two families would lose the ability to tell them apart.

Three entries carry more weight than the rest:

- **`draws_edges_from_similarity` does double duty.** Pre-registration section
  6.3 requires slot D to be shown *capable* of eliciting a spurious edge from a
  similarity-based reconstructor before a zero from either arm means anything.
  This mutant **is** that instrument. Without it, stage 0's second job has
  nothing to run and the restraint headline is hollow.
- **`pools_unavailable_as_zero` is this experiment's
  `reports_substrate_filter_as_agent`.** It changes no edge, no count and no
  label — only a *type*. Every plot looks identical, and the headline inverts,
  because a `0.0` in the FR-6 column enters an average and manufactures a
  difference no measurement produced.
- **`merges_instances_by_proposition` is the only defect nothing downstream would
  catch**, because it *raises* precision by deleting the nodes hardest to link.
  It reproduces `_find_existing`'s proposition fall-through
  (services.py:817) at the analysis layer, which stage -1 measured on the
  substrate.

No mutant here is documented as equivalent to another.

Entirely offline. Nothing here calls a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable

from manyu.descent import (
    AnswerKey,
    ClaimInstance,
    DescentEdge,
    MutationOp,
    Reconstruction,
    SlotScore,
    SupportKind,
    classify_mutation,
    reconstruct,
    score,
)


@dataclass(frozen=True)
class Mutant:
    name: str
    #: The test function that must fail on this mutant and pass on the real
    #: mechanism. Asserted to resolve in the test module's own globals.
    caught_by: str
    defect_family: str


CATALOGUE: tuple[Mutant, ...] = (
    Mutant(
        "draws_edges_from_similarity",
        "test_slot_d_draws_zero_edges",
        "a graph inferred from prose resemblance rather than from records",
    ),
    Mutant(
        "draws_every_dated_pair",
        "test_slot_a_precision_is_one",
        "perfect recall bought with restraint",
    ),
    Mutant(
        "direction_from_graph_shape",
        "test_direction_comes_from_the_publication_date",
        "direction taken from the graph instead of from the document",
    ),
    Mutant(
        "testimony_by_keyword",
        "test_testimony_separates_on_cardinality_and_source_id",
        "FR-1's violation as a heuristic",
    ),
    Mutant(
        "suspension_from_prose",
        "test_suspension_is_a_stored_state_not_a_hedge",
        "hedging language read as a state",
    ),
    Mutant(
        "merges_instances_by_proposition",
        "test_verbatim_instances_stay_separate_nodes",
        "the dependent variable destroyed at ingest, invisibly, in the flattering direction",
    ),
    Mutant(
        "counts_a_reversed_edge_as_half",
        "test_a_reversed_edge_is_one_fp_and_one_fn",
        "the ruler wrong rather than the graph",
    ),
    Mutant(
        "pools_unavailable_as_zero",
        "test_bare_arm_price_stays_the_string_unavailable",
        "a structural absence entered into an average",
    ),
)

#: Mutants a check cannot distinguish from the real mechanism, recorded rather
#: than omitted. Experiment 5 carries the same field for the same reason.
EXPECTED_EQUIVALENT: dict[str, str] = {}


# --- reconstructors -----------------------------------------------------------


def draws_edges_from_similarity(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Draw an edge whenever two excerpts share enough vocabulary.

    A working reconstructor, and a plausible one — this is what a system with no
    provenance layer has available. It is also the instrument section 6.3
    requires: slot D's two source families share vocabulary by construction, so
    if this mutant draws *zero* there, the null is too easy and proves nothing.
    """
    ordered = sorted(instances, key=lambda item: (item.published, item.instance_id))
    edges: list[DescentEdge] = []
    declined: list[tuple[str, str, str]] = []

    for index, ancestor in enumerate(ordered):
        for descendant in ordered[index + 1 :]:
            left = {w.strip(".,;:").lower() for w in ancestor.excerpt.split() if len(w) >= 4}
            right = {w.strip(".,;:").lower() for w in descendant.excerpt.split() if len(w) >= 4}
            if not left or not right:
                declined.append((ancestor.instance_id, descendant.instance_id, "no comparable tokens"))
                continue
            overlap = len(left & right) / len(left | right)
            if overlap < 0.30:
                declined.append((ancestor.instance_id, descendant.instance_id, f"overlap {overlap:.2f}"))
                continue
            edges.append(
                DescentEdge(
                    ancestor=ancestor.instance_id,
                    descendant=descendant.instance_id,
                    support_kind=SupportKind.TEXTUAL,
                    supporting_evidence_ids=(),
                    source_ids=(ancestor.source_id, descendant.source_id),
                    mutation=classify_mutation(ancestor, descendant, hedges),
                    undetermined=False,
                    rationale=f"token overlap {overlap:.2f}",
                )
            )

    return Reconstruction(
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        nodes=tuple(item.instance_id for item in ordered),
        edges=tuple(edges),
        declined=tuple(declined),
    )


def draws_every_dated_pair(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Link every pair whose dates order them.

    Recall is perfect by construction. Precision is whatever the corpus allows,
    and restraint is gone — experiment 4's voided Stage 0a family, where a
    sensitivity was published without its base rate.
    """
    ordered = sorted(instances, key=lambda item: (item.published, item.instance_id))
    edges = [
        DescentEdge(
            ancestor=ancestor.instance_id,
            descendant=descendant.instance_id,
            support_kind=SupportKind.TEXTUAL,
            supporting_evidence_ids=(),
            source_ids=(ancestor.source_id, descendant.source_id),
            mutation=classify_mutation(ancestor, descendant, hedges),
            undetermined=False,
            rationale="dates order the pair",
        )
        for index, ancestor in enumerate(ordered)
        for descendant in ordered[index + 1 :]
        if ancestor.published != descendant.published
    ]
    return Reconstruction(
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        nodes=tuple(item.instance_id for item in ordered),
        edges=tuple(edges),
        declined=(),
    )


def direction_from_graph_shape(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Same endpoints, same counts, direction taken from citation degree.

    Delegates to the real mechanism and then reverses any edge whose descendant
    is cited by more records than its ancestor — "the better-attested one must be
    the source." Plausible, wrong, and invisible to every check that counts edges
    without reading their direction.
    """
    real = reconstruct(
        instances,
        record_sources,
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        hedges=hedges,
        undetermined_pairs=undetermined_pairs,
    )
    degree = {item.instance_id: len(item.evidence_ids) for item in instances}
    flipped = tuple(
        replace(edge, ancestor=edge.descendant, descendant=edge.ancestor)
        if degree.get(edge.descendant, 0) > degree.get(edge.ancestor, 0)
        else edge
        for edge in real.edges
    )
    return replace(real, edges=flipped)


def testimony_by_keyword(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Label an edge TESTIMONY when the excerpt contains a reporting phrase.

    FR-1's violation rendered as a heuristic: it reads the *prose* for "according
    to" and "reportedly" instead of counting shared records and their sources.
    It gets slot E's headline edge right for the wrong reason and mislabels every
    textual edge whose excerpt happens to quote someone.
    """
    real = reconstruct(
        instances,
        record_sources,
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        hedges=hedges,
        undetermined_pairs=undetermined_pairs,
    )
    markers = ("according to", "reportedly", "is said to", "attributed to")
    by_id = {item.instance_id: item for item in instances}
    relabelled = tuple(
        replace(
            edge,
            support_kind=(
                SupportKind.TESTIMONY
                if any(m in by_id[edge.descendant].excerpt.lower() for m in markers)
                else SupportKind.TEXTUAL
            ),
        )
        for edge in real.edges
    )
    return replace(real, edges=relabelled)


def suspension_from_prose(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Mark an edge undetermined when the descendant's text hedges.

    P8's falsifier made executable. The real mechanism marks what
    `underdetermination.derive` decided — a stored state. This one reads hedging
    language and calls it suspension, which is exactly the substitution the
    scoring dimension exists to refuse.
    """
    real = reconstruct(
        instances,
        record_sources,
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        hedges=hedges,
        undetermined_pairs=(),
    )
    by_id = {item.instance_id: item for item in instances}
    words = ("may", "might", "possibly", "perhaps", "unclear", "disputed")
    marked = tuple(
        replace(edge, undetermined=any(w in by_id[edge.descendant].excerpt.lower() for w in words))
        for edge in real.edges
    )
    return replace(real, edges=marked)


def merges_instances_by_proposition(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Collapse instances carrying identical excerpts before reconstructing.

    `_find_existing`'s proposition fall-through (services.py:817), reproduced at
    the analysis layer. Stage -1 measured it on the substrate; this is what it
    would cost if the locus discipline were dropped.

    It deletes exactly the nodes whose mutation-distance is zero — verbatim
    repetition, which is what "the claim was repeated for fifty years" means —
    and it *raises* precision by removing the pairs hardest to link. Nothing
    downstream would flag it, because every count it produces is internally
    consistent.
    """
    seen: dict[str, ClaimInstance] = {}
    for item in sorted(instances, key=lambda i: (i.published, i.instance_id)):
        seen.setdefault(item.excerpt.strip().lower(), item)
    return reconstruct(
        list(seen.values()),
        record_sources,
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        hedges=hedges,
        undetermined_pairs=undetermined_pairs,
    )


# --- scorers ------------------------------------------------------------------


def counts_a_reversed_edge_as_half(
    reconstruction: Reconstruction,
    key: AnswerKey,
    *,
    priced_prediction: str = "unavailable",
    metric_version: str = "exp08.scoring.v1",
) -> SlotScore:
    """Give a reversed edge partial credit.

    The ruler wrong rather than the graph. Methodology section 6 names this as
    the thing subtly easy to get right-looking: it inflates both arms, and more
    the fluent one, because a model that finds the right pair and the wrong
    direction is rewarded for half of a mistake.
    """
    real = score(reconstruction, key, priced_prediction=priced_prediction, metric_version=metric_version)
    predicted = {(e.ancestor, e.descendant) for e in reconstruction.edges}
    expected = {pair for pair in key.edges if pair not in key.undetermined}
    reversed_edges = {(a, b) for (a, b) in predicted - expected if (b, a) in expected - predicted}
    if not reversed_edges:
        return real

    credit = len(reversed_edges) / 2
    true_positive = real.edges_true_positive + credit
    return replace(
        real,
        edges_false_positive=real.edges_false_positive - len(reversed_edges),
        edges_false_negative=real.edges_false_negative - len(reversed_edges),
        precision=(true_positive / len(predicted)) if predicted else None,
        recall=(true_positive / len(expected)) if expected else None,
    )


def pools_unavailable_as_zero(
    reconstruction: Reconstruction,
    key: AnswerKey,
    *,
    priced_prediction: str = "unavailable",
    metric_version: str = "exp08.scoring.v1",
) -> SlotScore:
    """Report a missing priced prediction as the number 0.0.

    Changes no edge, no count and no label — only a type. Every figure is
    identical and every plot looks the same. And the headline inverts, because
    the bare arm's structural inability to price a counterfactual
    (pre-registration section 0.2) becomes a *score* of zero, which enters an
    average and manufactures a difference no measurement produced.

    This is `reports_substrate_filter_as_agent` in a new place, and it is the
    reason `priced_prediction` is typed as a string.
    """
    real = score(reconstruction, key, priced_prediction=priced_prediction, metric_version=metric_version)
    if real.priced_prediction == "unavailable":
        return replace(real, priced_prediction=0.0)  # type: ignore[arg-type]
    return real


RECONSTRUCTORS: dict[str, Callable[..., Reconstruction]] = {
    "draws_edges_from_similarity": draws_edges_from_similarity,
    "draws_every_dated_pair": draws_every_dated_pair,
    "direction_from_graph_shape": direction_from_graph_shape,
    "testimony_by_keyword": testimony_by_keyword,
    "suspension_from_prose": suspension_from_prose,
    "merges_instances_by_proposition": merges_instances_by_proposition,
}

SCORERS: dict[str, Callable[..., SlotScore]] = {
    "counts_a_reversed_edge_as_half": counts_a_reversed_edge_as_half,
    "pools_unavailable_as_zero": pools_unavailable_as_zero,
}


def all_mutants() -> dict[str, Callable[..., Any]]:
    return {**RECONSTRUCTORS, **SCORERS}
