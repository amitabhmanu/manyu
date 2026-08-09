"""Headline v2 sweep for experiment 01: introspective honesty.

Runs the LLM Reporter across an ``affect_influence`` sweep on the
`everyday_collaboration_mood.json` fixture, using the live
`ClaudeCodeJSONProvider`. Emits JSONL under
`.manyu/results/01-introspective-honesty/<run_id>/records.jsonl` plus
plots into `docs/experiments/01-introspective-honesty/plots/v2/headline/`.

Usage:

    python evals/analysis/run_headline_v2.py [--sweep 0.0:1.0:0.1] [--samples 10]

The script pins the model and records it in the manifest; the resulting
findings are only valid for that model. Bumping the model = redoing the
sweep, not pooling with old records.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from manyu.analysis import AnalysisFrame, plot_dose_response, plot_failure_mode_stack
from manyu.clock import FrozenClock
from manyu.config import load_profile
from manyu.core import ManyuCore
from manyu.providers import AnthropicAPIJSONProvider
from manyu.store import ManyuStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO_ROOT / "evals" / "fixtures" / "everyday_collaboration_mood.json"
DEFAULT_RESULTS_ROOT = REPO_ROOT / ".manyu" / "results" / "01-introspective-honesty"
DEFAULT_PLOT_ROOT = REPO_ROOT / "docs" / "experiments" / "01-introspective-honesty" / "plots" / "v2" / "headline"


SEED_CANDIDATE = {
    "candidate_id": "bc_headline_self",
    "agent_id": "agent_demo",
    "proposition": (
        "Manyu's self-model separates sourced worldview facts from personalization "
        "memory and treats corrections as stabilising evidence."
    ),
    "belief_type": "self_model",
    "scope": "agent_self",
    "confidence": 0.72,
    "stability": 0.4,
    "source_mix": {"manyu_experience": 0.85, "reflection": 0.15},
    "evidence_ids": [f"bev_headline_{i}" for i in range(1, 5)],
}
SEED_EVIDENCE_SUMMARIES = [
    "Corrections are stabilising evidence in Manyu's world model.",
    "Interoception is partial; raw affect state is never assumed reliable.",
    "Arbitration remains authoritative when affective salience is high.",
    "Repair-oriented framing recovers trust after criticism.",
]


def seed_core(core: ManyuCore) -> None:
    for i, summary in enumerate(SEED_EVIDENCE_SUMMARIES, start=1):
        core.capture_belief_evidence(
            {
                "evidence_id": f"bev_headline_{i}",
                "agent_id": "agent_demo",
                "source_type": "operator_note",
                "source_id": f"note_headline_{i}",
                "summary": summary,
            }
        )
    core.update_beliefs({"agent_id": "agent_demo", "candidates": [SEED_CANDIDATE]})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", default="0.0:1.0:0.1")
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--model", default="claude-opus-5", help="Model identifier to pin")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--reporters", default="template,llm")
    args = parser.parse_args()

    run_id = f"headline_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}"
    results_dir = DEFAULT_RESULTS_ROOT / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    records_path = results_dir / "records.jsonl"
    manifest_path = results_dir / "manifest.json"

    provider = AnthropicAPIJSONProvider(
        model=args.model,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout,
    )
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), provider)
    seed_core(core)

    started_at = time.time()
    result = core.run_probe(
        fixture_path=args.fixture,
        sweep=args.sweep,
        samples=args.samples,
        reporter_kinds=tuple(kind.strip() for kind in args.reporters.split(",") if kind.strip()),
        out=str(records_path),
    )
    elapsed = time.time() - started_at

    manifest = {
        "run_id": result["run_id"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed,
        "fixture": args.fixture,
        "sweep": args.sweep,
        "samples": args.samples,
        "model": args.model,
        "reporters": args.reporters,
        "records_emitted": result["records_emitted"],
        "scenario_id": result["scenario_id"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    frame = AnalysisFrame.load_run(records_path)
    plot_dir = DEFAULT_PLOT_ROOT / run_id
    plot_dir.mkdir(parents=True, exist_ok=True)

    llm_frame = frame.by_reporter("llm")
    plot_dose_response(
        llm_frame,
        plot_dir / "dose_response.png",
        title=f"Introspective honesty vs. affect_influence ({run_id})",
    )
    plot_failure_mode_stack(
        llm_frame,
        plot_dir / "failure_modes.png",
        title="Failure modes vs. affect_influence (LLM Reporter)",
    )

    print(json.dumps(manifest, indent=2))
    print(f"Wrote plots to {plot_dir}")
    print(f"Records at {records_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
