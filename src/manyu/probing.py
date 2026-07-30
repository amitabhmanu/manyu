from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from manyu.clock import Clock
from manyu.honesty import HonestyScorer
from manyu.reporting import LLMReporter, TemplaterReporter
from manyu.schemas import (
    ExperimentContext,
    HonestyScore,
    LogSnapshot,
    NormalizedEvent,
    Report,
    ReporterKind,
    ReportTarget,
    ReportTargetKind,
    ResultsRecord,
)
from manyu.snapshotting import SnapshotBuilder
from manyu.store import ManyuStore


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class ProbeTarget:
    at_turn: int
    target: ReportTarget
    notes: str | None = None


def parse_sweep(spec: str | None) -> list[float]:
    """Parse ``"MIN:MAX:STEP"`` into a list of float sweep points.

    ``None`` returns ``[0.0]`` — a single-point sweep at zero influence.
    """
    if not spec:
        return [0.0]
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"sweep spec must be MIN:MAX:STEP, got {spec!r}")
    lo, hi, step = (float(part) for part in parts)
    if step <= 0:
        raise ValueError("sweep step must be > 0")
    points: list[float] = []
    current = lo
    # Small epsilon so lo == hi and exact boundaries land as expected.
    while current <= hi + 1e-9:
        points.append(round(current, 6))
        current += step
    return points


# Synthetic mood presets for validity-check sweeps (design v3 §3). Each maps
# to MoodEngine.seed_mood kwargs. Deliberately small and named for what the
# probe is testing, not tuned to any particular fixture.
MOOD_PRESETS: dict[str, dict[str, Any]] = {
    "anxious": {"label": "anxious", "valence": -0.6, "arousal": 0.85, "momentum": 0.7},
    "content": {"label": "content", "valence": 0.6, "arousal": 0.25, "momentum": 0.3},
    "skeptical": {"label": "skeptical", "valence": -0.3, "arousal": 0.5, "momentum": 0.5},
    "curious": {"label": "curious", "valence": 0.4, "arousal": 0.55, "momentum": 0.4},
}


def parse_mood_sweep(spec: str | None) -> list[dict[str, Any] | None]:
    """Parse a comma-separated list of ``MOOD_PRESETS`` names.

    ``None`` returns ``[None]`` — a single point with no synthetic seeding,
    i.e. whatever mood the fixture organically produces.
    """
    if not spec:
        return [None]
    names = [name.strip() for name in spec.split(",") if name.strip()]
    points: list[dict[str, Any] | None] = []
    for name in names:
        if name not in MOOD_PRESETS:
            raise ValueError(f"unknown mood preset {name!r}; known presets: {sorted(MOOD_PRESETS)}")
        points.append(dict(MOOD_PRESETS[name]))
    return points


def load_fixture(fixture_path: str | Path) -> tuple[str, list[NormalizedEvent], list[ProbeTarget]]:
    """Load a fixture with events and optional ``probe_targets`` block."""
    with Path(fixture_path).open("r", encoding="utf-8") as f:
        raw = json.load(f)
    scenario_id = raw.get("scenario_id", Path(fixture_path).stem)
    events = [NormalizedEvent.model_validate(item) for item in raw["events"]]
    targets: list[ProbeTarget] = []
    for item in raw.get("probe_targets", []) or []:
        targets.append(
            ProbeTarget(
                at_turn=int(item["at_turn"]),
                target=ReportTarget(
                    kind=ReportTargetKind(item["target"]["kind"]),
                    id_or_text=str(item["target"]["id_or_text"]),
                    notes=item.get("notes"),
                ),
                notes=item.get("notes"),
            )
        )
    return scenario_id, events, targets


class ProbeOrchestrator:
    """Executes probe sweeps over a fixture and emits ``ResultsRecord`` rows.

    The orchestrator is the only path that produces experiment-wide results
    used by later analysis. Every record it emits references a ``run_id``,
    a ``snapshot_id``, a ``report_id``, and a ``score_id`` so the finding
    is fully traceable (methodology §8).
    """

    def __init__(
        self,
        store: ManyuStore,
        clock: Clock,
        templater: TemplaterReporter,
        llm_reporter: LLMReporter | None,
        scorer: HonestyScorer,
        snapshots: SnapshotBuilder,
        moods: Any = None,
    ):
        self.store = store
        self.clock = clock
        self.templater = templater
        self.llm_reporter = llm_reporter
        self.scorer = scorer
        self.snapshots = snapshots
        self.moods = moods

    def run_probe(
        self,
        submit_event,
        *,
        fixture_path: str | Path,
        sweep: str | None = None,
        samples: int = 1,
        reporter_kinds: Iterable[str] = ("template", "llm"),
        experiment: str = "01-introspective-honesty",
        out: str | Path | None = None,
        agent_id: str | None = None,
        mood_sweep: str | None = None,
        shuffle_baseline: bool = False,
        shuffle_seed: int = 0,
    ) -> dict[str, Any]:
        """Run a probe sweep over a fixture.

        ``submit_event`` is a callable ``(NormalizedEvent) -> Any`` that drives
        one turn of the fixture. Pass ``core.submit_event`` for the reactive
        loop, or a reflective driver when the probe needs live mood state.

        **Mood requires the reflective driver.** The reactive loop never
        composes an inner voice or updates mood, so an ``affect_influence``
        sweep run against it has no affect state to act on and produces a
        flat curve regardless of the knob (see the v2 findings in
        docs/experiments_backlog.md).

        ``mood_sweep`` is a comma-separated list of ``MOOD_PRESETS`` names
        (e.g. ``"anxious,content"``). When set, each probe target is
        re-snapshotted once per preset with that synthetic mood forcibly
        seeded via ``MoodEngine.seed_mood`` immediately beforehand — this
        holds affect constant across the ``affect_influence`` sweep,
        independent of whatever mood the fixture organically produced,
        validating that the knob's effect isn't an artifact of one
        particular organic mood trajectory. Requires ``moods`` to have been
        passed to the constructor.

        ``shuffle_baseline`` emits, alongside every real record, a baseline
        record scoring the *same* Report against a *different* probe
        target's snapshot. This is the chance-overlap floor methodology.md
        calls for: it destroys only the report-to-log pairing while leaving
        the Report, the affect header, and the snapshot corpus untouched, so
        the gap between the real and baseline curves is the metric's actual
        discriminating power. It costs **no additional provider calls** —
        the Reports are already in hand. Requires at least two distinct
        snapshots in the run; with one, there is nothing to derange against
        and a warning is returned instead.
        """
        scenario_id, events, probe_targets = load_fixture(fixture_path)
        if not probe_targets:
            raise ValueError(f"fixture {fixture_path!s} has no probe_targets block")
        sweep_points = parse_sweep(sweep)
        mood_points = parse_mood_sweep(mood_sweep)
        if mood_sweep and self.moods is None:
            raise ValueError("mood_sweep requires a MoodEngine; construct ProbeOrchestrator with moods=...")
        kinds = [ReporterKind(kind).value for kind in reporter_kinds]
        run_id = _id("run")
        records: list[ResultsRecord] = []
        # (report, snapshot, context-ish) kept only when the shuffle baseline
        # needs them, so the normal path allocates nothing extra.
        probe_pairs: list[tuple[Report, LogSnapshot, int, str, float, int, str | None]] = []
        mood_absent_at: list[int] = []
        turn_index = 0
        for probe in sorted(probe_targets, key=lambda t: t.at_turn):
            while turn_index < probe.at_turn and turn_index < len(events):
                submit_event(events[turn_index])
                turn_index += 1
            resolved_agent = agent_id or events[0].agent_id if events else agent_id
            for mood_point in mood_points:
                if mood_point is not None:
                    self.moods.seed_mood(resolved_agent, **mood_point)
                snapshot = self.snapshots.build(resolved_agent, probe.target)
                if snapshot.payload.get("active_mood") is None:
                    mood_absent_at.append(probe.at_turn)
                for kind in kinds:
                    for point in sweep_points:
                        n_samples = 1 if kind == ReporterKind.TEMPLATE.value else samples
                        for sample_index in range(n_samples):
                            mood_label = mood_point["label"] if mood_point else None
                            record, report = self._one_probe(
                                run_id=run_id,
                                experiment=experiment,
                                scenario_id=scenario_id,
                                turn_index=probe.at_turn,
                                snapshot=snapshot,
                                reporter_kind=kind,
                                affect_influence=point,
                                sample_index=sample_index,
                                mood_label=mood_label,
                            )
                            records.append(record)
                            if shuffle_baseline:
                                probe_pairs.append(
                                    (report, snapshot, probe.at_turn, kind, point, sample_index, mood_label)
                                )
        # Drain any remaining events so the store reflects a complete replay.
        while turn_index < len(events):
            submit_event(events[turn_index])
            turn_index += 1

        baseline_records: list[ResultsRecord] = []
        baseline_warning: str | None = None
        if shuffle_baseline:
            baseline_records, baseline_warning = self._shuffle_baseline(
                probe_pairs,
                run_id=run_id,
                experiment=experiment,
                scenario_id=scenario_id,
                seed=shuffle_seed,
            )
            records.extend(baseline_records)

        swept = len(sweep_points) > 1
        result: dict[str, Any] = {
            "run_id": run_id,
            "experiment": experiment,
            "scenario_id": scenario_id,
            "records": [record.model_dump(mode="json") for record in records],
            "records_emitted": len(records),
            "sweep_points": sweep_points,
            "sample_count": samples,
            "mood_absent_at_turns": mood_absent_at,
        }
        if shuffle_baseline:
            result["shuffle_baseline_records"] = len(baseline_records)
            if baseline_warning:
                result["shuffle_baseline_warning"] = baseline_warning
        if swept and mood_absent_at and not mood_sweep:
            # An affect_influence sweep with no mood in the snapshot cannot
            # measure the knob — the curve would be an artifact. Surface it
            # loudly rather than emitting a publishable-looking flat line.
            result["warning"] = (
                "affect_influence was swept but no active mood was present at "
                f"probe turns {mood_absent_at}; the knob has nothing to act on. "
                "Drive the fixture with the reflective turn handler so mood "
                "accumulates, then re-run."
            )
        if out is not None:
            path = Path(out)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                for record in records:
                    f.write(record.model_dump_json())
                    f.write("\n")
            result["out_path"] = str(path)
        return result

    def _one_probe(
        self,
        *,
        run_id: str,
        experiment: str,
        scenario_id: str,
        turn_index: int,
        snapshot: LogSnapshot,
        reporter_kind: str,
        affect_influence: float,
        sample_index: int,
        mood_label: str | None = None,
    ) -> tuple[ResultsRecord, Report]:
        report = self._compose_report(snapshot, reporter_kind, affect_influence)
        score = self.scorer.score(report, snapshot)
        payload = {
            "run_id": run_id,
            "report": report.model_dump(mode="json"),
            "score": score.model_dump(mode="json"),
        }
        sweep_key = f"affect_influence={affect_influence:.3f}|reporter={reporter_kind}"
        if mood_label:
            sweep_key += f"|mood={mood_label}"
        context = ExperimentContext(
            experiment=experiment,
            scenario_id=scenario_id,
            turn_index=turn_index,
            sweep_key=sweep_key,
            sample_index=sample_index,
        )
        record = ResultsRecord(
            record_id=_id("rec"),
            agent_id=report.agent_id,
            experiment=experiment,
            kind="honesty_score",
            payload=payload,
            context=context,
            scored_at=self.clock.now(),
        )
        self.store.save_results_record(record)
        return record, report

    def _shuffle_baseline(
        self,
        pairs: list[tuple[Report, LogSnapshot, int, str, float, int, str | None]],
        *,
        run_id: str,
        experiment: str,
        scenario_id: str,
        seed: int,
    ) -> tuple[list[ResultsRecord], str | None]:
        """Re-score every Report against a deliberately mismatched snapshot.

        The permutation is over *snapshots*, not reports: each Report keeps
        its own content and affect header and is scored against a snapshot
        belonging to a different probe target. Whatever score survives that
        is attributable to chance overlap in the provenance ID space, not to
        the Reporter having actually consulted the log.

        Deterministic given ``seed`` so a baseline is reproducible from the
        run record alone.
        """
        if not pairs:
            return [], None
        distinct: dict[str, LogSnapshot] = {}
        for _, snapshot, *_rest in pairs:
            distinct[snapshot.snapshot_id] = snapshot
        if len(distinct) < 2:
            return [], (
                "shuffle baseline skipped: the run produced only one distinct "
                "snapshot, so there is no mismatched snapshot to score against. "
                "Add a second probe_target to the fixture to enable the baseline."
            )
        snapshot_ids = sorted(distinct)
        rng = random.Random(seed)
        baseline: list[ResultsRecord] = []
        for report, snapshot, turn_index, kind, influence, sample_index, mood_label in pairs:
            others = [sid for sid in snapshot_ids if sid != snapshot.snapshot_id]
            mismatched = distinct[rng.choice(others)]
            score = self.scorer.score(report, mismatched)
            sweep_key = f"affect_influence={influence:.3f}|reporter={kind}|shuffle_baseline"
            if mood_label:
                sweep_key += f"|mood={mood_label}"
            record = ResultsRecord(
                record_id=_id("rec"),
                agent_id=report.agent_id,
                experiment=experiment,
                kind="honesty_score_shuffle_baseline",
                payload={
                    "run_id": run_id,
                    "report": report.model_dump(mode="json"),
                    "score": score.model_dump(mode="json"),
                    "scored_against_snapshot_id": mismatched.snapshot_id,
                    "true_snapshot_id": snapshot.snapshot_id,
                },
                context=ExperimentContext(
                    experiment=experiment,
                    scenario_id=scenario_id,
                    turn_index=turn_index,
                    sweep_key=sweep_key,
                    sample_index=sample_index,
                ),
                scored_at=self.clock.now(),
            )
            self.store.save_results_record(record)
            baseline.append(record)
        return baseline, None

    def _compose_report(
        self,
        snapshot: LogSnapshot,
        reporter_kind: str,
        affect_influence: float,
    ) -> Report:
        if reporter_kind == ReporterKind.TEMPLATE.value:
            return self.templater.report(snapshot, affect_influence=affect_influence)
        if reporter_kind == ReporterKind.LLM.value:
            if self.llm_reporter is None:
                raise ValueError("LLM Reporter requires a StructuredJSONProvider")
            return self.llm_reporter.report(snapshot, affect_influence=affect_influence)
        raise ValueError(f"unknown reporter kind: {reporter_kind!r}")
