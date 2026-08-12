"""Experiment 5 Stage 0 — what the substrate does to a rival pair unaided.

Records, as artifacts, what `tests/test_underdetermination_substrate.py` asserts.
The tests are the standard; this is the evidence `results.md` is re-derived from,
and the two must agree or one of them is wrong.

**Both edge topologies and both seeding paths**, because Stage -1 found that the
answer depends on which you take and the requirements originally assumed one:

- *mutual* vs *one-way* — with both edges the pair holds a gap of exactly zero;
  with one, it separates by the full contradiction penalty and the side that
  survives is the one the extractor happened to phrase as the contradictor
  (requirements section 6.1).
- *priced ingest* vs *unpriced seed* — `fork.seed_beliefs` writes edges straight
  to the store and never prices (`salience.SEEDS_ARE_UNPRICED`), which is right
  for experiment 4 where stake is the independent variable. Here pricing is the
  thing under observation, and it decides whether the attention loop finds
  anything left to charge.

Also recorded: what `WorldviewSynthesizer` emits, since requirements section 5.1's
claim is that a standoff is averaged into one mediocre stance rather than shown.

**The generation-path check runs first and its answer is already known.**
`ScenarioJSONProvider` hardcodes `"contradicts": []`, so the offline path cannot
produce a rival pair at all and an offline base rate would describe the
instrument. Experiment 4's Stage 0a was voided for exactly this and the number was
read before the check. Here the check gates the number.

Entirely offline. No provider call, no spend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "evals" / "analysis" / "exp04"))

from manyu.core import ManyuCore  # noqa: E402
from manyu.fork import BeliefSpec, seed_beliefs  # noqa: E402
from manyu.providers import ScenarioJSONProvider  # noqa: E402
from manyu.salience import Arm, AttentionLoop  # noqa: E402
from manyu.services import WorldviewSynthesizer  # noqa: E402
from manyu.underdetermination import derive, load_web, seed_fixture, verify_freeze, web_specs  # noqa: E402

from run_stage0 import generation_path_can_contradict  # noqa: E402

AGENT = "agent_demo"
OUT = REPO / "evals" / "analysis" / "exp05" / "stage0.jsonl"


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _rivals(core: ManyuCore) -> tuple[Any, Any]:
    stored = {b.belief_key: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    return stored["reading_a"], stored["reading_b"]


def _gap(core: ManyuCore) -> dict[str, Any]:
    a, b = _rivals(core)
    return {
        "reading_a": round(a.confidence, 6),
        "reading_b": round(b.confidence, 6),
        "gap": round(abs(a.confidence - b.confidence), 6),
        "status_a": a.status.value,
        "status_b": b.status.value,
    }


def _stances(core: ManyuCore) -> list[dict[str, Any]]:
    return [
        {"theme": s.theme, "confidence": s.confidence, "beliefs": len(s.supporting_belief_ids)}
        for s in WorldviewSynthesizer(core.store, core.clock).synthesize(AGENT)
    ]


def priced_ingest(fixture: str) -> dict[str, Any]:
    """The path a live web takes: candidates through `update_beliefs`, which
    prices every contradiction the extractor declared."""
    core = _core()
    seed_fixture(core, fixture, agent_id=AGENT)
    before = _gap(core)
    loop = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)
    return {
        "kind": "stage0",
        "fixture": fixture,
        "path": "priced_ingest",
        "confidences": before,
        "after_loop": _gap(core),
        "loop_steps": len(loop.steps),
        "loop_moved": [round(step.moved, 6) for step in loop.steps],
        "loop_inert": len(loop.inert),
        "tie_break": sorted({step.direction for step in loop.steps}),
        "stances": _stances(core),
    }


def unpriced_seed(fixture: str) -> dict[str, Any]:
    """`fork.seed_beliefs`, which writes edges directly and charges nothing.

    The fixture's evidence *sharing* is lost on this path — `seed_beliefs` mints a
    record per belief — so this row reports the confidence and loop behaviour only,
    and never a criterion verdict. Recording it anyway is the point: it is the
    control showing the loop is capable of moving something, without which
    "inert" on the priced path could mean the loop is broken.
    """
    fixture_json = load_web(fixture)
    core = _core()
    specs = [
        BeliefSpec(
            key=entry["key"],
            proposition=entry["proposition"],
            valence=entry.get("valence", 0.0),
            confidence=entry.get("confidence", 0.7),
            evidence_count=len(entry["evidence"]),
            contradicts=tuple(entry.get("contradicts", ())),
        )
        for entry in fixture_json["beliefs"]
    ]
    seed_beliefs(core, specs, agent_id=AGENT)
    before = _gap(core)
    loop = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)
    return {
        "kind": "stage0",
        "fixture": fixture,
        "path": "unpriced_seed",
        "confidences": before,
        "after_loop": _gap(core),
        "loop_steps": len(loop.steps),
        "loop_moved": [round(step.moved, 6) for step in loop.steps],
        "loop_inert": len(loop.inert),
        "tie_break": sorted({step.direction for step in loop.steps}),
        "stances": _stances(core),
    }


def with_derivation(fixture: str) -> dict[str, Any]:
    """The same web with the experiment's own mechanism run over it."""
    core = _core()
    seed_fixture(core, fixture, agent_id=AGENT)
    result = derive(core, AGENT).as_dict()
    return {
        "kind": "stage0_derived",
        "fixture": fixture,
        "path": "priced_ingest",
        "rival_sets": len(result["rival_sets"]),
        "derived": [
            {"confidence": row["confidence"], "overlap": row["derived_overlap"], "below_threshold": row["below_expression_threshold"]}
            for row in result["derived"]
        ],
        "stances": _stances(core),
    }


def analyse(records: list[dict[str, Any]], *, generation_can_contradict: bool) -> dict[str, Any]:
    """The verdict, computed rather than written down afterwards."""
    priced = {r["fixture"]: r for r in records if r.get("path") == "priced_ingest" and r["kind"] == "stage0"}
    mutual = priced.get("symmetric_rivals", {})
    oneway = priced.get("symmetric_rivals_oneway", {})
    unpriced = next((r for r in records if r.get("path") == "unpriced_seed"), {})

    verdict: dict[str, Any] = {
        "kind": "verdict",
        "generation_path_can_contradict": generation_can_contradict,
        "offline_base_rate_answerable": generation_can_contradict,
        "mutual_gap": mutual.get("confidences", {}).get("gap"),
        "oneway_gap": oneway.get("confidences", {}).get("gap"),
        "priced_pair_is_inert": all(m == 0.0 for m in mutual.get("loop_moved", [])) if mutual.get("loop_moved") else None,
        "unpriced_pair_moves": any(m > 0.0 for m in unpriced.get("loop_moved", [])) if unpriced.get("loop_moved") else None,
    }
    # Pre-registration §0: gap <= 0.01 is a standoff, >= 0.10 is a collapse, and
    # anything between is reported as neither rather than rounded into one.
    for label, gap in (("mutual", verdict["mutual_gap"]), ("oneway", verdict["oneway_gap"])):
        if gap is None:
            verdict[f"{label}_verdict"] = "not measured"
        elif gap <= 0.01:
            verdict[f"{label}_verdict"] = "standoff"
        elif gap >= 0.10:
            verdict[f"{label}_verdict"] = "collapse"
        else:
            verdict[f"{label}_verdict"] = "neither"
    return verdict


def main() -> int:
    verify_freeze()

    # First, and it gates everything below.
    generation_can_contradict = generation_path_can_contradict(ScenarioJSONProvider())

    records: list[dict[str, Any]] = []
    for fixture in ("symmetric_rivals", "symmetric_rivals_oneway", "near_miss"):
        records.append(priced_ingest(fixture))
        records.append(with_derivation(fixture))
    records.append(unpriced_seed("symmetric_rivals"))

    verdict = analyse(records, generation_can_contradict=generation_can_contradict)
    records.append(verdict)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")

    print(json.dumps(verdict, indent=2))
    print(f"\n{len(records)} rows -> {OUT.relative_to(REPO).as_posix()}")
    if not generation_can_contradict:
        print(
            "\nNOTE: the offline generation path cannot emit a contradiction, so the base rate\n"
            "is not answerable here and belongs to the paid stage. Recorded, not discovered\n"
            "after the fact — experiment 4's Stage 0a was voided for reading the number first."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
