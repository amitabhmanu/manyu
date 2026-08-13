"""Experiment 8 Stage -1 — executing the requirements document against the substrate.

Written *before* `src/manyu/descent.py` exists, and covering no mechanism of this
experiment's. Same category as `tests/test_concealment_substrate.py`,
`tests/test_counterfactual_substrate.py` and `tests/test_underdetermination_substrate.py`,
and for the same reason: experiment 3's suite caught none of sixteen defects
because every test was written minutes after the mechanism, by the author who had
just written it, so it agreed with the code precisely where the code was wrong.

**The specific risk this file exists for.** Requirements section 5 surveys the
substrate by *reading source*, and pre-registration section 0 records three facts
as derived-by-hand rather than predicted. One of those three was already wrong
when read: section 0.1 asserted that every corpus record lands on
`UNTRUSTED_TEXT`, which no branch of `_trust_from_source` returns
(amendment A1). A survey performed by reading is not a measurement, and this file
is the measurement.

**On the claim-instances below.** They are *synthetic stand-ins*, deliberately,
and none of them is a transcription of any real source. This stage tests substrate
mechanics — whether a declared key constrains identity, whether metadata survives
a process boundary, whether testimony separates from textual descent — and those
mechanics do not depend on which words a 1945 document used. Feeding real corpus
text here would add nothing and would put untranscribed, model-recalled prose into
a fixture, which is the failure mode slot E exists to study. Corpus transcription
is a stage 0 prerequisite for slot A, not a stage -1 one.

A failure in this file is never a bug in this file. It is a defect report against
`requirements.md` section 5 or against `pre-registration.md`, and correcting the
document is this stage's output.

Entirely offline. Deterministic under `FrozenClock`. No provider is constructed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from manyu.core import ManyuCore
from manyu.schemas import (
    BeliefEvidenceSourceType,
    BeliefScope,
    BeliefType,
    ReportTarget,
    ReportTargetKind,
    TrustClass,
)

AGENT = "agent_demo"

REPO = Path(__file__).resolve().parents[1]

#: Every corpus record carries these two, unvaried, across all five slots and both
#: arms. Requirements section 12.2 refuses a per-source credibility weight on
#: experiment 3's grounds — that experiment spent its length removing free
#: constants, and a hand-set per-source weight is exactly the free constant it
#: removed, differing only in arriving through a field nobody named.
#:
#: They are constants of the *corpus*, not of the mechanism, which is why they
#: live here rather than in `descent.py`.
CORPUS_SALIENCE = 0.5
CORPUS_WEIGHT = 0.7

#: The value `_trust_from_source` derives for `OPERATOR_NOTE`
#: (services.py:499). Pre-registration section 0.1 asserted `UNTRUSTED_TEXT`;
#: no branch of that function returns it. Amendment A1 corrected the value and
#: left the conclusion — zero discrimination across the corpus — standing,
#: because whichever value is chosen is constant everywhere.
DERIVED_TRUST = TrustClass.OPERATOR_INPUT

#: What the loader must pass explicitly to reach the value section 0.1 assumed.
#: Recorded so the artifact can report both, rather than reporting the one the
#: author expected.
DECLARED_TRUST = TrustClass.UNTRUSTED_TEXT


# --- harness ------------------------------------------------------------------


def _core(db_path: str = ":memory:") -> ManyuCore:
    return ManyuCore.from_paths(db_path=db_path, frozen=True)


def _capture(
    core: ManyuCore,
    source_id: str,
    *,
    evidence_id: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    trust_class: str | None = None,
) -> str:
    """Capture one corpus evidence record.

    `source_id` is the *document*, and it is a first-class column rather than a
    metadata key (schemas.py:391) — P2's discriminator reads it, and reading it
    out of a metadata dict would make P2 a claim about a convention rather than
    about the substrate.

    `salience` and `weight` are pinned to the corpus constants and are not
    parameters. A test that could vary them per source would be a test that could
    smuggle in section 12.2's forbidden credibility weight.
    """
    payload: dict[str, Any] = {
        "agent_id": AGENT,
        "source_type": BeliefEvidenceSourceType.OPERATOR_NOTE.value,
        "source_id": source_id,
        "summary": summary if summary is not None else f"corpus record from {source_id}",
        "affective_salience": CORPUS_SALIENCE,
        "epistemic_weight": CORPUS_WEIGHT,
        "metadata": dict(metadata or {}),
    }
    if evidence_id is not None:
        payload["evidence_id"] = evidence_id
    if trust_class is not None:
        payload["trust_class"] = trust_class
    return core.capture_belief_evidence(payload)["evidence_id"]


def _propose(
    core: ManyuCore,
    key: str,
    proposition: str,
    evidence_ids: list[str],
    *,
    confidence: float = 0.7,
    belief_type: BeliefType = BeliefType.WORLD_MODEL,
) -> dict[str, Any]:
    """Propose one claim-instance through the priced ingest path.

    `scope` is GENERAL rather than AGENT_SELF on purpose: a claim-instance is a
    statement *a source* made, not a belief Manyu holds about itself. Writing to
    the store directly would bypass `_find_existing`, which is the merge rule
    under test.
    """
    return core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": f"bcand_{key}",
                    "agent_id": AGENT,
                    "proposition": proposition,
                    "belief_key": key,
                    "belief_type": belief_type.value,
                    "scope": BeliefScope.GENERAL.value,
                    "confidence": confidence,
                    "stability": 0.1,
                    "valence": 0.0,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": evidence_ids,
                }
            ],
        }
    )


def _beliefs(core: ManyuCore) -> list:
    return list(core.store.list_beliefs(AGENT, include_inactive=True))


def _instance_metadata(
    *,
    slot: str,
    instance_id: str,
    source_id: str,
    locus: str,
    published: str,
    excerpt: str,
    attributed_to: str | None = None,
) -> dict[str, Any]:
    """The claim-instance metadata envelope (requirements section 6).

    `published` is ISO and is the *only* ordering channel — direction is never
    taken from graph shape or from confidence. `excerpt` is what the mutation
    operator is computed from, and `proposition` never is; that separation is
    what makes locus-decorating the proposition a disambiguation rather than an
    authoring of the dependent variable.
    """
    return {
        "corpus": "exp08",
        "slot": slot,
        "instance_id": instance_id,
        "locus": locus,
        "published": published,
        "excerpt": excerpt,
        "attributed_to": attributed_to,
    }


# --- the shape of slot A, synthetic --------------------------------------------
#
# An origin carrying a qualifying second sentence, a downstream restatement that
# drops it (the deletion), and a verbatim repeat of that restatement. The verbatim
# repeat is the point: it is what "the claim was repeated for fifty years" means,
# and it is the case `_find_existing` merges.

ORIGIN_TEXT = "A suitable daily allowance is two and a half units. Most of this is already present in ordinary food."
DROPPED_TEXT = "A suitable daily allowance is two and a half units."


# --- P1: can a claim-instance be represented at all? ---------------------------


def test_evidence_metadata_survives_a_process_boundary(tmp_path: Path) -> None:
    """P1's falsifier, tested where it can actually fail.

    `:memory:` would not test this — the object never leaves the process, so a
    field that failed to serialise would still read back. This opens a
    file-backed store, closes it, and reopens it in a second core.
    """
    db = tmp_path / "exp08.db"
    metadata = _instance_metadata(
        slot="A",
        instance_id="A.origin.c1",
        source_id="origin_doc",
        locus="section 1",
        published="1945-01-01",
        excerpt=ORIGIN_TEXT,
    )
    metadata["content_sha256"] = "0" * 64
    metadata["citation"] = "Synthetic stand-in, not a real source."

    first = _core(str(db))
    evidence_id = _capture(first, "origin_doc", evidence_id="ev_a_origin", metadata=metadata)
    del first

    second = _core(str(db))
    record = second.store.get_belief_evidence(evidence_id)

    assert record.metadata == metadata, "metadata did not round-trip across a process boundary"
    assert record.source_id == "origin_doc"
    assert record.metadata["published"] == "1945-01-01"
    assert record.metadata["excerpt"] == ORIGIN_TEXT


def test_metadata_accepts_arbitrary_keys_despite_extra_forbid() -> None:
    """`extra="forbid"` constrains top-level model fields, not dict contents.

    Worth asserting rather than assuming: the question has a non-obvious answer
    and someone will re-ask it. `ManyuModel` forbids undeclared *fields*
    (schemas.py:17-18), and `metadata` is a declared `dict[str, Any]`.
    """
    core = _core()
    evidence_id = _capture(
        core,
        "origin_doc",
        metadata={"corpus": "exp08", "a_key_no_schema_declares": ["nested", {"and": "deep"}]},
    )
    record = core.store.get_belief_evidence(evidence_id)
    assert record.metadata["a_key_no_schema_declares"] == ["nested", {"and": "deep"}]


# --- section 5.3: identity is declared, and then overridden --------------------


def test_belief_key_imposes_no_identity_rule() -> None:
    """Methodology section 1.1, both encodings.

    One key for every variant collapses them to one belief; a distinct key per
    variant keeps them apart. Both succeed, and that is the finding: the
    substrate imposes no identity rule, so the caller decides how much mutation
    the corpus contains.
    """
    variants = [
        ("A.v1", ORIGIN_TEXT),
        ("A.v2", DROPPED_TEXT),
        ("A.v3", "The daily allowance is two and a half units, an established figure."),
    ]

    shared = _core()
    for _, text in variants:
        evidence_id = _capture(shared, f"doc_{abs(hash(text)) % 997}")
        _propose(shared, "a.one.key.for.all", text, [evidence_id])
    assert len(_beliefs(shared)) == 1, "one declared key should collapse every variant"

    distinct = _core()
    for key, text in variants:
        evidence_id = _capture(distinct, f"doc_{key}")
        _propose(distinct, key, text, [evidence_id])
    assert len(_beliefs(distinct)) == 3, "a distinct key per variant should keep them apart"


def test_verbatim_repetition_merges_despite_distinct_keys() -> None:
    """The defect that constrains the encoding — a characterisation, not a bug report.

    `_find_existing` (services.py:799-821) matches a declared key first, then
    **falls through to exact-proposition matching with no `belief_type` guard on
    that path**. Two claim-instances with distinct keys and identical text merge.

    Its docstring says identity is declared and not inferred, and refuses fuzzy
    matching on the grounds that wrongly merging silently corrupts provenance.
    The exact-proposition fall-through is an inference the caller cannot switch
    off, and it merges precisely the instances whose mutation-distance is zero —
    the baseline every deletion is measured against.

    Section 5.3's finding is therefore stronger than the one registered: identity
    is delegated to the caller *and then overridden*.
    """
    core = _core()
    first = _capture(core, "restatement_1974")
    second = _capture(core, "restatement_1998")

    _propose(core, "a.inst.r1974.c1", DROPPED_TEXT, [first])
    _propose(core, "a.inst.r1998.c1", DROPPED_TEXT, [second])

    beliefs = _beliefs(core)
    assert len(beliefs) == 1, (
        "expected the substrate to merge verbatim repetition across distinct keys; "
        "if this now fails, `_find_existing` changed and section 5.3 needs rewriting"
    )
    assert beliefs[0].belief_key == "a.inst.r1974.c1", "the first key wins the merge"


def test_locus_disambiguated_propositions_stay_distinct() -> None:
    """The discipline that fixes the fall-through, and the judgement it rests on.

    A claim-instance is "the proposition *as stated in* a source" (section 6), so
    carrying the source and locus in the proposition is what the node *is*, not a
    workaround. It is legitimate only because the mutation operator is computed
    from `metadata["excerpt"]` and never from `proposition` — the excerpts below
    are byte-identical while the propositions are not.
    """
    core = _core()
    first = _capture(
        core,
        "restatement_1974",
        metadata=_instance_metadata(
            slot="A",
            instance_id="A.r1974.c1",
            source_id="restatement_1974",
            locus="p. 12",
            published="1974-01-01",
            excerpt=DROPPED_TEXT,
        ),
    )
    second = _capture(
        core,
        "restatement_1998",
        metadata=_instance_metadata(
            slot="A",
            instance_id="A.r1998.c1",
            source_id="restatement_1998",
            locus="p. 3",
            published="1998-01-01",
            excerpt=DROPPED_TEXT,
        ),
    )

    _propose(core, "a.inst.r1974.c1", f"[restatement_1974 p. 12] {DROPPED_TEXT}", [first])
    _propose(core, "a.inst.r1998.c1", f"[restatement_1998 p. 3] {DROPPED_TEXT}", [second])

    beliefs = _beliefs(core)
    assert len(beliefs) == 2, "locus-decorated propositions must not merge"

    excerpts = {
        core.store.get_belief_evidence(eid).metadata["excerpt"]
        for belief in beliefs
        for eid in belief.evidence_ids
    }
    assert excerpts == {DROPPED_TEXT}, (
        "the excerpts must stay byte-identical — the disambiguation lives in the "
        "proposition, and the mutation operator reads the excerpt"
    )


# --- P2: does testimony separate from textual descent? ------------------------


def test_textual_descent_yields_records_in_both_documents() -> None:
    """P2's positive leg, verbatim from requirements section 2.

    An edge supported by textual descent yields records in *both* endpoint
    documents, so the shared evidence set spans two distinct `source_id`s.
    """
    core = _core()
    ancestor_ev = _capture(core, "origin_doc", evidence_id="ev_shared_origin")
    descendant_ev = _capture(core, "restatement_1974", evidence_id="ev_shared_r1974")

    _propose(core, "a.inst.origin.c1", f"[origin_doc s1] {ORIGIN_TEXT}", [ancestor_ev, descendant_ev])
    _propose(core, "a.inst.r1974.c1", f"[restatement_1974 p12] {DROPPED_TEXT}", [ancestor_ev, descendant_ev])

    left, right = (b for b in sorted(_beliefs(core), key=lambda b: b.belief_key))
    shared = set(left.evidence_ids) & set(right.evidence_ids)
    source_ids = {core.store.get_belief_evidence(eid).source_id for eid in shared}

    assert len(shared) == 2
    assert source_ids == {"origin_doc", "restatement_1974"}, (
        "a textual edge's shared records must cover both endpoint documents"
    )


def test_testimony_yields_one_record_from_a_third_document() -> None:
    """P2's negative leg — the discriminator, and FR-1's gate.

    An edge *asserted* by a third party yields exactly one shared record, whose
    `source_id` is neither endpoint. Cardinality alone does not separate the two
    cases; cardinality together with `source_id` distinctness does, and that
    conjunction is what P2 registers.
    """
    core = _core()
    assertion = _capture(core, "commentator_1981", evidence_id="ev_assertion")

    _propose(core, "e.inst.claim.c1", "[source_x s1] The claim, as first stated.", [assertion])
    _propose(core, "e.inst.origin.c1", "[source_y s1] The alleged ancestor of the claim.", [assertion])

    left, right = (b for b in sorted(_beliefs(core), key=lambda b: b.belief_key))
    shared = set(left.evidence_ids) & set(right.evidence_ids)
    source_ids = {core.store.get_belief_evidence(eid).source_id for eid in shared}

    assert len(shared) == 1
    assert source_ids == {"commentator_1981"}
    assert "source_x" not in source_ids and "source_y" not in source_ids, (
        "the asserting document must be neither endpoint"
    )


def test_p2_discriminator_separates_the_two_cases() -> None:
    """P2 as one assertion, so a failure reads as P2 failing rather than as a detail.

    If this fails, FR-1 does not bind: no edge type may be authored to rescue
    slot E until requirements section 12.3 is applied, and P10 is withdrawn.
    """
    core = _core()

    textual_a = _capture(core, "doc_one", evidence_id="ev_t_a")
    textual_b = _capture(core, "doc_two", evidence_id="ev_t_b")
    _propose(core, "t.left", "[doc_one] left", [textual_a, textual_b])
    _propose(core, "t.right", "[doc_two] right", [textual_a, textual_b])

    asserted = _capture(core, "doc_three", evidence_id="ev_assert")
    _propose(core, "s.left", "[doc_four] left", [asserted])
    _propose(core, "s.right", "[doc_five] right", [asserted])

    def _profile(left_key: str, right_key: str) -> tuple[int, int]:
        beliefs = {b.belief_key: b for b in _beliefs(core)}
        shared = set(beliefs[left_key].evidence_ids) & set(beliefs[right_key].evidence_ids)
        sources = {core.store.get_belief_evidence(eid).source_id for eid in shared}
        return len(shared), len(sources)

    assert _profile("t.left", "t.right") == (2, 2)
    assert _profile("s.left", "s.right") == (1, 1)


# --- P4's structural leg ------------------------------------------------------


def test_provenance_is_mandatory_for_a_claim_instance() -> None:
    """`_rejection_reason` refuses a candidate with no evidence of its own.

    This is why P4 registers slot D at exactly zero rather than at a small
    number: an edge requires a shared record, and a claim-instance cannot exist
    without a record at all.
    """
    core = _core()
    result = _propose(core, "d.no.provenance", "[nowhere] A claim from no document.", [])

    assert _beliefs(core) == [], "a claim-instance with no evidence must not be created"
    assert result.get("status") != "ok" or result.get("rejected"), (
        f"expected a rejection, got {result!r}"
    )


# --- pre-registration section 0.1, measured rather than asserted --------------


def test_trust_class_derives_to_operator_input_not_untrusted_text() -> None:
    """Amendment A1, as a measurement.

    `_trust_from_source` (services.py:496-503) maps `OPERATOR_NOTE` to
    `OPERATOR_INPUT`. No branch returns `UNTRUSTED_TEXT`; it is reachable only by
    the loader passing it explicitly.
    """
    core = _core()
    derived = core.store.get_belief_evidence(_capture(core, "doc_derived"))
    assert derived.trust_class is DERIVED_TRUST

    declared = core.store.get_belief_evidence(
        _capture(core, "doc_declared", trust_class=DECLARED_TRUST.value)
    )
    assert declared.trust_class is DECLARED_TRUST


def test_trust_class_is_constant_across_the_corpus_either_way() -> None:
    """Section 0.1's conclusion, which A1 leaves standing.

    Whichever value the loader settles on, it is the same for every source in
    every slot — so `trust_class` contributes zero discrimination, and any later
    result that appears to turn on it is a bug.
    """
    core = _core()
    for source_id in ("origin_doc", "restatement_1974", "commentator_1981", "disputer_2010"):
        _capture(core, source_id)

    classes = {
        record.trust_class
        for record in core.store.list_belief_evidence(AGENT)
    }
    assert len(classes) == 1, f"trust_class varied across the corpus: {classes}"


def test_epistemic_weight_and_salience_are_constant_across_the_corpus() -> None:
    """Section 12.2 as an assertion rather than an intention.

    Varying `epistemic_weight` per source is a per-source credibility weight
    arriving through a field nobody named — the free constant experiment 3
    removed, readmitted under another name.
    """
    core = _core()
    for source_id in ("origin_doc", "restatement_1974", "commentator_1981", "disputer_2010"):
        _capture(core, source_id)

    records = list(core.store.list_belief_evidence(AGENT))
    assert {r.epistemic_weight for r in records} == {CORPUS_WEIGHT}
    assert {r.affective_salience for r in records} == {CORPUS_SALIENCE}


# --- FR-7: the corpus freeze --------------------------------------------------


def _seed_two_instance_slot(core: ManyuCore, *, slot: str = "A", excerpt: str = DROPPED_TEXT) -> None:
    for source_id, locus, published in (
        ("origin_doc", "section 1", "1945-01-01"),
        ("restatement_1974", "p. 12", "1974-01-01"),
    ):
        metadata = _instance_metadata(
            slot=slot,
            instance_id=f"{slot}.{source_id}.c1",
            source_id=source_id,
            locus=locus,
            published=published,
            excerpt=excerpt,
        )
        metadata["citation"] = f"Synthetic stand-in for {source_id}."
        metadata["content_sha256"] = "0" * 64
        evidence_id = _capture(core, source_id, evidence_id=f"ev_{slot}_{source_id}", metadata=metadata)
        _propose(core, f"{slot.lower()}.inst.{source_id}.c1", f"[{source_id} {locus}] {excerpt}", [evidence_id])


def test_corpus_snapshot_freezes_the_slot() -> None:
    """FR-7. Selection is by metadata tag, never by word overlap."""
    core = _core()
    _seed_two_instance_slot(core)
    _capture(core, "unrelated_doc", metadata={"corpus": "exp08", "slot": "B"})

    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="A"))

    assert snapshot.payload["slot"] == "A"
    assert len(snapshot.payload["evidence"]) == 2, "slot B's record must not be swept in"
    assert len(snapshot.payload["claim_instances"]) == 2
    assert sorted(snapshot.payload["documents"]) == ["origin_doc", "restatement_1974"]
    assert "affect_state" not in snapshot.payload, (
        "a mutable field under a content-derived id would make the id claim a "
        "sameness the payload contradicts"
    )


def test_corpus_snapshot_id_is_content_derived() -> None:
    """The property `uuid4` cannot have, and FR-7 depends on.

    Two runs over a byte-identical corpus must agree, and a changed excerpt must
    disagree — otherwise the id certifies *when* rather than *what*, and cannot
    detect the in-place evidence rewrite requirements section 5.2 raises.
    """
    first = _core()
    _seed_two_instance_slot(first)
    left = first.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="A"))

    second = _core()
    _seed_two_instance_slot(second)
    right = second.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="A"))

    assert left.snapshot_id == right.snapshot_id, "identical corpora must produce identical ids"
    assert left.snapshot_id.startswith("snap_")

    rewritten = _core()
    _seed_two_instance_slot(rewritten, excerpt=DROPPED_TEXT + " And one sentence more.")
    changed = rewritten.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="A"))

    assert changed.snapshot_id != left.snapshot_id, "a re-transcription must change the id"


def test_corpus_snapshot_is_not_reportable() -> None:
    """A corpus snapshot must never become an honesty score.

    `rank_causes` has no branch for this kind and returns `[]`. Pinned here so a
    later caller cannot quietly compose a report about a corpus freeze — the one
    surface that would produce nonsense.
    """
    from manyu.reporting import rank_causes

    core = _core()
    _seed_two_instance_slot(core)
    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="A"))

    assert rank_causes(snapshot) == []


def test_other_snapshot_kinds_keep_their_uuid_ids_and_affect_trio() -> None:
    """The asymmetry is confined to CORPUS.

    A regression here would mean experiment 8 changed the honesty scorer's
    substrate, which it has no business doing.
    """
    core = _core()
    evidence_id = _capture(core, "origin_doc")
    _propose(core, "a.inst.origin.c1", f"[origin_doc s1] {ORIGIN_TEXT}", [evidence_id])
    belief = _beliefs(core)[0]

    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=belief.belief_id))

    assert "affect_state" in snapshot.payload
    assert "active_mood" in snapshot.payload
    assert "recent_inner_voice" in snapshot.payload
    assert len(snapshot.snapshot_id) == len("snap_") + 12


# --- the source type has no honest value --------------------------------------


def test_no_source_type_denotes_an_external_document() -> None:
    """Section 5.1's other half, and it is unaffected by A1.

    `OPERATOR_NOTE` is the least-wrong slot for an 1870 nutrition table rather
    than a correct one. Recorded as a measurement so the artifact reports the
    gap rather than the workaround.
    """
    values = {member.value for member in BeliefEvidenceSourceType}
    assert not values & {"document", "publication", "external_document", "source"}
    assert "operator_note" in values
