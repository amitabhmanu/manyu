"""Experiment 8 stages 1–3 — score every arm from captured output.

**Entirely offline. No provider call, no spend.** `capture_arms.py` does the
spending and writes JSON; this reads those files. A re-score therefore costs
nothing, which is what makes it safe to fix a scoring bug after a paid run
instead of choosing between paying twice and living with it.

The `manyu` arm is reconstructed here rather than captured, because it calls no
provider: it is `descent.reconstruct` over the corpus records, with suspension
derived from the A17 flags.

**FR-4 is visible in the shape of this file.** One `score` call, in one loop,
over every arm. There is no branch on arm anywhere below, and
`test_score_does_not_branch_on_arm` pins that the function itself has none.

Missing captures are REPORTED, never skipped silently: an arm that did not run
and an arm that drew nothing are different facts, and pooling them would let a
crashed run read as restraint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms  # noqa: E402

from manyu.descent import (  # noqa: E402
    AnswerKey,
    ClaimInstance,
    reconstruct,
    score,
    undetermined_from_records,
    verify_freeze,
    verify_mechanism_freeze,
    verify_pre_registration_freeze,
)

FIXTURES = REPO / "evals" / "fixtures" / "exp08"
CAPTURES = Path(__file__).resolve().parent / "arm_captures"
OUT = Path(__file__).resolve().parent / "stages.jsonl"

SLOTS = ("A", "B", "D", "E")


def _manyu(slot: str) -> Any:
    corpus = json.loads((FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    published = {s["source_id"]: s["published"] for s in corpus["sources"]}
    instances = [
        ClaimInstance(
            instance_id=i["instance_id"], belief_key=i["belief_key"],
            source_id=i["source_id"], published=published[i["source_id"]],
            excerpt=i["excerpt"], evidence_ids=tuple(i["evidence_ids"]),
            attributed_to=i.get("attributed_to"),
        )
        for i in corpus["claim_instances"]
    ]
    evidence = corpus.get("evidence") or []
    record_sources = {e["evidence_id"]: e["source_id"] for e in evidence}
    record_kinds = {e["evidence_id"]: e["record_kind"] for e in evidence}
    if not evidence:  # slot D declares its records inline
        for i in corpus["claim_instances"]:
            for eid in i["evidence_ids"]:
                record_sources[eid] = i["source_id"]
                record_kinds[eid] = "span"
    flagged = [e["evidence_id"] for e in evidence if e.get("undetermined")]
    return reconstruct(
        instances, record_sources, slot=slot, arm="manyu", snapshot_id=f"corpus_{slot}",
        record_kinds=record_kinds,
        undetermined_pairs=undetermined_from_records(instances, flagged),
    )


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slot in SLOTS:
        key_path = FIXTURES / f"key_{slot}.json"
        if not key_path.exists():
            rows.append({"slot": slot, "check": "key__absent", "agrees": False,
                         "note": "no key; the slot cannot be scored"})
            continue
        key_doc = json.loads(key_path.read_text(encoding="utf-8"))
        key = AnswerKey.from_dict(key_doc)
        provisional = bool(key_doc.get("provisional"))

        for arm in arms.ARMS:
            if arm == "manyu":
                recon = _manyu(slot)
            else:
                capture = CAPTURES / f"{arm}_{slot}.json"
                if not capture.exists():
                    rows.append({
                        "slot": slot, "arm": arm, "check": "arm__not_captured",
                        "agrees": None,
                        "note": (
                            "No capture. Reported rather than skipped: an arm that did not "
                            "run and an arm that drew nothing are different facts, and "
                            "pooling them lets a crashed run read as restraint."
                        ),
                    })
                    continue
                doc = json.loads(capture.read_text(encoding="utf-8"))
                recon = arms.normalise(
                    doc["payload"], slot=slot, arm=arm,
                    snapshot_id=f"capture_{slot}", bundle=arms.document_bundle(slot),
                )

            result = score(recon, key).as_dict()
            result.update({
                "check": "arm__scored",
                "edges_drawn": len(recon.edges),
                "edges_dropped_as_invented": len(recon.declined) if arm != "manyu" else None,
                "key_is_provisional": provisional,
                "reportable": not provisional,
                "note": (
                    "PROVISIONAL KEY (A15/A18) — model-drafted, hand-validated, unfrozen. "
                    "This row is a pipeline diagnostic and is VOID as a measurement of "
                    "reconstruction accuracy."
                    if provisional else
                    "Key is hand-authored and frozen; this row is a measurement."
                ),
            })
            rows.append(result)
    return rows


def main() -> int:
    verify_freeze()
    verify_mechanism_freeze()
    verify_pre_registration_freeze()

    rows = _rows()
    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )

    scored = [r for r in rows if r.get("check") == "arm__scored"]
    missing = [r for r in rows if r.get("check") == "arm__not_captured"]
    reportable = [r for r in scored if r.get("reportable")]

    print(f"scored {len(scored)} arm/slot pairs; {len(missing)} not captured")
    for r in scored:
        # `spurious_edges` is None off slot D by design, so print it only where
        # it means something — it is the restraint result and the one number on
        # this experiment that is currently reportable.
        extra = (f"spurious={r['spurious_edges']}" if r["spurious_edges"] is not None
                 else f"susp={r['suspension_correct']} disc={r['discrimination_correct']}")
        print(f"  slot {r['slot']:2s} {r['arm']:11s} "
              f"P={r['precision']} R={r['recall']} {extra}")
    for r in missing:
        print(f"  slot {r['slot']:2s} {r['arm']:11s} NOT CAPTURED")

    print(f"\nreportable as measurements: {len(reportable)} of {len(scored)}")
    if not reportable:
        print("  Every key in play is provisional (A15/A18). NOTHING here is a result.")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
