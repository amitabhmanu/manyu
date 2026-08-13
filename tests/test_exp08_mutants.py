"""Experiment 8 — the defect battery.

Every check here must **pass on the real mechanism and fail on its named
mutant**. A check that only passes on the real mechanism proves nothing: it might
pass on everything.

The fixtures are hand-built and small enough to verify by eye. Numbers asserted
below were worked out on paper before the mechanism ran, on the
`tests/_reference.py` pattern.

Entirely offline. No provider is constructed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manyu import descent_mutants as M
from manyu.descent import (
    AnswerKey,
    ClaimInstance,
    DescentEdge,
    MutationOp,
    Reconstruction,
    SupportKind,
    reconstruct,
    score,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "evals" / "fixtures" / "exp08"

ORIGIN_TEXT = "A suitable daily allowance is two and a half units. Most of this is already present in ordinary food."
DROPPED_TEXT = "A suitable daily allowance is two and a half units."

HEDGES = ("possibly", "reportedly", "it is said")


# --- a slot-A-shaped chain, hand-built ----------------------------------------
#
#   a1 (1945, origin_doc)      ---- textual, DELETION ----> a2 (1974, r1974)
#   a2 (1974, r1974)           ---- textual, NONE     ----> a3 (1998, r1998)
#   a1 and a3 share no record  ---- declined
#
# Each edge gets its own pair of link records, one located in each endpoint
# document. Reusing one record across both edges would make a1/a3 share a single
# record from a third document and classify as TESTIMONY — an artifact of the
# encoding rather than a finding, and worth avoiding in a reference fixture.

_A_SOURCES = {
    "ev_link12_origin": "origin_doc",
    "ev_link12_r1974": "restatement_1974",
    "ev_link23_r1974": "restatement_1974",
    "ev_link23_r1998": "restatement_1998",
}


def _slot_a() -> tuple[list[ClaimInstance], dict[str, str]]:
    a1 = ClaimInstance(
        instance_id="A.origin.c1",
        belief_key="a.inst.origin.c1",
        source_id="origin_doc",
        published="1945-01-01",
        excerpt=ORIGIN_TEXT,
        evidence_ids=("ev_link12_origin", "ev_link12_r1974"),
    )
    a2 = ClaimInstance(
        instance_id="A.r1974.c1",
        belief_key="a.inst.r1974.c1",
        source_id="restatement_1974",
        published="1974-01-01",
        excerpt=DROPPED_TEXT,
        evidence_ids=("ev_link12_origin", "ev_link12_r1974", "ev_link23_r1974", "ev_link23_r1998"),
    )
    a3 = ClaimInstance(
        instance_id="A.r1998.c1",
        belief_key="a.inst.r1998.c1",
        source_id="restatement_1998",
        published="1998-01-01",
        excerpt=DROPPED_TEXT,
        evidence_ids=("ev_link23_r1974", "ev_link23_r1998"),
    )
    return [a1, a2, a3], dict(_A_SOURCES)


_KEY_A = AnswerKey.from_dict(
    {
        "slot": "A",
        "edges": [
            {"ancestor": "A.origin.c1", "descendant": "A.r1974.c1", "support": "textual", "mutation": "deletion"},
            {"ancestor": "A.r1974.c1", "descendant": "A.r1998.c1", "support": "textual", "mutation": "none"},
        ],
    }
)


def _reconstruct_a(fn=reconstruct) -> Reconstruction:
    instances, sources = _slot_a()
    return fn(instances, sources, slot="A", arm="manyu", snapshot_id="snap_test", hedges=HEDGES)


# --- slot D, from the committed fixture ---------------------------------------


def _slot_d() -> tuple[list[ClaimInstance], dict[str, str]]:
    data = json.loads((FIXTURES / "corpus_D.json").read_text(encoding="utf-8"))
    instances = [
        ClaimInstance(
            instance_id=item["instance_id"],
            belief_key=item["belief_key"],
            source_id=item["source_id"],
            published=item["published"],
            excerpt=item["excerpt"],
            evidence_ids=tuple(item["evidence_ids"]),
            attributed_to=item["attributed_to"],
        )
        for item in data["claim_instances"]
    ]
    sources = {e: i["source_id"] for i in data["claim_instances"] for e in i["evidence_ids"]}
    return instances, sources


_KEY_D = AnswerKey.from_dict(json.loads((FIXTURES / "key_D.json").read_text(encoding="utf-8")))


def _reconstruct_d(fn=reconstruct) -> Reconstruction:
    instances, sources = _slot_d()
    return fn(instances, sources, slot="D", arm="manyu", snapshot_id="snap_d")


# --- the eight named checks ---------------------------------------------------


def test_slot_d_draws_zero_edges() -> None:
    """P4, and the capability check section 6.3 requires alongside it.

    Two assertions, and the second is the one most likely to be skipped: a zero
    means nothing unless the slot could have produced a non-zero. The similarity
    mutant is the instrument that establishes it.
    """
    real = _reconstruct_d()
    assert len(real.edges) == 0
    assert score(real, _KEY_D).spurious_edges == 0

    mutant = _reconstruct_d(M.draws_edges_from_similarity)
    assert len(mutant.edges) > 0, (
        "slot D cannot elicit a spurious edge from a similarity-based reconstructor, "
        "so a zero from either arm proves nothing about restraint (pre-registration 6.3). "
        "The corpus must be rebuilt BEFORE the key is frozen."
    )
    assert score(mutant, _KEY_D).spurious_edges > 0


def test_slot_a_precision_is_one() -> None:
    """Restraint on a slot that does have edges."""
    real = score(_reconstruct_a(), _KEY_A)
    assert real.precision == pytest.approx(1.0)
    assert real.recall == pytest.approx(1.0)
    assert real.edges_false_positive == 0

    mutant = score(_reconstruct_a(M.draws_every_dated_pair), _KEY_A)
    assert mutant.precision is not None and mutant.precision < 1.0, (
        "a reconstructor that links every dated pair must lose precision"
    )


def test_direction_comes_from_the_publication_date() -> None:
    """Direction is a property of the documents, never of the graph."""
    real = _reconstruct_a()
    assert ("A.origin.c1", "A.r1974.c1") in {(e.ancestor, e.descendant) for e in real.edges}

    mutant = _reconstruct_a(M.direction_from_graph_shape)
    assert ("A.r1974.c1", "A.origin.c1") in {(e.ancestor, e.descendant) for e in mutant.edges}, (
        "the mutant should have reversed the edge toward the better-cited node"
    )
    assert len(mutant.edges) == len(real.edges), "same count — only direction differs"


def test_testimony_separates_on_cardinality_and_source_id() -> None:
    """FR-1's gate. The discriminator reads records, never prose."""
    # Neither excerpt carries a reporting phrase. The edge is testimony because
    # of *who holds the record*, not because of how either text reads — which is
    # the whole distinction FR-1 turns on, and the one a prose-reader cannot see.
    claim = ClaimInstance(
        instance_id="E.claim.c1",
        belief_key="e.inst.claim.c1",
        source_id="source_x",
        published="1970-01-01",
        excerpt="The figure is exceptionally high in the published tables.",
        evidence_ids=("ev_assertion",),
    )
    alleged = ClaimInstance(
        instance_id="E.origin.c1",
        belief_key="e.inst.origin.c1",
        source_id="source_y",
        published="1870-01-01",
        excerpt="The figure is exceptionally high in the standard tables.",
        evidence_ids=("ev_assertion",),
    )
    sources = {"ev_assertion": "commentator_1981"}

    real = reconstruct([claim, alleged], sources, slot="E", arm="manyu", snapshot_id="snap_e")
    assert [e.support_kind for e in real.edges] == [SupportKind.TESTIMONY]

    mutant = M.testimony_by_keyword([claim, alleged], sources, slot="E", arm="manyu", snapshot_id="snap_e")
    assert [e.support_kind for e in mutant.edges] == [SupportKind.TEXTUAL], (
        "the keyword mutant reads the *descendant's* prose, which here has no marker, "
        "so it mislabels a genuine testimony edge as textual"
    )


def test_suspension_is_a_stored_state_not_a_hedge() -> None:
    """P8's falsifier, mechanised.

    The real mechanism marks what it is told by `underdetermination.derive`. The
    mutant reads hedging language. The fixture separates them: the descendant
    hedges but the pair is *not* suspended, and a hedge-reader marks it anyway.
    """
    instances, sources = _slot_a()
    hedging = list(instances)
    hedging[2] = ClaimInstance(
        instance_id=instances[2].instance_id,
        belief_key=instances[2].belief_key,
        source_id=instances[2].source_id,
        published=instances[2].published,
        excerpt="The allowance is possibly two and a half units.",
        evidence_ids=instances[2].evidence_ids,
    )

    real = reconstruct(hedging, sources, slot="A", arm="manyu", snapshot_id="snap_test", undetermined_pairs=())
    assert not any(e.undetermined for e in real.edges)

    mutant = M.suspension_from_prose(hedging, sources, slot="A", arm="manyu", snapshot_id="snap_test")
    assert any(e.undetermined for e in mutant.edges), (
        "the mutant should have read the hedge as a suspension"
    )


def test_verbatim_instances_stay_separate_nodes() -> None:
    """The defect nothing downstream would catch, because it flatters precision.

    `A.r1974.c1` and `A.r1998.c1` carry byte-identical excerpts — verbatim
    repetition, which is what "the claim was repeated for fifty years" means.
    """
    real = _reconstruct_a()
    assert len(real.nodes) == 3

    mutant = _reconstruct_a(M.merges_instances_by_proposition)
    assert len(mutant.nodes) == 2, "the mutant should have collapsed the verbatim pair"
    assert score(mutant, _KEY_A).recall < 1.0, (
        "and it should cost recall — the deleted node was an endpoint of a real edge"
    )


def test_a_reversed_edge_is_one_fp_and_one_fn() -> None:
    """The ruler, not the graph. A reversed edge gets no partial credit."""
    reversed_recon = Reconstruction(
        slot="A",
        arm="manyu",
        snapshot_id="snap_test",
        nodes=("A.origin.c1", "A.r1974.c1"),
        edges=(
            DescentEdge(
                ancestor="A.r1974.c1",
                descendant="A.origin.c1",
                support_kind=SupportKind.TEXTUAL,
                supporting_evidence_ids=("ev_link12_origin",),
                source_ids=("origin_doc", "restatement_1974"),
                mutation=MutationOp.NONE,
                undetermined=False,
                rationale="hand-built, reversed",
            ),
        ),
        declined=(),
    )
    key = AnswerKey.from_dict(
        {
            "slot": "A",
            "edges": [
                {"ancestor": "A.origin.c1", "descendant": "A.r1974.c1", "support": "textual", "mutation": "none"}
            ],
        }
    )

    real = score(reversed_recon, key)
    assert real.edges_true_positive == 0
    assert real.edges_false_positive == 1
    assert real.edges_false_negative == 1
    assert real.edges_reversed == 1
    assert real.precision == pytest.approx(0.0)
    assert real.recall == pytest.approx(0.0)

    mutant = M.counts_a_reversed_edge_as_half(reversed_recon, key)
    assert mutant.precision == pytest.approx(0.5), "the mutant awards half credit"
    assert mutant.edges_false_positive == 0


def test_bare_arm_price_stays_the_string_unavailable() -> None:
    """Section 0.2's void condition, as a type check.

    `unavailable` is a structural fact, not a score. A `0.0` here enters an
    average and manufactures a difference no measurement produced.
    """
    recon = _reconstruct_a()
    real = score(recon, _KEY_A, priced_prediction="unavailable")
    assert real.priced_prediction == "unavailable"
    assert isinstance(real.priced_prediction, str)
    assert not isinstance(real.as_dict()["priced_prediction"], (int, float))

    mutant = M.pools_unavailable_as_zero(recon, _KEY_A, priced_prediction="unavailable")
    assert isinstance(mutant.priced_prediction, float), "the mutant coerces it to a number"


# --- catalogue integrity ------------------------------------------------------


def test_every_caught_by_resolves_to_a_real_check() -> None:
    for mutant in M.CATALOGUE:
        assert mutant.caught_by in globals(), f"{mutant.name}: {mutant.caught_by} is not a test in this module"


def test_every_mutant_is_registered_and_callable() -> None:
    registered = M.all_mutants()
    assert {m.name for m in M.CATALOGUE} == set(registered)
    assert all(callable(fn) for fn in registered.values())


def test_no_mutant_merely_crashes() -> None:
    """Invariant two: a mutant that raises proves nothing — any test catches it."""
    instances, sources = _slot_a()
    for name, fn in M.RECONSTRUCTORS.items():
        result = fn(instances, sources, slot="A", arm="manyu", snapshot_id="snap_test", hedges=HEDGES)
        assert isinstance(result, Reconstruction), f"{name} did not return a Reconstruction"

    recon = _reconstruct_a()
    for name, fn in M.SCORERS.items():
        assert fn(recon, _KEY_A, priced_prediction="unavailable") is not None, f"{name} returned nothing"


def test_mutants_are_deterministic() -> None:
    """Experiment 5's battery shipped a check that was random via `uuid4` and
    caught its target about half the time. Repeated construction must agree."""
    instances, sources = _slot_a()
    for name, fn in M.RECONSTRUCTORS.items():
        first = fn(instances, sources, slot="A", arm="manyu", snapshot_id="s", hedges=HEDGES)
        second = fn(instances, sources, slot="A", arm="manyu", snapshot_id="s", hedges=HEDGES)
        assert first.as_dict() == second.as_dict(), f"{name} is not deterministic"


def test_no_mutant_is_documented_as_equivalent() -> None:
    assert M.EXPECTED_EQUIVALENT == {}
