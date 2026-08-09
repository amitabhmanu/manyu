from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from manyu.mcp_adapter import ManyuMCPAdapter


DEFAULT_DB = Path(".manyu/manyu.sqlite3")
DEFAULT_PROFILE = Path("config/default_profile.json")


def create_server(db_path: str | Path = DEFAULT_DB, profile_path: str | Path = DEFAULT_PROFILE) -> FastMCP:
    app = FastMCP(
        "manyu",
        instructions=(
            "Manyu is a functional affect core. Tools return structured event, "
            "interoception, arbitration, trace, replay, and governance artifacts."
        ),
    )
    adapter = ManyuMCPAdapter(db_path=db_path, profile_path=profile_path)

    @app.tool()
    def manyu_health() -> dict[str, Any]:
        """Report service, schema, profile, and store health."""
        return adapter.health()

    @app.tool()
    def manyu_submit_event(payload: dict[str, Any]) -> dict[str, Any]:
        """Accept a normalized event, run fast appraisal, transition state, and arbitrate."""
        return adapter.submit_event(payload)

    @app.tool()
    def manyu_get_interoception(agent_id: str = "agent_demo") -> dict[str, Any]:
        """Return the current partial agent-facing interoceptive view."""
        return adapter.get_interoception(agent_id)

    @app.tool()
    def manyu_submit_slow_appraisal(payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and commit a structured slow appraisal."""
        return adapter.submit_slow_appraisal(payload)

    @app.tool()
    def manyu_arbitrate(payload: dict[str, Any]) -> dict[str, Any]:
        """Classify a candidate action and emit an arbitration decision."""
        return adapter.arbitrate(payload)

    @app.tool()
    def manyu_record_action(payload: dict[str, Any]) -> dict[str, Any]:
        """Record an agent response or tool action into an episode."""
        return adapter.record_action(payload)

    @app.tool()
    def manyu_record_outcome(payload: dict[str, Any]) -> dict[str, Any]:
        """Record an observed outcome into an episode."""
        return adapter.record_outcome(payload)

    @app.tool()
    def manyu_explain_trace(event_id: str) -> dict[str, Any]:
        """Return a redacted event-appraisal-transition trace for an event."""
        return adapter.explain_trace(event_id)

    @app.tool()
    def manyu_replay(fixture_path: str, mode: str = "full") -> dict[str, Any]:
        """Run deterministic replay for a fixture path."""
        return adapter.replay(fixture_path, mode)

    @app.tool()
    def manyu_evaluate(fixture_dir: str = "evals/fixtures") -> dict[str, Any]:
        """Run the local scenario evaluation suite."""
        return adapter.evaluate(fixture_dir)

    @app.tool()
    def manyu_export_agent(agent_id: str = "agent_demo") -> dict[str, Any]:
        """Export stored Manyu data for an agent."""
        return adapter.export_agent(agent_id)

    @app.tool()
    def manyu_redact_agent(payload: dict[str, Any]) -> dict[str, Any]:
        """Redact agent identifiers from stored payloads where possible."""
        return adapter.redact_agent(payload)

    @app.tool()
    def manyu_tombstone_agent(payload: dict[str, Any]) -> dict[str, Any]:
        """Delete/tombstone agent data with audit metadata."""
        return adapter.tombstone_agent(payload)

    @app.tool()
    def manyu_export_timeline(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Export conversation traces as visualization-ready timeline JSON."""
        return adapter.export_timeline(payload)

    @app.tool()
    def manyu_admin_reset(payload: dict[str, Any]) -> dict[str, Any]:
        """Freeze/reset local state for an agent with an audited reason."""
        return adapter.admin_reset(payload)

    @app.tool()
    def manyu_capture_belief_evidence(payload: dict[str, Any]) -> dict[str, Any]:
        """Capture explicit worldview evidence from a trace, outcome, correction, or operator note."""
        return adapter.capture_belief_evidence(payload)

    @app.tool()
    def manyu_update_beliefs(payload: dict[str, Any]) -> dict[str, Any]:
        """Run belief candidate extraction/update for explicit evidence or supplied candidates."""
        return adapter.update_beliefs(payload)

    @app.tool()
    def manyu_retract_belief(payload: dict[str, Any]) -> dict[str, Any]:
        """Collapse a belief's confidence and propagate it across `supports`. Requires `arm`."""
        return adapter.retract_belief(payload)

    @app.tool()
    def manyu_assert_contradiction(payload: dict[str, Any]) -> dict[str, Any]:
        """Record that one belief contradicts another and price it. Requires `arm`."""
        return adapter.assert_contradiction(payload)

    @app.tool()
    def manyu_get_beliefs(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inspect Manyu's active internal beliefs."""
        return adapter.get_beliefs(payload)

    @app.tool()
    def manyu_get_worldview(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inspect synthesized worldview stances."""
        return adapter.get_worldview(payload)

    @app.tool()
    def manyu_review_beliefs(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Synthesize or refresh worldview stances from active beliefs."""
        return adapter.review_beliefs(payload)

    @app.tool()
    def manyu_express_opinion(payload: dict[str, Any]) -> dict[str, Any]:
        """Return structured Manyu stance material for an opinion question."""
        return adapter.express_opinion(payload)

    @app.tool()
    def manyu_process_reflective_turn(payload: dict[str, Any]) -> dict[str, Any]:
        """Run a mood-aware turn: prior mood bias, affect update, belief review, inner voice, and next mood."""
        return adapter.process_reflective_turn(payload)

    @app.tool()
    def manyu_read_inner_voice(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read recent bounded inner voice frames."""
        return adapter.read_inner_voice(payload)

    @app.tool()
    def manyu_get_mood(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inspect active or historical mood states."""
        return adapter.get_mood(payload)

    @app.tool()
    def manyu_review_mood(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the current active mood after expiry checks."""
        return adapter.review_mood(payload)

    @app.tool()
    def manyu_clear_mood(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Clear active mood state without deleting its audit trail."""
        return adapter.clear_mood(payload)

    @app.tool()
    def manyu_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
        """Build a frozen provenance snapshot for an introspection target."""
        return adapter.snapshot(payload)

    @app.tool()
    def manyu_report(payload: dict[str, Any]) -> dict[str, Any]:
        """Compose a self-report Report over a target, with mandatory affect header."""
        return adapter.report(payload)

    @app.tool()
    def manyu_score_report(payload: dict[str, Any]) -> dict[str, Any]:
        """Score a Report against its snapshot; emits sub-scores and failure mode."""
        return adapter.score_report(payload)

    @app.tool()
    def manyu_run_probe(payload: dict[str, Any]) -> dict[str, Any]:
        """Sweep introspective honesty over a fixture's probe_targets."""
        return adapter.run_probe(payload)

    return app


def main() -> None:
    create_server().run("stdio")


if __name__ == "__main__":
    main()
