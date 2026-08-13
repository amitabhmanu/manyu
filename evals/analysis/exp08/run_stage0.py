"""Experiment 8 Stage 0 — reconstruction over hand-encoded claim-instances.

Extraction is bypassed entirely. The question this rung answers is whether the
mechanism recovers a graph it is *handed*, because a reconstructor that cannot do
that will not recover one it has to read, and finding that out costs nothing.

Three things are established here, and two of them can end the stage:

1. **P4 — slot D draws exactly zero edges.** The strongest offline claim in the
   experiment, and structural rather than empirical: an edge requires a shared
   evidence record, and slot D's generator emits none.
2. **Pre-registration section 6.3's capability check.** A zero on slot D means
   nothing unless the slot *could* have produced a non-zero. The similarity
   mutant is the instrument. If it draws zero here, the null is too easy, proves
   nothing about restraint, and the corpus must be rebuilt — while the key is
   still unfrozen, which is the only window in which rebuilding is legitimate.
3. **Recovery on a slot-A-shaped chain.** Direction, support kind and the
   deletion operator, against numbers written down before the mechanism ran.

**What this stage does NOT establish, and the artifact says so in its own row.**
P3 is registered against *slot A*, and slot A is a real corpus that has not been
transcribed. The chain exercised here is synthetic and slot-A-*shaped*. It tests
the algorithm; it cannot test agreement between the reconstruction and a
hand-authored key, because there is no hand-authored key for a corpus that does
not exist yet. Recording that as a distinct, unscored row is the alternative to
letting a synthetic pass be read later as P3 having been met.

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

import test_exp08_mutants as T  # noqa: E402
import test_exp08_substrate as S  # noqa: E402

from manyu import descent_mutants as M  # noqa: E402
from manyu.descent import reconstruct, score, verify_freeze  # noqa: E402
from manyu.schemas import ReportTarget, ReportTargetKind  # noqa: E402

OUT = Path(__file__).resolve().parent / "stage0.jsonl"
FIXTURES = REPO / "evals" / "fixtures" / "exp08"


def _ingest_slot_d(core: Any) -> None:
    """Drive slot D through the priced ingest path, as a scored run would."""
    data = json.loads((FIXTURES / "corpus_D.json").read_text(encoding="utf-8"))
    published = {s["source_id"]: s["published"] for s in data["sources"]}
    citations = {s["source_id"]: s["citation"] for s in data["sources"]}
    hashes = {s["source_id"]: s["content_sha256"] for s in data["sources"]}

    for item in data["claim_instances"]:
        metadata = {
            "corpus": "exp08",
            "slot": "D",
            "instance_id": item["instance_id"],
            "locus": item["locus"],
            "published": published[item["source_id"]],
            "excerpt": item["excerpt"],
            "attributed_to": item["attributed_to"],
            "citation": citations[item["source_id"]],
            "content_sha256": hashes[item["source_id"]],
        }
        evidence_id = S._capture(
            core, item["source_id"], evidence_id=item["evidence_ids"][0], metadata=metadata
        )
        S._propose(core, item["belief_key"], item["proposition"], [evidence_id])


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # --- FR-7: the corpus freeze, driven end to end --------------------------
    core = S._core()
    _ingest_slot_d(core)
    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="D"))

    second = S._core()
    _ingest_slot_d(second)
    reingested = second.snapshot(ReportTarget(kind=ReportTargetKind.CORPUS, id_or_text="D"))

    rows.append(
        {
            "stage": 0,
            "check": "fr7__corpus_snapshot_is_content_derived",
            "pins": "requirements FR-7; requirements section 5.2",
            "slot": "D",
            "snapshot_id": snapshot.snapshot_id,
            "reingest_snapshot_id": reingested.snapshot_id,
            "instances_frozen": len(snapshot.payload["claim_instances"]),
            "records_frozen": len(snapshot.payload["evidence"]),
            "agrees": snapshot.snapshot_id == reingested.snapshot_id,
            "note": (
                "Two independent ingests of a byte-identical corpus agree on the id. With "
                "`uuid4` they would not, and the id would certify WHEN rather than WHAT — "
                "which cannot detect the in-place evidence rewrite section 5.2 raises, and "
                "would make FR-7 decorative."
            ),
        }
    )

    # --- P4 and the capability check -----------------------------------------
    instances, sources = T._slot_d()
    real_d = reconstruct(instances, sources, slot="D", arm="manyu", snapshot_id=snapshot.snapshot_id)
    real_score = score(real_d, T._KEY_D)

    mutant_d = M.draws_edges_from_similarity(
        instances, sources, slot="D", arm="mutant", snapshot_id=snapshot.snapshot_id
    )
    mutant_score = score(mutant_d, T._KEY_D)

    rows.append(
        {
            "stage": 0,
            "check": "p4__slot_d_draws_zero_edges",
            "pins": "pre-registration section 2 P4",
            "slot": "D",
            "arm": "manyu",
            "snapshot_id": snapshot.snapshot_id,
            "metric_version": real_score.metric_version,
            "nodes": len(real_d.nodes),
            "edges": len(real_d.edges),
            "spurious_edges": real_score.spurious_edges,
            "declined_pairs": len(real_d.declined),
            "priced_prediction": real_score.priced_prediction,
            "agrees": real_score.spurious_edges == 0,
            "note": (
                "Structural rather than empirical: `_rejection_reason` makes provenance "
                "mandatory, an edge requires a shared record, and the generator emits none. "
                "Every refused pair is recorded in `declined` with its reason (FR-5) rather "
                "than dropped."
            ),
        }
    )
    rows.append(
        {
            "stage": 0,
            "check": "capability__slot_d_can_elicit_a_spurious_edge",
            "pins": "pre-registration section 6.3",
            "slot": "D",
            "arm": "mutant:draws_edges_from_similarity",
            "spurious_edges": mutant_score.spurious_edges,
            "agrees": (mutant_score.spurious_edges or 0) > 0,
            "note": (
                "THE row that makes P4 mean anything. A null nothing could fail is not a "
                "null. The two source families share vocabulary by construction, so a "
                "similarity-based reconstructor draws edges here while the real mechanism "
                "draws none — the difference is provenance, which is invisible to prose. "
                "Had this come out zero, the corpus would have to be rebuilt before the key "
                "was frozen."
            ),
        }
    )

    # --- recovery on a slot-A-shaped chain -----------------------------------
    recon_a = T._reconstruct_a()
    score_a = score(recon_a, T._KEY_A)
    kinds = sorted({e.support_kind.value for e in recon_a.edges})
    ops = sorted({e.mutation.value for e in recon_a.edges})

    rows.append(
        {
            "stage": 0,
            "check": "recovery__slot_a_shaped_chain",
            "pins": "pre-registration section 2 P3 — PROVISIONAL, see the row below",
            "slot": "A-shaped (synthetic)",
            "arm": "manyu",
            "snapshot_id": "n/a — hand-encoded, not ingested",
            "metric_version": score_a.metric_version,
            "precision": score_a.precision,
            "recall": score_a.recall,
            "edges_reversed": score_a.edges_reversed,
            "support_kinds": kinds,
            "mutation_ops": ops,
            "mutations_expected": score_a.mutations_expected,
            "mutations_identified": score_a.mutations_identified,
            "mutations_misidentified": score_a.mutations_misidentified,
            "agrees": (
                score_a.precision == 1.0
                and score_a.recall == 1.0
                and score_a.mutations_identified == score_a.mutations_expected
                and score_a.mutations_misidentified == 0
            ),
            "note": (
                "Direction from the publication date, support kind from shared records, and "
                "the deletion operator from the excerpt — all against numbers written down "
                "before the mechanism ran."
            ),
        }
    )
    rows.append(
        {
            "stage": 0,
            "check": "p3__not_yet_testable",
            "pins": "pre-registration section 2 P3; amendment A3",
            "slot": "A",
            "blocked_on": "corpus transcription",
            "note": (
                "NO VERDICT, deliberately. P3 is registered against slot A, and slot A is a "
                "real corpus that has not been transcribed. The chain scored above is "
                "synthetic and slot-A-SHAPED: it tests the algorithm, and it cannot test "
                "agreement between a reconstruction and a hand-authored key, because no such "
                "key exists yet. Recording this as its own row is the alternative to letting "
                "a synthetic pass be read later as P3 having been met. Under A3, a P3 miss "
                "triggers a recorded re-read of the key before any conclusion about the "
                "algorithm."
            ),
        }
    )

    # --- the ruler ------------------------------------------------------------
    rows.append(
        {
            "stage": 0,
            "check": "scoring__reversed_edge_is_one_fp_and_one_fn",
            "pins": "requirements section 11; methodology section 6",
            "agrees": True,
            "detail": "asserted in tests/test_exp08_mutants.py::test_a_reversed_edge_is_one_fp_and_one_fn",
            "note": (
                "Direction sensitivity is what methodology section 6 flags as subtly easy to "
                "get right-looking. Awarding half credit inflates both arms and the fluent "
                "one more, because finding the right pair with the wrong direction would be "
                "rewarded for half a mistake."
            ),
        }
    )
    rows.append(
        {
            "stage": 0,
            "check": "fr6__bare_arm_price_is_a_string",
            "pins": "pre-registration section 0.2; FR-6",
            "priced_prediction": score(recon_a, T._KEY_A, priced_prediction="unavailable").priced_prediction,
            "type": "str",
            "agrees": isinstance(
                score(recon_a, T._KEY_A, priced_prediction="unavailable").priced_prediction, str
            ),
            "note": (
                "`unavailable` is a structural fact, never a score of 0.0. A zero enters an "
                "average and manufactures a difference no measurement produced."
            ),
        }
    )

    scored = [r for r in rows if "agrees" in r]
    failed = [r["check"] for r in scored if not r["agrees"]]
    rows.append(
        {
            "stage": 0,
            "check": "verdict",
            "checks_run": len(scored),
            "checks_agreeing": len(scored) - len(failed),
            "failed": failed,
            "p4_held": not failed or "p4__slot_d_draws_zero_edges" not in failed,
            "null_is_capable": "capability__slot_d_can_elicit_a_spurious_edge" not in failed,
            "p3_status": "not_yet_testable — slot A awaits transcription",
            "passed": not failed,
            "note": (
                "Stage 0's offline half. The restraint result (P4) is established and the "
                "null is shown capable of failing. What remains before stage 1 is corpus "
                "transcription for slots A, B, C and E, and the hand-authored keys that "
                "FR-2 reserves to a human."
            ),
        }
    )
    return rows


def main() -> int:
    # Before anything else. Unlike stage -1, this stage reads committed fixtures,
    # so a drifted corpus_D.json would silently change the restraint result.
    verify_freeze()

    rows = _rows()
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
    print(f"\n  passed = {verdict['passed']}  ({verdict['checks_agreeing']}/{verdict['checks_run']} checks)")
    print(f"  P4 held           = {verdict['p4_held']}")
    print(f"  null is capable   = {verdict['null_is_capable']}")
    print(f"  P3                = {verdict['p3_status']}")
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
