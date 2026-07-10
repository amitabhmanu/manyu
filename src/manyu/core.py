from __future__ import annotations

import json
from pathlib import Path

from manyu.clock import Clock, FrozenClock
from manyu.config import load_profile
from manyu.schemas import (
    AffectState,
    Appraisal,
    CandidateAction,
    ConsequenceClass,
    EventType,
    ManyuProfile,
    NormalizedEvent,
    ReplayReport,
    TraceRecord,
)
from manyu.services import Arbiter, EpisodeService, EventGateway, FastAppraiser, InteroceptionService, SlowAppraisalService, TransitionEngine
from manyu.services import MemoryService
from manyu.store import ManyuStore


class ManyuCore:
    def __init__(self, store: ManyuStore, profile: ManyuProfile, clock: Clock | None = None):
        self.store = store
        self.profile = profile
        self.clock = clock or Clock()
        self.gateway = EventGateway(store)
        self.fast_appraiser = FastAppraiser(store)
        self.transitions = TransitionEngine(store, profile, self.clock)
        self.interoception = InteroceptionService(store, profile, self.clock)
        self.arbiter = Arbiter(store, profile, self.clock)
        self.slow = SlowAppraisalService(store)
        self.episodes = EpisodeService(store)
        self.memory = MemoryService(store)

    @classmethod
    def from_paths(
        cls,
        db_path: str | Path = ":memory:",
        profile_path: str | Path = "config/default_profile.json",
        frozen: bool = False,
    ) -> "ManyuCore":
        profile = load_profile(profile_path)
        clock = FrozenClock() if frozen else Clock()
        return cls(ManyuStore(db_path), profile, clock)

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
        accepted = self.gateway.submit_event(event)
        state = self.transitions.initial_state(accepted.agent_id)
        appraisal = self.fast_appraiser.appraise(accepted, state.revision)
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
