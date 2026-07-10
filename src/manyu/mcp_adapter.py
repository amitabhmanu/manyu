from __future__ import annotations

from pathlib import Path
from typing import Any

from manyu.core import ManyuCore, ReplayService
from manyu.evaluation import EvaluationRunner
from manyu.visualization import timeline_from_fixture, timeline_from_store
from manyu.schemas import Appraisal, CandidateAction, NormalizedEvent


class ManyuMCPAdapter:
    """Dependency-free MCP-shaped adapter.

    The real MCP server should call these methods after the MCP package is added.
    Keeping this layer thin preserves the plan's rule that MCP must not bypass core
    validation, persistence, or policy checks.
    """

    def __init__(self, db_path: str | Path = ".manyu/manyu.sqlite3", profile_path: str | Path = "config/default_profile.json"):
        self.core = ManyuCore.from_paths(db_path=db_path, profile_path=profile_path)

    def health(self) -> dict[str, Any]:
        return self.core.health()

    def submit_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.submit_event(NormalizedEvent.model_validate(payload)).model_dump(mode="json")

    def get_interoception(self, agent_id: str) -> dict[str, Any]:
        state = self.core.state(agent_id)
        return self.core.interoception.derive(state).model_dump(mode="json")

    def submit_slow_appraisal(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.submit_slow_appraisal(Appraisal.model_validate(payload)).model_dump(mode="json")

    def arbitrate(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = CandidateAction.model_validate(payload)
        state = self.core.state(action.agent_id)
        return self.core.arbiter.arbitrate(action, state).model_dump(mode="json")

    def record_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.record_action(
            episode_id=payload["episode_id"],
            agent_id=payload["agent_id"],
            action_id=payload["action_id"],
            payload=payload,
        )

    def record_outcome(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.record_outcome(
            episode_id=payload["episode_id"],
            agent_id=payload["agent_id"],
            outcome_id=payload["outcome_id"],
            payload=payload,
        )

    def explain_trace(self, event_id: str) -> dict[str, Any]:
        return self.core.trace(event_id).model_dump(mode="json")

    def replay(self, fixture_path: str, mode: str = "full") -> dict[str, Any]:
        return ReplayService().replay(fixture_path, mode).model_dump(mode="json")

    def admin_reset(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.admin_reset(payload.get("agent_id"), payload.get("reason", "operator requested reset"))

    def evaluate(self, fixture_dir: str = "evals/fixtures") -> dict[str, Any]:
        return EvaluationRunner().run_directory(fixture_dir)

    def export_agent(self, agent_id: str | None = None) -> dict[str, Any]:
        return self.core.export_agent(agent_id)

    def redact_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.redact_agent(payload.get("agent_id"), payload.get("replacement", "[REDACTED]"))

    def tombstone_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.tombstone_agent(payload.get("agent_id"), payload.get("reason", "operator requested deletion"))

    def export_timeline(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        if payload.get("fixture_path"):
            return timeline_from_fixture(payload["fixture_path"], payload.get("mode", "full"))
        return timeline_from_store(self.core, payload.get("agent_id"))
