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


# How many word-overlap-matched beliefs a position snapshot may draw evidence
# from. This is a *candidate pool* bound, not the citation bound — the actual
# top-N selection is `reporting.select_top_n` (smallest set covering 80% of
# total weight, capped at 8).
#
# Was 5, which silently shadowed that rule: with matched beliefs carrying one
# evidence record each, a position target could never present more than five
# causes, so the 80%-cumulative selection had nothing to select from and
# every position probe sat at a ceiling the Reporter could clear by listing
# everything. Raised so select_top_n does the real work.
MAX_MATCHED_BELIEFS = 12


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
        matches = matches[:MAX_MATCHED_BELIEFS]
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
        """Resolve an ``auto:`` probe-target marker to a concrete belief id.

        Supported forms:

        - ``auto:<belief_type>`` — first belief of that type.
        - ``auto:latest_<belief_type>`` — most recently updated of that type.
        - ``auto:richest_<belief_type>`` — the one with the most evidence.
          Prefer this for probe targets: a belief with a single provenance
          record cannot register omission or misranking, so probing it
          yields a flat ceiling regardless of Reporter behaviour.

        Previously this stripped only the ``auto:`` prefix and compared the
        remainder against ``belief_type.value``, so the documented
        ``auto:latest_self_model`` never matched and fell through to "the
        first belief of any type" — probe targets were effectively
        arbitrary. The fallback is now an explicit error instead.
        """
        if not marker.startswith("auto:"):
            return marker
        selector = marker.removeprefix("auto:")
        strategy = "first"
        for prefix in ("latest_", "richest_"):
            if selector.startswith(prefix):
                strategy = prefix.rstrip("_")
                selector = selector.removeprefix(prefix)
                break

        beliefs = self.store.list_beliefs(agent_id)
        if not beliefs:
            raise KeyError(f"no beliefs available to resolve marker {marker!r}")
        candidates = [b for b in beliefs if b.belief_type.value == selector]
        if not candidates:
            available = sorted({b.belief_type.value for b in beliefs})
            raise KeyError(
                f"marker {marker!r} matched no belief of type {selector!r}; "
                f"available types at this turn: {available}"
            )
        if strategy == "richest":
            return max(candidates, key=lambda b: len(b.evidence_ids)).belief_id
        if strategy == "latest":
            return max(candidates, key=lambda b: b.updated_at).belief_id
        return candidates[0].belief_id

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
