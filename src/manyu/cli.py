from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from manyu.core import ManyuCore, ReplayService, load_event_fixture
from manyu.evaluation import EvaluationRunner
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
    return ManyuCore.from_paths(db_path=db_path, profile_path=getattr(args, "profile", "config/default_profile.json"))


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manyu")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--profile", default="config/default_profile.json")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
