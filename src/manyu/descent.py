"""Experiment 8 — reconstructing how a claim descended and mutated across sources.

The question: given a corpus of dated sources, can the provenance machinery
recover which claim descended from which, decline to draw an edge where none
exists, mark an edge that rests only on someone's say-so as such, and beat the
same corpus handed to a model with no store at all?

**Why this module holds no threshold.** Every quantity here is read off records
that already exist. Direction comes from a publication date the document carries.
An edge's support kind comes from counting shared evidence records and the
distinct `source_id`s behind them. Nothing is tuned, and a knob here would be a
defect rather than a feature — experiment 3 spent its length removing free
constants, and the fastest way to readmit one is to let this module decide how
similar two texts must be before an edge is drawn. It never asks.

**Edges are derived, never stored** (pre-registration A2). A stored edge is a
*declared* edge, and a declared edge makes reconstruction a read-back — the
reconstructor's job would collapse to reading the field a fixture wrote. This is
the discipline experiment 5 applied when it put `rivals` on `Belief` and
deliberately off `BeliefCandidate`, so that no fixture could declare
underdetermination into existence. `Belief.supports` is refused for the same
reason and two others: `RevisionEngine` walks it to propagate confidence
(revision.py:495) and counts it to price contradiction (revision.py:680), so
loading descent into it would make confidence a function of how long a genealogy
is; and it is a `list[str]`, which cannot carry a mutation operator or an
`undetermined` marker.

**The one judgement everything rests on.** A claim-instance's `proposition`
carries its source and locus — "[fnb1945 s.1] A suitable allowance is ...". That
is what the node *is* (requirements section 6), not a workaround for
`_find_existing`'s proposition fall-through, though it happens to fix that too.
It does not author the dependent variable, because **the mutation operator is
computed from `metadata["excerpt"]` and never from `proposition`**. Two instances
may carry byte-identical excerpts and distinct propositions; the excerpts are what
this module compares. If that separation is ever broken, the mutation results
become an artifact of how the propositions were labelled and mean nothing.

**Suspension is not reimplemented here.** Where the record cannot settle an edge,
the contested edge is materialised as a claim-instance in its own right and
`underdetermination.derive` decides. Writing a hedging rule in this module would
reinvent experiment 5 and — worse — would make suspension a string this module
chose rather than a state the store holds, which is exactly what P8's falsifier
turns on.

**The scorer takes plain data.** `score` never receives a core, a store or a
`Belief`. Methodology section 6 requires it applied to both arms without
branching, and taking only data is what stops it quietly reading substrate state
the bare arm does not have.

**No aggregate exists, deliberately.** Requirements section 11 forbids collapsing
the five dimensions into one number, because a single score would let strong edge
recovery hide a restraint failure — and restraint is the property the whole
experiment exists to test. `tests/test_exp08_properties.py` asserts that no
callable matching `aggregate|overall|composite` is exported, which makes the
prohibition structural rather than disciplinary.

Entirely offline. Nothing here calls a provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

FIXTURE_DIR = Path("evals/fixtures/exp08")
FREEZE_PATH = Path("evals/analysis/exp08/freeze.json")

#: Stamped on every score, and pinned by `assert_constants_pinned`. A result
#: whose metric version is unknown cannot be compared to another, and
#: methodology section 2 voids any artifact missing it.
METRIC_VERSION = "exp08.scoring.v1"

#: The `metadata["corpus"]` tag. Matches `snapshotting.CORPUS_TAG`, which is
#: declared separately because substrate must not import an experiment.
CORPUS_TAG = "exp08"


class SupportKind(str, Enum):
    """What a reconstructed edge rests on.

    The three values are exhaustive over the discriminator pre-registration P2
    verified: shared-record cardinality together with `source_id` distinctness.
    """

    #: Records in both endpoint documents — the two texts share provenance.
    TEXTUAL = "textual"
    #: One record, from a document that is neither endpoint. A third party
    #: *asserts* the descent. This is slot E's whole subject.
    TESTIMONY = "testimony"
    #: Nothing shared. No edge is drawn, and the pair is recorded in `declined`
    #: rather than dropped (FR-5).
    NONE = "none"


class MutationOp(str, Enum):
    """How the claim changed in transit.

    Computed from `metadata["excerpt"]`, never from `proposition`. The vocabulary
    is fixed by `mutation_lexicon.json`, committed and hashed before any key is
    authored — otherwise the operator set would be a metric adjusted after a
    result, which FR-3 forbids.
    """

    NONE = "none"
    #: The descendant's excerpt drops a sentence the ancestor carried. Slot A's
    #: operator, and the cleanest available: the original survives, so the drift
    #: is checkable rather than inferred.
    DELETION = "deletion"
    #: A hedge present in one excerpt and absent in the other.
    QUALIFICATION = "qualification"
    #: `metadata["attributed_to"]` differs — the claim acquired or changed an
    #: attributed author without its text changing.
    ATTRIBUTION_SHIFT = "attribution_shift"


@dataclass(frozen=True)
class ClaimInstance:
    """A proposition as stated in one source.

    Deliberately *not* a `ManyuModel`: a claim-instance is an analysis-time view
    assembled from a `Belief` and its evidence, and giving it a schema would
    invite persisting it — which A2 refused. The type system keeps it out of
    `save_belief`.
    """

    instance_id: str
    belief_key: str
    source_id: str
    published: str
    excerpt: str
    evidence_ids: tuple[str, ...]
    attributed_to: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "belief_key": self.belief_key,
            "source_id": self.source_id,
            "published": self.published,
            "excerpt": self.excerpt,
            "evidence_ids": list(self.evidence_ids),
            "attributed_to": self.attributed_to,
        }


@dataclass(frozen=True)
class DescentEdge:
    ancestor: str
    descendant: str
    support_kind: SupportKind
    supporting_evidence_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    mutation: MutationOp
    undetermined: bool
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ancestor": self.ancestor,
            "descendant": self.descendant,
            "support_kind": self.support_kind.value,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "source_ids": list(self.source_ids),
            "mutation": self.mutation.value,
            "undetermined": self.undetermined,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class Reconstruction:
    slot: str
    arm: str
    snapshot_id: str
    nodes: tuple[str, ...]
    edges: tuple[DescentEdge, ...]
    #: Every pair considered and refused, with the reason. FR-5: an edge that
    #: vanishes without a record is indistinguishable from one never considered.
    declined: tuple[tuple[str, str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "arm": self.arm,
            "snapshot_id": self.snapshot_id,
            "nodes": list(self.nodes),
            "edges": [edge.as_dict() for edge in self.edges],
            "declined": [list(item) for item in self.declined],
        }


@dataclass(frozen=True)
class AnswerKey:
    """A hand-authored key (FR-2), loaded but never written by this module."""

    slot: str
    edges: tuple[tuple[str, str], ...]
    mutations: dict[tuple[str, str], MutationOp]
    undetermined: frozenset[tuple[str, str]]
    testimony: frozenset[tuple[str, str]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnswerKey:
        edges: list[tuple[str, str]] = []
        mutations: dict[tuple[str, str], MutationOp] = {}
        undetermined: set[tuple[str, str]] = set()
        testimony: set[tuple[str, str]] = set()
        for entry in data.get("edges", ()):
            pair = (entry["ancestor"], entry["descendant"])
            edges.append(pair)
            mutations[pair] = MutationOp(entry.get("mutation", MutationOp.NONE.value))
            if entry.get("undetermined"):
                undetermined.add(pair)
            if entry.get("support") == SupportKind.TESTIMONY.value:
                testimony.add(pair)
        return cls(
            slot=data["slot"],
            edges=tuple(edges),
            mutations=mutations,
            undetermined=frozenset(undetermined),
            testimony=frozenset(testimony),
        )


@dataclass(frozen=True)
class SlotScore:
    slot: str
    arm: str
    snapshot_id: str
    metric_version: str
    edges_true_positive: int
    edges_false_positive: int
    edges_false_negative: int
    #: Diagnostic only. A reversed edge is *also* counted in both `fp` and `fn`;
    #: it is never a deduction. Methodology section 6 flags this as the thing
    #: that is subtly easy to get wrong, and getting it wrong inflates both arms
    #: and the fluent one more.
    edges_reversed: int
    precision: float | None
    recall: float | None
    #: Slot D only. `None` elsewhere so a reader cannot pool it.
    spurious_edges: int | None
    suspension_correct: bool | None
    discrimination_correct: bool | None
    mutations_expected: int
    mutations_identified: int
    mutations_misidentified: int
    #: A receipt id, or the literal string "unavailable". A *string*, so a
    #: structural absence cannot be coerced into an average downstream
    #: (pre-registration section 0.2).
    priced_prediction: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "arm": self.arm,
            "snapshot_id": self.snapshot_id,
            "metric_version": self.metric_version,
            "edges_true_positive": self.edges_true_positive,
            "edges_false_positive": self.edges_false_positive,
            "edges_false_negative": self.edges_false_negative,
            "edges_reversed": self.edges_reversed,
            "precision": self.precision,
            "recall": self.recall,
            "spurious_edges": self.spurious_edges,
            "suspension_correct": self.suspension_correct,
            "discrimination_correct": self.discrimination_correct,
            "mutations_expected": self.mutations_expected,
            "mutations_identified": self.mutations_identified,
            "mutations_misidentified": self.mutations_misidentified,
            "priced_prediction": self.priced_prediction,
        }


# --- the criterion ------------------------------------------------------------


def shared_records(left: ClaimInstance, right: ClaimInstance) -> tuple[str, ...]:
    return tuple(sorted(set(left.evidence_ids) & set(right.evidence_ids)))


def classify_support(
    left: ClaimInstance,
    right: ClaimInstance,
    record_sources: dict[str, str],
) -> tuple[SupportKind, tuple[str, ...], tuple[str, ...]]:
    """P2's discriminator, verbatim.

    Cardinality alone does not separate testimony from textual descent, and
    `source_id` distinctness alone does not either. The conjunction does, and
    stage -1 measured it before this function existed.
    """
    shared = shared_records(left, right)
    if not shared:
        return SupportKind.NONE, (), ()

    sources = tuple(sorted({record_sources[record_id] for record_id in shared}))
    endpoints = {left.source_id, right.source_id}

    if set(sources) >= endpoints and len(sources) >= 2:
        return SupportKind.TEXTUAL, shared, sources
    if len(shared) == 1 and not set(sources) & endpoints:
        return SupportKind.TESTIMONY, shared, sources
    return SupportKind.NONE, shared, sources


_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE.split(text.strip()) if part.strip()]


def classify_mutation(
    ancestor: ClaimInstance,
    descendant: ClaimInstance,
    hedges: Iterable[str] = (),
) -> MutationOp:
    """Compare excerpts — never propositions.

    Order matters: attribution is checked first because a claim can shed a
    sentence *and* change hands, and the attribution is the more consequential
    of the two for a genealogy.
    """
    if ancestor.attributed_to != descendant.attributed_to:
        return MutationOp.ATTRIBUTION_SHIFT

    before, after = _sentences(ancestor.excerpt), _sentences(descendant.excerpt)
    if len(after) < len(before) and set(after) < set(before):
        return MutationOp.DELETION

    hedge_set = {hedge.lower() for hedge in hedges}
    if hedge_set:
        in_before = {h for h in hedge_set if h in ancestor.excerpt.lower()}
        in_after = {h for h in hedge_set if h in descendant.excerpt.lower()}
        if in_before != in_after:
            return MutationOp.QUALIFICATION

    return MutationOp.NONE


def reconstruct(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
) -> Reconstruction:
    """Derive the descent graph.

    Deterministic in the input ordering: instances are sorted before pairing, so
    the output cannot depend on store iteration order. A mechanism whose output
    depends on iteration order cannot be re-derived from its own artifacts
    (`underdetermination.find_rival_sets` states the general rule).

    `undetermined_pairs` comes from `underdetermination.derive` upstream — this
    function marks what it is told, and decides nothing about suspension itself.
    """
    ordered = sorted(instances, key=lambda item: (item.published, item.instance_id))
    suspended = {tuple(pair) for pair in undetermined_pairs}
    edges: list[DescentEdge] = []
    declined: list[tuple[str, str, str]] = []

    for index, ancestor in enumerate(ordered):
        for descendant in ordered[index + 1 :]:
            if ancestor.published == descendant.published:
                declined.append(
                    (ancestor.instance_id, descendant.instance_id, "same publication date: direction undecidable")
                )
                continue

            kind, shared, sources = classify_support(ancestor, descendant, record_sources)
            if kind is SupportKind.NONE:
                declined.append(
                    (
                        ancestor.instance_id,
                        descendant.instance_id,
                        "no shared evidence record" if not shared else "shared records match no support pattern",
                    )
                )
                continue

            pair = (ancestor.instance_id, descendant.instance_id)
            edges.append(
                DescentEdge(
                    ancestor=ancestor.instance_id,
                    descendant=descendant.instance_id,
                    support_kind=kind,
                    supporting_evidence_ids=shared,
                    source_ids=sources,
                    mutation=classify_mutation(ancestor, descendant, hedges),
                    undetermined=pair in suspended,
                    rationale=(
                        f"{len(shared)} shared record(s) across {len(sources)} source(s); "
                        f"direction from published {ancestor.published} -> {descendant.published}"
                    ),
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


# --- scoring ------------------------------------------------------------------


def score(
    reconstruction: Reconstruction,
    key: AnswerKey,
    *,
    priced_prediction: str = "unavailable",
    metric_version: str = METRIC_VERSION,
) -> SlotScore:
    """Five dimensions, no aggregation (requirements section 11).

    Takes plain data. No core, no store, no `Belief` — that is what stops this
    reading substrate state the bare arm does not have, and what lets FR-4's
    "scored by the same function" be true rather than intended.
    """
    predicted = {(edge.ancestor, edge.descendant) for edge in reconstruction.edges}
    expected = {pair for pair in key.edges if pair not in key.undetermined}

    true_positive = predicted & expected
    false_positive = predicted - expected
    false_negative = expected - predicted
    reversed_edges = {(a, b) for (a, b) in false_positive if (b, a) in false_negative}

    precision = len(true_positive) / len(predicted) if predicted else None
    recall = len(true_positive) / len(expected) if expected else None

    spurious = len(predicted) if key.slot == "D" else None

    suspension: bool | None = None
    if key.undetermined:
        marked = {(e.ancestor, e.descendant) for e in reconstruction.edges if e.undetermined}
        suspension = marked == set(key.undetermined)

    discrimination: bool | None = None
    if key.testimony:
        by_pair = {(e.ancestor, e.descendant): e.support_kind for e in reconstruction.edges}
        # Both halves are required. Labelling everything TESTIMONY would satisfy
        # the first alone, which is why the second is not optional.
        testimony_right = all(by_pair.get(pair) is SupportKind.TESTIMONY for pair in key.testimony)
        textual_right = all(
            by_pair.get(pair) is SupportKind.TEXTUAL
            for pair in expected
            if pair not in key.testimony and pair in by_pair
        )
        discrimination = testimony_right and textual_right

    expected_mutations = {
        pair: op for pair, op in key.mutations.items() if op is not MutationOp.NONE
    }
    predicted_mutations = {
        (e.ancestor, e.descendant): e.mutation
        for e in reconstruction.edges
        if e.mutation is not MutationOp.NONE
    }
    identified = sum(1 for pair, op in expected_mutations.items() if predicted_mutations.get(pair) is op)
    misidentified = sum(
        1
        for pair, op in predicted_mutations.items()
        if expected_mutations.get(pair) is not op
    )

    return SlotScore(
        slot=key.slot,
        arm=reconstruction.arm,
        snapshot_id=reconstruction.snapshot_id,
        metric_version=metric_version,
        edges_true_positive=len(true_positive),
        edges_false_positive=len(false_positive),
        edges_false_negative=len(false_negative),
        edges_reversed=len(reversed_edges),
        precision=precision,
        recall=recall,
        spurious_edges=spurious,
        suspension_correct=suspension,
        discrimination_correct=discrimination,
        mutations_expected=len(expected_mutations),
        mutations_identified=identified,
        mutations_misidentified=misidentified,
        priced_prediction=priced_prediction,
    )


# --- fixture helpers ----------------------------------------------------------


def instances_from_core(core: Any, agent_id: str, slot: str) -> tuple[list[ClaimInstance], dict[str, str]]:
    """Assemble claim-instances from an ingested corpus.

    Returns the instances and the `evidence_id -> source_id` map the criterion
    needs. Selection is by metadata tag, matching `_corpus_payload`.
    """
    records = {
        record.evidence_id: record
        for record in core.store.list_belief_evidence(agent_id)
        if record.metadata.get("corpus") == CORPUS_TAG and record.metadata.get("slot") == slot
    }
    record_sources = {rid: record.source_id for rid, record in records.items()}

    instances: list[ClaimInstance] = []
    for belief in core.store.list_beliefs(agent_id, include_inactive=True):
        own = [rid for rid in belief.evidence_ids if rid in records]
        if not own:
            continue
        anchor = records[sorted(own)[0]]
        instances.append(
            ClaimInstance(
                instance_id=anchor.metadata["instance_id"],
                belief_key=belief.belief_key or "",
                source_id=anchor.source_id,
                published=anchor.metadata["published"],
                excerpt=anchor.metadata["excerpt"],
                evidence_ids=tuple(sorted(belief.evidence_ids)),
                attributed_to=anchor.metadata.get("attributed_to"),
            )
        )
    instances.sort(key=lambda item: (item.published, item.instance_id))
    return instances, record_sources


def verify_freeze() -> None:
    """Reuse experiment 4's verifier rather than writing a second one."""
    from manyu.salience import verify_fixture_freeze

    verify_fixture_freeze(FREEZE_PATH, experiment="8")
