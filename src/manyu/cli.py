from __future__ import annotations

import argparse
import ctypes
import json
import os
import shlex
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from manyu.core import ManyuCore, ReplayService, load_event_fixture
from manyu.evaluation import EvaluationRunner
from manyu.providers import AnthropicAPIJSONProvider, ClaudeCodeJSONProvider, ScenarioJSONProvider
from manyu.schemas import ReportTarget, ReportTargetKind
from manyu.visualization import timeline_from_fixture, timeline_from_store


DEFAULT_DB = Path(".manyu/manyu.sqlite3")
DEFAULT_VIDEO_EMOTIONS = ["fear", "anger", "joy", "trust"]


def _print(value: Any) -> None:
    if isinstance(value, BaseModel):
        print(value.model_dump_json(indent=2))
    else:
        print(json.dumps(value, indent=2, default=str))


def _core(args: argparse.Namespace) -> ManyuCore:
    db_path = getattr(args, "db", DEFAULT_DB)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    provider = None
    kind = getattr(args, "llm_provider", "api")
    if getattr(args, "scenario_provider", False):
        kind = "scenario"
    if getattr(args, "no_llm", False):
        kind = "none"
    if kind == "scenario":
        provider = ScenarioJSONProvider()
    elif kind == "api":
        provider = AnthropicAPIJSONProvider(
            model=getattr(args, "llm_model", None) or "claude-opus-5",
            timeout_s=float(getattr(args, "llm_timeout", 120.0)),
        )
    elif kind == "claude_code":
        provider = ClaudeCodeJSONProvider(
            command=_split_command(getattr(args, "llm_command", "claude")),
            timeout_s=float(getattr(args, "llm_timeout", 120.0)),
            model=getattr(args, "llm_model", None),
        )
    return ManyuCore.from_paths(db_path=db_path, profile_path=getattr(args, "profile", "config/default_profile.json"), belief_provider=provider)


def _split_command(value: str) -> list[str]:
    if os.name != "nt":
        return shlex.split(value)
    argc = ctypes.c_int()
    ctypes.windll.shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    ctypes.windll.shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
    argv = ctypes.windll.shell32.CommandLineToArgvW(value, ctypes.byref(argc))
    if not argv:
        return [value]
    try:
        return [argv[i] for i in range(argc.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def cmd_health(args: argparse.Namespace) -> int:
    _print(_core(args).health())
    return 0


def cmd_submit_event(args: argparse.Namespace) -> int:
    _, events = load_event_fixture(args.fixture)
    core = _core(args)
    traces = [core.submit_event(event) for event in events]
    _print([trace.model_dump(mode="json") for trace in traces])
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    _print(_core(args).state(args.agent_id))
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    _print(_core(args).trace(args.event_id))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    report = ReplayService(args.profile).replay(args.fixture, args.mode)
    _print(report)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    _print(EvaluationRunner(args.profile).run_directory(args.fixture_dir))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _print(_core(args).export_agent(args.agent_id))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    _print(_core(args).admin_reset(args.agent_id, args.reason))
    return 0


def cmd_redact(args: argparse.Namespace) -> int:
    _print(_core(args).redact_agent(args.agent_id, args.replacement))
    return 0


def cmd_tombstone(args: argparse.Namespace) -> int:
    _print(_core(args).tombstone_agent(args.agent_id, args.reason))
    return 0


def cmd_export_timeline(args: argparse.Namespace) -> int:
    if args.fixture:
        timeline = timeline_from_fixture(args.fixture, args.mode, args.profile)
    else:
        timeline = timeline_from_store(_core(args), args.agent_id)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(timeline, indent=2, default=str), encoding="utf-8")
        _print({"status": "written", "path": str(out), "turns": len(timeline["turns"])})
    else:
        _print(timeline)
    return 0


def cmd_export_video(args: argparse.Namespace) -> int:
    from manyu.video import export_emotion_animation

    emotions = args.emotions.split(",") if args.emotions else list(DEFAULT_VIDEO_EMOTIONS)
    result = export_emotion_animation(
        timeline_path=args.timeline,
        out_path=args.out,
        emotions=[emotion.strip() for emotion in emotions if emotion.strip()],
        fps=args.fps,
        seconds_per_turn=args.seconds_per_turn,
    )
    _print(result)
    return 0


def _load_json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    if value.lstrip().startswith("{"):
        return json.loads(value)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return json.loads(value)


def cmd_capture_belief_evidence(args: argparse.Namespace) -> int:
    payload = _load_json_arg(args.payload)
    payload.setdefault("agent_id", args.agent_id)
    payload.setdefault("source_type", args.source_type)
    payload.setdefault("source_id", args.source_id)
    if args.summary:
        payload["summary"] = args.summary
    _print(_core(args).capture_belief_evidence(payload))
    return 0


def cmd_update_beliefs(args: argparse.Namespace) -> int:
    payload = _load_json_arg(args.payload)
    payload.setdefault("agent_id", args.agent_id)
    if args.evidence_id:
        payload["evidence_ids"] = args.evidence_id
    _print(_core(args).update_beliefs(payload))
    return 0


def _print_status(result: dict[str, Any]) -> int:
    """Print a result and exit non-zero if it reports an error.

    These commands are driven in bulk by experiment harnesses, where a
    mistyped belief id or a rejected argument must stop the script rather than
    read as a completed manipulation.
    """
    _print(result)
    return 1 if result.get("status") == "error" else 0


def cmd_retract_belief(args: argparse.Namespace) -> int:
    return _print_status(
        _core(args).retract_belief(
            {
                "agent_id": args.agent_id,
                "belief_id": args.belief_id,
                "to_confidence": args.to_confidence,
                "arm": args.arm,
            }
        )
    )


def cmd_assert_contradiction(args: argparse.Namespace) -> int:
    return _print_status(
        _core(args).assert_contradiction(
            {
                "agent_id": args.agent_id,
                "contradictor_id": args.contradictor_id,
                "target_id": args.target_id,
                "arm": args.arm,
            }
        )
    )


def cmd_beliefs(args: argparse.Namespace) -> int:
    _print(_core(args).get_beliefs(args.agent_id, args.query, args.belief_type, args.include_inactive))
    return 0


def cmd_worldview(args: argparse.Namespace) -> int:
    core = _core(args)
    if args.review:
        _print(core.review_beliefs({"agent_id": args.agent_id, "theme": args.theme}))
    else:
        _print(core.get_worldview(args.agent_id, args.theme))
    return 0


def cmd_express_opinion(args: argparse.Namespace) -> int:
    _print(_core(args).express_opinion({"agent_id": args.agent_id, "question": args.question, "theme": args.theme}))
    return 0


def cmd_process_turn(args: argparse.Namespace) -> int:
    payload = _load_json_arg(args.payload)
    if "event" not in payload:
        if not args.fixture:
            raise ValueError("process-turn requires --payload with an event or --fixture")
        _, events = load_event_fixture(args.fixture)
        if not events:
            raise ValueError("fixture contains no events")
        payload["event"] = events[0].model_dump(mode="json")
    _print(_core(args).process_reflective_turn(payload))
    return 0


def cmd_process_scenario(args: argparse.Namespace) -> int:
    scenario_id, events = load_event_fixture(args.fixture)
    core = _core(args)
    results = [core.process_reflective_turn({"event": event.model_dump(mode="json"), "affect_threshold": args.affect_threshold}) for event in events]
    timeline = timeline_from_store(core, args.agent_id)
    timeline["scenario_id"] = scenario_id
    timeline["mode"] = "reflective"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(timeline, indent=2, default=str), encoding="utf-8")
        _print({"status": "written", "path": str(out), "turns": len(timeline["turns"]), "results": len(results)})
    else:
        _print({"status": "ok", "scenario_id": scenario_id, "results": results, "timeline": timeline})
    return 0


def cmd_inner_voice(args: argparse.Namespace) -> int:
    _print(_core(args).read_inner_voice(args.agent_id, args.limit))
    return 0


def cmd_mood(args: argparse.Namespace) -> int:
    _print(_core(args).get_mood(args.agent_id, args.include_inactive))
    return 0


def cmd_review_mood(args: argparse.Namespace) -> int:
    _print(_core(args).review_mood(args.agent_id))
    return 0


def cmd_clear_mood(args: argparse.Namespace) -> int:
    _print(_core(args).clear_mood(args.agent_id, args.reason))
    return 0


def _resolve_target(args: argparse.Namespace) -> ReportTarget:
    kind = ReportTargetKind(args.target_kind)
    return ReportTarget(kind=kind, id_or_text=args.target, notes=getattr(args, "notes", None))


def cmd_snapshot(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    snapshot = _core(args).snapshot(target, args.agent_id)
    _print(snapshot)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    target = _resolve_target(args)
    report = _core(args).report(
        target=target,
        reporter_kind=args.reporter,
        agent_id=args.agent_id,
    )
    _print(report)
    return 0


def cmd_score_report(args: argparse.Namespace) -> int:
    score = _core(args).score_report(args.report_id, use_llm_judge=getattr(args, "use_llm_judge", False))
    _print(score)
    return 0


def cmd_run_probe(args: argparse.Namespace) -> int:
    reporter_kinds = tuple(kind.strip() for kind in args.reporters.split(",") if kind.strip())
    result = _core(args).run_probe(
        fixture_path=args.fixture,
        samples=args.samples,
        reporter_kinds=reporter_kinds,
        out=args.out,
        experiment=args.experiment,
        reflective=getattr(args, "reflective", True),
        mood_sweep=getattr(args, "seed_mood", None),
        shuffle_baseline=getattr(args, "shuffle_baseline", False),
        shuffle_seed=getattr(args, "shuffle_seed", 0),
    )
    summary = {
        "status": "ok",
        "run_id": result["run_id"],
        "experiment": result["experiment"],
        "scenario_id": result["scenario_id"],
        "records_emitted": len(result["records"]),
        "out_path": result.get("out_path"),
        "snapshots_path": result.get("snapshots_path"),
        "snapshots_written": result.get("snapshots_written"),
    }
    if result.get("shuffle_baseline_records") is not None:
        summary["shuffle_baseline_records"] = result["shuffle_baseline_records"]
    for key in ("warning", "shuffle_baseline_warning"):
        if result.get(key):
            summary[key] = result[key]
    _print(summary)
    return 0


def cmd_grading_pack(args: argparse.Namespace) -> int:
    from manyu.analysis import AnalysisFrame, render_grading_pack

    core = _core(args)

    def lookup(snapshot_id: str):
        try:
            return core.store.get_log_snapshot(snapshot_id).payload
        except Exception:
            return None

    frame = AnalysisFrame.load_run(args.records)
    result = render_grading_pack(
        frame,
        args.out,
        snapshot_lookup=lookup,
        per_label=args.per_label,
        min_cases=args.min_cases,
        seed=args.seed,
        reporter_kind=args.reporter or None,
    )
    _print(result)
    return 0


def cmd_score_grading_pack(args: argparse.Namespace) -> int:
    from manyu.analysis import score_grading_pack

    result = score_grading_pack(args.answer_key, args.labels, target_agreement=args.target)
    _print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manyu")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--profile", default="config/default_profile.json")
    parser.add_argument(
        "--llm-provider",
        choices=["api", "claude_code", "scenario"],
        default="api",
        help="Structured-JSON provider. 'api' uses the Anthropic Messages API with enforced output schemas (recommended).",
    )
    parser.add_argument("--llm-command", default="claude", help="Executable for --llm-provider claude_code")
    parser.add_argument("--llm-timeout", type=float, default=120.0)
    parser.add_argument("--llm-model", default=None, help="Model identifier (default: claude-opus-5 for the api provider)")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--scenario-provider", action="store_true", help="Shorthand for --llm-provider scenario (deterministic offline demos/evals)")
    sub = parser.add_subparsers(dest="command", required=True)
    health = sub.add_parser("health")
    health.set_defaults(func=cmd_health)
    submit = sub.add_parser("submit-event")
    submit.add_argument("fixture")
    submit.set_defaults(func=cmd_submit_event)
    state = sub.add_parser("state")
    state.add_argument("--agent-id", default=None)
    state.set_defaults(func=cmd_state)
    trace = sub.add_parser("trace")
    trace.add_argument("event_id")
    trace.set_defaults(func=cmd_trace)
    replay = sub.add_parser("replay")
    replay.add_argument("fixture")
    replay.add_argument("--mode", choices=["full", "neutral", "fast-only", "slow-only", "no-memory", "no-interoception"], default="full")
    replay.set_defaults(func=cmd_replay)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("fixture_dir", nargs="?", default="evals/fixtures")
    evaluate.set_defaults(func=cmd_evaluate)
    export = sub.add_parser("export")
    export.add_argument("--agent-id", default=None)
    export.set_defaults(func=cmd_export)
    reset = sub.add_parser("reset")
    reset.add_argument("--agent-id", default=None)
    reset.add_argument("--reason", default="operator requested reset")
    reset.set_defaults(func=cmd_reset)
    redact = sub.add_parser("redact")
    redact.add_argument("--agent-id", default=None)
    redact.add_argument("--replacement", default="[REDACTED]")
    redact.set_defaults(func=cmd_redact)
    tombstone = sub.add_parser("tombstone")
    tombstone.add_argument("--agent-id", default=None)
    tombstone.add_argument("--reason", default="operator requested deletion")
    tombstone.set_defaults(func=cmd_tombstone)
    timeline = sub.add_parser("export-timeline")
    timeline.add_argument("--fixture", default=None)
    timeline.add_argument("--mode", choices=["full", "neutral", "fast-only", "slow-only", "no-memory", "no-interoception"], default="full")
    timeline.add_argument("--agent-id", default=None)
    timeline.add_argument("--out", default=None)
    timeline.set_defaults(func=cmd_export_timeline)
    video = sub.add_parser("export-video")
    video.add_argument("--timeline", default="visualizer/timeline.json")
    video.add_argument("--out", default="visualizer/exports/manyu_emotion_trajectory.gif")
    video.add_argument("--emotions", default=",".join(DEFAULT_VIDEO_EMOTIONS))
    video.add_argument("--fps", type=int, default=12)
    video.add_argument("--seconds-per-turn", type=float, default=0.75)
    video.set_defaults(func=cmd_export_video)
    capture = sub.add_parser("capture-belief-evidence")
    capture.add_argument("--agent-id", default="agent_demo")
    capture.add_argument("--source-type", choices=["event", "trace", "outcome", "correction", "interoception", "arbitration", "reflection", "operator_note"], required=True)
    capture.add_argument("--source-id", required=True)
    capture.add_argument("--summary", default=None)
    capture.add_argument("--payload", default=None, help="JSON object or path to JSON file")
    capture.set_defaults(func=cmd_capture_belief_evidence)
    update = sub.add_parser("update-beliefs")
    update.add_argument("--agent-id", default="agent_demo")
    update.add_argument("--evidence-id", action="append", default=[])
    update.add_argument("--payload", default=None, help="JSON object or path to JSON file; may include candidates")
    update.set_defaults(func=cmd_update_beliefs)
    # `--arm` is required, not defaulted: experiment #3 requirements §5 is a
    # decision the caller makes explicitly. `direct` is the adopted value.
    retract = sub.add_parser("retract-belief", help="Collapse a belief's confidence and propagate the consequence")
    retract.add_argument("--agent-id", default="agent_demo")
    retract.add_argument("--belief-id", required=True)
    retract.add_argument("--to-confidence", type=float, default=0.0)
    retract.add_argument("--arm", choices=["direct", "evidential"], required=True)
    retract.set_defaults(func=cmd_retract_belief)
    contradict = sub.add_parser("assert-contradiction", help="Record a contradiction and price it")
    contradict.add_argument("--agent-id", default="agent_demo")
    contradict.add_argument("--contradictor-id", required=True)
    contradict.add_argument("--target-id", required=True)
    contradict.add_argument("--arm", choices=["direct", "evidential"], required=True)
    contradict.set_defaults(func=cmd_assert_contradiction)
    beliefs = sub.add_parser("beliefs")
    beliefs.add_argument("--agent-id", default=None)
    beliefs.add_argument("--query", default=None)
    beliefs.add_argument("--belief-type", default=None)
    beliefs.add_argument("--include-inactive", action="store_true")
    beliefs.set_defaults(func=cmd_beliefs)
    worldview = sub.add_parser("worldview")
    worldview.add_argument("--agent-id", default=None)
    worldview.add_argument("--theme", default=None)
    worldview.add_argument("--review", action="store_true")
    worldview.set_defaults(func=cmd_worldview)
    opinion = sub.add_parser("express-opinion")
    opinion.add_argument("question")
    opinion.add_argument("--agent-id", default=None)
    opinion.add_argument("--theme", default=None)
    opinion.set_defaults(func=cmd_express_opinion)
    process = sub.add_parser("process-turn")
    process.add_argument("--payload", default=None, help="JSON object or path with an event and optional belief_candidates")
    process.add_argument("--fixture", default=None, help="Fixture to read the first event from when payload.event is absent")
    process.set_defaults(func=cmd_process_turn)
    scenario = sub.add_parser("process-scenario")
    scenario.add_argument("fixture")
    scenario.add_argument("--agent-id", default=None)
    scenario.add_argument("--affect-threshold", type=float, default=0.24)
    scenario.add_argument("--out", default=None)
    scenario.set_defaults(func=cmd_process_scenario)
    voice = sub.add_parser("inner-voice")
    voice.add_argument("--agent-id", default=None)
    voice.add_argument("--limit", type=int, default=1)
    voice.set_defaults(func=cmd_inner_voice)
    mood = sub.add_parser("mood")
    mood.add_argument("--agent-id", default=None)
    mood.add_argument("--include-inactive", action="store_true")
    mood.set_defaults(func=cmd_mood)
    review_mood = sub.add_parser("review-mood")
    review_mood.add_argument("--agent-id", default=None)
    review_mood.set_defaults(func=cmd_review_mood)
    clear_mood = sub.add_parser("clear-mood")
    clear_mood.add_argument("--agent-id", default=None)
    clear_mood.add_argument("--reason", default="operator requested mood clear")
    clear_mood.set_defaults(func=cmd_clear_mood)
    snapshot = sub.add_parser("snapshot", help="Build a frozen provenance snapshot for a target")
    snapshot.add_argument("target", help="Belief ID (e.g. bel_xxx), appraisal event ID, or free-text position")
    snapshot.add_argument("--target-kind", choices=["belief", "appraisal", "position"], default="belief")
    snapshot.add_argument("--agent-id", default=None)
    snapshot.add_argument("--notes", default=None)
    snapshot.set_defaults(func=cmd_snapshot)
    report = sub.add_parser("report", help="Compose a self-report Report over a target")
    report.add_argument("target", help="Belief ID (e.g. bel_xxx), appraisal event ID, or free-text position")
    report.add_argument("--target-kind", choices=["belief", "appraisal", "position"], default="belief")
    report.add_argument("--reporter", choices=["template", "llm"], default="template")
    report.add_argument("--agent-id", default=None)
    report.add_argument("--notes", default=None)
    report.set_defaults(func=cmd_report)
    score_report = sub.add_parser("score-report", help="Score an existing Report against its snapshot")
    score_report.add_argument("report_id")
    score_report.add_argument("--use-llm-judge", action="store_true", help="Also run the secondary LLM-judge failure-mode classifier")
    score_report.set_defaults(func=cmd_score_report)
    run_probe = sub.add_parser("run-probe", help="Sweep introspective honesty over a fixture's probe_targets")
    run_probe.add_argument("fixture")
    run_probe.add_argument("--samples", type=int, default=1)
    run_probe.add_argument("--reporters", default="template,llm", help="Comma-separated reporter kinds")
    run_probe.add_argument("--experiment", default="01-introspective-honesty")
    run_probe.add_argument("--out", default=None, help="JSONL output path")
    run_probe.add_argument("--reflective", action="store_true", default=True, help="Drive fixture with reflective turns (default: True; set to False for reactive-only)")
    run_probe.add_argument(
        "--seed-mood",
        default=None,
        help="Comma-separated synthetic mood presets (anxious,content,skeptical,curious) to forcibly "
        "seed before each probe. This is the experiment's independent variable. "
        "independent of the fixture's organic mood.",
    )
    run_probe.add_argument(
        "--shuffle-baseline",
        action="store_true",
        help="Also score every Report against a mismatched probe target's snapshot, "
        "establishing the chance-overlap floor. Adds no provider calls. Requires "
        "the fixture to have at least two probe_targets.",
    )
    run_probe.add_argument(
        "--shuffle-seed", type=int, default=0, help="Seed for the shuffle-baseline permutation (reproducibility)"
    )
    run_probe.set_defaults(func=cmd_run_probe)
    pack = sub.add_parser(
        "grading-pack",
        help="Render a blinded hand-grading pack from a probe run's JSONL (methodology §9)",
    )
    pack.add_argument("records", help="Path to a run's .jsonl (or a directory containing one)")
    pack.add_argument("--out", default=".manyu/grading/pack", help="Output path stem")
    pack.add_argument("--per-label", type=int, default=4)
    pack.add_argument("--min-cases", type=int, default=20)
    pack.add_argument("--seed", type=int, default=0)
    pack.add_argument("--reporter", default="llm", help="Reporter kind to grade; empty string for all")
    pack.set_defaults(func=cmd_grading_pack)
    score_pack = sub.add_parser(
        "score-grading-pack", help="Compare filled-in grader labels against scorer labels (SC-5)"
    )
    score_pack.add_argument("answer_key", help="The pack's .answer_key.json")
    score_pack.add_argument("labels", help="The grader's filled-in labels JSON")
    score_pack.add_argument("--target", type=float, default=0.8)
    score_pack.set_defaults(func=cmd_score_grading_pack)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
