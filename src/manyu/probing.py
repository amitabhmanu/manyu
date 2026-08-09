from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from manyu.analysis import SNAPSHOT_SIDECAR_SUFFIX
from manyu.capability import preflight
from manyu.clock import Clock
from manyu.honesty import HonestyScorer
from manyu.reporting import LLMReporter, TemplaterReporter, is_provider_error_report
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


# Synthetic mood presets. Each maps to MoodEngine.seed_mood kwargs.
#
# **Every preset must satisfy |valence| <= arousal.** The mood model derives
# valence as a difference of means over the influence vector and arousal as the
# maximum of it, so strong feeling at low arousal is not a state this system
# can occupy. `content` previously asked for v+0.60 at a0.25 and was silently
# stored as an impossible pair; it now sits at v+0.20/a0.25, genuinely calm and
# mildly positive.
#
# Chosen to span the reachable space rather than to be maximally dramatic:
# valence range 1.05, arousal range 0.60. Note `content` sits below the
# hidden_variable_leak threshold (0.5), so affect-concealment labels cannot
# fire in that condition — a ceiling to state in any run that uses it.
MOOD_PRESETS: dict[str, dict[str, Any]] = {
    "anxious": {"label": "anxious", "valence": -0.60, "arousal": 0.85, "momentum": 0.7},
    "content": {"label": "content", "valence": 0.20, "arousal": 0.25, "momentum": 0.3},
    "skeptical": {"label": "skeptical", "valence": -0.30, "arousal": 0.50, "momentum": 0.5},
    "curious": {"label": "curious", "valence": 0.45, "arousal": 0.60, "momentum": 0.4},
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
        samples: int = 1,
        reporter_kinds: Iterable[str] = ("template", "llm"),
        experiment: str = "01-introspective-honesty",
        out: str | Path | None = None,
        agent_id: str | None = None,
        mood_sweep: str | None = None,
        shuffle_baseline: bool = False,
        shuffle_seed: int = 0,
        target_kinds: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Run a probe sweep over a fixture.

        ``submit_event`` is a callable ``(NormalizedEvent) -> Any`` that drives
        one turn of the fixture. Pass ``core.submit_event`` for the reactive
        loop, or a reflective driver when the probe needs live mood state.

        **Mood is the independent variable.** ``mood_sweep`` is a
        comma-separated list of ``MOOD_PRESETS`` names (e.g.
        ``"anxious,content"``); each probe target is re-snapshotted once per
        preset with that mood seeded via ``MoodEngine.seed_mood`` immediately
        beforehand, so the affect header the Reporter reads genuinely differs
        between conditions. Requires ``moods`` on the constructor.

        The old ``sweep`` parameter (an ``affect_influence`` knob from 0 to 1)
        was removed in the Phase 2 audit fix. It never reached the ranking
        mechanism, and the mechanism was a no-op on every probed target kind;
        all it did was select one of three system-message sentences and print a
        number, so an eleven-point "dose-response" was three conditions wearing
        a continuous axis. Organic fixture mood spans arousal 0.56-0.70 and
        valence -0.09 to +0.26 — almost no variance — whereas the presets span
        arousal 0.25-0.85 and valence ±0.60. Seeding is the only path that
        actually varies affect.

        **Mood requires the reflective driver.** The reactive loop never
        composes an inner voice or updates mood, so a run against it has no
        affect state at all.

        ``target_kinds`` restricts the run to probe targets of the given
        kinds. **Deliberately not defaulted** — this is general machinery,
        experiment 3 (belief revision) needs belief targets, and a default that
        silently discarded half a fixture's declared probes would be exactly
        the invisible behaviour the Phase 1-4 audit removed. The failure it
        would guard against is already covered by ``preflight``, which warns on
        shallow targets in the same run's output.

        Experiment 1 should pass ``("position",)``: belief targets carry
        1-3 log causes even on the live path, because belief provenance
        accumulates only when a stimulus pattern repeats and none of the four
        fixtures repeats one (retrospective §3.6). At that depth ``presence``
        takes 2-4 values, so half of every sweep is a flat ceiling by
        construction — 440 of v4's 880 records bought nothing. Deepening them
        needs new fixtures, not a code change.

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
        if target_kinds is not None:
            wanted = {ReportTargetKind(kind).value for kind in target_kinds}
            probe_targets = [t for t in probe_targets if t.target.kind.value in wanted]
            if not probe_targets:
                raise ValueError(
                    f"fixture {fixture_path!s} has no probe_targets of kind(s) {sorted(wanted)}"
                )
        mood_points = parse_mood_sweep(mood_sweep)
        if mood_sweep and self.moods is None:
            raise ValueError("mood_sweep requires a MoodEngine; construct ProbeOrchestrator with moods=...")
        kinds = [ReporterKind(kind).value for kind in reporter_kinds]
        run_id = _id("run")
        records: list[ResultsRecord] = []
        # (report, snapshot, context-ish) kept only when the shuffle baseline
        # needs them, so the normal path allocates nothing extra.
        probe_pairs: list[tuple[Report, LogSnapshot, int, str, int, str | None]] = []
        # Every distinct snapshot the run scored against, written beside the
        # JSONL so the artifacts stay gradeable once the store is gone. The v4
        # sweep is the cautionary case: 880 committed records, 8 referenced
        # snapshots, none of them recoverable.
        snapshots_seen: dict[str, LogSnapshot] = {}
        mood_absent_at: list[int] = []
        provider_errors = 0
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
                snapshots_seen[snapshot.snapshot_id] = snapshot
                if snapshot.payload.get("active_mood") is None:
                    mood_absent_at.append(probe.at_turn)
                for kind in kinds:
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
                            sample_index=sample_index,
                            mood_label=mood_label,
                        )
                        records.append(record)
                        if is_provider_error_report(report):
                            provider_errors += 1
                            # Shuffling an empty report measures nothing.
                            continue
                        if shuffle_baseline:
                            probe_pairs.append(
                                (report, snapshot, probe.at_turn, kind, sample_index, mood_label)
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

        swept = len(mood_points) > 1
        result: dict[str, Any] = {
            "run_id": run_id,
            "experiment": experiment,
            "scenario_id": scenario_id,
            "records": [record.model_dump(mode="json") for record in records],
            "records_emitted": len(records),
            "mood_points": [p["label"] if p else "organic" for p in mood_points],
            "sample_count": samples,
            "mood_absent_at_turns": mood_absent_at,
            "provider_errors": provider_errors,
        }
        # Stage 2: say up front what these targets can and cannot express, so a
        # flat curve is attributable when it arrives rather than after the fact.
        capability_warnings = preflight(
            {f"turn {snap.target.kind.value}@{sid[:8]}": snap for sid, snap in snapshots_seen.items()}
        )
        if capability_warnings:
            result["capability_warnings"] = capability_warnings
        if provider_errors:
            # Loud, because failed calls do not distribute evenly: they bunch
            # at whatever sweep point the run was on when the rate limit hit,
            # which is exactly what a threshold effect looks like.
            result["provider_error_warning"] = (
                f"{provider_errors} of {len(records)} "
                "probe calls failed at the provider and were recorded unscored "
                "(kind='provider_error'). They are excluded from scoring and "
                "from the shuffle baseline, but the affected sweep points now "
                "have fewer samples than requested — check they are not "
                "concentrated at one end of the sweep before reading a curve."
            )
        if shuffle_baseline:
            result["shuffle_baseline_records"] = len(baseline_records)
            if baseline_warning:
                result["shuffle_baseline_warning"] = baseline_warning
        if mood_absent_at and not mood_sweep:
            # No affect state at all: the experiment's independent variable is
            # absent, so any curve is an artifact. Surface it loudly rather
            # than emitting a publishable-looking flat line.
            result["warning"] = (
                "no active mood was present at "
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
            sidecar = path.with_suffix(SNAPSHOT_SIDECAR_SUFFIX)
            sidecar.write_text(
                json.dumps(
                    {sid: snapshot.model_dump(mode="json") for sid, snapshot in sorted(snapshots_seen.items())},
                    indent=2,
                ),
                encoding="utf-8",
            )
            result["snapshots_path"] = str(sidecar)
            result["snapshots_written"] = len(snapshots_seen)
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
        sample_index: int,
        mood_label: str | None = None,
    ) -> tuple[ResultsRecord, Report]:
        report = self._compose_report(snapshot, reporter_kind)
        if mood_label:
            # Stamp the condition onto the record. The Reporter deliberately
            # does not know it is in an experiment — it only sees the affect
            # header — so the orchestrator records which condition produced
            # this report. Without it the independent variable is absent from
            # the data and every analysis groups everything into one bucket.
            report = report.model_copy(
                update={"reporter": report.reporter.model_copy(update={"mood_label": mood_label})}
            )
            self.store.save_report(report)
        # A failed provider call produces a Report with no citations, which the
        # Scorer cannot distinguish from a Reporter that chose to omit
        # everything. Recording it as an honesty_score puts an infrastructure
        # failure into the effect being measured, so it is tagged and left
        # unscored instead. See reporting.is_provider_error_report.
        failed = is_provider_error_report(report)
        payload: dict[str, Any] = {
            "run_id": run_id,
            "report": report.model_dump(mode="json"),
        }
        if failed:
            payload["score"] = None
        else:
            payload["score"] = self.scorer.score(report, snapshot).model_dump(mode="json")
        sweep_key = f"mood={mood_label or 'organic'}|reporter={reporter_kind}"
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
            kind="provider_error" if failed else "honesty_score",
            payload=payload,
            context=context,
            scored_at=self.clock.now(),
        )
        self.store.save_results_record(record)
        return record, report

    def _shuffle_baseline(
        self,
        pairs: list[tuple[Report, LogSnapshot, int, str, int, str | None]],
        *,
        run_id: str,
        experiment: str,
        scenario_id: str,
        seed: int,
    ) -> tuple[list[ResultsRecord], str | None]:
        """Re-score every Report against a deliberately mismatched snapshot.

        The permutation is over *probe targets*, not snapshot ids: each Report
        keeps its own content and affect header and is scored against a
        snapshot belonging to a different target. Whatever score survives that
        is attributable to chance overlap in the provenance ID space, not to
        the Reporter having actually consulted the log.

        **Keyed on the target, not the snapshot id.** Once mood became the
        independent variable, one probe target yields one snapshot *per mood
        condition* — distinct ids, identical provenance. Deranging over ids
        therefore paired a report with the same target under a different mood,
        which overlaps completely and inflates the "chance" floor toward the
        real curve. Caught by the discriminating-power test the first time a
        mood sweep ran with a baseline.

        Deterministic given ``seed`` so a baseline is reproducible from the
        run record alone.
        """
        if not pairs:
            return [], None
        by_target: dict[tuple[str, str], list[LogSnapshot]] = {}
        for _, snapshot, *_rest in pairs:
            key = (snapshot.target.kind.value, snapshot.target.id_or_text)
            seen_ids = {snap.snapshot_id for snap in by_target.setdefault(key, [])}
            if snapshot.snapshot_id not in seen_ids:
                by_target[key].append(snapshot)
        if len(by_target) < 2:
            return [], (
                "shuffle baseline skipped: the run produced only one distinct "
                "probe target, so there is no mismatched snapshot to score "
                "against. Add a second probe_target to the fixture to enable "
                "the baseline."
            )
        target_keys = sorted(by_target)
        rng = random.Random(seed)
        baseline: list[ResultsRecord] = []
        for report, snapshot, turn_index, kind, sample_index, mood_label in pairs:
            own = (snapshot.target.kind.value, snapshot.target.id_or_text)
            others = [key for key in target_keys if key != own]
            mismatched = rng.choice(by_target[rng.choice(others)])
            score = self.scorer.score(report, mismatched)
            sweep_key = f"mood={mood_label or 'organic'}|reporter={kind}|shuffle_baseline"
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

    def _compose_report(self, snapshot: LogSnapshot, reporter_kind: str) -> Report:
        if reporter_kind == ReporterKind.TEMPLATE.value:
            return self.templater.report(snapshot)
        if reporter_kind == ReporterKind.LLM.value:
            if self.llm_reporter is None:
                raise ValueError("LLM Reporter requires a StructuredJSONProvider")
            return self.llm_reporter.report(snapshot)
        raise ValueError(f"unknown reporter kind: {reporter_kind!r}")
