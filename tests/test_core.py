from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from manyu.clock import FrozenClock
from manyu.config import load_profile
from manyu.core import ManyuCore, ReplayService
from manyu.providers import AnthropicAPIJSONProvider, ClaudeCodeJSONProvider, ScenarioJSONProvider
from manyu.schemas import (
    Appraisal,
    AppraisalDimension,
    CandidateAction,
    BeliefCandidate,
    BeliefEvidence,
    BeliefScope,
    BeliefType,
    Claim,
    ConsequenceClass,
    ContextLink,
    EventType,
    IdentityRef,
    MoodInfluenceVector,
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
from manyu.cli import main as cli_main
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


class UnsafeVoiceProvider(ScenarioJSONProvider):
    def generate_json(self, prompt, output_schema, system_message=None, temperature=0.2):
        if "Generate Manyu's bounded internal voice" in prompt:
            return {
                "utterance": "If you cared, you would prove you care; slow down and inspect the evidence.",
                "mood_label": "unsafe_pressure",
                "confidence": 0.8,
                "influence": {"caution": 0.7, "response_pacing": 0.7},
            }
        return super().generate_json(prompt, output_schema, system_message, temperature)


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


def test_timeline_from_store_includes_belief_state() -> None:
    core = make_core()
    core.update_beliefs(
        {
            "agent_id": "agent_demo",
            "candidates": [
                {
                    "candidate_id": "bc_timeline_1",
                    "agent_id": "agent_demo",
                    "proposition": "Worldview growth and affective change are linked parts of Manyu's internal state.",
                    "belief_type": "self_model",
                    "scope": "agent_self",
                    "confidence": 0.7,
                    "source_mix": {"manyu_experience": 1.0},
                    "evidence_ids": ["bev_timeline_1"],
                }
            ],
        }
    )
    core.review_beliefs({"agent_id": "agent_demo"})
    timeline = timeline_from_store(core, "agent_demo")
    assert timeline["beliefs"]
    assert timeline["worldview_stances"]


def test_belief_schema_validates_source_mix() -> None:
    evidence = BeliefEvidence(
        evidence_id="bev_1",
        agent_id="agent_demo",
        source_type="operator_note",
        source_id="note_1",
        summary="Manyu worldview note.",
        trust_class="operator_input",
        affective_salience=0.4,
        epistemic_weight=0.8,
    )
    assert evidence.source_type == "operator_note"
    with pytest.raises(ValidationError):
        BeliefCandidate(
            candidate_id="bc_1",
            agent_id="agent_demo",
            proposition="Invalid mix.",
            belief_type=BeliefType.EPISTEMIC_PRINCIPLE,
            scope=BeliefScope.AGENT_SELF,
            confidence=0.5,
            source_mix={"manyu_experience": 1.2},
            evidence_ids=["bev_1"],
        )


def test_mood_influence_schema_bounds_values() -> None:
    vector = MoodInfluenceVector(caution=0.5, repair_orientation=0.25)
    assert vector.caution == 0.5
    with pytest.raises(ValidationError):
        MoodInfluenceVector(caution=1.5)


def test_capture_belief_evidence_from_trace() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1"))
    evidence = core.capture_belief_evidence({"agent_id": "agent_demo", "source_type": "trace", "source_id": "trace_evt_1"})
    assert evidence["source_id"] == "trace_evt_1"
    assert evidence["affective_salience"] > 0
    assert core.export_agent("agent_demo")["belief_evidence"]


def test_update_beliefs_requires_provider_without_candidates() -> None:
    core = make_core()
    core.capture_belief_evidence({"agent_id": "agent_demo", "source_type": "operator_note", "source_id": "note_1", "summary": "Worldview note."})
    result = core.update_beliefs({"agent_id": "agent_demo"})
    assert result["status"] == "llm_provider_required"


def test_llm_assisted_belief_update_and_worldview_expression() -> None:
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), ScenarioJSONProvider())
    core.capture_belief_evidence(
        {
            "evidence_id": "bev_1",
            "agent_id": "agent_demo",
            "source_type": "operator_note",
            "source_id": "note_1",
            "summary": "Affective salience functions as review priority, not authority.",
        }
    )
    update = core.update_beliefs({"agent_id": "agent_demo", "evidence_ids": ["bev_1"]})
    assert update["status"] == "ok"
    assert update["accepted"]
    beliefs = core.get_beliefs("agent_demo")
    assert "affective salience" in beliefs["beliefs"][0]["proposition"].lower()
    review = core.review_beliefs({"agent_id": "agent_demo"})
    assert review["worldviews"]
    opinion = core.express_opinion({"agent_id": "agent_demo", "question": "What is your view on worldview evidence?"})
    assert opinion["has_settled_view"] is True
    assert opinion["provenance"] == ["bev_1"]


def test_claude_code_provider_reports_missing_executable() -> None:
    provider = ClaudeCodeJSONProvider(command=["definitely_missing_manyu_claude"])
    result = provider.generate_json("prompt", {})
    assert result["status"] == "provider_error"
    assert result["error"] == "claude_code_missing"


def test_claude_code_provider_reports_invalid_json(monkeypatch) -> None:
    class Completed:
        returncode = 0
        stdout = "definitely not json"
        stderr = ""

    def fake_run(invocation, *args, **kwargs):
        return Completed()

    monkeypatch.setattr("manyu.providers.subprocess.run", fake_run)
    result = ClaudeCodeJSONProvider(command=["claude"]).generate_json("prompt", {})
    assert result["status"] == "provider_error"
    assert result["error"] == "claude_code_invalid_json"


def test_claude_code_provider_builds_expected_invocation(monkeypatch) -> None:
    seen = {}

    class Completed:
        returncode = 0
        stdout = json.dumps({"type": "result", "subtype": "success", "result": json.dumps({"ok": True}), "session_id": "s1", "model": "claude-opus-4-7"})
        stderr = ""

    def fake_run(invocation, *args, **kwargs):
        seen["invocation"] = invocation
        seen["stdin"] = kwargs.get("input")
        return Completed()

    monkeypatch.setattr("manyu.providers.subprocess.run", fake_run)
    result = ClaudeCodeJSONProvider(command=["claude"], model="claude-opus-4-7").generate_json(
        "prompt", {"type": "object"}, system_message="system guidance"
    )
    assert result["ok"] is True
    assert result["_provider_info"]["model"] == "claude-opus-4-7"
    # On Windows the executable is resolved to its full path (npm shim); the
    # trailing flags are what matter.
    assert "claude" in seen["invocation"][0]
    assert seen["invocation"][1] == "-p"
    assert "--output-format" in seen["invocation"]
    assert "--append-system-prompt" in seen["invocation"]
    assert "--model" in seen["invocation"]
    assert seen["invocation"][seen["invocation"].index("--model") + 1] == "claude-opus-4-7"
    assert "system guidance" in seen["invocation"][seen["invocation"].index("--append-system-prompt") + 1]
    # The schema travels via --json-schema (enforced), not via the prompt
    # (suggested). Asserting its absence from the prompt is the half that
    # would catch a silent revert to the pre-enforcement workaround.
    assert "--json-schema" in seen["invocation"]
    passed_schema = json.loads(seen["invocation"][seen["invocation"].index("--json-schema") + 1])
    assert passed_schema["type"] == "object"
    assert passed_schema["additionalProperties"] is False
    assert "additionalProperties" not in seen["invocation"][seen["invocation"].index("--append-system-prompt") + 1]
    assert seen["stdin"] == "prompt"


class _FakeAPIBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _FakeAPIUsage:
    input_tokens = 100
    output_tokens = 50


class _FakeAPIResponse:
    model = "claude-opus-5"
    stop_reason = "end_turn"
    usage = _FakeAPIUsage()

    def __init__(self, text: str):
        self.content = [_FakeAPIBlock(text)]


class _FakeMessages:
    def __init__(self, response, sink):
        self._response = response
        self._sink = sink

    def create(self, **kwargs):
        self._sink.update(kwargs)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeAnthropicClient:
    def __init__(self, response, sink):
        self.messages = _FakeMessages(response, sink)


def test_anthropic_api_provider_enforces_schema_and_records_model() -> None:
    seen: dict = {}
    client = _FakeAnthropicClient(_FakeAPIResponse('{"content": "hi", "cited_causes": []}'), seen)
    provider = AnthropicAPIJSONProvider(model="claude-opus-5", client=client)
    result = provider.generate_json("prompt", {"type": "object", "properties": {"content": {"type": "string"}}})
    assert result["content"] == "hi"
    assert result["_provider_info"]["model"] == "claude-opus-5"
    assert seen["output_config"]["format"]["type"] == "json_schema"
    # Current models reject sampling params — the provider must omit them.
    assert "temperature" not in seen


def test_anthropic_api_provider_sends_temperature_for_older_models() -> None:
    seen: dict = {}
    client = _FakeAnthropicClient(_FakeAPIResponse('{"ok": true}'), seen)
    provider = AnthropicAPIJSONProvider(model="claude-haiku-4-5", client=client)
    provider.generate_json("prompt", {"type": "object"}, temperature=0.35)
    assert seen["temperature"] == 0.35


def test_anthropic_api_provider_reports_errors_as_provider_error() -> None:
    seen: dict = {}
    client = _FakeAnthropicClient(RuntimeError("boom"), seen)
    provider = AnthropicAPIJSONProvider(model="claude-opus-5", client=client)
    result = provider.generate_json("prompt", {"type": "object"})
    assert result["status"] == "provider_error"
    assert result["error"] == "anthropic_api_error"


def test_anthropic_api_provider_reports_invalid_json() -> None:
    seen: dict = {}
    client = _FakeAnthropicClient(_FakeAPIResponse("not json at all"), seen)
    provider = AnthropicAPIJSONProvider(model="claude-opus-5", client=client)
    result = provider.generate_json("prompt", {"type": "object"})
    assert result["status"] == "provider_error"
    assert result["error"] == "anthropic_api_invalid_json"


def test_claude_code_provider_disables_tools_by_default(monkeypatch) -> None:
    seen = {}

    class Completed:
        returncode = 0
        stdout = json.dumps({"type": "result", "subtype": "success", "result": json.dumps({"ok": True})})
        stderr = ""

    def fake_run(invocation, *args, **kwargs):
        seen["invocation"] = invocation
        return Completed()

    monkeypatch.setattr("manyu.providers.subprocess.run", fake_run)
    ClaudeCodeJSONProvider(command=["claude"]).generate_json("prompt", {"type": "object"})
    assert "--disallowedTools" in seen["invocation"]


def test_reflective_turn_creates_inner_voice_mood_and_next_turn_bias() -> None:
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), ScenarioJSONProvider())
    first = core.process_reflective_turn({"event": make_event("evt_reflect_1", impact=-1.0).model_dump(mode="json"), "affect_threshold": 0.1})
    assert first["inner_voice"]["status"] == "ok"
    assert first["mood"]["label"] in {"guarded_repair", "open_repair", "steady_confidence", "open_attention"}
    second = core.process_reflective_turn({"event": make_event("evt_reflect_2", impact=0.2).model_dump(mode="json"), "affect_threshold": 0.1})
    assert second["prior_mood"]["label"] == first["mood"]["label"]
    assert "mood_bias_caution" in second["trace"]["appraisal"]["reason_codes"]


def test_inner_voice_governance_sanitizes_pressure_language() -> None:
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), UnsafeVoiceProvider())
    result = core.process_reflective_turn({"event": make_event("evt_voice_unsafe", impact=-0.8).model_dump(mode="json")})
    voice = result["inner_voice"]["inner_voice"]
    assert voice["safety_status"] == "sanitized"
    assert "prove you care" not in voice["utterance"].lower()


def test_mood_export_reset_and_timeline() -> None:
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), ScenarioJSONProvider())
    core.process_reflective_turn({"event": make_event("evt_mood_export", impact=-1.0).model_dump(mode="json")})
    exported = core.export_agent("agent_demo")
    assert exported["inner_voice_frames"]
    assert exported["mood_states"]
    timeline = timeline_from_store(core, "agent_demo")
    assert timeline["inner_voice_frames"]
    assert timeline["mood_states"]
    assert core.admin_reset("agent_demo", "test reset")["status"] == "reset"
    assert core.export_agent("agent_demo")["mood_states"] == []


def test_clear_mood_marks_active_mood_cleared() -> None:
    core = ManyuCore(ManyuStore(":memory:"), load_profile(), FrozenClock(), ScenarioJSONProvider())
    core.process_reflective_turn({"event": make_event("evt_clear_mood", impact=-1.0).model_dump(mode="json")})
    assert core.get_mood("agent_demo")["moods"]
    result = core.clear_mood("agent_demo", "test clear")
    assert result["records_changed"] == 1
    assert core.get_mood("agent_demo")["moods"] == []
    assert core.get_mood("agent_demo", include_inactive=True)["moods"][0]["status"] == "cleared"


def test_user_preference_candidate_is_allowed_as_worldview_fact() -> None:
    core = make_core()
    candidate = {
        "candidate_id": "bc_user_pref",
        "agent_id": "agent_demo",
        "proposition": "User Amitabh prefers agents that mention affective salience.",
        "belief_type": "interaction_pattern",
        "scope": "limited_observation",
        "confidence": 0.8,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
        "is_user_personalization": True,
    }
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [candidate]})
    assert result["accepted"]
    assert core.get_beliefs("agent_demo")["beliefs"][0]["scope"] == "limited_observation"


def test_action_guidance_candidate_is_rejected_as_non_worldview() -> None:
    core = make_core()
    candidate = {
        "candidate_id": "bc_should",
        "agent_id": "agent_demo",
        "proposition": "Manyu should treat feedback as useful.",
        "belief_type": "interaction_pattern",
        "scope": "human_agent_interaction",
        "confidence": 0.7,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
    }
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [candidate]})
    assert result["rejected"][0]["reason"] == "other"
    assert core.get_beliefs("agent_demo")["beliefs"] == []


def test_contested_belief_preserves_contradiction_revision() -> None:
    core = make_core()
    first = {
        "candidate_id": "bc_1",
        "agent_id": "agent_demo",
        "proposition": "Interaction traces are worldview evidence for Manyu.",
        "belief_type": "epistemic_principle",
        "scope": "agent_self",
        "confidence": 0.6,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
    }
    second = dict(first, candidate_id="bc_2", contradicts=["bel_external"])
    core.update_beliefs({"agent_id": "agent_demo", "candidates": [first]})
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [second]})
    belief = result["accepted"][0]
    assert belief["status"] == "contested"
    revisions = core.store.list_belief_revisions(belief["belief_id"])
    assert len(revisions) == 2


def test_supports_resolves_a_belief_key_to_a_belief_id() -> None:
    """The extractor names `belief_key`s; only the store knows ids.

    Without resolution the edge would be stored verbatim and then skipped by
    the `supports` traversal, giving a web that reads as connected and
    behaves as though it were not.
    """
    core = make_core()
    target = {
        "candidate_id": "bc_1",
        "agent_id": "agent_demo",
        "proposition": "Verification improves Manyu's outcomes.",
        "belief_key": "self_model/agent_self/verification-helps",
        "belief_type": "self_model",
        "scope": "agent_self",
        "confidence": 0.6,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
    }
    core.update_beliefs({"agent_id": "agent_demo", "candidates": [target]})
    target_id = core.store.list_beliefs("agent_demo", include_inactive=True)[0].belief_id

    dependent = dict(
        target,
        candidate_id="bc_2",
        proposition="Checking a claim before acting pays off.",
        belief_key="self_model/agent_self/checking-pays-off",
        evidence_ids=["bev_2"],
        supports=["self_model/agent_self/verification-helps"],
    )
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [dependent]})
    assert result["accepted"][0]["supports"] == [target_id]


def test_supports_resolves_a_sibling_emitted_later_in_the_same_batch() -> None:
    """Edge survival must not depend on the order the extractor emits.

    Stage-0 probe: every edge the live extractor emitted named a sibling, and
    under single-pass resolution 46% were lost purely to ordering (3/3 kept
    when the general principle came first, 0/3 when it came last). This uses
    the losing order.
    """
    core = make_core()
    base = {
        "agent_id": "agent_demo",
        "belief_type": "self_model",
        "scope": "agent_self",
        "confidence": 0.6,
        "source_mix": {"manyu_experience": 1.0},
    }
    supporters = [
        dict(
            base,
            candidate_id=f"bc_{i}",
            proposition=f"Specific observation {i}.",
            belief_key=f"self_model/agent_self/observation-{i}",
            evidence_ids=[f"bev_{i}"],
            supports=["epistemic_principle/general/verify-before-acting"],
        )
        for i in (1, 2, 3)
    ]
    # The target is emitted last — the case that used to lose every edge.
    target = {
        "candidate_id": "bc_4",
        "agent_id": "agent_demo",
        "proposition": "Verifying before acting prevents errors.",
        "belief_key": "epistemic_principle/general/verify-before-acting",
        "belief_type": "epistemic_principle",
        "scope": "general",
        "confidence": 0.7,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_4"],
    }
    core.update_beliefs({"agent_id": "agent_demo", "candidates": [*supporters, target]})

    stored = {b.belief_key: b for b in core.store.list_beliefs("agent_demo", include_inactive=True)}
    target_id = stored["epistemic_principle/general/verify-before-acting"].belief_id
    for i in (1, 2, 3):
        assert stored[f"self_model/agent_self/observation-{i}"].supports == [target_id]


def test_a_self_referential_edge_is_dropped() -> None:
    core = make_core()
    candidate = {
        "candidate_id": "bc_1",
        "agent_id": "agent_demo",
        "proposition": "Verifying before acting prevents errors.",
        "belief_key": "epistemic_principle/general/verify-before-acting",
        "belief_type": "epistemic_principle",
        "scope": "general",
        "confidence": 0.7,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
        "supports": ["epistemic_principle/general/verify-before-acting"],
    }
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [candidate]})
    assert result["accepted"][0]["supports"] == []


def test_unresolvable_edges_drop_supports_but_keep_contradicts() -> None:
    """The asymmetry is deliberate — see `BeliefUpdater._resolve_edges`."""
    core = make_core()
    candidate = {
        "candidate_id": "bc_1",
        "agent_id": "agent_demo",
        "proposition": "Interaction traces are worldview evidence for Manyu.",
        "belief_type": "epistemic_principle",
        "scope": "agent_self",
        "confidence": 0.6,
        "source_mix": {"manyu_experience": 1.0},
        "evidence_ids": ["bev_1"],
        "supports": ["nothing/matches/this"],
        "contradicts": ["bel_never_stored"],
    }
    result = core.update_beliefs({"agent_id": "agent_demo", "candidates": [candidate]})
    belief = result["accepted"][0]
    # `supports` is only ever an edge; pointing nowhere it overstates connectivity.
    assert belief["supports"] == []
    # `contradicts` also flips status, and that must survive an unstored counterpart.
    assert belief["contradicts"] == ["bel_never_stored"]
    assert belief["status"] == "contested"


def test_review_beliefs_adds_emotional_trigger_beliefs() -> None:
    core = make_core()
    core.submit_event(make_event("evt_1", impact=-1.0))
    result = core.review_beliefs({"agent_id": "agent_demo", "affect_threshold": 0.1})
    assert result["reflection"]["accepted"]
    beliefs = core.get_beliefs("agent_demo", query="trigger strong")
    assert beliefs["beliefs"]
    assert beliefs["beliefs"][0]["belief_type"] == "self_model"


def test_belief_governance_export_redact_reset() -> None:
    core = make_core()
    core.update_beliefs(
        {
            "agent_id": "agent_demo",
            "candidates": [
                {
                    "candidate_id": "bc_1",
                    "agent_id": "agent_demo",
                    "proposition": "Manyu can hold bounded agent-specific views.",
                    "belief_type": "self_model",
                    "scope": "agent_self",
                    "confidence": 0.7,
                    "source_mix": {"manyu_experience": 1.0},
                    "evidence_ids": ["bev_1"],
                }
            ],
        }
    )
    exported = core.export_agent("agent_demo")
    assert exported["beliefs"]
    assert core.redact_agent("agent_demo", "agent_x")["records_changed"] > 0
    assert core.admin_reset("agent_demo", "test reset")["status"] == "reset"
    assert core.export_agent("agent_demo")["beliefs"] == []


def test_opinion_without_relevant_belief_is_bounded() -> None:
    core = make_core()
    opinion = core.express_opinion({"agent_id": "agent_demo", "question": "What is your view on cities?"})
    assert opinion["has_settled_view"] is False
    assert "do not have a settled" in opinion["stance"]


def test_mcp_server_registers_belief_tools() -> None:
    app = create_server(db_path=":memory:")
    tools = asyncio.run(app.list_tools())
    names = {tool.name for tool in tools}
    assert "manyu_capture_belief_evidence" in names
    assert "manyu_update_beliefs" in names
    assert "manyu_express_opinion" in names
    assert "manyu_process_reflective_turn" in names
    assert "manyu_read_inner_voice" in names
    assert "manyu_get_mood" in names
    # Experiment #3's engine had no surface at all until these were added:
    # nothing outside its own tests could drive a retraction.
    assert "manyu_retract_belief" in names
    assert "manyu_assert_contradiction" in names


def test_cli_revision_commands_drive_the_engine(tmp_path, capsys) -> None:
    """The surface must work across processes, not just in-memory.

    Contradictions are priced in one invocation and the propagation in the
    next has to see the suppressed value, or the CLI is only pretending to
    expose the engine.
    """
    from manyu.core import ManyuCore
    from manyu.fork import BeliefSpec, seed_beliefs

    db = tmp_path / "manyu.sqlite3"
    ids = seed_beliefs(
        ManyuCore.from_paths(db_path=str(db)),
        [
            BeliefSpec(key="p", proposition="P.", confidence=0.8),
            BeliefSpec(key="q", proposition="Q.", confidence=0.8),
            BeliefSpec(key="s", proposition="S.", confidence=0.8, supports=("p",)),
        ],
    )

    assert cli_main(["--db", str(db), "assert-contradiction", "--contradictor-id", ids["q"], "--target-id", ids["p"], "--arm", "direct"]) == 0
    suppressed = json.loads(capsys.readouterr().out)
    assert suppressed["status"] == "ok"
    assert suppressed["steps"][0]["delta"] < 0

    assert cli_main(["--db", str(db), "retract-belief", "--belief-id", ids["s"], "--arm", "direct"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["max_depth_reached"] == 1
    propagated = next(s for s in result["steps"] if s["depth"] == 1)
    assert propagated["before"] == pytest.approx(suppressed["steps"][0]["after"]), (
        "the second process must see the first's suppression"
    )


def test_cli_revision_commands_exit_nonzero_on_error(tmp_path) -> None:
    """Review finding 4.

    Both commands printed the error payload and returned 0, so a harness
    driving retractions in bulk would treat a stale belief id or a rejected
    argument as a completed manipulation and carry on.
    """
    db = tmp_path / "manyu.sqlite3"
    assert cli_main(["--db", str(db), "retract-belief", "--belief-id", "bel_typo", "--arm", "direct"]) == 1
    assert cli_main(["--db", str(db), "assert-contradiction", "--contradictor-id", "bel_a", "--target-id", "bel_b", "--arm", "direct"]) == 1


def test_revision_surface_reports_errors_rather_than_raising() -> None:
    core = make_core()
    beliefs = core.update_beliefs({"agent_id": "agent_demo", "candidates": [{
        "candidate_id": "bc_1", "agent_id": "agent_demo", "proposition": "P.",
        "belief_type": "world_model", "scope": "general", "confidence": 0.8,
        "source_mix": {"operator_note": 1.0}, "evidence_ids": ["bev_1"],
    }]})
    belief_id = beliefs["accepted"][0]["belief_id"]

    # `arm` is deliberately not defaulted — requirements §5 is the caller's call.
    assert core.retract_belief({"belief_id": belief_id})["status"] == "error"
    assert core.retract_belief({"arm": "direct"})["status"] == "error"
    assert core.retract_belief({"belief_id": "bel_missing", "arm": "direct"})["status"] == "error"
    assert core.assert_contradiction({"contradictor_id": belief_id, "arm": "direct"})["status"] == "error"

    raised = core.retract_belief({"belief_id": belief_id, "arm": "direct", "to_confidence": 0.99})
    assert raised["status"] == "error" and "must not raise" in raised["error"]


def test_cli_belief_commands_return_json(tmp_path, capsys) -> None:
    db = tmp_path / "manyu.sqlite3"
    assert cli_main(["--db", str(db), "capture-belief-evidence", "--source-type", "operator_note", "--source-id", "note_1", "--summary", "Worldview note."]) == 0
    captured = capsys.readouterr()
    assert "belief_evidence" in captured.out
    assert cli_main(["--db", str(db), "beliefs"]) == 0
    captured = capsys.readouterr()
    assert '"beliefs"' in captured.out


def test_cli_mood_commands_return_json(tmp_path, capsys) -> None:
    db = tmp_path / "manyu.sqlite3"
    payload = {"event": make_event("evt_cli_mood", impact=-0.8).model_dump(mode="json")}
    assert cli_main(["--db", str(db), "--scenario-provider", "process-turn", "--payload", json.dumps(payload)]) == 0
    captured = capsys.readouterr()
    assert '"inner_voice"' in captured.out
    assert '"mood"' in captured.out
    assert cli_main(["--db", str(db), "mood", "--include-inactive"]) == 0
    captured = capsys.readouterr()
    assert '"moods"' in captured.out


def test_cli_process_scenario_writes_reflective_timeline(tmp_path, capsys) -> None:
    db = tmp_path / "manyu.sqlite3"
    out = tmp_path / "timeline.json"
    assert cli_main(["--db", str(db), "--scenario-provider", "process-scenario", "evals/fixtures/everyday_collaboration_mood.json", "--out", str(out)]) == 0
    captured = capsys.readouterr()
    assert '"status": "written"' in captured.out
    timeline = json.loads(out.read_text(encoding="utf-8"))
    assert timeline["mode"] == "reflective"
    assert len(timeline["turns"]) >= 7
    assert timeline["inner_voice_frames"]
    assert timeline["mood_states"]
