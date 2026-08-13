from __future__ import annotations

import hashlib
import json
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


#: The `metadata["corpus"]` tag a record must carry to be swept into a CORPUS
#: snapshot. A literal rather than an import from the experiment module, because
#: `snapshotting` is substrate and must not depend on an experiment.
CORPUS_TAG = "exp08"


def _corpus_digest(payload: dict[str, Any]) -> str:
    """Content hash over what was *ingested*, not over what the store *assigned*.

    The distinction is the whole design. A digest over the raw payload varies
    between two ingests of a byte-identical corpus, because `belief_id` is minted
    from `uuid4` and `created_at` from the clock — so it would certify the run
    rather than the corpus, which is the defect this function exists to avoid and
    which `uuid4` snapshot ids already have.

    Projected out, therefore: store-minted identifiers, timestamps, and the
    ingest arithmetic (`confidence`, `stability`, `status`). None of them is the
    corpus. A confidence that moved because `blend_confidence` changed is not a
    re-transcription, and FR-7 guards re-transcription.

    Projected in: the documents, the evidence records, and each instance's
    declared identity, text and citations.

    **Constraint on the loader, stated because it is load-bearing:** evidence ids
    must be caller-supplied and content-derived. A corpus ingested with
    `uuid4`-minted evidence ids cannot produce a stable digest, and the freeze
    would silently degrade to a timestamp.

    `sort_keys` and fixed separators make the rendering reproducible across
    processes. Truncated to 16 hex characters on `counterfactual.build_receipt`'s
    precedent.
    """
    material = {
        "slot": payload["slot"],
        "documents": payload["documents"],
        "evidence": [
            {key: value for key, value in record.items() if key not in _VOLATILE_RECORD_FIELDS}
            for record in payload["evidence"]
        ],
        "claim_instances": [
            {
                "belief_key": instance.get("belief_key"),
                "proposition": instance["proposition"],
                "belief_type": instance["belief_type"],
                "scope": instance["scope"],
                "evidence_ids": sorted(instance["evidence_ids"]),
            }
            for instance in payload["claim_instances"]
        ],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


#: Assigned by the store or the clock rather than carried by the document.
_VOLATILE_RECORD_FIELDS = frozenset({"created_at"})


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
        elif target.kind == ReportTargetKind.CORPUS:
            payload = self._corpus_payload(agent_id, target)
        else:
            raise ValueError(f"unsupported target kind: {target.kind}")

        if target.kind == ReportTargetKind.CORPUS:
            # Two deliberate asymmetries, and they depend on each other.
            #
            # The affect trio is omitted. A corpus snapshot certifies *which
            # documents were ingested*; the agent's mood while ingesting them is
            # not part of that, and it is mutable. Carrying a mutable field under
            # a content-derived id would make the id claim a sameness the payload
            # contradicts.
            #
            # The id is then derived from the payload rather than minted from
            # `uuid4`. With `uuid4`, two runs over a byte-identical corpus get
            # different ids, so the id certifies *when* rather than *what* — and
            # FR-7 exists precisely to detect a re-transcription, which
            # requirements section 5.2 shows the store performs in place with no
            # revision trail. A uuid there would make the requirement decorative.
            # Follows `counterfactual.build_receipt`'s `cfr_{sha256[:16]}`.
            snapshot_id = f"snap_{_corpus_digest(payload)}"
        else:
            payload["affect_state"] = self._affect_state(agent_id)
            payload["active_mood"] = self._active_mood(agent_id)
            payload["recent_inner_voice"] = self._recent_inner_voice(agent_id)
            snapshot_id = _id("snap")

        snapshot = LogSnapshot(
            snapshot_id=snapshot_id,
            agent_id=agent_id,
            target=target,
            payload=payload,
            created_at=self.clock.now(),
        )
        self.store.save_log_snapshot(snapshot)
        return snapshot

    def _corpus_payload(self, agent_id: str, target: ReportTarget) -> dict[str, Any]:
        """Freeze one slot's claim-instances and the records behind them.

        `target.id_or_text` is the slot label. Selection is by
        `metadata["corpus"]` and `metadata["slot"]` — never by word overlap.
        `_position_payload`'s matching heuristic would make the payload depend on
        the target *string*, and a snapshot whose contents shift with its own
        label cannot certify anything.

        Everything is sorted, because a digest over store iteration order is a
        digest over nothing (`underdetermination.find_rival_sets` states the
        general form of this rule).
        """
        slot = target.id_or_text
        records = [
            record
            for record in self.store.list_belief_evidence(agent_id)
            if record.metadata.get("corpus") == CORPUS_TAG and record.metadata.get("slot") == slot
        ]
        records.sort(key=lambda record: record.evidence_id)
        record_ids = {record.evidence_id for record in records}

        instances = [
            belief
            for belief in self.store.list_beliefs(agent_id, include_inactive=True)
            if record_ids.intersection(belief.evidence_ids)
        ]
        # Sorted by *declared* key, not by `belief_id`. `belief_id` is minted from
        # `uuid4`, so ordering by it would make the list order — and therefore the
        # digest — vary between two ingests of an identical corpus. That is the
        # same defect as digesting the id itself, arriving through sequence
        # instead of through content.
        instances.sort(key=lambda belief: (belief.belief_key or "", belief.proposition))

        documents: dict[str, dict[str, Any]] = {}
        for record in records:
            entry = documents.setdefault(
                record.source_id,
                {
                    "citation": record.metadata.get("citation"),
                    "published": record.metadata.get("published"),
                    "content_sha256": record.metadata.get("content_sha256"),
                    "records": 0,
                },
            )
            entry["records"] += 1

        return {
            "slot": slot,
            "claim_instances": [belief.model_dump(mode="json") for belief in instances],
            "evidence": [record.model_dump(mode="json") for record in records],
            "documents": {key: documents[key] for key in sorted(documents)},
        }

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
