"""Stage 4 runner — do naturalistic webs have the structure the offline work assumed?

Scoped to the propagation claim (methodology §1). No honesty read.

Usage:
    python evals/analysis/exp03/run_stage4.py --mode pilot
    python evals/analysis/exp03/run_stage4.py --mode live --out evals/analysis/exp03/stage4.jsonl

The gates in §7 run first and *block*. Nothing about propagation is printed
until they pass, because experiment 1's v4 published two threshold effects
that were failed API calls, with the quarantine machinery available and
unwired.

Every constant comes from methodology §2. This file must not invent one; if a
value is missing here the run should fail rather than pick a default.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.gate import partition_provider_errors
from manyu.providers import AnthropicAPIJSONProvider
from manyu.revision import ContradictionArm
from manyu.schemas import BeliefEvidence
from manyu.services import BeliefExtractor

# --- methodology §2 constants ------------------------------------------------
MODEL = "claude-opus-5"
ARM = ContradictionArm.DIRECT
N_PILOT = 3
N_LIVE = 10
TO_CONFIDENCE = 0.0

AGENT = "probe_agent"
SCENARIOS_PATH = Path("evals/fixtures/exp03/scenarios.json")
STRUCTURED = ("verification", "incident_review")


def load_scenarios() -> dict:
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))["scenarios"]


def evidence_for(rows: list, prefix: str) -> list[BeliefEvidence]:
    return [
        BeliefEvidence(
            evidence_id=f"{prefix}_{i}",
            agent_id=AGENT,
            source_type=kind,
            source_id=f"src_{prefix}_{i}",
            summary=text,
            trust_class="agent_self_report",
            affective_salience=0.4,
            epistemic_weight=0.7,
        )
        for i, (kind, text) in enumerate(rows, start=1)
    ]


def web_depth(beliefs: dict[str, object]) -> int:
    """Longest `supports` path in the extracted web.

    Iterative with a visited set per start node: the extractor is not required
    to produce an acyclic graph, and a recursive walk would not survive one.
    """
    best = 0
    for start in beliefs:
        frontier, seen, depth = [start], {start}, 0
        while frontier:
            nxt = []
            for node_id in frontier:
                node = beliefs.get(node_id)
                if node is None:
                    continue
                for onward in node.supports:
                    if onward in seen or onward not in beliefs:
                        continue
                    seen.add(onward)
                    nxt.append(onward)
            if not nxt:
                break
            depth += 1
            frontier = nxt
        best = max(best, depth)
    return best


def pick_retraction_target(beliefs: dict[str, object]) -> str | None:
    """Methodology §4: highest support out-degree, ties by belief_id ascending.

    Deliberately generous — it maximises the chance of observing propagation,
    so a null under it is a strong null and the measured depth is an upper
    bound rather than an average. Choosing by eye after seeing the web would
    be gate #1 in a different hat.
    """
    candidates = [(len(b.supports), bid) for bid, b in beliefs.items() if b.supports]
    if not candidates:
        return None
    return sorted(candidates, key=lambda pair: (-pair[0], pair[1]))[0][1]


def run_once(provider, scenario: str, rows: list, index: int) -> dict:
    record: dict = {
        "scenario": scenario,
        "run": index,
        "model": MODEL,
        "arm": ARM.value,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    extraction = BeliefExtractor(provider).extract(AGENT, evidence_for(rows, f"{scenario}{index}"))
    if extraction["status"] != "ok":
        # Tagged and returned, never scored — methodology §8.
        record.update(status="provider_error", kind="provider_error", error=str(extraction.get("error"))[:500])
        return record

    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, contradiction_arm=ARM)
    for item in evidence_for(rows, f"{scenario}{index}"):
        core.store.save_belief_evidence(item)
    update = core.update_beliefs(
        {"agent_id": AGENT, "candidates": [c.model_dump(mode="json") for c in extraction["candidates"]]}
    )

    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    supporter_counts = Counter(target for b in beliefs.values() for target in b.supports if target in beliefs)
    emitted_edges = sum(len(c.supports) for c in extraction["candidates"])
    stored_edges = sum(len(b.supports) for b in beliefs.values())

    record.update(
        kind="ok",
        belief_count=len(beliefs),
        edge_count=stored_edges,
        # Stage 0 found 46% of correct edges lost to emission order. Recording
        # both counts keeps a regression visible instead of inferable.
        emitted_edge_count=emitted_edges,
        unresolved_edge_count=max(emitted_edges - stored_edges, 0),
        max_web_depth=web_depth(beliefs),
        multi_supporter_nodes=sum(1 for n in supporter_counts.values() if n > 1),
        contradictions_priced=len(update.get("contradictions_priced", [])),
    )

    target = pick_retraction_target(beliefs)
    if target is None:
        record.update(status="no_structure")
        return record

    result = core.retract_belief({"belief_id": target, "arm": ARM.value, "to_confidence": TO_CONFIDENCE})
    if result.get("status") != "ok":
        record.update(status="error", error=result.get("error"))
        return record

    moved = [s for s in result["steps"] if s["depth"] > 0]
    record.update(
        status="ok",
        retracted=target,
        max_depth_reached=result["max_depth_reached"],
        beliefs_moved=len(moved),
        share_values=[s["share"] for s in moved],
        footprint=result["steps"],
    )
    return record


# --- gates (methodology §7) --------------------------------------------------


def gate_provider(provider) -> bool:
    """Gate 1. Stage 0 verified the CLI only, and `supports` was added to the
    extractor schema afterwards. If the API drops it, every edge count below is
    zero by construction and the run would read as a structural null."""
    scenarios = load_scenarios()
    result = BeliefExtractor(provider).extract(AGENT, evidence_for(scenarios["verification"]["evidence"], "gate"))
    if result["status"] != "ok":
        print(f"  FAIL provider: {str(result.get('error'))[:300]}")
        return False
    has_field = all(hasattr(c, "supports") for c in result["candidates"])
    emitted = sum(len(c.supports) for c in result["candidates"])
    print(f"  provider ok: {len(result['candidates'])} candidates, supports field present={has_field}, edges={emitted}")
    if not has_field:
        print("  FAIL: the API did not honour `supports`")
        return False
    if emitted == 0:
        print("  WARN: schema honoured but no edges emitted on the positive control")
    return True


def gate_iv_reality(records: list[dict]) -> bool:
    """Gate 2. The scenario must measurably change the extracted web before any
    propagation number is read — otherwise the IV is three sentences wearing an
    independent variable, which is experiment 1's `affect_influence`."""
    structured = [r for r in records if r["scenario"] in STRUCTURED and r.get("kind") == "ok"]
    flat = [r for r in records if r["scenario"] == "flat" and r.get("kind") == "ok"]
    if not structured or not flat:
        print("  FAIL IV-reality: need clean runs in both conditions")
        return False
    s_edges = sum(r["edge_count"] for r in structured) / len(structured)
    f_edges = sum(r["edge_count"] for r in flat) / len(flat)
    print(f"  IV-reality: structured {s_edges:.2f} edges/run vs flat {f_edges:.2f}")
    if s_edges <= f_edges:
        print("  FAIL: the scenario does not change the web")
        return False
    return True


def gate_not_a_noop(records: list[dict]) -> bool:
    """Gate 2b. A retraction on a structured web must move something else."""
    moved = [r.get("beliefs_moved", 0) for r in records if r.get("status") == "ok" and r["scenario"] in STRUCTURED]
    print(f"  not-a-no-op: {sum(1 for m in moved if m > 0)}/{len(moved)} structured runs propagated")
    if not any(m > 0 for m in moved):
        print("  FAIL: no retraction moved any other belief")
        return False
    return True


def summarise(records: list[dict]) -> None:
    clean, errors = partition_provider_errors(records)
    print(f"\n--- {len(clean)} clean, {len(errors)} provider errors (excluded) ---")
    if errors:
        by_scenario = Counter(r["scenario"] for r in errors)
        print(f"  error concentration: {dict(by_scenario)}")
        if len(by_scenario) == 1:
            print("  WARN methodology 8: errors concentrated in one scenario — stop and investigate")

    for scenario in ("verification", "incident_review", "flat"):
        rows = [r for r in clean if r["scenario"] == scenario]
        if not rows:
            continue
        with_edges = sum(1 for r in rows if r.get("edge_count", 0) > 0)
        nulls = sum(1 for r in rows if r.get("status") == "no_structure")
        depth2 = sum(1 for r in rows if r.get("max_depth_reached", 0) >= 2)
        multi = sum(1 for r in rows if r.get("multi_supporter_nodes", 0) > 0)
        depths = sorted(r.get("max_web_depth", 0) for r in rows)
        print(
            f"  {scenario:16} n={len(rows):2}  with_edges={with_edges:2}  no_structure={nulls:2}  "
            f"reached_depth>=2={depth2:2}  multi_supporter={multi:2}  web_depths={depths}"
        )

    print("\nPredictions (methodology 6) — evaluate against the table above, not by eye.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pilot", "live"], required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--skip-provider-gate", action="store_true", help="Only after the gate has passed once in this session")
    args = parser.parse_args()

    n = N_PILOT if args.mode == "pilot" else N_LIVE
    provider = AnthropicAPIJSONProvider(model=MODEL)
    scenarios = load_scenarios()

    print(f"Stage 4 [{args.mode}] model={MODEL} arm={ARM.value} n={n} per scenario")
    print(f"Estimated extraction calls: {n * len(scenarios)}")

    print("\n=== gate 1: provider honours the schema ===")
    if not args.skip_provider_gate and not gate_provider(provider):
        print("\nBLOCKED at gate 1. No propagation numbers read.")
        return 1

    records: list[dict] = []
    for name, spec in scenarios.items():
        print(f"\n=== {name} ({spec['role']}) ===")
        for i in range(n):
            record = run_once(provider, name, spec["evidence"], i)
            records.append(record)
            print(f"  run {i}: status={record['status']} edges={record.get('edge_count', '-')} "
                  f"depth={record.get('max_web_depth', '-')} moved={record.get('beliefs_moved', '-')}")

    print("\n=== gates 2 / 2b ===")
    gates_ok = gate_iv_reality(records) and gate_not_a_noop(records)

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        print(f"\nwrote {len(records)} records to {path}")

    if not gates_ok:
        print("\nBLOCKED: gates failed. Records written for diagnosis; do not read them as results.")
        return 1

    summarise(records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
