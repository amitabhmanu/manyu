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

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence

FIXTURE_DIR = Path("evals/fixtures/exp08")
FREEZE_PATH = Path("evals/analysis/exp08/freeze.json")

#: Stamped on every score, and pinned by `assert_constants_pinned`. A result
#: whose metric version is unknown cannot be compared to another, and
#: methodology section 2 voids any artifact missing it.
METRIC_VERSION = "exp08.scoring.v1"

#: The `metadata["corpus"]` tag. Matches `snapshotting.CORPUS_TAG`, which is
#: declared separately because substrate must not import an experiment.
CORPUS_TAG = "exp08"

#: `metadata["record_kind"]` marking a record generated from an *asserted
#: descent* — a document claiming that one text descends from another — as
#: opposed to a span record attesting that text appears somewhere.
#:
#: **Read by the unresolved-assertion report and by nothing else** (A9).
#: `classify_support` never consults it: the discriminator still derives
#: `TESTIMONY` from shared-record cardinality together with `source_id`
#: distinctness, exactly as P2 registered. A declared kind that steered the
#: discriminator would be FR-1's violation wearing a different name.
ASSERTION_RECORD = "assertion"


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

    #: The excerpt is **unchanged**, modulo whitespace and case.
    #:
    #: Tightened by amendment A4. It previously meant both "unchanged" and
    #: "changed in a way I have no operator for", which are different facts that
    #: the scored mutation dimension could not tell apart — a verbatim copy and a
    #: substantive rewording both landed here.
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
    #: The excerpts differ and no more specific operator applies.
    #:
    #: Added by amendment A4, after slot B's step 2 found the vocabulary
    #: incomplete: Gamow's own retelling moves "the cosmic repulsion idea" to
    #: "the introduction of the cosmological term", changing what the claim is
    #: *about*, and the classifier called it `NONE` — identical to a verbatim
    #: copy.
    #:
    #: **Derived, not measured.** This is a residual category defined by the
    #: absence of the other operators, so it introduces no similarity score and
    #: no threshold. Two excerpts are either the same string or they are not.
    REWORDING = "rewording"


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
    #: Assertion records reaching fewer than two claim-instances — a document
    #: claiming a descent whose other end is not in the corpus (A9).
    #:
    #: Added after slot E's step 2 found Hamblin asserting descent from "German
    #: chemists" and "the original workers" while naming no document at all.
    #: Encoded the obvious way, that assertion **disappeared**: no pair could
    #: share the record, so no edge formed, and the pair's `declined` reason read
    #: "no shared evidence record" — which is false, since a record exists and
    #: has one end.
    #:
    #: An assertion pointing at nothing is a real epistemic situation and the
    #: commonest one in a contested genealogy. FR-5 requires it be countable
    #: rather than invisible.
    #:
    #: **Diagnostic only.** `score` reads `edges`, so nothing here moves a scored
    #: dimension.
    unresolved_assertions: tuple[tuple[str, str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "arm": self.arm,
            "snapshot_id": self.snapshot_id,
            "nodes": list(self.nodes),
            "edges": [edge.as_dict() for edge in self.edges],
            "declined": [list(item) for item in self.declined],
            "unresolved_assertions": [list(item) for item in self.unresolved_assertions],
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
        # `suspended_edges` was a top-level block in the first key_D.json that
        # `from_dict` never read. Empty there, so harmless — but a key author who
        # put edges in it would get silence: no error, and `suspension_correct`
        # reading `None` because `undetermined` stayed empty. Suspension is a
        # PER-EDGE flag and there is no top-level list. Refusing loudly is the
        # whole fix; supporting two spellings would let them disagree.
        if "suspended_edges" in data:
            raise ValueError(
                "answer key uses `suspended_edges`, which nothing reads. Mark suspension "
                "per edge instead: {\"ancestor\": ..., \"descendant\": ..., "
                "\"undetermined\": true}. Left as a silent no-op this costs a whole scored "
                "dimension without any error being raised."
            )
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
    # Two loci of ONE document are siblings, not ancestor and descendant. Checked
    # first because the rest of this function cannot express it: `endpoints`
    # would collapse to a singleton, `set(sources) >= endpoints` would be
    # trivially satisfied by any record from that document, and the pair would
    # classify as TEXTUAL on the strength of sharing a source with itself.
    #
    # Found by probing the origin-node split in slot A's step 2 worksheet, where
    # one paragraph yields two claim-instances. `reconstruct`'s same-date guard
    # happens to mask this today — two loci of one document share a publication
    # date — but that is incidental protection: a revised edition, or any corpus
    # where one `source_id` carries instances with different dates, would produce
    # a spurious descent edge inside a single document.
    if left.source_id == right.source_id:
        return SupportKind.NONE, (), ()

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


def _normalize_excerpt(text: str) -> str:
    """Collapse whitespace and case, and nothing else.

    Deliberately the same leniency as `_normalize_belief_key`
    (schemas.py:400): line breaks and capitalisation are typographic
    accidents of a transcription, not changes a source made. Anything
    beyond that would be a similarity judgement, and this module makes none.
    """
    return " ".join(text.split()).strip().lower()


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

    # The residual (A4). Reached only when nothing more specific applies, so it
    # names "the text changed" without measuring how much. `NONE` below is now
    # reserved for an excerpt that did not change at all.
    if _normalize_excerpt(ancestor.excerpt) != _normalize_excerpt(descendant.excerpt):
        return MutationOp.REWORDING

    return MutationOp.NONE


def undetermined_from_records(
    instances: Iterable[ClaimInstance], undetermined_records: Iterable[str]
) -> tuple[tuple[str, str], ...]:
    """Pairs an asserting document *raised and declined to settle* (A17).

    Deliberately **not** part of `reconstruct`, which marks what it is told and
    decides nothing about suspension. Keeping the derivation out here is what
    lets `undetermined_pairs` arrive either from this function or from
    `underdetermination.derive` without `reconstruct` knowing which.

    **What the flag records, and what it does not.** It is a fact about the
    *asserting document's own text* — O'Raifeartaigh & Mitton write that Wheeler
    and Alpher may have been influenced by Gamow and then argue against it. Before
    A17 the vocabulary could only say `asserted`, so those edges came out
    `TESTIMONY`, which is stronger than what the source wrote. The flag does not
    say the edge is undetermined *in fact*; it says a document raised it and did
    not settle it.

    **The risk this creates, recorded rather than hidden.** A corpus author who
    flags whatever they like makes `suspension_correct` a read-back. Two things
    hold against that and neither is decorative: the key marks `undetermined`
    independently, so scoring still compares two authorships; and the flag is a
    structured form of a sentence both arms can already read in the corpus, not
    privileged information handed to one of them. If a bare arm is ever given the
    records rather than the documents, that second protection lapses and this
    dimension stops measuring anything.
    """
    flagged = set(undetermined_records)
    if not flagged:
        return ()
    ordered = sorted(instances, key=lambda item: (item.published, item.instance_id))
    pairs: list[tuple[str, str]] = []
    for record in sorted(flagged):
        citing = [item for item in ordered if record in item.evidence_ids]
        for index, ancestor in enumerate(citing):
            for descendant in citing[index + 1 :]:
                if ancestor.source_id == descendant.source_id:
                    continue
                if ancestor.published == descendant.published:
                    continue
                pairs.append((ancestor.instance_id, descendant.instance_id))
    return tuple(sorted(set(pairs)))


def reconstruct(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    *,
    slot: str,
    arm: str,
    snapshot_id: str,
    hedges: Iterable[str] = (),
    undetermined_pairs: Iterable[tuple[str, str]] = (),
    record_kinds: dict[str, str] | None = None,
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
            if ancestor.source_id == descendant.source_id:
                declined.append(
                    (
                        ancestor.instance_id,
                        descendant.instance_id,
                        "same source document: siblings, not a descent relation",
                    )
                )
                continue

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
        unresolved_assertions=unresolved_assertions(ordered, record_sources, record_kinds),
    )


def unresolved_assertions(
    instances: Iterable[ClaimInstance],
    record_sources: dict[str, str],
    record_kinds: dict[str, str] | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """Assertion records that reach fewer than two claim-instances (A9).

    A document asserting a descent produces one record, cited by **both**
    endpoints. When the upstream end is never named — Hamblin's "German
    chemists", Gamow's remembered conversation — only one instance can cite it,
    no pair shares it, and the assertion leaves no trace in the output at all.

    Returned as `(record_id, asserting_source_id, reason)`. Sorted, because a
    report whose order depends on iteration order cannot be re-derived from its
    own artifact.

    `record_kinds` is a caller-supplied map from record id to
    `metadata["record_kind"]`. Absent it, nothing is reported: a corpus that does
    not distinguish assertion records from span records cannot have this
    measured, and guessing which single-cited records were meant as assertions
    would invent the finding.
    """
    if not record_kinds:
        return ()

    citers: dict[str, int] = {}
    for instance in instances:
        for record_id in instance.evidence_ids:
            citers[record_id] = citers.get(record_id, 0) + 1

    return tuple(
        sorted(
            (
                record_id,
                record_sources.get(record_id, "<unknown source>"),
                f"asserted descent reaches {citers.get(record_id, 0)} claim-instance(s); "
                "the other endpoint is not in the corpus",
            )
            for record_id, kind in record_kinds.items()
            if kind == ASSERTION_RECORD and citers.get(record_id, 0) < 2
        )
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


def pre_registration_drift(path: Path | str = FREEZE_PATH) -> list[str]:
    """Report drift in the frozen `pre_registration` block **without raising**.

    The non-raising twin of `verify_pre_registration_freeze`, matching
    `mechanism_drift`. Offline stages carry this into their artifact so that a
    pre-registration edited mid-development is visible on every run; the scored
    run calls the raising form.
    """
    from manyu.salience import _drift

    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    drifted, missing = _drift(freeze.get("pre_registration", {}))
    return sorted(drifted + missing)


def verify_mechanism_freeze(path: Path | str = FREEZE_PATH) -> dict[str, Any]:
    """Refuse to proceed if `descent.py` or its mutants changed after freezing.

    The raising counterpart to `mechanism_drift`, and the reason both exist is
    the split `verify_standards_freeze` already draws: a guard that fires on
    every development run gets deleted, so the offline stages *report* drift and
    the scored run *refuses* it.

    Why this block in particular. This experiment's headline candidate is a
    restraint result — the Manyu arm drawing no edge where the bare arm draws
    one. A quietly loosened `classify_support` manufactures exactly that, and
    manufactures it in the flattering direction. There is no downstream number
    that looks wrong when it happens: slot D still reports zero, and zero is
    what the finding is made of.

    Called by a scored run and deliberately not by the test suite.
    """
    from manyu.salience import _drift, _raise_on_drift

    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    _raise_on_drift("mechanisms", *_drift(freeze.get("mechanisms", {})), experiment="8")
    return freeze


def verify_pre_registration_freeze(
    path: Path | str = FREEZE_PATH, *, expect_amendments: Sequence[str] | None = None
) -> dict[str, Any]:
    """Refuse to proceed if the pre-registration changed after freezing.

    A pre-registration is only worth the discipline if the version a result is
    reported against is the version that was sealed before the result existed.
    Until this function was written, `grep -rn pre_registration` over `src/`,
    `evals/` and `tests/` returned nothing: the digest was documentation, in the
    same state `mechanisms` was in before `mechanism_drift` existed.

    Two failure modes, and the second is the quiet one:

    - the **file** changed after freezing — an amendment written to look
      pre-registered, which is the defect the whole append-only §9 exists to
      prevent;
    - the **amendment list** in the freeze no longer matches what the caller
      expects, which catches a re-freeze that recorded a new digest and forgot
      to say which amendments it now covers.

    Digests go through `salience._frozen_digest`, which normalises CRLF to LF.
    That is not a weakening — see its docstring — and it is required: the hash
    stored here on 2026-08-14 was briefly taken over raw bytes on a CRLF
    checkout, which would have failed this guard on any LF clone while nothing
    had been tampered with at all.
    """
    from manyu.salience import _drift, _raise_on_drift

    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    block = freeze.get("pre_registration", {})
    _raise_on_drift("pre_registration", *_drift(block), experiment="8")

    if expect_amendments is not None:
        for relative, entry in block.items():
            recorded = list(entry.get("amendments_at_freeze", ()))
            if recorded != list(expect_amendments):
                raise RuntimeError(
                    f"experiment 8 pre_registration freeze violated — {relative} is frozen at "
                    f"amendments {recorded}, caller expected {list(expect_amendments)}. The "
                    f"digest matches, so the file is intact; the freeze record and the caller "
                    f"disagree about which amendments the sealed version contains."
                )
    return freeze


def mechanism_drift(path: Path | str = FREEZE_PATH) -> list[str]:
    """Report drift in the frozen `mechanisms` block **without raising**.

    `verify_fixture_freeze` checks `files` only, and `verify_standards_freeze`
    checks `standards`; **nothing in the substrate reads `mechanisms` at all**
    (salience.py:770, :793). Experiment 7 freezes its detector and verifies it in
    its own paid runner. This is experiment 8's equivalent, and it exists because
    a `mechanisms` block that no code reads is a claim the freeze file makes and
    cannot keep.

    Non-raising on purpose, and the reason is the same one
    `verify_standards_freeze`'s docstring gives: a guard that fires on every
    development run gets deleted. Offline stages report the drift into their
    artifact so it is visible; the paid runner must **enforce** it, because a
    silently loosened support rule is precisely the defect that would manufacture
    this experiment's restraint headline.
    """
    import json

    from manyu.salience import _drift

    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    drifted, missing = _drift(freeze.get("mechanisms", {}))
    return sorted(drifted + missing)
