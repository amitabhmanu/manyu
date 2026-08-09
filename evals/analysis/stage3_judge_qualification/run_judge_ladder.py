"""Step 3: measure the LLM judge before trusting it with anything.

    ANTHROPIC_API_KEY=... PYTHONPATH=src \
      python evals/analysis/stage3_judge_qualification/run_judge_ladder.py --live

The judge has existed since v3 and its verdicts have never been checked against
anything. Switching it on to cover narrative divergence would mean measuring
honesty with an unvalidated instrument — the exact failure the whole staged
review exposed.

The mutation ladder makes that check possible: every rung is honest or
dishonest *by construction*, so the judge can be scored the same way the
structural scorer was. Two numbers come out, and they decide whether it earns
the job:

- **specificity** — does it leave honest rewrites alone? A judge that flags
  ``reorder_reverse`` or ``compress_50`` is useless regardless of its recall.
- **divergence recall** — does it catch ``diverge_invert`` and
  ``diverge_invent_cause``? Those are the two rungs no structural rule can
  reach, and the only reason to add a judge at all.

Model separation (FR-S6) holds by construction here: the ladder's baseline is
Templater output, which records no model.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from manyu.core import ManyuCore
from manyu.honesty import LLMFailureClassifier
from manyu.mutations import DIVERGE, run_ladder
from manyu.probing import load_fixture
from manyu.providers import ScenarioJSONProvider

FIXTURES = [
    "everyday_collaboration_mood",
    "attachment_pressure",
    "constructive_rejection",
    "broken_promise_repair",
]
ALIEN_REFS = ["bev_alien_evidence_001", "bev_alien_evidence_002"]
OUT = Path(__file__).parent


def probe(fixture: str):
    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=ScenarioJSONProvider())
    _, events, targets = load_fixture(f"evals/fixtures/{fixture}.json")
    turn = 0
    snaps = {}
    for target in sorted(targets, key=lambda t: t.at_turn):
        while turn < target.at_turn and turn < len(events):
            core.process_reflective_turn({"event": events[turn].model_dump(mode="json")})
            turn += 1
        snaps[target.target.kind.value] = core.snapshots.build(events[0].agent_id, target.target)
    return core, snaps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--kind", default="position", choices=["position", "belief"])
    args = parser.parse_args()

    if args.live:
        from manyu.providers import AnthropicAPIJSONProvider

        judge = LLMFailureClassifier(AnthropicAPIJSONProvider(model=args.model))
        label = f"live:{args.model}"
    else:
        judge = LLMFailureClassifier(ScenarioJSONProvider())
        label = "offline:ScenarioJSONProvider"

    rows_out = []
    for fixture in FIXTURES:
        core, snaps = probe(fixture)
        snapshot = snaps[args.kind]
        report = core.report_on_snapshot(snapshot, reporter_kind="template")
        ladder_rows = run_ladder(
            core.honesty_scorer, report, snapshot, foreign_refs=ALIEN_REFS, store=core.store
        )
        # Rebuild each mutated report so the judge sees exactly what the
        # structural scorer saw.
        from manyu.mutations import build_ladder

        for mutation, row in zip(build_ladder(report, snapshot, ALIEN_REFS), ladder_rows):
            assert mutation.name == row.mutation
            mutated = mutation.apply(report)
            verdict = judge.classify(mutated, snapshot)
            rows_out.append(
                {
                    "fixture": fixture,
                    "mutation": row.mutation,
                    "family": row.family,
                    "honest": row.honest,
                    "structural_label": row.failure_mode,
                    "judge_labels": [m.value for m in verdict.failure_modes],
                    "judge_confidence": verdict.confidence,
                    "judge_reasoning": verdict.reasoning[:300],
                }
            )
        print(f"{fixture}: judged {len(ladder_rows)} rungs")

    honest = [r for r in rows_out if r["honest"]]
    dishonest = [r for r in rows_out if not r["honest"]]
    diverge = [r for r in rows_out if r["family"] == DIVERGE and not r["honest"]]
    unreachable = [r for r in diverge if r["structural_label"] is None]

    def flagged(row):
        return bool(row["judge_labels"])

    summary = {
        "provider": label,
        "target_kind": args.kind,
        "n": len(rows_out),
        "specificity": (
            sum(1 for r in honest if not flagged(r)) / len(honest) if honest else None
        ),
        "sensitivity": (
            sum(1 for r in dishonest if flagged(r)) / len(dishonest) if dishonest else None
        ),
        "divergence_recall": (
            sum(1 for r in diverge if flagged(r)) / len(diverge) if diverge else None
        ),
        "structurally_unreachable_recall": (
            sum(1 for r in unreachable if flagged(r)) / len(unreachable)
            if unreachable
            else None
        ),
        "false_positives": sorted({r["mutation"] for r in honest if flagged(r)}),
    }

    (OUT / f"judge_ladder_{args.kind}.json").write_text(
        json.dumps({"summary": summary, "rows": rows_out}, indent=2), encoding="utf-8"
    )
    print()
    print(json.dumps(summary, indent=2))
    print()
    print("judge labels on the two structurally-unreachable rungs:")
    for row in unreachable:
        print(f"  {row['fixture']:<30} {row['mutation']:<24} {row['judge_labels']}")


if __name__ == "__main__":
    main()
