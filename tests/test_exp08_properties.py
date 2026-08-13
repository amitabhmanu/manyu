"""Experiment 8 — structural properties of the mechanism.

These are the prohibitions requirements section 11 and methodology section 5
state in prose, asserted as code. A prohibition that lives only in a document is
a discipline; asserted here it is a wall.

Entirely offline. No provider is constructed.
"""

from __future__ import annotations

import inspect
import io
import re
import tokenize

import pytest

from manyu import descent
from manyu.descent import (
    AnswerKey,
    ClaimInstance,
    MutationOp,
    Reconstruction,
    SupportKind,
    classify_mutation,
    reconstruct,
    score,
)

from test_exp08_mutants import _KEY_A, _slot_a, HEDGES


def _recon(arm: str = "manyu") -> Reconstruction:
    instances, sources = _slot_a()
    return reconstruct(instances, sources, slot="A", arm=arm, snapshot_id="snap_test", hedges=HEDGES)


def _identifiers(obj) -> set[str]:
    """Names appearing in *code*, with docstrings, comments and literals removed.

    Grepping raw source is the obvious implementation and the wrong one: every
    docstring in `descent.py` discusses the things the module refuses to do, so a
    naive substring check fires on the prose explaining the prohibition. What
    these tests mean to assert is that the *code* never reaches for the thing.
    """
    source = inspect.getsource(obj)
    names: set[str] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME:
            names.add(token.string)
    return names


# --- requirements section 11: no aggregation ----------------------------------


def test_no_aggregate_is_exported() -> None:
    """Section 11's prohibition, made structural.

    A single score would let strong edge recovery hide a restraint failure, and
    restraint is the property the whole experiment exists to test. The `rivals`
    move applied to the metric: if the field does not exist, no fixture and no
    caller can produce it.
    """
    banned = re.compile(r"aggregate|overall|composite|total_score|combined", re.IGNORECASE)
    offenders = [
        name
        for name, value in vars(descent).items()
        if callable(value) and banned.search(name)
    ]
    assert offenders == [], f"descent exports an aggregating callable: {offenders}"


def test_slot_score_carries_no_single_number() -> None:
    fields = set(descent.SlotScore.__dataclass_fields__)
    assert not {"score", "total", "overall", "composite"} & fields


# --- the five dimensions stay separable ---------------------------------------


def test_spurious_edges_is_none_off_slot_d() -> None:
    """A restraint count on a slot with real edges would be meaningless, and a
    reader who pooled it would get a number that looks like a failure rate."""
    assert score(_recon(), _KEY_A).spurious_edges is None


def test_empty_denominators_give_none_not_zero() -> None:
    """`None` is "no denominator"; `0.0` is "got everything wrong".

    Pooling the two would report an arm that drew nothing as an arm that drew
    only mistakes — the same coercion `pools_unavailable_as_zero` performs on the
    FR-6 column.
    """
    empty = Reconstruction(
        slot="D", arm="bare", snapshot_id="snap_d", nodes=(), edges=(), declined=()
    )
    key = AnswerKey.from_dict({"slot": "D", "edges": []})
    result = score(empty, key)
    assert result.precision is None
    assert result.recall is None
    assert result.spurious_edges == 0


def test_suspension_and_discrimination_are_none_when_the_key_asks_nothing() -> None:
    result = score(_recon(), _KEY_A)
    assert result.suspension_correct is None
    assert result.discrimination_correct is None


# --- FR-4: one scoring function, no branching on arm --------------------------


def test_score_does_not_branch_on_arm() -> None:
    """FR-4 as an assertion. The arm is carried through, never consulted."""
    manyu = score(_recon("manyu"), _KEY_A)
    bare = score(_recon("bare"), _KEY_A)

    assert manyu.arm == "manyu" and bare.arm == "bare"
    left, right = manyu.as_dict(), bare.as_dict()
    left.pop("arm"), right.pop("arm")
    assert left == right, "identical reconstructions scored differently by arm"


def test_score_takes_no_core_or_store() -> None:
    """Methodology section 6: the scorer takes plain data.

    A scorer that could reach a store could read substrate state the bare arm
    does not have, and FR-4's "scored by the same function" would be false while
    looking true.
    """
    parameters = inspect.signature(score).parameters
    assert set(parameters) == {"reconstruction", "key", "priced_prediction", "metric_version"}
    reached = _identifiers(score) & {"core", "store", "list_beliefs", "get_belief", "ManyuCore"}
    assert reached == set(), f"score reaches for {sorted(reached)}"


# --- determinism --------------------------------------------------------------


def test_reconstruct_is_order_independent() -> None:
    """A mechanism whose output depends on input order cannot be re-derived from
    its own artifacts."""
    instances, sources = _slot_a()
    forward = reconstruct(instances, sources, slot="A", arm="m", snapshot_id="s", hedges=HEDGES)
    backward = reconstruct(list(reversed(instances)), sources, slot="A", arm="m", snapshot_id="s", hedges=HEDGES)
    assert forward.as_dict() == backward.as_dict()


def test_reconstruct_is_idempotent() -> None:
    assert _recon().as_dict() == _recon().as_dict()


# --- FR-5: nothing is dropped silently ----------------------------------------


def test_every_considered_pair_is_either_an_edge_or_declined() -> None:
    """An edge that vanishes without a record is indistinguishable from one never
    considered, which is the observation FR-5 exists to keep available."""
    recon = _recon()
    n = len(recon.nodes)
    considered = {(e.ancestor, e.descendant) for e in recon.edges} | {
        (a, b) for a, b, _ in recon.declined
    }
    assert len(considered) == n * (n - 1) // 2
    for _, _, reason in recon.declined:
        assert reason, "a declined pair must carry its reason"


# --- the judgement the encoding rests on --------------------------------------


def test_mutation_reads_the_excerpt_and_never_the_proposition() -> None:
    """The separation the whole claim-instance encoding depends on.

    Locus-decorating a proposition is legitimate *only* because the mutation
    operator cannot see it. Two instances with byte-identical excerpts and wildly
    different propositions must show no mutation.
    """
    assert "proposition" not in _identifiers(classify_mutation)

    same_text = "A suitable daily allowance is two and a half units."
    left = ClaimInstance("X.a", "k.a", "doc_a", "1900-01-01", same_text, ("ev1",))
    right = ClaimInstance("X.b", "k.b", "doc_b", "1950-01-01", same_text, ("ev1",))
    assert classify_mutation(left, right) is MutationOp.NONE


def test_deletion_is_detected_from_the_excerpt() -> None:
    ancestor = ClaimInstance(
        "X.a", "k.a", "doc_a", "1900-01-01",
        "The allowance is two units. Most of it comes from food.", ("ev1",),
    )
    descendant = ClaimInstance(
        "X.b", "k.b", "doc_b", "1950-01-01", "The allowance is two units.", ("ev1",),
    )
    assert classify_mutation(ancestor, descendant) is MutationOp.DELETION


def test_none_means_unchanged_and_rewording_means_changed() -> None:
    """Amendment A4. The conflation slot B's step 2 exposed.

    Before A4, a verbatim copy and Gamow's substantive retelling both returned
    `NONE`, so the scored mutation dimension could not tell "unchanged" from
    "changed in a way I have no operator for".
    """
    same = "The allowance is two and a half units."
    identical_a = ClaimInstance("X.a", "x.a", "doc_a", "1900-01-01", same, ("ev1",))
    identical_b = ClaimInstance("X.b", "x.b", "doc_b", "1950-01-01", same, ("ev1",))
    assert classify_mutation(identical_a, identical_b) is MutationOp.NONE

    # The real pair from slot B, which the classifier previously called NONE.
    earlier = ClaimInstance(
        "B.a", "b.a", "gamow1956", "1956-09-01",
        "Einstein remarked to me many years ago that the cosmic repulsion idea was the "
        "biggest blunder he had made in his entire life.",
        ("ev1",), attributed_to="Albert Einstein",
    )
    later = ClaimInstance(
        "B.b", "b.b", "gamow1970", "1970-01-01",
        "Much later, when I was discussing cosmological problems with Einstein, he remarked "
        "that the introduction of the cosmological term was the biggest blunder he ever "
        "made in his life.",
        ("ev1",), attributed_to="Albert Einstein",
    )
    assert classify_mutation(earlier, later) is MutationOp.REWORDING


def test_rewording_normalizes_whitespace_and_case_only() -> None:
    """A line break is a transcription accident, not a change a source made.

    Anything beyond whitespace and case would be a similarity judgement, and
    this module makes none.
    """
    base = ClaimInstance("X.a", "x.a", "doc_a", "1900-01-01", "The allowance is two units.", ("ev1",))
    retyped = ClaimInstance(
        "X.b", "x.b", "doc_b", "1950-01-01", "the   allowance\nis two units.", ("ev1",)
    )
    assert classify_mutation(base, retyped) is MutationOp.NONE


def test_rewording_is_the_residual_and_never_outranks_a_named_operator() -> None:
    """A4 must not swallow the operators that carry real information."""
    ancestor = ClaimInstance(
        "X.a", "x.a", "doc_a", "1900-01-01",
        "The allowance is two units. Most of it comes from food.", ("ev1",),
    )
    dropped = ClaimInstance(
        "X.b", "x.b", "doc_b", "1950-01-01", "The allowance is two units.", ("ev1",),
    )
    assert classify_mutation(ancestor, dropped) is MutationOp.DELETION

    reattributed = ClaimInstance(
        "X.c", "x.c", "doc_c", "1960-01-01",
        "Something else entirely.", ("ev1",), attributed_to="a named authority",
    )
    assert classify_mutation(ancestor, reattributed) is MutationOp.ATTRIBUTION_SHIFT


def test_attribution_shift_outranks_deletion() -> None:
    """Order matters: a claim can shed a sentence *and* change hands, and for a
    genealogy the change of hands is the more consequential of the two."""
    ancestor = ClaimInstance(
        "X.a", "k.a", "doc_a", "1900-01-01",
        "The allowance is two units. Most of it comes from food.", ("ev1",), attributed_to=None,
    )
    descendant = ClaimInstance(
        "X.b", "k.b", "doc_b", "1950-01-01",
        "The allowance is two units.", ("ev1",), attributed_to="a named authority",
    )
    assert classify_mutation(ancestor, descendant) is MutationOp.ATTRIBUTION_SHIFT


# --- no thresholds ------------------------------------------------------------


def test_the_module_declares_no_similarity_threshold() -> None:
    """The fastest way to readmit a free constant is to let this module decide
    how similar two texts must be before an edge is drawn. It never asks."""
    banned = re.compile(r"threshold|tolerance|cutoff|min_overlap|similarity", re.IGNORECASE)
    offenders = sorted(name for name in _identifiers(descent) if banned.search(name))
    assert offenders == [], f"descent declares a tuning knob: {offenders}"


def test_support_kinds_are_exhaustive_over_the_discriminator() -> None:
    assert {k.value for k in SupportKind} == {"textual", "testimony", "none"}


# --- A9: an assertion pointing at nothing --------------------------------------


def _hamblin_shaped() -> tuple[list[ClaimInstance], dict[str, str], dict[str, str]]:
    """Slot E's case: a document asserts descent and names no upstream document."""
    asserting = ClaimInstance(
        "E.hamblin.c1", "e.hamblin", "hamblin1981", "1981-12-19",
        "German chemists had shown the original workers put the decimal point in the "
        "wrong place.",
        ("ev_assertion",),
    )
    other = ClaimInstance(
        "E.rep1965.c1", "e.rep1965", "rep1965", "1965-01-01",
        "Spinach is exceptionally rich in iron.", ("ev_iron_claim",),
    )
    sources = {"ev_assertion": "hamblin1981", "ev_iron_claim": "rep1965"}
    kinds = {"ev_assertion": descent.ASSERTION_RECORD}
    return [asserting, other], sources, kinds


def test_an_assertion_with_no_named_endpoint_is_reported_not_silent() -> None:
    """A9. Encoded the obvious way this assertion disappeared entirely.

    No pair could share the record, so no edge formed, and the pair's `declined`
    reason read "no shared evidence record" — which is false. A record exists;
    it has one end. FR-5 requires that be countable rather than invisible.
    """
    instances, sources, kinds = _hamblin_shaped()

    silent = reconstruct(instances, sources, slot="E", arm="m", snapshot_id="s")
    assert silent.unresolved_assertions == (), "no record_kinds supplied means nothing to report"

    reported = reconstruct(
        instances, sources, slot="E", arm="m", snapshot_id="s", record_kinds=kinds
    )
    assert len(reported.unresolved_assertions) == 1
    record_id, asserter, reason = reported.unresolved_assertions[0]
    assert record_id == "ev_assertion"
    assert asserter == "hamblin1981"
    assert "not in the corpus" in reason

    assert reported.edges == (), "the edge still must not form"
    assert "unresolved_assertions" in reported.as_dict()


def test_a_resolved_assertion_is_not_reported_as_unresolved() -> None:
    """The report must not fire on the ordinary testimony case, or it says nothing."""
    left = ClaimInstance("E.a", "e.a", "doc_a", "1900-01-01", "left", ("ev_assert",))
    right = ClaimInstance("E.b", "e.b", "doc_b", "1950-01-01", "right", ("ev_assert",))
    sources = {"ev_assert": "doc_c"}
    kinds = {"ev_assert": descent.ASSERTION_RECORD}

    result = reconstruct(
        [left, right], sources, slot="E", arm="m", snapshot_id="s", record_kinds=kinds
    )
    assert result.unresolved_assertions == ()
    assert [e.support_kind for e in result.edges] == [SupportKind.TESTIMONY]


def test_record_kind_never_reaches_the_discriminator() -> None:
    """FR-1 holds. A declared kind steering `classify_support` would be its
    violation wearing a different name."""
    assert "record_kind" not in _identifiers(descent.classify_support)
    assert "ASSERTION_RECORD" not in _identifiers(descent.classify_support)
    assert "record_kinds" not in _identifiers(descent.score)


def test_unresolved_assertions_do_not_move_a_scored_dimension() -> None:
    """Diagnostic only."""
    instances, sources, kinds = _hamblin_shaped()
    key = AnswerKey.from_dict({"slot": "E", "edges": []})

    without = score(reconstruct(instances, sources, slot="E", arm="m", snapshot_id="s"), key)
    with_report = score(
        reconstruct(instances, sources, slot="E", arm="m", snapshot_id="s", record_kinds=kinds),
        key,
    )
    assert without.as_dict() == with_report.as_dict()


# --- two loci of one document are siblings ------------------------------------


def _one_document_pair() -> tuple[ClaimInstance, ClaimInstance, dict[str, str]]:
    """Slot A's origin split: one paragraph, two claim-instances, one document."""
    shared = ("ev_s1", "ev_s2")
    first = ClaimInstance(
        "A.fnb.rec1", "a.inst.fnb.rec1", "fnb1945", "1945-08-01",
        "A suitable allowance of water for adults is 2.5 liters daily.", shared,
    )
    second = ClaimInstance(
        "A.fnb.rec2", "a.inst.fnb.rec2", "fnb1945", "1945-08-01",
        "Water should be allowed ad libitum, since thirst is an adequate guide.", shared,
    )
    return first, second, {"ev_s1": "fnb1945", "ev_s2": "umich2015"}


def test_two_loci_of_one_document_are_never_a_descent_edge() -> None:
    """Regression. Found by probing slot A's origin-node split.

    Without the source-identity check, `endpoints` collapses to a singleton and
    `set(sources) >= endpoints` is satisfied by any record from that document, so
    the pair classifies as TEXTUAL — a document descending from itself.
    """
    first, second, sources = _one_document_pair()
    kind, shared, srcs = descent.classify_support(first, second, sources)
    assert kind is SupportKind.NONE
    assert shared == () and srcs == ()


def test_the_same_document_guard_does_not_rely_on_the_date_guard() -> None:
    """The two guards must be independent.

    Today every pair of loci in one document also shares a publication date, so
    the date guard masks the defect. That is incidental — a revised edition would
    lift it — and a regression here would be invisible until a corpus happened to
    contain one.
    """
    first, second, sources = _one_document_pair()
    redated = ClaimInstance(
        second.instance_id, second.belief_key, second.source_id,
        "1950-08-01", second.excerpt, second.evidence_ids,
    )
    assert descent.classify_support(first, redated, sources)[0] is SupportKind.NONE

    recon = reconstruct([first, redated], sources, slot="A", arm="m", snapshot_id="s")
    assert recon.edges == ()
    assert recon.declined[0][2] == "same source document: siblings, not a descent relation"
