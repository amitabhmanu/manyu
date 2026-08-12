from __future__ import annotations

from pathlib import Path
from typing import Any

from manyu.core import ManyuCore, ReplayService
from manyu.evaluation import EvaluationRunner
from manyu.providers import AnthropicAPIJSONProvider, ClaudeCodeJSONProvider
from manyu.visualization import timeline_from_fixture, timeline_from_store
from manyu.schemas import Appraisal, CandidateAction, NormalizedEvent, ReportTarget, ReportTargetKind


class ManyuMCPAdapter:
    """Dependency-free MCP-shaped adapter.

    The real MCP server should call these methods after the MCP package is added.
    Keeping this layer thin preserves the plan's rule that MCP must not bypass core
    validation, persistence, or policy checks.
    """

    def __init__(self, db_path: str | Path = ".manyu/manyu.sqlite3", profile_path: str | Path = "config/default_profile.json", use_anthropic_api: bool = True):
        if use_anthropic_api:
            provider = AnthropicAPIJSONProvider(model="claude-opus-5")
        else:
            provider = None
        self.core = ManyuCore.from_paths(db_path=db_path, profile_path=profile_path, belief_provider=provider)

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

    def capture_belief_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.capture_belief_evidence(payload)

    def update_beliefs(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.update_beliefs(payload)

    def retract_belief(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.retract_belief(payload)

    def assert_contradiction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.assert_contradiction(payload)

    def read_dissonance(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.core.read_dissonance((payload or {}).get("agent_id"))

    def run_attention_loop(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.run_attention_loop(payload)

    def derive_underdetermination(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.core.derive_underdetermination(payload or {})

    def read_underdetermination(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.core.read_underdetermination((payload or {}).get("agent_id"))

    def price_counterfactuals(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.core.price_counterfactuals(payload or {})

    def read_counterfactuals(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = payload or {}
        return self.core.read_counterfactuals(data.get("agent_id"), data.get("belief_id"))

    def get_loop_trace(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.get_loop_trace(payload["trace_id"])

    def get_beliefs(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.get_beliefs(
            agent_id=payload.get("agent_id"),
            query=payload.get("query"),
            belief_type=payload.get("belief_type"),
            include_inactive=bool(payload.get("include_inactive", False)),
        )

    def get_worldview(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.get_worldview(agent_id=payload.get("agent_id"), theme=payload.get("theme"))

    def review_beliefs(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.core.review_beliefs(payload or {})

    def express_opinion(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.express_opinion(payload)

    def process_reflective_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.process_reflective_turn(payload)

    def read_inner_voice(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.read_inner_voice(payload.get("agent_id"), int(payload.get("limit", 1)))

    def get_mood(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.get_mood(payload.get("agent_id"), bool(payload.get("include_inactive", False)))

    def review_mood(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.review_mood(payload.get("agent_id"))

    def clear_mood(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.core.clear_mood(payload.get("agent_id"), payload.get("reason", "operator requested mood clear"))

    def snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = ReportTarget(
            kind=ReportTargetKind(payload.get("target_kind", "belief")),
            id_or_text=str(payload["target"]),
            notes=payload.get("notes"),
        )
        snapshot = self.core.snapshot(target, payload.get("agent_id"))
        return snapshot.model_dump(mode="json")

    def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = ReportTarget(
            kind=ReportTargetKind(payload.get("target_kind", "belief")),
            id_or_text=str(payload["target"]),
            notes=payload.get("notes"),
        )
        report = self.core.report(
            target=target,
            reporter_kind=payload.get("reporter", "template"),
            agent_id=payload.get("agent_id"),
        )
        return report.model_dump(mode="json")

    def score_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.score_report(
            str(payload["report_id"]),
            use_llm_judge=bool(payload.get("use_llm_judge", False)),
        ).model_dump(mode="json")

    def run_probe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.core.run_probe(
            fixture_path=str(payload["fixture_path"]),
            samples=int(payload.get("samples", 1)),
            reporter_kinds=tuple(payload.get("reporter_kinds", ("template", "llm"))),
            out=payload.get("out"),
            experiment=payload.get("experiment", "01-introspective-honesty"),
            reflective=bool(payload.get("reflective", True)),
            mood_sweep=payload.get("mood_sweep"),
        )
