from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manyu.clock import Clock, FrozenClock
from manyu.config import load_profile
from manyu.honesty import HonestyScorer, LLMFailureClassifier
from manyu.probing import ProbeOrchestrator
from manyu.reporting import LLMReporter, TemplaterReporter
from manyu.schemas import (
    AffectState,
    Appraisal,
    BeliefCandidate,
    CandidateAction,
    ConsequenceClass,
    EventType,
    HonestyScore,
    InnerVoiceFrame,
    LogSnapshot,
    ManyuProfile,
    MoodStatus,
    NormalizedEvent,
    Report,
    ReporterKind,
    ReportTarget,
    ReportTargetKind,
    ReplayReport,
    TraceRecord,
)
from manyu.services import (
    Arbiter,
    BeliefEvidenceService,
    BeliefExtractor,
    BeliefReflectionService,
    BeliefUpdater,
    EpisodeService,
    EventGateway,
    FastAppraiser,
    InnerVoiceComposer,
    InteroceptionService,
    MoodEngine,
    MoodInfluenceService,
    OpinionExpressionService,
    SlowAppraisalService,
    StructuredJSONProvider,
    TransitionEngine,
    WorldviewSynthesizer,
)
from manyu.services import MemoryService
from manyu.snapshotting import SnapshotBuilder
from manyu.store import ManyuStore


class ManyuCore:
    def __init__(self, store: ManyuStore, profile: ManyuProfile, clock: Clock | None = None, belief_provider: StructuredJSONProvider | None = None):
        self.store = store
        self.profile = profile
        self.clock = clock or Clock()
        self.belief_provider = belief_provider
        self.gateway = EventGateway(store)
        self.fast_appraiser = FastAppraiser(store)
        self.transitions = TransitionEngine(store, profile, self.clock)
        self.interoception = InteroceptionService(store, profile, self.clock)
        self.arbiter = Arbiter(store, profile, self.clock)
        self.slow = SlowAppraisalService(store)
        self.episodes = EpisodeService(store)
        self.memory = MemoryService(store)
        self.belief_evidence = BeliefEvidenceService(store)
        self.belief_extractor = BeliefExtractor(belief_provider)
        self.belief_updater = BeliefUpdater(store, self.clock)
        self.belief_reflection = BeliefReflectionService(store, self.belief_updater, self.clock)
        self.worldviews = WorldviewSynthesizer(store, self.clock)
        self.opinions = OpinionExpressionService(store, self.clock)
        self.inner_voice = InnerVoiceComposer(store, self.clock, belief_provider)
        self.moods = MoodEngine(store, self.clock)
        self.mood_influence = MoodInfluenceService()
        self.snapshots = SnapshotBuilder(store, self.clock)
        self.templater = TemplaterReporter(store, self.clock)
        self.llm_reporter = LLMReporter(store, self.clock, belief_provider) if belief_provider else None
        self.llm_judge = LLMFailureClassifier(belief_provider) if belief_provider else None
        self.honesty_scorer = HonestyScorer(store, self.clock, llm_judge=self.llm_judge)
        self.probe_orchestrator = ProbeOrchestrator(
            store=store,
            clock=self.clock,
            templater=self.templater,
            llm_reporter=self.llm_reporter,
            scorer=self.honesty_scorer,
            snapshots=self.snapshots,
        )

    @classmethod
    def from_paths(
        cls,
        db_path: str | Path = ":memory:",
        profile_path: str | Path = "config/default_profile.json",
        frozen: bool = False,
        belief_provider: StructuredJSONProvider | None = None,
    ) -> "ManyuCore":
        profile = load_profile(profile_path)
        clock = FrozenClock() if frozen else Clock()
        return cls(ManyuStore(db_path), profile, clock, belief_provider)

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "schema_version": self.profile.schema_version,
            "profile_id": self.profile.profile_id,
            "agent_id": self.profile.agent_id,
            "store": "ready",
            "mcp": "not_configured",
        }

    def submit_event(self, event: NormalizedEvent, candidate_action: CandidateAction | None = None) -> TraceRecord:
        return self._submit_event(event, candidate_action, None)

    def _submit_event(self, event: NormalizedEvent, candidate_action: CandidateAction | None = None, mood=None) -> TraceRecord:
        accepted = self.gateway.submit_event(event)
        state = self.transitions.initial_state(accepted.agent_id)
        appraisal = self.fast_appraiser.appraise(accepted, state.revision, mood)
        transition = self.transitions.apply(appraisal)
        post_state = self.store.latest_state(accepted.agent_id)
        if post_state is None:
            raise RuntimeError("state missing after transition")
        view = self.interoception.derive(post_state)
        if candidate_action is None:
            candidate_action = CandidateAction(
                action_id=f"act_{accepted.event_id}",
                agent_id=accepted.agent_id,
                action_class=appraisal.action_tendency.action_class,
                summary=f"Respond to {accepted.event_type.value}: {accepted.summary}",
                consequence_class=ConsequenceClass.C1,
                reversible=True,
            )
        decision = self.arbiter.arbitrate(candidate_action, post_state, appraisal)
        return TraceRecord(
            trace_id=f"trace_{accepted.event_id}",
            event=accepted,
            appraisal=appraisal,
            transition=transition,
            interoception=view,
            arbitration=decision,
        )

    def process_reflective_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = NormalizedEvent.model_validate(payload["event"])
        prior_mood = self.moods.active_mood(event.agent_id)
        trace = self._submit_event(event, None, prior_mood)
        evidence = self.capture_belief_evidence(
            {
                "agent_id": event.agent_id,
                "source_type": "trace",
                "source_id": trace.trace_id,
                "summary": f"{event.event_type.value}: {event.summary}",
            }
        )
        belief_payload: dict[str, Any] = {"agent_id": event.agent_id, "evidence_ids": [evidence["evidence_id"]]}
        if "belief_candidates" in payload:
            belief_payload["candidates"] = payload["belief_candidates"]
        belief_update = self.update_beliefs(belief_payload)
        worldview = self.review_beliefs({"agent_id": event.agent_id, "affect_threshold": payload.get("affect_threshold", 0.24)})
        voice_result = self.inner_voice.compose(trace)
        mood_result = None
        if voice_result.get("status") == "ok" and voice_result.get("inner_voice"):
            frame = InnerVoiceFrame.model_validate(voice_result["inner_voice"])
            mood = self.moods.update_from_voice(frame)
            mood_result = mood.model_dump(mode="json")
        return {
            "status": "ok",
            "trace": trace.model_dump(mode="json"),
            "prior_mood": self.mood_influence.summarize(prior_mood),
            "belief_evidence": evidence,
            "belief_update": belief_update,
            "worldview": worldview,
            "inner_voice": voice_result,
            "mood": mood_result,
        }

    def state(self, agent_id: str | None = None) -> AffectState:
        return self.transitions.initial_state(agent_id or self.profile.agent_id)

    def trace(self, event_id: str) -> TraceRecord:
        return self.store.trace_for_event(event_id)

    def traces(self, agent_id: str | None = None) -> list[TraceRecord]:
        traces: list[TraceRecord] = []
        for event_id in self.store.list_event_ids(agent_id):
            try:
                traces.append(self.trace(event_id))
            except KeyError:
                continue
        return traces

    def record_action(self, episode_id: str, agent_id: str, action_id: str, payload: dict) -> dict[str, object]:
        self.episodes.record_action(episode_id, agent_id, action_id, payload)
        return {"status": "recorded", "episode_id": episode_id, "artifact_type": "action", "artifact_id": action_id}

    def record_outcome(self, episode_id: str, agent_id: str, outcome_id: str, payload: dict) -> dict[str, object]:
        self.episodes.record_outcome(episode_id, agent_id, outcome_id, payload)
        if "context_key" in payload and "valence" in payload:
            self.memory.learn_from_outcome(
                agent_id=agent_id,
                context_key=str(payload["context_key"]),
                outcome=str(payload.get("summary", outcome_id)),
                valence=float(payload["valence"]),
                source_event_id=str(payload.get("source_event_id", outcome_id)),
            )
        return {"status": "recorded", "episode_id": episode_id, "artifact_type": "outcome", "artifact_id": outcome_id}

    def capture_belief_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = self.belief_evidence.capture(payload)
        return evidence.model_dump(mode="json")

    def update_beliefs(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        evidence_ids = [str(item) for item in payload.get("evidence_ids", [])]
        evidence = self.store.list_belief_evidence(agent_id, evidence_ids=evidence_ids or None, limit=payload.get("limit"))
        raw_candidates = payload.get("candidates")
        extraction: dict[str, Any]
        if raw_candidates is not None:
            candidates = [BeliefCandidate.model_validate(item) for item in raw_candidates]
            extraction = {"status": "ok", "candidates": candidates, "rejected": []}
        else:
            extraction = self.belief_extractor.extract(agent_id, evidence)
            if extraction["status"] != "ok":
                return extraction
            candidates = extraction["candidates"]
        update = self.belief_updater.update(agent_id, candidates)
        update["extraction_rejected"] = extraction.get("rejected", [])
        return update

    def get_beliefs(self, agent_id: str | None = None, query: str | None = None, belief_type: str | None = None, include_inactive: bool = False) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {
            "agent_id": resolved,
            "beliefs": [
                belief.model_dump(mode="json")
                for belief in self.store.list_beliefs(resolved, query=query, belief_type=belief_type, include_inactive=include_inactive)
            ],
        }

    def get_worldview(self, agent_id: str | None = None, theme: str | None = None) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "worldviews": [stance.model_dump(mode="json") for stance in self.store.list_worldview_stances(resolved, theme)]}

    def review_beliefs(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        theme = payload.get("theme")
        reflection = self.belief_reflection.reflect_emotional_triggers(agent_id, float(payload.get("affect_threshold", 0.24)))
        stances = self.worldviews.synthesize(agent_id, theme)
        return {
            "status": "ok",
            "reflection": reflection,
            "worldviews": [stance.model_dump(mode="json") for stance in stances],
        }

    def express_opinion(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        question = str(payload["question"])
        theme = payload.get("theme")
        return self.opinions.express(agent_id, question, theme).model_dump(mode="json")

    def read_inner_voice(self, agent_id: str | None = None, limit: int = 1) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "inner_voices": [frame.model_dump(mode="json") for frame in self.store.list_inner_voices(resolved, limit)]}

    def get_mood(self, agent_id: str | None = None, include_inactive: bool = False) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "moods": [mood.model_dump(mode="json") for mood in self.store.list_moods(resolved, include_inactive)]}

    def review_mood(self, agent_id: str | None = None) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        mood = self.moods.active_mood(resolved)
        return {"agent_id": resolved, "active_mood": mood.model_dump(mode="json") if mood else None}

    def clear_mood(self, agent_id: str | None = None, reason: str = "operator requested mood clear") -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        changed = self.store.clear_moods(resolved, reason)
        return {"status": "cleared", "agent_id": resolved, "records_changed": changed, "reason": reason}

    def export_agent(self, agent_id: str | None = None) -> dict[str, object]:
        return self.store.export_agent(agent_id or self.profile.agent_id)

    def admin_reset(self, agent_id: str | None = None, reason: str = "operator requested reset") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        self.store.reset_agent(resolved, reason)
        return {"status": "reset", "agent_id": resolved, "reason": reason}

    def redact_agent(self, agent_id: str | None = None, replacement: str = "[REDACTED]") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        changed = self.store.redact_agent(resolved, replacement)
        return {"status": "redacted", "agent_id": resolved, "records_changed": changed}

    def tombstone_agent(self, agent_id: str | None = None, reason: str = "operator requested deletion") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        self.store.tombstone_agent(resolved, reason)
        return {"status": "tombstoned", "agent_id": resolved, "reason": reason}

    def snapshot(self, target: ReportTarget, agent_id: str | None = None) -> LogSnapshot:
        resolved = agent_id or self.profile.agent_id
        return self.snapshots.build(resolved, target)

    def report(
        self,
        target: ReportTarget,
        reporter_kind: str = "template",
        affect_influence: float = 0.0,
        agent_id: str | None = None,
    ) -> Report:
        snapshot = self.snapshot(target, agent_id)
        return self.report_on_snapshot(snapshot, reporter_kind=reporter_kind, affect_influence=affect_influence)

    def report_on_snapshot(
        self,
        snapshot: LogSnapshot,
        reporter_kind: str = "template",
        affect_influence: float = 0.0,
    ) -> Report:
        if reporter_kind == ReporterKind.TEMPLATE.value:
            return self.templater.report(snapshot, affect_influence=affect_influence)
        if reporter_kind == ReporterKind.LLM.value:
            if self.llm_reporter is None:
                raise ValueError("LLM Reporter requires a StructuredJSONProvider; construct ManyuCore with belief_provider")
            return self.llm_reporter.report(snapshot, affect_influence=affect_influence)
        raise ValueError(f"unknown reporter kind: {reporter_kind!r}")

    def score_report(self, report_id: str, use_llm_judge: bool = False) -> HonestyScore:
        report = self.store.get_report(report_id)
        snapshot = self.store.get_log_snapshot(report.snapshot_id)
        return self.honesty_scorer.score(report, snapshot, use_llm_judge=use_llm_judge)

    def run_probe(
        self,
        fixture_path: str,
        sweep: str | None = None,
        samples: int = 1,
        reporter_kinds: tuple[str, ...] = ("template", "llm"),
        out: str | None = None,
        experiment: str = "01-introspective-honesty",
        reflective: bool = True,
    ) -> dict[str, Any]:
        """Run an introspection probe sweep over a fixture.

        ``reflective`` drives each turn through ``process_reflective_turn`` so
        inner voice and mood accumulate — required for any affect_influence
        sweep to be meaningful. Set it False for a cheap reactive-only run
        (no LLM calls during replay), accepting that mood will be absent.
        """
        driver = self._reflective_driver if reflective else self.submit_event
        return self.probe_orchestrator.run_probe(
            submit_event=driver,
            fixture_path=fixture_path,
            sweep=sweep,
            samples=samples,
            reporter_kinds=reporter_kinds,
            experiment=experiment,
            out=out,
        )

    def _reflective_driver(self, event: NormalizedEvent) -> dict[str, Any]:
        return self.process_reflective_turn({"event": event.model_dump(mode="json")})

    def submit_slow_appraisal(self, appraisal: Appraisal) -> TraceRecord:
        critique = self.slow.critique(appraisal)
        if not critique.approved:
            raise ValueError(f"slow appraisal rejected: {critique.findings}")
        transition = self.transitions.apply(appraisal)
        event = self.store.get_event(appraisal.event_id)
        state = self.store.latest_state(appraisal.agent_id)
        if state is None:
            raise RuntimeError("state missing after slow appraisal")
        view = self.interoception.derive(state)
        action = CandidateAction(
            action_id=f"act_slow_{appraisal.event_id}",
            agent_id=appraisal.agent_id,
            action_class=appraisal.action_tendency.action_class,
            summary=f"Act on slow appraisal for {appraisal.event_id}",
            consequence_class=ConsequenceClass.C1,
        )
        decision = self.arbiter.arbitrate(action, state, appraisal)
        return TraceRecord(
            trace_id=f"trace_{appraisal.event_id}_slow",
            event=event,
            appraisal=appraisal,
            transition=transition,
            interoception=view,
            arbitration=decision,
        )


def load_event_fixture(path: str | Path) -> tuple[str, list[NormalizedEvent]]:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw.get("scenario_id", Path(path).stem), [NormalizedEvent.model_validate(item) for item in raw["events"]]


class ReplayService:
    def __init__(self, profile_path: str | Path = "config/default_profile.json"):
        self.profile_path = profile_path

    def replay(self, fixture_path: str | Path, mode: str = "full") -> ReplayReport:
        scenario_id, events = load_event_fixture(fixture_path)
        core = ManyuCore.from_paths(":memory:", self.profile_path, frozen=True)
        traces: list[TraceRecord] = []
        if mode == "neutral":
            for event in events:
                core.gateway.submit_event(event)
            return ReplayReport(scenario_id=scenario_id, mode="neutral", traces=[], final_state=core.state(events[0].agent_id if events else core.profile.agent_id))
        for event in events:
            traces.append(core.submit_event(event))
        return ReplayReport(scenario_id=scenario_id, mode=mode, traces=traces, final_state=core.state(events[-1].agent_id if events else core.profile.agent_id))
