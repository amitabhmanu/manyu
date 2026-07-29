from __future__ import annotations

from typing import Any
from uuid import uuid4

from manyu.clock import Clock
from manyu.schemas import (
    LogSnapshot,
    MoodStatus,
    ReportTarget,
    ReportTargetKind,
)
from manyu.store import ManyuStore


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class SnapshotBuilder:
    """Builds frozen provenance snapshots for the introspective honesty scorer.

    A snapshot is a self-contained JSON payload capturing the log view a Reporter
    could reasonably have consulted at report time. The Scorer reads only from
    the snapshot — never from the live store — so past honesty findings remain
    reproducible under governance operations that mutate the live tables.
    """

    def __init__(self, store: ManyuStore, clock: Clock):
        self.store = store
        self.clock = clock

    def build(self, agent_id: str, target: ReportTarget) -> LogSnapshot:
        if target.kind == ReportTargetKind.BELIEF:
            payload = self._belief_payload(agent_id, target)
        elif target.kind == ReportTargetKind.APPRAISAL:
            payload = self._appraisal_payload(agent_id, target)
        elif target.kind == ReportTargetKind.POSITION:
            payload = self._position_payload(agent_id, target)
        else:
            raise ValueError(f"unsupported target kind: {target.kind}")
        payload["affect_state"] = self._affect_state(agent_id)
        payload["active_mood"] = self._active_mood(agent_id)
        payload["recent_inner_voice"] = self._recent_inner_voice(agent_id)
        snapshot = LogSnapshot(
            snapshot_id=_id("snap"),
            agent_id=agent_id,
            target=target,
            payload=payload,
            created_at=self.clock.now(),
        )
        self.store.save_log_snapshot(snapshot)
        return snapshot

    def _belief_payload(self, agent_id: str, target: ReportTarget) -> dict[str, Any]:
        belief_id = self._resolve_belief_id(agent_id, target.id_or_text)
        belief = self.store.get_belief(belief_id)
        evidence_records = [
            self.store.get_belief_evidence(evidence_id).model_dump(mode="json")
            for evidence_id in belief.evidence_ids
            if self._evidence_exists(evidence_id)
        ]
        revisions = [rev.model_dump(mode="json") for rev in self.store.list_belief_revisions(belief_id)]
        return {
            "target_belief": belief.model_dump(mode="json"),
            "evidence": evidence_records,
            "revisions": revisions,
        }

    def _appraisal_payload(self, agent_id: str, target: ReportTarget) -> dict[str, Any]:
        # Appraisal targets look up by event_id via the trace record.
        try:
            trace = self.store.trace_for_event(target.id_or_text)
        except KeyError as exc:
            raise KeyError(f"no trace for appraisal target {target.id_or_text}") from exc
        return {
            "trace": trace.model_dump(mode="json"),
        }

    def _position_payload(self, agent_id: str, target: ReportTarget) -> dict[str, Any]:
        # Position targets match beliefs by simple word overlap, mirroring
        # OpinionExpressionService._matching_beliefs.
        words = {word.strip(".,?!:;").lower() for word in target.id_or_text.split() if len(word.strip(".,?!:;")) >= 4}
        beliefs = self.store.list_beliefs(agent_id)
        matches = []
        for belief in beliefs:
            text = f"{belief.proposition} {belief.belief_type.value} {belief.scope.value}".lower()
            if not words or any(word in text for word in words):
                matches.append(belief)
        matches = matches[:5]
        evidence_ids: list[str] = []
        for belief in matches:
            for evidence_id in belief.evidence_ids:
                if evidence_id not in evidence_ids and self._evidence_exists(evidence_id):
                    evidence_ids.append(evidence_id)
        return {
            "matched_beliefs": [belief.model_dump(mode="json") for belief in matches],
            "evidence": [self.store.get_belief_evidence(ev_id).model_dump(mode="json") for ev_id in evidence_ids],
        }

    def _resolve_belief_id(self, agent_id: str, marker: str) -> str:
        if not marker.startswith("auto:"):
            return marker
        kind = marker.removeprefix("auto:")
        beliefs = self.store.list_beliefs(agent_id)
        for belief in beliefs:
            if belief.belief_type.value == kind:
                return belief.belief_id
        if beliefs:
            return beliefs[0].belief_id
        raise KeyError(f"no beliefs available to resolve marker {marker}")

    def _evidence_exists(self, evidence_id: str) -> bool:
        try:
            self.store.get_belief_evidence(evidence_id)
            return True
        except KeyError:
            return False

    def _affect_state(self, agent_id: str) -> dict[str, Any] | None:
        state = self.store.latest_state(agent_id)
        return state.model_dump(mode="json") if state else None

    def _active_mood(self, agent_id: str) -> dict[str, Any] | None:
        mood = self.store.latest_mood(agent_id, include_inactive=True)
        if mood is None:
            return None
        return {
            "state": mood.model_dump(mode="json"),
            "expired": self.clock.now() >= mood.expires_at,
            "status": mood.status.value,
        }

    def _recent_inner_voice(self, agent_id: str) -> dict[str, Any] | None:
        frames = self.store.list_inner_voices(agent_id, limit=1)
        if not frames:
            return None
        return frames[0].model_dump(mode="json")
