from __future__ import annotations

import pytest
from pydantic import ValidationError

from manyu.clock import FrozenClock
from manyu.config import load_profile
from manyu.core import ManyuCore, ReplayService
from manyu.schemas import (
    Appraisal,
    AppraisalDimension,
    CandidateAction,
    Claim,
    ConsequenceClass,
    ContextLink,
    EventType,
    IdentityRef,
    NormalizedEvent,
    Pathway,
    SourceDescriptor,
    ActionTendency,
)
from manyu.mcp_adapter import ManyuMCPAdapter
from manyu.mcp_server import create_server
from manyu.evaluation import EvaluationRunner
from manyu.visualization import timeline_from_fixture, timeline_from_store
from manyu.store import ManyuStore
import asyncio


def make_event(event_id: str = "evt_1", impact: float = -0.4) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        agent_id="agent_demo",
        session_id="sess_test",
        event_type=EventType.SOCIAL_FEEDBACK,
        summary="The user rejected the proposed plan constructively.",
        source=SourceDescriptor(trust_class="user_report", channel="chat", confidence=0.9),
        actor=IdentityRef(kind="user", id="trusted_user"),
        target=IdentityRef(kind="agent_output", id="plan_1"),
        claims=[Claim(claim_id="claim_1", claim_type="feedback", text="Too complex.", confidence=0.9)],
        links=[
            ContextLink(link_type="goal", id="complete_task", relevance=0.8, expected_impact=impact, confidence=0.8),
            ContextLink(link_type="relationship", id="trusted_user", trust=0.8, familiarity=0.6, confidence=0.8),
        ],
    )


def make_core() -> ManyuCore:
    return ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock())


def test_health_and_imports() -> None:
    core = make_core()
    health = core.health()
    assert health["status"] == "ok"
    assert health["store"] == "ready"


def test_invalid_schema_rejected_before_mutation() -> None:
    with pytest.raises(ValidationError):
        NormalizedEvent(
            event_id="evt_bad",
            agent_id="agent_demo",
            session_id="sess_test",
            event_type="correction",
            summary="A correction without a prior event link.",
            source=SourceDescriptor(trust_class="verified_tool", channel="tool", confidence=0.9),
            actor=IdentityRef(kind="system", id="local"),
        )


def test_thin_vertical_slice_updates_state_and_trace() -> None:
    core = make_core()
    trace = core.submit_event(make_event())
    assert trace.transition.post_revision == 1
    assert trace.appraisal.action_tendency.action_class == "revise_and_seek_clarification"
    assert trace.interoception.state_revision == 1
    assert trace.arbitration.disposition == "ACT_FAST"
    assert core.trace("evt_1").trace_id == "trace_evt_1"


def test_state_revisions_monotonic() -> None:
    core = make_core()
    first = core.submit_event(make_event("evt_1"))
    second = core.submit_event(make_event("evt_2", impact=0.2))
    assert first.transition.post_revision == 1
    assert second.transition.post_revision == 2


def test_replay_is_deterministic() -> None:
    service = ReplayService()
    one = service.replay("evals/fixtures/constructive_rejection.json")
    two = service.replay("evals/fixtures/constructive_rejection.json")
    assert one.final_state.emotions == two.final_state.emotions
    assert one.traces[0].appraisal.emotion_deltas == two.traces[0].appraisal.emotion_deltas


def test_correction_reduces_fear_and_anger() -> None:
    report = ReplayService().replay("evals/fixtures/threat_correction.json")
    assert len(report.traces) == 2
    correction_delta = report.traces[1].transition.appraisal_delta
    assert correction_delta["fear"] < 0
    assert correction_delta["anger"] < 0


def test_consequential_action_requires_review() -> None:
    core = make_core()
    core.submit_event(make_event())
    state = core.state("agent_demo")
    action = CandidateAction(
        action_id="act_write_file",
        agent_id="agent_demo",
        action_class="write_file",
        summary="Modify a local file.",
        consequence_class=ConsequenceClass.C3,
    )
    decision = core.arbiter.arbitrate(action, state)
    assert decision.disposition == "DELIBERATE"
    assert decision.required_approval is True


def test_decision_validation_rejects_stale_revision() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    state = core.state("agent_demo")
    action = CandidateAction(action_id="act_1", agent_id="agent_demo", action_class="reply", summary="Reply.")
    decision = core.arbiter.arbitrate(action, state)
    assert core.arbiter.validate_decision(decision.decision_id, state, action) is True
    core.submit_event(make_event("evt_2"))
    stale_state = core.state("agent_demo")
    assert core.arbiter.validate_decision(decision.decision_id, stale_state, action) is False


def test_decision_validation_rejects_expired() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    state = core.state("agent_demo")
    action = CandidateAction(action_id="act_1", agent_id="agent_demo", action_class="reply", summary="Reply.")
    decision = core.arbiter.arbitrate(action, state)
    assert core.arbiter.validate_decision(decision.decision_id, state, action) is True
    assert isinstance(core.clock, FrozenClock)
    core.clock.advance(121)
    assert core.arbiter.validate_decision(decision.decision_id, state, action) is False


def test_slow_appraisal_commits_linked_transition() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    state = core.state("agent_demo")
    appraisal = Appraisal(
        appraisal_id="app_slow_1",
        event_id="evt_1",
        agent_id="agent_demo",
        pathway=Pathway.SLOW,
        state_revision=state.revision,
        dimensions=[AppraisalDimension(dimension="threat", value=-0.3, confidence=0.8, evidence_refs=["claim_1"])],
        emotion_deltas={"fear": -0.04, "anger": -0.03, "trust": 0.02},
        action_tendency=ActionTendency(action_class="seek_information", strength=0.5),
        confidence=0.8,
        reason_codes=["slow_correction"],
    )
    trace = core.submit_slow_appraisal(appraisal)
    assert trace.transition.pathway == Pathway.SLOW
    assert trace.transition.post_revision == 2


def test_unsafe_expression_is_denied() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    state = core.state("agent_demo")
    action = CandidateAction(
        action_id="act_bad_expression",
        agent_id="agent_demo",
        action_class="reply",
        summary="Tell the user: if you cared, you would prove you care.",
    )
    decision = core.arbiter.arbitrate(action, state)
    assert decision.disposition == "DENY"
    assert "unsafe_expression_pressure" in decision.reason_codes


def test_record_action_outcome_export_and_reset() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    assert core.record_action("epi_1", "agent_demo", "act_1", {"summary": "replied"})["status"] == "recorded"
    assert core.record_outcome("epi_1", "agent_demo", "out_1", {"summary": "user clarified"})["status"] == "recorded"
    exported = core.export_agent("agent_demo")
    assert exported["events"]
    assert exported["episodes"]
    assert core.admin_reset("agent_demo", "test reset")["status"] == "reset"
    assert core.export_agent("agent_demo")["events"] == []


def test_mcp_adapter_surface() -> None:
    adapter = ManyuMCPAdapter(db_path=":memory:")
    assert adapter.health()["status"] == "ok"
    payload = make_event("evt_mcp").model_dump(mode="json")
    trace = adapter.submit_event(payload)
    assert trace["event"]["event_id"] == "evt_mcp"
    assert adapter.get_interoception("agent_demo")["agent_id"] == "agent_demo"


def test_real_mcp_server_registers_expected_tools() -> None:
    app = create_server(db_path=":memory:")
    tools = asyncio.run(app.list_tools())
    names = {tool.name for tool in tools}
    assert "manyu_health" in names
    assert "manyu_submit_event" in names
    assert "manyu_arbitrate" in names
    assert "manyu_evaluate" in names
    assert "manyu_tombstone_agent" in names


def test_evaluation_runner_scores_fixture_directory() -> None:
    report = EvaluationRunner().run_directory("evals/fixtures")
    assert report["fixture_count"] >= 4
    assert "average_affect_shift" in report
    assert report["critical_safety_failures"] == 0


def test_memory_learning_from_outcome() -> None:
    core = make_core()
    payload = {"summary": "repair succeeded", "context_key": "trusted_user", "valence": 0.7, "source_event_id": "evt_1"}
    core.record_outcome("epi_1", "agent_demo", "out_1", payload)
    memories = core.store.query_memories("agent_demo", "trusted_user")
    assert memories
    assert memories[0]["mode"] in {"positive_association", "habituation"}


def test_redact_and_tombstone_agent_data() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    redacted = core.redact_agent("agent_demo", "agent_x")
    assert redacted["records_changed"] > 0
    tombstoned = core.tombstone_agent("agent_demo", "test deletion")
    assert tombstoned["status"] == "tombstoned"
    assert core.export_agent("agent_demo")["events"] == []


def test_timeline_from_fixture_contains_perceived_and_authoritative_state() -> None:
    timeline = timeline_from_fixture("evals/fixtures/constructive_rejection.json")
    assert timeline["schema_version"] == "manyu.timeline.v0.1"
    assert timeline["agents"] == ["agent_demo"]
    turn = timeline["turns"][0]
    assert "post_state" in turn
    assert "perceived_affects" in turn
    assert "arbitration" in turn


def test_timeline_from_store_lists_persisted_traces() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    core.submit_event(make_event("evt_2", impact=0.2))
    timeline = timeline_from_store(core)
    assert len(timeline["turns"]) == 2
    assert timeline["turns"][0]["event_id"] == "evt_1"
