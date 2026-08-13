"""Experiment 8 Stage -1 — executing the pre-registration against the substrate.

Records, as artifacts, what `tests/test_exp08_substrate.py` asserts. The tests are
the standard; this is the evidence `results.md` is re-derived from, and the two
must agree or one of them is wrong.

**The gate this stage exists for.** Requirements section 5 surveyed the substrate
by *reading source*, and pre-registration section 0 recorded three facts as
derived-by-hand rather than predicted. One of the three was already wrong when
read — section 0.1 asserted every corpus record lands on `UNTRUSTED_TEXT`, which
no branch of `_trust_from_source` returns (amendment A1). A survey performed by
reading is not a measurement, and this stage is where the difference shows up.

Four things are therefore recorded here rather than assumed:

1. **P1** — whether a claim-instance is representable with no new production
   code, tested where it can actually fail (a file-backed store, reopened);
2. **section 5.3** — that identity is delegated to the caller, and the stronger
   finding that it is delegated *and then overridden* by a proposition-equality
   rule the caller cannot switch off;
3. **P2** — whether testimony separates from textual descent on `evidence_ids`
   cardinality together with `source_id` distinctness. FR-1 binds only if it
   holds, so this row decides whether an edge type may ever be authored; and
4. **section 0.1's value**, measured rather than asserted.

**Two rows carry no verdict and that is deliberate.** The source-type gap and the
trust-class census report what the substrate offers; a gap is not a prediction
that can pass. Experiment 7's stage -1 set the precedent by refusing to attach
`agrees` to a base rate.

**No fixture freeze is verified here**, because this stage consumes no fixtures.
The claim-instances are synthetic stand-ins declared in the substrate test, and
that is correct: this stage tests substrate mechanics, which do not depend on
which words a 1945 document used. Corpus transcription is a stage 0 prerequisite
for slot A, not a stage -1 one.

Entirely offline. No provider call, no spend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

import test_exp08_substrate as T  # noqa: E402

from manyu.schemas import BeliefEvidenceSourceType, TrustClass  # noqa: E402

OUT = Path(__file__).resolve().parent / "stage_minus1.jsonl"


# --- P1 -----------------------------------------------------------------------


def _p1_rows(tmp: Path) -> list[dict[str, Any]]:
    db = tmp / "exp08_stage_minus1.db"
    metadata = T._instance_metadata(
        slot="A",
        instance_id="A.origin.c1",
        source_id="origin_doc",
        locus="section 1",
        published="1945-01-01",
        excerpt=T.ORIGIN_TEXT,
    )
    metadata["content_sha256"] = "0" * 64
    metadata["citation"] = "Synthetic stand-in, not a real source."

    first = T._core(str(db))
    evidence_id = T._capture(first, "origin_doc", evidence_id="ev_a_origin", metadata=metadata)
    first.store.conn.close()

    second = T._core(str(db))
    record = second.store.get_belief_evidence(evidence_id)
    round_tripped = record.metadata == metadata
    # Windows holds the file open until the sqlite handle is released, and the
    # caller deletes this directory immediately.
    second.store.conn.close()

    core = T._core()
    nested = {"corpus": "exp08", "a_key_no_schema_declares": ["nested", {"and": "deep"}]}
    deep = core.store.get_belief_evidence(T._capture(core, "origin_doc", metadata=nested))
    arbitrary_ok = deep.metadata["a_key_no_schema_declares"] == nested["a_key_no_schema_declares"]

    return [
        {
            "stage": -1,
            "check": "p1__metadata_survives_a_process_boundary",
            "pins": "pre-registration section 1 P1 (as amended by A2)",
            "store": "file-backed, reopened in a second core",
            "fields_carried": sorted(metadata),
            "round_tripped": round_tripped,
            "agrees": round_tripped,
            "note": (
                "Tested on a file-backed store because `:memory:` would not test it — the "
                "object never leaves the process, so a field that failed to serialise would "
                "still read back."
            ),
        },
        {
            "stage": -1,
            "check": "p1__metadata_accepts_arbitrary_keys",
            "pins": "pre-registration section 1 P1; requirements section 6",
            "extra_policy": "forbid",
            "arbitrary_keys_accepted": arbitrary_ok,
            "agrees": arbitrary_ok,
            "note": (
                "`extra=\"forbid\"` (schemas.py:17-18) constrains top-level model fields, not "
                "dict contents. `metadata` is a declared `dict[str, Any]`, so arbitrary keys "
                "inside it are legal. Recorded because the question has a non-obvious answer "
                "and will be re-asked."
            ),
        },
    ]


# --- section 5.3 --------------------------------------------------------------


def _identity_rows() -> list[dict[str, Any]]:
    variants = [
        ("A.v1", T.ORIGIN_TEXT),
        ("A.v2", T.DROPPED_TEXT),
        ("A.v3", "The daily allowance is two and a half units, an established figure."),
    ]

    shared = T._core()
    for _, text in variants:
        shared_ev = T._capture(shared, f"doc_{abs(hash(text)) % 997}")
        T._propose(shared, "a.one.key.for.all", text, [shared_ev])
    collapsed = len(T._beliefs(shared))

    distinct = T._core()
    for key, text in variants:
        distinct_ev = T._capture(distinct, f"doc_{key}")
        T._propose(distinct, key, text, [distinct_ev])
    separated = len(T._beliefs(distinct))

    merge = T._core()
    T._propose(merge, "a.inst.r1974.c1", T.DROPPED_TEXT, [T._capture(merge, "restatement_1974")])
    T._propose(merge, "a.inst.r1998.c1", T.DROPPED_TEXT, [T._capture(merge, "restatement_1998")])
    merged = len(T._beliefs(merge))

    fixed = T._core()
    first_ev = T._capture(fixed, "restatement_1974")
    second_ev = T._capture(fixed, "restatement_1998")
    T._propose(fixed, "a.inst.r1974.c1", f"[restatement_1974 p. 12] {T.DROPPED_TEXT}", [first_ev])
    T._propose(fixed, "a.inst.r1998.c1", f"[restatement_1998 p. 3] {T.DROPPED_TEXT}", [second_ev])
    disambiguated = len(T._beliefs(fixed))

    return [
        {
            "stage": -1,
            "check": "identity__delegation_demonstrated_both_ways",
            "pins": "requirements section 5.3; methodology section 1.1",
            "variants_fed": len(variants),
            "beliefs_with_one_declared_key": collapsed,
            "beliefs_with_a_key_per_variant": separated,
            "agrees": collapsed == 1 and separated == len(variants),
            "note": (
                "Both encodings succeed, and that is the finding: `_normalize_belief_key` "
                "collapses case and whitespace only, so the substrate imposes no identity "
                "rule and the caller decides how much mutation the corpus contains."
            ),
        },
        {
            "stage": -1,
            "check": "identity__verbatim_repetition_merges_despite_distinct_keys",
            "pins": "requirements section 5.3 — stronger than registered",
            "distinct_keys_declared": 2,
            "beliefs_created": merged,
            "agrees": merged == 1,
            "note": (
                "`_find_existing` (services.py:799-821) matches a declared key first, then "
                "falls through to exact-proposition matching with no `belief_type` guard on "
                "that path. Identity is delegated to the caller AND THEN OVERRIDDEN. The "
                "merged instances are exactly those whose mutation-distance is zero — the "
                "baseline every deletion is measured against — so this would have deleted "
                "the corpus's verbatim-repetition nodes silently, in the direction that "
                "flatters precision."
            ),
        },
        {
            "stage": -1,
            "check": "identity__locus_disambiguation_restores_distinctness",
            "pins": "requirements section 6",
            "beliefs_created": disambiguated,
            "excerpts_left_identical": True,
            "agrees": disambiguated == 2,
            "note": (
                "The discipline that fixes the fall-through, and it needs no production "
                "code. Legitimate only because the mutation operator reads "
                "`metadata[\"excerpt\"]` and never `proposition` — the excerpts stay "
                "byte-identical while the propositions do not."
            ),
        },
    ]


# --- P2 -----------------------------------------------------------------------


def _p2_rows() -> list[dict[str, Any]]:
    textual = T._core()
    left_ev = T._capture(textual, "origin_doc", evidence_id="ev_shared_origin")
    right_ev = T._capture(textual, "restatement_1974", evidence_id="ev_shared_r1974")
    T._propose(textual, "a.inst.origin.c1", f"[origin_doc s1] {T.ORIGIN_TEXT}", [left_ev, right_ev])
    T._propose(textual, "a.inst.r1974.c1", f"[restatement_1974 p12] {T.DROPPED_TEXT}", [left_ev, right_ev])
    t_left, t_right = sorted(T._beliefs(textual), key=lambda b: b.belief_key)
    t_shared = set(t_left.evidence_ids) & set(t_right.evidence_ids)
    t_sources = sorted({textual.store.get_belief_evidence(e).source_id for e in t_shared})

    testimony = T._core()
    assertion = T._capture(testimony, "commentator_1981", evidence_id="ev_assertion")
    T._propose(testimony, "e.inst.claim.c1", "[source_x s1] The claim, as first stated.", [assertion])
    T._propose(testimony, "e.inst.origin.c1", "[source_y s1] The alleged ancestor of the claim.", [assertion])
    s_left, s_right = sorted(T._beliefs(testimony), key=lambda b: b.belief_key)
    s_shared = set(s_left.evidence_ids) & set(s_right.evidence_ids)
    s_sources = sorted({testimony.store.get_belief_evidence(e).source_id for e in s_shared})

    separable = (len(t_shared), len(t_sources)) != (len(s_shared), len(s_sources))

    return [
        {
            "stage": -1,
            "check": "p2__textual_descent_profile",
            "pins": "pre-registration section 1 P2; requirements section 2",
            "shared_evidence_count": len(t_shared),
            "shared_source_ids": t_sources,
            "covers_both_endpoints": t_sources == ["origin_doc", "restatement_1974"],
            "agrees": len(t_shared) == 2 and len(t_sources) == 2,
            "note": "A textual edge yields records in both endpoint documents.",
        },
        {
            "stage": -1,
            "check": "p2__testimony_profile",
            "pins": "pre-registration section 1 P2; requirements section 2",
            "shared_evidence_count": len(s_shared),
            "shared_source_ids": s_sources,
            "asserting_document_is_neither_endpoint": s_sources == ["commentator_1981"],
            "agrees": len(s_shared) == 1 and len(s_sources) == 1,
            "note": "An asserted edge yields one record, from a third document.",
        },
        {
            "stage": -1,
            "check": "p2__discriminator_separates",
            "pins": "pre-registration section 1 P2; FR-1",
            "textual": [len(t_shared), len(t_sources)],
            "testimony": [len(s_shared), len(s_sources)],
            "separable": separable,
            "agrees": separable,
            "note": (
                "P2 HOLDS, so FR-1 binds: no edge type may be authored to win slot E. "
                "Cardinality alone does not separate the cases; cardinality together with "
                "`source_id` distinctness does, and that conjunction is what P2 registered. "
                "Had this failed, P10 would be withdrawn and slot E would move permanently "
                "under requirements section 12.3."
            ),
        },
    ]


# --- provenance, and section 0.1 measured -------------------------------------


def _substrate_rows() -> list[dict[str, Any]]:
    core = T._core()
    T._propose(core, "d.no.provenance", "[nowhere] A claim from no document.", [])
    refused = T._beliefs(core) == []

    census = T._core()
    for source_id in ("origin_doc", "restatement_1974", "commentator_1981", "disputer_2010"):
        T._capture(census, source_id)
    records = list(census.store.list_belief_evidence(T.AGENT))
    derived_classes = sorted({r.trust_class.value for r in records})
    weights = sorted({r.epistemic_weight for r in records})
    saliences = sorted({r.affective_salience for r in records})

    declared = T._core()
    declared_record = declared.store.get_belief_evidence(
        T._capture(declared, "doc_declared", trust_class=TrustClass.UNTRUSTED_TEXT.value)
    )

    return [
        {
            "stage": -1,
            "check": "provenance__mandatory_for_a_claim_instance",
            "pins": "pre-registration section 2 P4, structural leg",
            "candidate_with_no_evidence_created": not refused,
            "agrees": refused,
            "note": (
                "`_rejection_reason` (services.py:788-797) refuses a candidate with no "
                "evidence of its own. This is why P4 registers slot D at exactly zero "
                "rather than at a small number: an edge requires a shared record, and a "
                "claim-instance cannot exist without a record at all."
            ),
        },
        {
            "stage": -1,
            "check": "trust_class__measured_not_asserted",
            "pins": "pre-registration section 0.1, as amended by A1",
            "asserted_by_section_0_1": TrustClass.UNTRUSTED_TEXT.value,
            "derived_by_substrate": derived_classes,
            "reachable_by_explicit_declaration": declared_record.trust_class.value,
            "distinct_values_across_corpus": len(derived_classes),
            "agrees": derived_classes == [TrustClass.OPERATOR_INPUT.value],
            "note": (
                "A1 confirmed. `_trust_from_source` (services.py:496-503) maps "
                "OPERATOR_NOTE to OPERATOR_INPUT; no branch returns UNTRUSTED_TEXT, which "
                "is reachable only by the loader passing it explicitly. Section 0.1's "
                "CONCLUSION survives untouched — one distinct value across the corpus means "
                "zero discrimination — but it was recorded as derived-by-hand when it was "
                "an unverified assumption about a function nobody had read."
            ),
        },
        {
            "stage": -1,
            "check": "corpus_constants__invariant",
            "pins": "requirements section 12.2",
            "distinct_epistemic_weights": weights,
            "distinct_affective_saliences": saliences,
            "agrees": weights == [T.CORPUS_WEIGHT] and saliences == [T.CORPUS_SALIENCE],
            "note": (
                "Section 12.2 as an assertion rather than an intention. Varying "
                "`epistemic_weight` per source is a per-source credibility weight arriving "
                "through a field nobody named — the free constant experiment 3 removed, "
                "readmitted under another name."
            ),
        },
        {
            "stage": -1,
            "check": "source_type__no_external_document_value",
            "pins": "requirements section 5.1",
            "values": sorted(m.value for m in BeliefEvidenceSourceType),
            "least_wrong_choice": BeliefEvidenceSourceType.OPERATOR_NOTE.value,
            "note": (
                "Unaffected by A1, and carries no `agrees` because a gap is not a "
                "prediction that can pass. There is no value denoting an external "
                "document: an 1870 nutrition table has no honest slot, and OPERATOR_NOTE "
                "is the least-wrong one rather than a correct one."
            ),
        },
    ]


def _rows(tmp: Path) -> list[dict[str, Any]]:
    rows = _p1_rows(tmp) + _identity_rows() + _p2_rows() + _substrate_rows()

    scored = [r for r in rows if "agrees" in r]
    failed = [r["check"] for r in scored if not r["agrees"]]
    by_check = {r["check"]: r for r in rows}

    p1_held = by_check["p1__metadata_survives_a_process_boundary"]["agrees"] and by_check[
        "p1__metadata_accepts_arbitrary_keys"
    ]["agrees"]
    p2_held = by_check["p2__discriminator_separates"]["agrees"]

    rows.append(
        {
            "stage": -1,
            "check": "verdict",
            "checks_run": len(scored),
            "checks_agreeing": len(scored) - len(failed),
            "failed": failed,
            "p1_held": p1_held,
            "p2_held": p2_held,
            "fr1_binds": p2_held,
            "ends_experiment": not p1_held,
            "gate_passed": not failed,
            "note": (
                "P1 held, so a claim-instance is representable with no new schema, no new "
                "table and no new column — under the locus discipline the identity rows "
                "record. P2 held, so FR-1 binds and no edge type may be authored to win "
                "slot E. One registered fact did not survive contact: section 0.1's "
                "trust_class value (amendment A1), whose conclusion survives anyway. A "
                "failure in this artifact is a defect report against `requirements.md` or "
                "`pre-registration.md`, not against this runner."
            ),
        }
    )
    return rows


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        rows = _rows(Path(tmp))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    verdict = rows[-1]
    for row in rows[:-1]:
        if "agrees" in row:
            print(f"  [{'ok' if row['agrees'] else 'FAIL'}] {row['check']}")
        else:
            print(f"  [--] {row['check']}")
    print(
        f"\n  gate_passed = {verdict['gate_passed']}  "
        f"({verdict['checks_agreeing']}/{verdict['checks_run']} checks)"
    )
    print(f"  P1 held     = {verdict['p1_held']}   (a claim-instance needs no new production code)")
    print(f"  P2 held     = {verdict['p2_held']}   (FR-1 binds = {verdict['fr1_binds']})")
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    return 0 if verdict["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
