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
    InteroceptiveView,
    NormalizedEvent,
    TraceRecord,
    Transition,
)


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
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

    def export_agent(self, agent_id: str) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for table in [
            "events",
            "appraisals",
            "affect_states",
            "transitions",
            "interoceptive_views",
            "arbitration_decisions",
            "episodes",
            "memories",
        ]:
            rows = self.conn.execute(f"SELECT payload FROM {table} WHERE agent_id = ?", (agent_id,)).fetchall()
            result[table] = [json.loads(row["payload"]) for row in rows]
        return result

    def redact_agent(self, agent_id: str, replacement: str = "[REDACTED]") -> int:
        changed = 0
        for table in ["events", "appraisals", "transitions", "interoceptive_views", "arbitration_decisions", "episodes", "memories"]:
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
        self.audit("operator", "tombstone_agent", {"agent_id": agent_id, "reason": reason, "removed_counts": {k: len(v) for k, v in exported.items()}})

    def reset_agent(self, agent_id: str, reason: str) -> None:
        for table in [
            "episode_links",
            "events",
            "appraisals",
            "affect_states",
            "transitions",
            "interoceptive_views",
            "arbitration_decisions",
            "episodes",
            "memories",
        ]:
            if table == "episode_links":
                self.conn.execute(
                    "DELETE FROM episode_links WHERE episode_id IN (SELECT episode_id FROM episodes WHERE agent_id = ?)",
                    (agent_id,),
                )
            else:
                self.conn.execute(f"DELETE FROM {table} WHERE agent_id = ?", (agent_id,))
        self.audit("operator", "admin_reset", {"agent_id": agent_id, "reason": reason})
        self.conn.commit()
