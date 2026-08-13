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
