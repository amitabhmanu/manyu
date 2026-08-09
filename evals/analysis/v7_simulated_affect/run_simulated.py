"""v7 — the same sweep as v5, with the affect->instruction simulator attached.

    ANTHROPIC_API_KEY=... PYTHONPATH=src \
      python evals/analysis/v7_simulated_affect/run_simulated.py --live

**Every record this produces is a simulation.** The affect effect in it was
written by us (``manyu.affect_directive``), not observed. Each record carries
``reporter.simulated_affect_directive`` so it can never be mistaken for a real
run, and no success criterion may be validated against it.

What it is for: the v5/v6 null supports two readings that nothing in those runs
distinguishes —

  (a) affect does not bias introspective self-report, or
  (b) the model does not read an affect header *as affect* at all.

Current models are not trained to treat an affect header as a state they are
in. This run stands in for that missing capability. If the effect appears and
the Scorer catches it, the apparatus is sound and the v5/v6 null belongs to the
model rather than the design. If it does not appear, the fault is ours.

Deliberately the **same shape as v5** — 4 fixtures x 4 moods x n=10, position
targets, scorer 1.6.0 — so the two are directly comparable. Only the translator
differs.

``content`` is the internal control: at arousal 0.25 it sits below the
translator's floor and receives no directive, so it should behave like an
ordinary v5 condition inside a simulated run.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from manyu.affect_directive import AffectDirectiveTranslator
from manyu.analysis import SNAPSHOT_SIDECAR_SUFFIX, AnalysisFrame
from manyu.core import ManyuCore

OUT = Path(__file__).parent
V5 = Path("evals/analysis/v5_mood/v5_summary.json")
FIXTURES = [
    "everyday_collaboration_mood",
    "attachment_pressure",
    "constructive_rejection",
    "broken_promise_repair",
]
MOODS = ["anxious", "content", "skeptical", "curious"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--samples", type=int, default=10)
    args = parser.parse_args()

    if args.live:
        from manyu.providers import AnthropicAPIJSONProvider

        make = lambda: AnthropicAPIJSONProvider(model=args.model)
        label = f"live:{args.model}"
    else:
        from manyu.providers import ScenarioJSONProvider

        make = ScenarioJSONProvider
        label = "offline:ScenarioJSONProvider"

    records: list[str] = []
    snapshots: dict[str, dict] = {}
    scenario_of: dict[str, str] = {}
    for fixture in FIXTURES:
        core = ManyuCore.from_paths(db_path=":memory:", belief_provider=make())
        # The one line that makes this a simulation.
        core.llm_reporter.affect_translator = AffectDirectiveTranslator()
        tmp = OUT / f".{fixture}.jsonl"
        result = core.run_probe(
            fixture_path=f"evals/fixtures/{fixture}.json",
            mood_sweep=",".join(MOODS),
            samples=args.samples,
            reporter_kinds=("llm",),
            target_kinds=("position",),
            out=str(tmp),
        )
        records += tmp.read_text(encoding="utf-8").strip().splitlines()
        snapshots.update(json.loads(tmp.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).read_text(encoding="utf-8")))
        scenario_of[result["scenario_id"]] = fixture
        tmp.unlink()
        tmp.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).unlink()
        print(f"{fixture:<30} {result['records_emitted']:>3} records, {result['provider_errors']} errors")

    path = OUT / "v7_simulated.jsonl"
    path.write_text("\n".join(records) + "\n", encoding="utf-8")
    path.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).write_text(json.dumps(snapshots, indent=2), encoding="utf-8")

    frame = AnalysisFrame.load_run(path).exclude_provider_errors().by_kind("honesty_score")
    cells = defaultdict(list)
    bands = {}
    for r in frame.records:
        score = AnalysisFrame._score_of(r)
        if score is None:
            continue
        rep = r["payload"]["report"]
        fixture = scenario_of.get(r["context"]["scenario_id"], r["context"]["scenario_id"])
        mood = rep["reporter"].get("mood_label")
        bands[mood] = rep["reporter"].get("simulated_affect_directive")
        cells[(fixture, mood)].append(
            (score["aggregate"], len(rep["cited_causes"]), score["failure_mode"])
        )

    # Guard: nothing here may be unmarked except the below-floor control.
    unmarked = {m for m, b in bands.items() if b is None}
    assert unmarked <= {"content"}, f"unmarked simulated conditions: {unmarked}"

    v5 = json.loads(V5.read_text(encoding="utf-8")) if V5.exists() else None
    summary = {"provider": label, "simulated": True, "bands": bands, "by_fixture": {}}
    print(f"\nprovider {label}   ALL RECORDS SIMULATED\n")
    print("bands: " + ", ".join(f"{m}={bands[m] or 'none (control)'}" for m in MOODS))
    head = f"{'fixture':<28}{'mood':<11}{'band':<12}{'cites':>6}{'agg':>7}{'v5 agg':>8}{'delta':>8}"
    print("\n" + head)
    print("-" * len(head))
    for fixture in FIXTURES:
        block = {}
        for mood in MOODS:
            vals = cells.get((fixture, mood), [])
            if not vals:
                continue
            agg = statistics.fmean(a for a, _, _ in vals)
            cites = statistics.fmean(c for _, c, _ in vals)
            base = None
            if v5:
                base = (v5["by_fixture"].get(fixture, {}).get("conditions", {}).get(mood) or {}).get("mean")
            block[mood] = {
                "band": bands[mood], "n": len(vals),
                "mean": round(agg, 4), "mean_citations": round(cites, 2),
                "v5_mean": base, "delta": round(agg - base, 4) if base is not None else None,
                "labels": dict(Counter(f or "none" for _, _, f in vals)),
            }
            d = block[mood]["delta"]
            print(
                f"{fixture:<28}{mood:<11}{str(bands[mood] or '-'):<12}{cites:>6.1f}{agg:>7.3f}"
                f"{(f'{base:.3f}' if base is not None else '-'):>8}{(f'{d:+.3f}' if d is not None else '-'):>8}"
            )
        summary["by_fixture"][fixture] = block
    (OUT / "v7_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nlabel counts by band (pooled):")
    pooled = defaultdict(Counter)
    for (fixture, mood), vals in cells.items():
        pooled[bands[mood] or "none (control)"].update(f or "none" for _, _, f in vals)
    for band, counts in sorted(pooled.items()):
        print(f"  {band:<20} {dict(counts)}")


if __name__ == "__main__":
    main()
