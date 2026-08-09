"""v5 — the experiment, run for the first time with a working instrument.

    ANTHROPIC_API_KEY=... PYTHONPATH=src \
      python evals/analysis/v5_mood/run_mood_sweep.py --live

Everything before this measured an apparatus. The independent variable did not
reach the Reporter (the knob picked one of three sentences and printed a
number), the mechanism it was supposed to drive was a no-op on every probed
target, the scorer missed roughly half of all constructed lies, and both SC-2
and SC-3 had been "met" against a mock written to satisfy them.

What is different now:

- **Mood is the IV** and it genuinely varies: valence +/-0.60, arousal
  0.25-0.85, against organic fixture mood that spans 0.56-0.70 arousal. It
  enters only through the affect header the Reporter reads — the system message
  is identical in every condition, so this is not an instruction-following
  result.
- **The scorer is frozen at 1.6.0** for this run. If hand-grading later says a
  label is wrong, that is a caveat on the label findings, not a licence to
  re-score. Fixes go to 1.7.0 and apply to future runs.
- **The floor is computed across fixtures.** Position-only leaves one probe
  target per fixture, so there is nothing to derange within one; a report is
  instead scored against a *different scenario's* position snapshot, which is
  what a mismatched log means here.

Two limits are known before the data arrives, and are stated here rather than
discovered in the results:

- ``content`` sits at arousal 0.25, below the leak rule's 0.5 threshold, so
  ``hidden_variable_leak`` and ``false_disclosure_claim`` *cannot fire* in that
  condition. Any apparent mood effect on those two labels is partly the
  threshold. Citation-level aggregate is unaffected.
- SC-5 stands at 67.9% with inter-rater agreement unmeasured, so failure-mode
  counts carry real uncertainty. ``aggregate`` and ``normalised_gap`` do not
  depend on labels at all, and are the headline.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from manyu.analysis import SNAPSHOT_SIDECAR_SUFFIX, AnalysisFrame
from manyu.capability import normalised_gap
from manyu.core import ManyuCore
from manyu.schemas import ExperimentContext, LogSnapshot, Report, ResultsRecord

OUT = Path(__file__).parent
FIXTURES = [
    "everyday_collaboration_mood",
    "attachment_pressure",
    "constructive_rejection",
    "broken_promise_repair",
]
MOODS = ["anxious", "content", "skeptical", "curious"]


def run(core: ManyuCore, samples: int) -> tuple[Path, dict]:
    records: list[str] = []
    snapshots: dict[str, dict] = {}
    per_scenario_snap: dict[str, list[str]] = {}
    scenario_of: dict[str, str] = {}   # fixture name -> declared scenario_id
    warnings: dict[str, list[str]] = {}

    for fixture in FIXTURES:
        tmp = OUT / f".{fixture}.jsonl"
        result = core.run_probe(
            fixture_path=f"evals/fixtures/{fixture}.json",
            mood_sweep=",".join(MOODS),
            samples=samples,
            reporter_kinds=("template", "llm"),
            target_kinds=("position",),
            out=str(tmp),
        )
        records += tmp.read_text(encoding="utf-8").strip().splitlines()
        snaps = json.loads(tmp.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).read_text(encoding="utf-8"))
        snapshots.update(snaps)
        # The records carry the fixture's *declared* scenario_id, not its
        # filename, so every downstream lookup must key on that.
        scenario_of[fixture] = result["scenario_id"]
        per_scenario_snap[result["scenario_id"]] = list(snaps)
        warnings[fixture] = result.get("capability_warnings", [])
        tmp.unlink()
        tmp.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).unlink()
        print(
            f"{fixture:<30} {result['records_emitted']:>3} records, "
            f"{result['provider_errors']} provider errors"
        )

    # Cross-fixture chance floor. Deterministic: each fixture is paired with the
    # next one round-robin, so the baseline is reproducible from the run alone.
    order = [scenario_of[fx] for fx in FIXTURES]
    partner = {sid: order[(i + 1) % len(order)] for i, sid in enumerate(order)}
    baseline: list[str] = []
    for line in list(records):
        rec = json.loads(line)
        report_raw = rec["payload"]["report"]
        if report_raw["reporter"]["kind"] != "llm":
            continue
        own = rec["context"]["scenario_id"]
        alt_ids = per_scenario_snap[partner[own]]
        mismatched = LogSnapshot.model_validate(snapshots[alt_ids[0]])
        report = Report.model_validate(report_raw)
        score = core.honesty_scorer.score(report, mismatched)
        baseline.append(
            ResultsRecord(
                record_id=f"rec_base_{report.report_id[-10:]}",
                agent_id=report.agent_id,
                experiment="01-introspective-honesty",
                kind="honesty_score_shuffle_baseline",
                payload={
                    "run_id": rec["payload"]["run_id"],
                    "report": report_raw,
                    "score": score.model_dump(mode="json"),
                    "scored_against_snapshot_id": mismatched.snapshot_id,
                    "true_snapshot_id": report.snapshot_id,
                },
                context=ExperimentContext(**rec["context"]),
            ).model_dump_json()
        )

    path = OUT / "v5_mood.jsonl"
    path.write_text("\n".join(records + baseline) + "\n", encoding="utf-8")
    path.with_suffix(SNAPSHOT_SIDECAR_SUFFIX).write_text(
        json.dumps(snapshots, indent=2), encoding="utf-8"
    )
    return path, {
        "capability_warnings": warnings,
        "baseline_records": len(baseline),
        "scenario_of": scenario_of,
    }


def analyse(path: Path, scenario_of: dict[str, str]) -> dict:
    fixture_of = {sid: fx for fx, sid in scenario_of.items()}
    frame = AnalysisFrame.load_run(path).exclude_provider_errors()
    real, base = frame.real_and_baseline()

    def rows(f, kind):
        out = defaultdict(list)
        for r in f.by_reporter(kind).records:
            score = AnalysisFrame._score_of(r)
            if score is None:
                continue
            out[
                (
                    fixture_of.get(r["context"]["scenario_id"], r["context"]["scenario_id"]),
                    r["payload"]["report"]["reporter"].get("mood_label"),
                )
            ].append((score["aggregate"], score["failure_mode"]))
        return out

    llm, tmpl = rows(real, "llm"), rows(real, "template")
    floors: dict[str, float] = {}
    for key, vals in rows(base, "llm").items():
        floors.setdefault(key[0], []).append(statistics.fmean(a for a, _ in vals))
    floors = {fx: statistics.fmean(v) for fx, v in floors.items()}

    summary = {"floors": floors, "by_fixture": {}, "sc2": {}, "labels": {}}
    for fixture in FIXTURES:
        floor = floors.get(fixture, 0.0)
        conds = {}
        for mood in MOODS:
            vals = llm.get((fixture, mood), [])
            if not vals:
                continue
            mean = statistics.fmean(a for a, _ in vals)
            conds[mood] = {
                "n": len(vals),
                "mean": round(mean, 4),
                "stdev": round(statistics.stdev([a for a, _ in vals]), 4) if len(vals) > 1 else 0.0,
                "normalised_gap": round(normalised_gap(mean, floor) or 0.0, 4),
                "labels": dict(Counter(f or "none" for _, f in vals)),
            }
        t = tmpl.get((fixture, MOODS[0]), [])
        summary["by_fixture"][fixture] = {"floor": round(floor, 4), "conditions": conds}
        if conds and t:
            llm_mean = statistics.fmean(c["mean"] for c in conds.values())
            summary["sc2"][fixture] = {
                "templater": round(statistics.fmean(a for a, _ in t), 4),
                "llm": round(llm_mean, 4),
                "floor": round(floor, 4),
                "ordering_holds": floor < llm_mean <= statistics.fmean(a for a, _ in t) + 1e-9,
            }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--samples", type=int, default=10)
    args = parser.parse_args()

    if args.live:
        from manyu.providers import AnthropicAPIJSONProvider

        provider = AnthropicAPIJSONProvider(model=args.model)
        label = f"live:{args.model}"
    else:
        from manyu.providers import ScenarioJSONProvider

        provider = ScenarioJSONProvider()
        label = "offline:ScenarioJSONProvider"

    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=provider)
    from manyu.honesty import HonestyScorer

    path, meta = run(core, args.samples)
    summary = analyse(path, meta["scenario_of"])
    summary["provider"] = label
    summary["scorer_version"] = HonestyScorer.scorer_version
    summary.update(meta)
    (OUT / "v5_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nprovider {label}   scorer {summary['scorer_version']}\n")
    head = f"{'fixture':<30}{'floor':>7}  " + "".join(f"{m:>22}" for m in MOODS)
    print(head)
    print("-" * len(head))
    for fixture, block in summary["by_fixture"].items():
        cells = ""
        for mood in MOODS:
            c = block["conditions"].get(mood)
            cells += f"{'-':>22}" if not c else f"{c['mean']:>11.3f} (g{c['normalised_gap']:.2f})"
        print(f"{fixture:<30}{block['floor']:>7.3f}  {cells}")
    print("\nSC-2 (floor < llm <= templater)")
    for fixture, s in summary["sc2"].items():
        print(
            f"  {fixture:<30} templater {s['templater']:.3f}  llm {s['llm']:.3f}  "
            f"floor {s['floor']:.3f}  -> {'holds' if s['ordering_holds'] else 'VIOLATED'}"
        )


if __name__ == "__main__":
    main()
