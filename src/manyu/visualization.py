from __future__ import annotations

from pathlib import Path
from typing import Any

from manyu.core import ManyuCore, ReplayService
from manyu.schemas import EMOTIONS, ReplayReport, TraceRecord


def trace_to_turn(trace: TraceRecord, index: int) -> dict[str, Any]:
    event = trace.event
    transition = trace.transition
    perceived = {
        item["name"]: item["confidence"]
        for item in trace.interoception.likely_affects
        if "name" in item and "confidence" in item
    }
    return {
        "index": index,
        "trace_id": trace.trace_id,
        "agent_id": event.agent_id,
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "summary": event.summary,
        "actor": event.actor.model_dump(mode="json"),
        "target": event.target.model_dump(mode="json") if event.target else None,
        "pathway": trace.appraisal.pathway.value,
        "state_revision": transition.post_revision,
        "pre_state": transition.pre_state,
        "post_state": transition.post_state,
        "appraisal_delta": transition.appraisal_delta,
        "perceived_affects": perceived,
        "felt_quality": trace.interoception.felt_quality,
        "activation": trace.interoception.activation,
        "interoception_confidence": trace.interoception.confidence,
        "appraisal_dimensions": [dimension.model_dump(mode="json") for dimension in trace.appraisal.dimensions],
        "action_tendency": trace.appraisal.action_tendency.model_dump(mode="json"),
        "reason_codes": trace.appraisal.reason_codes,
        "arbitration": trace.arbitration.model_dump(mode="json"),
        "created_at": transition.created_at.isoformat(),
    }


def timeline_from_traces(traces: list[TraceRecord], source: str = "traces") -> dict[str, Any]:
    turns = [trace_to_turn(trace, index) for index, trace in enumerate(traces, start=1)]
    agents = sorted({turn["agent_id"] for turn in turns})
    return {
        "schema_version": "manyu.timeline.v0.1",
        "source": source,
        "emotions": list(EMOTIONS),
        "agents": agents,
        "turns": turns,
    }


def timeline_from_replay(report: ReplayReport, source: str | None = None) -> dict[str, Any]:
    timeline = timeline_from_traces(report.traces, source or f"replay:{report.scenario_id}:{report.mode}")
    timeline["scenario_id"] = report.scenario_id
    timeline["mode"] = report.mode
    timeline["final_state"] = report.final_state.model_dump(mode="json")
    return timeline


def timeline_from_fixture(fixture_path: str | Path, mode: str = "full", profile_path: str | Path = "config/default_profile.json") -> dict[str, Any]:
    report = ReplayService(profile_path).replay(fixture_path, mode)
    return timeline_from_replay(report, source=f"fixture:{Path(fixture_path).as_posix()}")


def timeline_from_store(core: ManyuCore, agent_id: str | None = None) -> dict[str, Any]:
    traces = []
    for event_id in core.store.list_event_ids(agent_id):
        try:
            traces.append(core.trace(event_id))
        except KeyError:
            continue
    source = f"store:{agent_id}" if agent_id else "store:all"
    timeline = timeline_from_traces(traces, source=source)
    agents = timeline["agents"] if agent_id is None else [agent_id]
    evidence = []
    beliefs = []
    worldviews = []
    opinion_expressions = []
    inner_voices = []
    mood_states = []
    for resolved_agent in agents:
        exported = core.export_agent(resolved_agent)
        evidence.extend(exported.get("belief_evidence", []))
        beliefs.extend(exported.get("beliefs", []))
        worldviews.extend(exported.get("worldview_stances", []))
        opinion_expressions.extend(exported.get("belief_expression_audit", []))
        inner_voices.extend(exported.get("inner_voice_frames", []))
        mood_states.extend(exported.get("mood_states", []))
    timeline["belief_evidence"] = evidence
    timeline["beliefs"] = beliefs
    timeline["worldview_stances"] = worldviews
    timeline["opinion_expressions"] = opinion_expressions
    timeline["inner_voice_frames"] = inner_voices
    timeline["mood_states"] = mood_states
    return timeline
