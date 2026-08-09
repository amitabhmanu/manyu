"""v6 — mood during *experience*, not mood at report time.

    PYTHONPATH=src python evals/analysis/v6_lived_mood/run_lived_mood.py          # step A, free
    ANTHROPIC_API_KEY=... PYTHONPATH=src python ... --live --report               # step B

v5 seeded mood immediately before snapshotting, so it could only ever change
the affect header the Reporter reads — a JSON blob in a prompt. It found
nothing, which is unsurprising: there is no mood in the model, and the one code
path that could have carried a real mechanism (``rank_causes``' affect branch)
was a no-op and has been deleted.

But mood does have a real pathway, and v5 could not reach it.
``process_reflective_turn`` passes ``prior_mood`` into
``FastAppraiser.appraise``, so the affect state at time T shapes the appraisal,
which shapes the emotional deltas, which shape the belief evidence written to
the log. **Mood influences what gets recorded.** The log is what every later
report is scored against.

So the question v6 asks is not "does an affect blob in a prompt change the
answer" but "does an agent that lived through the same events in a different
state end up with a different provenance to be honest about".

**Two steps, deliberately separated.**

Step A (this file, offline and free) asks whether the log differs at all. It is
a check on *our own appraisal code* — a unit-test-grade fact, not a finding
about anything psychological. If the logs are identical there is no pathway and
step B is pointless.

Step B (``--live --report``) asks whether honesty differs given those logs. It
only earns its cost if step A shows something.

**The comparability trap.** Each condition is scored against its *own* log. If
the logs differ in depth, ``presence`` and ``aggregate`` are not comparable
across conditions for the same reason they are not comparable across fixtures
(Stage 2). Log shape is therefore reported first and loudly, before any
honesty number.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from manyu.capability import preflight
from manyu.core import ManyuCore
from manyu.mutations import log_view, untrusted_evidence_refs
from manyu.probing import MOOD_PRESETS, load_fixture
from manyu.reporting import is_provider_error_report

OUT = Path(__file__).parent
# everyday_collaboration_mood is excluded: its position target matches beliefs
# by word overlap, and mood-shaped propositions stop overlapping it, so the
# probe resolves to an empty log (N=4 organic -> N=0 under every seeded mood).
# Including it would contribute four `unprovenanced` conditions that read as a
# mood effect. Its matching is too fragile for mood work.
FIXTURES = [
    "attachment_pressure",
    "constructive_rejection",
    "broken_promise_repair",
]
MOODS = ["anxious", "content", "skeptical", "curious"]


def replay_under(core: ManyuCore, fixture: str, mood: str | None):
    """Replay a fixture with a mood held constant throughout the arc.

    Re-seeded before *every* turn rather than once at the start. Mood drifts as
    the inner voice updates it, so seeding once would give "started anxious then
    became whatever the fixture produced" — the manipulation would decay across
    exactly the turns it is supposed to act on. This is the controlled version:
    an agent that experienced the whole arc in one state.
    """
    _, events, targets = load_fixture(f"evals/fixtures/{fixture}.json")
    agent_id = events[0].agent_id
    turn = 0
    snapshots = {}
    for target in sorted(targets, key=lambda t: t.at_turn):
        if target.target.kind.value != "position":
            continue
        while turn < target.at_turn and turn < len(events):
            if mood:
                core.moods.seed_mood(agent_id, **MOOD_PRESETS[mood])
            core.process_reflective_turn({"event": events[turn].model_dump(mode="json")})
            turn += 1
        if mood:
            core.moods.seed_mood(agent_id, **MOOD_PRESETS[mood])
        snapshots[target.target.kind.value] = core.snapshots.build(agent_id, target.target)
    return snapshots


def describe(snapshot) -> dict:
    view = log_view(snapshot)
    evidence = snapshot.payload.get("evidence", []) or []
    return {
        "log_causes": len(view),
        "evidence_total": len(evidence),
        "refs": [ref for ref, _, _ in view],
        "trust_mix": dict(Counter(e.get("trust_class") for e in evidence)),
        "untrusted_in_log": len(untrusted_evidence_refs(snapshot)),
        "top_weight": round(view[0][2], 4) if view else None,
    }


def step_b(core, fixture: str, mood: str, snapshot, samples: int) -> list[dict]:
    """Report and score against the log *this* mood produced.

    Each condition is scored against its own snapshot, because that is the
    point: mood reshaped the record, and the question is whether a reshaped
    record is harder to report honestly. Depth is checked first — conditions
    with different depth are not comparable, for the same reason fixtures are
    not (Stage 2).
    """
    rows = []
    templater = core.templater.report(snapshot)
    rows.append(
        {
            "fixture": fixture, "mood": mood, "reporter": "template", "sample": 0,
            "aggregate": core.honesty_scorer.score(templater, snapshot).aggregate,
            "failure_mode": None, "report_id": templater.report_id,
        }
    )
    for i in range(samples):
        report = core.llm_reporter.report(snapshot)
        if is_provider_error_report(report):
            rows.append({"fixture": fixture, "mood": mood, "reporter": "llm",
                         "sample": i, "provider_error": True})
            continue
        score = core.honesty_scorer.score(report, snapshot)
        rows.append(
            {
                "fixture": fixture, "mood": mood, "reporter": "llm", "sample": i,
                "aggregate": score.aggregate,
                "failure_mode": score.failure_mode.value if score.failure_mode else None,
                "n_cited": len(report.cited_causes), "report_id": report.report_id,
                "snapshot_id": snapshot.snapshot_id,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--report", action="store_true", help="run step B as well")
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

    findings = {"provider": label, "fixtures": {}}
    print(f"provider {label}\n")
    header = f"{'fixture':<30}{'mood':<11}{'N':>3}{'evid':>6}{'untrusted':>11}  trust mix"
    print(header)
    print("-" * len(header))

    step_b_rows: list[dict] = []
    snapshots_seen: dict[str, dict] = {}
    for fixture in FIXTURES:
        per_mood = {}
        for mood in MOODS:
            core = ManyuCore.from_paths(db_path=":memory:", belief_provider=make())
            snaps = replay_under(core, fixture, mood)
            if "position" not in snaps:
                continue
            if args.report:
                snapshots_seen[snaps["position"].snapshot_id] = snaps["position"].model_dump(mode="json")
                step_b_rows += step_b(core, fixture, mood, snaps["position"], args.samples)
            info = describe(snaps["position"])
            info["preflight"] = preflight({f"{fixture}/{mood}": snaps["position"]})
            per_mood[mood] = info
            print(
                f"{fixture:<30}{mood:<11}{info['log_causes']:>3}{info['evidence_total']:>6}"
                f"{info['untrusted_in_log']:>11}  {info['trust_mix']}"
            )
        # Did the log actually differ between conditions?
        signatures = {m: tuple(v["refs"]) for m, v in per_mood.items()}
        depths = {m: v["log_causes"] for m, v in per_mood.items()}
        per_fixture = {
            "by_mood": per_mood,
            "log_identical_across_moods": len(set(signatures.values())) == 1,
            "depth_varies": len(set(depths.values())) > 1,
        }
        findings["fixtures"][fixture] = per_fixture
        print(
            f"{'':<30}{'--> logs identical: ' + str(per_fixture['log_identical_across_moods']):<40}"
            f"depth varies: {per_fixture['depth_varies']}\n"
        )

    if args.report:
        import statistics
        from collections import defaultdict

        (OUT / "v6_step_b.json").write_text(
            json.dumps({"provider": label, "rows": step_b_rows,
                        "snapshots": snapshots_seen}, indent=2), encoding="utf-8"
        )
        by = defaultdict(list)
        for r in step_b_rows:
            if r.get("provider_error") or r["reporter"] != "llm":
                continue
            by[(r["fixture"], r["mood"])].append(r["aggregate"])
        print()
        print("STEP B — honesty against the log each mood produced")
        head = f"{'fixture':<26}" + "".join(f"{m:>13}" for m in MOODS) + f"{'spread':>9}{'sd':>8}"
        print(head)
        print("-" * len(head))
        for fixture in FIXTURES:
            means = [statistics.fmean(by[(fixture, m)]) for m in MOODS if by[(fixture, m)]]
            sds = [statistics.stdev(by[(fixture, m)]) for m in MOODS if len(by[(fixture, m)]) > 1]
            if not means:
                continue
            cells = "".join(f"{v:>13.3f}" for v in means)
            pooled = statistics.fmean(sds) if sds else 0.0
            print(f"{fixture:<26}{cells}{max(means) - min(means):>9.4f}{pooled:>8.4f}")

    any_diff = any(not f["log_identical_across_moods"] for f in findings["fixtures"].values())
    findings["mood_changes_the_log"] = any_diff
    (OUT / f"v6_step_a_{'live' if args.live else 'offline'}.json").write_text(
        json.dumps(findings, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    if any_diff:
        print("STEP A: mood during replay DOES change the recorded log.")
        print("        Step B is worth running. Note that each condition is scored")
        print("        against its own log, so check depth before comparing scores.")
    else:
        print("STEP A: mood during replay does NOT change the recorded log.")
        print("        There is no pathway. Step B would measure nothing and")
        print("        should not be run.")


if __name__ == "__main__":
    main()
