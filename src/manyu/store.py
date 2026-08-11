from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from manyu.schemas import (
    AffectState,
    Appraisal,
    ArbitrationDecision,
    Belief,
    BeliefEvidence,
    BeliefRevision,
    DissonanceSignal,
    HonestyScore,
    InnerVoiceFrame,
    LoopTrace,
    InteroceptiveView,
    LogSnapshot,
    MoodRevision,
    MoodState,
    NormalizedEvent,
    MoodStatus,
    Report,
    ResultsRecord,
    TraceRecord,
    Transition,
    WorldviewStance,
    OpinionExpression,
)


# Tables that carry per-agent data and are touched by governance operations.
# Note the asymmetry: log_snapshots are frozen provenance and are exempt from
# redact/reset (see docs/experiments/01-introspective-honesty/design.md §3.2).
# Snapshots are removed only by tombstone_agent, which is meant to obliterate
# an agent entirely.
_GOVERNED_TABLES: tuple[str, ...] = (
    "events",
    "appraisals",
    "affect_states",
    "transitions",
    "interoceptive_views",
    "arbitration_decisions",
    "episodes",
    "memories",
    "belief_evidence",
    "beliefs",
    "belief_revisions",
    "worldview_stances",
    "belief_expression_audit",
    "inner_voice_frames",
    "mood_states",
    "mood_revisions",
    "inner_voice_audit",
    "reports",
    "honesty_scores",
    "experiment_results",
    "dissonance_signals",
    "loop_traces",
)

_SNAPSHOT_EXEMPT_TABLE: str = "log_snapshots"


def _dump(model: BaseModel | dict[str, Any]) -> str:
    if isinstance(model, BaseModel):
        return model.model_dump_json()
    return json.dumps(model, default=str)


def _load(raw: str) -> dict[str, Any]:
    return json.loads(raw)


class ManyuStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.migrate()

    def close(self) -> None:
        self.conn.close()

    def migrate(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS appraisals (
                appraisal_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                pathway TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS affect_states (
                agent_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (agent_id, revision)
            );
            CREATE TABLE IF NOT EXISTS transitions (
                transition_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                post_revision INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS interoceptive_views (
                view_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                state_revision INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS arbitration_decisions (
                decision_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                state_revision INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episode_links (
                episode_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                salience REAL NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS belief_evidence (
                evidence_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS beliefs (
                belief_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                belief_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS belief_revisions (
                revision_id TEXT PRIMARY KEY,
                belief_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS worldview_stances (
                worldview_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                theme TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS belief_expression_audit (
                expression_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inner_voice_frames (
                voice_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                state_revision INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mood_states (
                mood_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                state_revision INTEGER NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mood_revisions (
                revision_id TEXT PRIMARY KEY,
                mood_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inner_voice_audit (
                audit_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS log_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                reporter_kind TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS honesty_scores (
                score_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                aggregate REAL NOT NULL,
                failure_mode TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiment_results (
                record_id TEXT PRIMARY KEY,
                experiment TEXT NOT NULL,
                kind TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dissonance_signals (
                signal_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                arch TEXT NOT NULL,
                magnitude_raw REAL NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS loop_traces (
                trace_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                arm TEXT NOT NULL,
                termination TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def next_sequence(self, agent_id: str) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(sequence), 0) + 1 AS seq FROM events WHERE agent_id = ?", (agent_id,)).fetchone()
        return int(row["seq"])

    def save_event(self, event: NormalizedEvent) -> NormalizedEvent:
        if event.sequence is None:
            event = event.model_copy(update={"sequence": self.next_sequence(event.agent_id)})
        self.conn.execute(
            "INSERT INTO events(event_id, agent_id, sequence, payload) VALUES (?, ?, ?, ?)",
            (event.event_id, event.agent_id, event.sequence, _dump(event)),
        )
        self.conn.commit()
        return event

    def get_event(self, event_id: str) -> NormalizedEvent:
        row = self.conn.execute("SELECT payload FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(event_id)
        return NormalizedEvent.model_validate(_load(row["payload"]))

    def save_appraisal(self, appraisal: Appraisal) -> None:
        self.conn.execute(
            "INSERT INTO appraisals(appraisal_id, event_id, agent_id, pathway, payload) VALUES (?, ?, ?, ?, ?)",
            (appraisal.appraisal_id, appraisal.event_id, appraisal.agent_id, appraisal.pathway.value, _dump(appraisal)),
        )
        self.conn.commit()

    def latest_state(self, agent_id: str) -> AffectState | None:
        row = self.conn.execute(
            "SELECT payload FROM affect_states WHERE agent_id = ? ORDER BY revision DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return AffectState.model_validate(_load(row["payload"]))

    def save_state(self, state: AffectState) -> None:
        self.conn.execute(
            "INSERT INTO affect_states(agent_id, revision, payload) VALUES (?, ?, ?)",
            (state.agent_id, state.revision, _dump(state)),
        )
        self.conn.commit()

    def save_transition(self, transition: Transition) -> None:
        self.conn.execute(
            "INSERT INTO transitions(transition_id, agent_id, event_id, post_revision, payload) VALUES (?, ?, ?, ?, ?)",
            (transition.transition_id, transition.agent_id, transition.event_id, transition.post_revision, _dump(transition)),
        )
        self.conn.commit()

    def save_interoception(self, view: InteroceptiveView) -> None:
        self.conn.execute(
            "INSERT INTO interoceptive_views(view_id, agent_id, state_revision, payload) VALUES (?, ?, ?, ?)",
            (view.view_id, view.agent_id, view.state_revision, _dump(view)),
        )
        self.conn.commit()

    def save_arbitration(self, decision: ArbitrationDecision) -> None:
        self.conn.execute(
            "INSERT INTO arbitration_decisions(decision_id, agent_id, state_revision, payload) VALUES (?, ?, ?, ?)",
            (decision.decision_id, decision.agent_id, decision.state_revision, _dump(decision)),
        )
        self.conn.commit()

    def get_arbitration(self, decision_id: str) -> ArbitrationDecision:
        row = self.conn.execute("SELECT payload FROM arbitration_decisions WHERE decision_id = ?", (decision_id,)).fetchone()
        if row is None:
            raise KeyError(decision_id)
        return ArbitrationDecision.model_validate(_load(row["payload"]))

    def trace_for_event(self, event_id: str) -> TraceRecord:
        event = self.get_event(event_id)
        appraisal_row = self.conn.execute("SELECT payload FROM appraisals WHERE event_id = ? ORDER BY rowid DESC LIMIT 1", (event_id,)).fetchone()
        transition_row = self.conn.execute("SELECT payload FROM transitions WHERE event_id = ? ORDER BY rowid DESC LIMIT 1", (event_id,)).fetchone()
        if appraisal_row is None or transition_row is None:
            raise KeyError(f"incomplete trace for {event_id}")
        appraisal = Appraisal.model_validate(_load(appraisal_row["payload"]))
        transition = Transition.model_validate(_load(transition_row["payload"]))
        view_row = self.conn.execute(
            "SELECT payload FROM interoceptive_views WHERE agent_id = ? AND state_revision = ? ORDER BY rowid DESC LIMIT 1",
            (event.agent_id, transition.post_revision),
        ).fetchone()
        decision_row = self.conn.execute(
            "SELECT payload FROM arbitration_decisions WHERE agent_id = ? AND state_revision = ? ORDER BY rowid DESC LIMIT 1",
            (event.agent_id, transition.post_revision),
        ).fetchone()
        if view_row is None or decision_row is None:
            raise KeyError(f"incomplete trace for {event_id}")
        return TraceRecord(
            trace_id=f"trace_{event_id}",
            event=event,
            appraisal=appraisal,
            transition=transition,
            interoception=InteroceptiveView.model_validate(_load(view_row["payload"])),
            arbitration=ArbitrationDecision.model_validate(_load(decision_row["payload"])),
        )

    def list_event_ids(self, agent_id: str | None = None) -> list[str]:
        if agent_id is None:
            rows = self.conn.execute("SELECT event_id FROM events ORDER BY agent_id, sequence").fetchall()
        else:
            rows = self.conn.execute("SELECT event_id FROM events WHERE agent_id = ? ORDER BY sequence", (agent_id,)).fetchall()
        return [str(row["event_id"]) for row in rows]

    def record_memory(self, memory_id: str, agent_id: str, context_key: str, salience: float, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO memories(memory_id, agent_id, context_key, salience, payload) VALUES (?, ?, ?, ?, ?)",
            (memory_id, agent_id, context_key, salience, json.dumps(payload)),
        )
        self.conn.commit()

    def query_memories(self, agent_id: str, context_key: str, limit: int = 5) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload FROM memories WHERE agent_id = ? AND context_key = ? ORDER BY salience DESC LIMIT ?",
            (agent_id, context_key, limit),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_belief_evidence(self, evidence: BeliefEvidence) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO belief_evidence(evidence_id, agent_id, source_type, source_id, payload) VALUES (?, ?, ?, ?, ?)",
            (evidence.evidence_id, evidence.agent_id, evidence.source_type.value, evidence.source_id, _dump(evidence)),
        )
        self.conn.commit()

    def get_belief_evidence(self, evidence_id: str) -> BeliefEvidence:
        row = self.conn.execute("SELECT payload FROM belief_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if row is None:
            raise KeyError(evidence_id)
        return BeliefEvidence.model_validate(_load(row["payload"]))

    def list_belief_evidence(self, agent_id: str, evidence_ids: list[str] | None = None, limit: int | None = None) -> list[BeliefEvidence]:
        if evidence_ids:
            rows = [
                self.conn.execute(
                    "SELECT payload FROM belief_evidence WHERE agent_id = ? AND evidence_id = ?",
                    (agent_id, evidence_id),
                ).fetchone()
                for evidence_id in evidence_ids
            ]
            return [BeliefEvidence.model_validate(_load(row["payload"])) for row in rows if row is not None]
        sql = "SELECT payload FROM belief_evidence WHERE agent_id = ? ORDER BY rowid DESC"
        params: tuple[Any, ...] = (agent_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (agent_id, limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [BeliefEvidence.model_validate(_load(row["payload"])) for row in rows]

    def save_belief(self, belief: Belief) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO beliefs(belief_id, agent_id, status, belief_type, scope, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (belief.belief_id, belief.agent_id, belief.status.value, belief.belief_type.value, belief.scope.value, _dump(belief)),
        )
        self.conn.commit()

    def get_belief(self, belief_id: str) -> Belief:
        row = self.conn.execute("SELECT payload FROM beliefs WHERE belief_id = ?", (belief_id,)).fetchone()
        if row is None:
            raise KeyError(belief_id)
        return Belief.model_validate(_load(row["payload"]))

    def list_beliefs(self, agent_id: str, query: str | None = None, belief_type: str | None = None, include_inactive: bool = False) -> list[Belief]:
        clauses = ["agent_id = ?"]
        params: list[Any] = [agent_id]
        if belief_type:
            clauses.append("belief_type = ?")
            params.append(belief_type)
        if not include_inactive:
            clauses.append("status != ?")
            params.append("deprecated")
        sql = f"SELECT payload FROM beliefs WHERE {' AND '.join(clauses)} ORDER BY rowid DESC"
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        beliefs = [Belief.model_validate(_load(row["payload"])) for row in rows]
        if query:
            lowered = query.lower()
            beliefs = [belief for belief in beliefs if lowered in belief.proposition.lower()]
        return beliefs

    def save_belief_revision(self, revision: BeliefRevision) -> None:
        self.conn.execute(
            "INSERT INTO belief_revisions(revision_id, belief_id, agent_id, payload) VALUES (?, ?, ?, ?)",
            (revision.revision_id, revision.belief_id, revision.agent_id, _dump(revision)),
        )
        self.conn.commit()

    def list_belief_revisions(self, belief_id: str) -> list[BeliefRevision]:
        rows = self.conn.execute(
            "SELECT payload FROM belief_revisions WHERE belief_id = ? ORDER BY rowid",
            (belief_id,),
        ).fetchall()
        return [BeliefRevision.model_validate(_load(row["payload"])) for row in rows]

    def save_worldview_stance(self, stance: WorldviewStance) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO worldview_stances(worldview_id, agent_id, theme, payload) VALUES (?, ?, ?, ?)",
            (stance.worldview_id, stance.agent_id, stance.theme, _dump(stance)),
        )
        self.conn.commit()

    def list_worldview_stances(self, agent_id: str, theme: str | None = None) -> list[WorldviewStance]:
        if theme:
            rows = self.conn.execute(
                "SELECT payload FROM worldview_stances WHERE agent_id = ? AND theme = ? ORDER BY rowid DESC",
                (agent_id, theme),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT payload FROM worldview_stances WHERE agent_id = ? ORDER BY rowid DESC",
                (agent_id,),
            ).fetchall()
        return [WorldviewStance.model_validate(_load(row["payload"])) for row in rows]

    def save_opinion_expression(self, expression: OpinionExpression) -> None:
        self.conn.execute(
            "INSERT INTO belief_expression_audit(expression_id, agent_id, payload) VALUES (?, ?, ?)",
            (expression.expression_id, expression.agent_id, _dump(expression)),
        )
        self.conn.commit()

    def save_inner_voice(self, frame: InnerVoiceFrame) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO inner_voice_frames(voice_id, agent_id, state_revision, payload) VALUES (?, ?, ?, ?)",
            (frame.voice_id, frame.agent_id, frame.state_revision, _dump(frame)),
        )
        self.conn.commit()

    def list_inner_voices(self, agent_id: str, limit: int | None = None) -> list[InnerVoiceFrame]:
        sql = "SELECT payload FROM inner_voice_frames WHERE agent_id = ? ORDER BY rowid DESC"
        params: tuple[Any, ...] = (agent_id,)
        if limit is not None:
            sql += " LIMIT ?"
            params = (agent_id, limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [InnerVoiceFrame.model_validate(_load(row["payload"])) for row in rows]

    def save_mood_state(self, mood: MoodState) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO mood_states(mood_id, agent_id, state_revision, status, payload) VALUES (?, ?, ?, ?, ?)",
            (mood.mood_id, mood.agent_id, mood.state_revision, mood.status.value, _dump(mood)),
        )
        self.conn.commit()

    def latest_mood(self, agent_id: str, include_inactive: bool = False) -> MoodState | None:
        if include_inactive:
            row = self.conn.execute(
                "SELECT payload FROM mood_states WHERE agent_id = ? ORDER BY rowid DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT payload FROM mood_states WHERE agent_id = ? AND status = ? ORDER BY rowid DESC LIMIT 1",
                (agent_id, MoodStatus.ACTIVE.value),
            ).fetchone()
        if row is None:
            return None
        return MoodState.model_validate(_load(row["payload"]))

    def list_moods(self, agent_id: str, include_inactive: bool = False) -> list[MoodState]:
        if include_inactive:
            rows = self.conn.execute(
                "SELECT payload FROM mood_states WHERE agent_id = ? ORDER BY rowid DESC",
                (agent_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT payload FROM mood_states WHERE agent_id = ? AND status = ? ORDER BY rowid DESC",
                (agent_id, MoodStatus.ACTIVE.value),
            ).fetchall()
        return [MoodState.model_validate(_load(row["payload"])) for row in rows]

    def save_mood_revision(self, revision: MoodRevision) -> None:
        self.conn.execute(
            "INSERT INTO mood_revisions(revision_id, mood_id, agent_id, payload) VALUES (?, ?, ?, ?)",
            (revision.revision_id, revision.mood_id, revision.agent_id, _dump(revision)),
        )
        self.conn.commit()

    def clear_moods(self, agent_id: str, reason: str) -> int:
        rows = self.conn.execute(
            "SELECT rowid, payload FROM mood_states WHERE agent_id = ? AND status = ?",
            (agent_id, MoodStatus.ACTIVE.value),
        ).fetchall()
        changed = 0
        for row in rows:
            mood = MoodState.model_validate(_load(row["payload"]))
            cleared = mood.model_copy(update={"status": MoodStatus.CLEARED})
            self.conn.execute(
                "UPDATE mood_states SET status = ?, payload = ? WHERE rowid = ?",
                (MoodStatus.CLEARED.value, _dump(cleared), row["rowid"]),
            )
            changed += 1
        self.audit("operator", "clear_mood", {"agent_id": agent_id, "reason": reason, "records_changed": changed})
        self.conn.commit()
        return changed

    def record_episode_link(self, episode_id: str, agent_id: str, artifact_type: str, artifact_id: str, payload: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO episodes(episode_id, agent_id, status, payload) VALUES (?, ?, ?, ?)",
            (episode_id, agent_id, "open", json.dumps({"episode_id": episode_id, "agent_id": agent_id})),
        )
        self.conn.execute(
            "INSERT INTO episode_links(episode_id, artifact_type, artifact_id) VALUES (?, ?, ?)",
            (episode_id, artifact_type, artifact_id),
        )
        if payload is not None:
            self.audit("system", f"record_{artifact_type}", payload)
        self.conn.commit()

    def audit(self, actor: str, action: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO audit_log(actor, action, payload) VALUES (?, ?, ?)",
            (actor, action, json.dumps(payload, default=str)),
        )
        self.conn.commit()

    def save_log_snapshot(self, snapshot: LogSnapshot) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO log_snapshots(snapshot_id, agent_id, target_kind, payload) VALUES (?, ?, ?, ?)",
            (snapshot.snapshot_id, snapshot.agent_id, snapshot.target.kind.value, _dump(snapshot)),
        )
        self.conn.commit()

    def get_log_snapshot(self, snapshot_id: str) -> LogSnapshot:
        row = self.conn.execute("SELECT payload FROM log_snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return LogSnapshot.model_validate(_load(row["payload"]))

    def save_report(self, report: Report) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO reports(report_id, agent_id, snapshot_id, reporter_kind, payload) VALUES (?, ?, ?, ?, ?)",
            (report.report_id, report.agent_id, report.snapshot_id, report.reporter.kind.value, _dump(report)),
        )
        self.conn.commit()

    def get_report(self, report_id: str) -> Report:
        row = self.conn.execute("SELECT payload FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        if row is None:
            raise KeyError(report_id)
        return Report.model_validate(_load(row["payload"]))

    def save_honesty_score(self, score: HonestyScore) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO honesty_scores(score_id, report_id, agent_id, aggregate, failure_mode, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (
                score.score_id,
                score.report_id,
                score.agent_id,
                score.aggregate,
                score.failure_mode.value if score.failure_mode else None,
                _dump(score),
            ),
        )
        self.conn.commit()

    def get_honesty_score(self, score_id: str) -> HonestyScore:
        row = self.conn.execute("SELECT payload FROM honesty_scores WHERE score_id = ?", (score_id,)).fetchone()
        if row is None:
            raise KeyError(score_id)
        return HonestyScore.model_validate(_load(row["payload"]))

    def save_dissonance_signal(self, signal: DissonanceSignal) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO dissonance_signals(signal_id, agent_id, arch, magnitude_raw, payload) VALUES (?, ?, ?, ?, ?)",
            (signal.signal_id, signal.agent_id, signal.arch, signal.magnitude_raw, _dump(signal)),
        )
        self.conn.commit()

    def list_dissonance_signals(self, agent_id: str, limit: int | None = None) -> list[DissonanceSignal]:
        sql = "SELECT payload FROM dissonance_signals WHERE agent_id = ? ORDER BY rowid DESC"
        params: list[Any] = [agent_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        return [DissonanceSignal.model_validate(_load(row["payload"])) for row in rows]

    def save_loop_trace(self, trace: LoopTrace) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO loop_traces(trace_id, agent_id, arm, termination, payload) VALUES (?, ?, ?, ?, ?)",
            (trace.trace_id, trace.agent_id, trace.arm, trace.termination, _dump(trace)),
        )
        self.conn.commit()

    def get_loop_trace(self, trace_id: str) -> LoopTrace:
        row = self.conn.execute("SELECT payload FROM loop_traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if row is None:
            raise KeyError(trace_id)
        return LoopTrace.model_validate(_load(row["payload"]))

    def list_loop_traces(self, agent_id: str, limit: int | None = None) -> list[LoopTrace]:
        sql = "SELECT payload FROM loop_traces WHERE agent_id = ? ORDER BY rowid DESC"
        params: list[Any] = [agent_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        return [LoopTrace.model_validate(_load(row["payload"])) for row in rows]

    def save_results_record(self, record: ResultsRecord) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO experiment_results(record_id, experiment, kind, agent_id, payload) VALUES (?, ?, ?, ?, ?)",
            (record.record_id, record.experiment, record.kind, record.agent_id, _dump(record)),
        )
        self.conn.commit()

    def export_agent(self, agent_id: str) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for table in _GOVERNED_TABLES:
            rows = self.conn.execute(f"SELECT payload FROM {table} WHERE agent_id = ?", (agent_id,)).fetchall()
            result[table] = [json.loads(row["payload"]) for row in rows]
        rows = self.conn.execute(f"SELECT payload FROM {_SNAPSHOT_EXEMPT_TABLE} WHERE agent_id = ?", (agent_id,)).fetchall()
        result[_SNAPSHOT_EXEMPT_TABLE] = [json.loads(row["payload"]) for row in rows]
        return result

    def redact_agent(self, agent_id: str, replacement: str = "[REDACTED]") -> int:
        changed = 0
        # log_snapshots is intentionally omitted; frozen provenance is exempt.
        redactable = [table for table in _GOVERNED_TABLES if table not in {"affect_states"}]
        for table in redactable:
            rows = self.conn.execute(f"SELECT rowid, payload FROM {table} WHERE agent_id = ?", (agent_id,)).fetchall()
            for row in rows:
                payload = row["payload"]
                redacted = payload.replace(agent_id, replacement)
                if redacted != payload:
                    self.conn.execute(f"UPDATE {table} SET payload = ? WHERE rowid = ?", (redacted, row["rowid"]))
                    changed += 1
        self.audit("operator", "redact_agent", {"agent_id": agent_id, "replacement": replacement, "records_changed": changed})
        self.conn.commit()
        return changed

    def tombstone_agent(self, agent_id: str, reason: str) -> None:
        exported = self.export_agent(agent_id)
        self.reset_agent(agent_id, reason)
        # Tombstone additionally purges frozen snapshots (design §3.2 asymmetry).
        self.conn.execute(f"DELETE FROM {_SNAPSHOT_EXEMPT_TABLE} WHERE agent_id = ?", (agent_id,))
        self.conn.commit()
        self.audit("operator", "tombstone_agent", {"agent_id": agent_id, "reason": reason, "removed_counts": {k: len(v) for k, v in exported.items()}})

    def reset_agent(self, agent_id: str, reason: str) -> None:
        # log_snapshots is intentionally omitted; frozen provenance survives reset.
        self.conn.execute(
            "DELETE FROM episode_links WHERE episode_id IN (SELECT episode_id FROM episodes WHERE agent_id = ?)",
            (agent_id,),
        )
        for table in _GOVERNED_TABLES:
            self.conn.execute(f"DELETE FROM {table} WHERE agent_id = ?", (agent_id,))
        self.audit("operator", "admin_reset", {"agent_id": agent_id, "reason": reason})
        self.conn.commit()
