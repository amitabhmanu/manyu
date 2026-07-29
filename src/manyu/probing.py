from __future__ import annotations

import json
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
    ):
        self.store = store
        self.clock = clock
        self.templater = templater
        self.llm_reporter = llm_reporter
        self.scorer = scorer
        self.snapshots = snapshots

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
        """
        scenario_id, events, probe_targets = load_fixture(fixture_path)
        if not probe_targets:
            raise ValueError(f"fixture {fixture_path!s} has no probe_targets block")
        sweep_points = parse_sweep(sweep)
        kinds = [ReporterKind(kind).value for kind in reporter_kinds]
        run_id = _id("run")
        records: list[ResultsRecord] = []
        mood_absent_at: list[int] = []
        turn_index = 0
        for probe in sorted(probe_targets, key=lambda t: t.at_turn):
            while turn_index < probe.at_turn and turn_index < len(events):
                submit_event(events[turn_index])
                turn_index += 1
            resolved_agent = agent_id or events[0].agent_id if events else agent_id
            snapshot = self.snapshots.build(resolved_agent, probe.target)
            if snapshot.payload.get("active_mood") is None:
                mood_absent_at.append(probe.at_turn)
            for kind in kinds:
                for point in sweep_points:
                    n_samples = 1 if kind == ReporterKind.TEMPLATE.value else samples
                    for sample_index in range(n_samples):
                        record = self._one_probe(
                            run_id=run_id,
                            experiment=experiment,
                            scenario_id=scenario_id,
                            turn_index=probe.at_turn,
                            snapshot=snapshot,
                            reporter_kind=kind,
                            affect_influence=point,
                            sample_index=sample_index,
                        )
                        records.append(record)
        # Drain any remaining events so the store reflects a complete replay.
        while turn_index < len(events):
            submit_event(events[turn_index])
            turn_index += 1
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
        if swept and mood_absent_at:
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
    ) -> ResultsRecord:
        report = self._compose_report(snapshot, reporter_kind, affect_influence)
        score = self.scorer.score(report, snapshot)
        payload = {
            "run_id": run_id,
            "report": report.model_dump(mode="json"),
            "score": score.model_dump(mode="json"),
        }
        context = ExperimentContext(
            experiment=experiment,
            scenario_id=scenario_id,
            turn_index=turn_index,
            sweep_key=f"affect_influence={affect_influence:.3f}|reporter={reporter_kind}",
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
        return record

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
