"""FR-1 and FR-5 — pricing never writes, and the surface works from another process.

Two properties that cannot be established by reading code.

**FR-1** is the one this experiment adds: a counterfactual that mutates the store
is not a counterfactual, and one that mutates and rolls back is a defect waiting
for the first exception. It is checked by comparing `export_agent` either side of
a call rather than by inspecting the implementation for writes.

**FR-5** is experiment 3 section 13's property, carried forward.
`MergedDissonanceQuery` before experiment 4 section 6 and `RevisionEngine` before
experiment 3 section 13 were both imported by nothing but their own module and
their own test file. A surface that only works in-process is not a surface.

Only the *analytic* pricer is surfaced. Replay is an instrument that grades it and
deliberately has none (requirements section 14.1), so its absence from the CLI is
asserted here rather than left to be noticed as a gap.

Entirely offline.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from manyu.core import ManyuCore
from manyu.underdetermination import derive, seed_fixture

REPO = Path(__file__).resolve().parents[1]
AGENT = "agent_demo"


def _seeded_db(tmp_path, fixture: str = "symmetric_rivals") -> str:
    db = str(tmp_path / "cf_surface.sqlite3")
    core = ManyuCore.from_paths(db_path=db, frozen=True)
    seed_fixture(core, fixture, agent_id=AGENT)
    derive(core, AGENT)
    core.store.close()
    return db


def _run_cli(db: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "manyu", "--db", db, *args],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )


def _cli(db: str, *args: str) -> dict:
    result = _run_cli(db, *args)
    assert result.returncode == 0, f"{args} failed ({result.returncode}): {result.stderr[-2000:]}"
    assert result.stdout.strip(), f"{args} produced no output; stderr: {result.stderr[-2000:]}"
    return json.loads(result.stdout)


# --- FR-1 --------------------------------------------------------------------


def test_pricing_leaves_the_store_byte_identical(tmp_path):
    """The default path must not write. Checked by comparison, not by inspection."""
    db = _seeded_db(tmp_path)
    core = ManyuCore.from_paths(db_path=db, frozen=True)

    before = core.store.export_agent(AGENT)
    result = core.price_counterfactuals({"agent_id": AGENT})
    after = core.store.export_agent(AGENT)

    assert result["status"] == "ok"
    assert result["count"] == 3
    assert result["persisted"] is False
    assert before == after, "pricing mutated the store"
    core.store.close()


def test_persist_writes_only_receipts(tmp_path):
    """With `persist`, receipts appear and nothing else moves.

    The asymmetry matters: a receipt is a new row, not an edit to a belief. If
    persisting changed a belief, the act of asking what would change Manyu's mind
    would itself have changed it.
    """
    db = _seeded_db(tmp_path)
    core = ManyuCore.from_paths(db_path=db, frozen=True)

    before = core.store.export_agent(AGENT)
    core.price_counterfactuals({"agent_id": AGENT, "persist": True})
    after = core.store.export_agent(AGENT)

    assert after["counterfactual_receipts"] and not before["counterfactual_receipts"]
    for table in ("beliefs", "belief_evidence", "belief_revisions"):
        assert before[table] == after[table], f"{table} changed while persisting a receipt"
    core.store.close()


# --- FR-5, across a genuinely separate interpreter ---------------------------


def test_cli_prices_and_reads_back_across_processes(tmp_path):
    db = _seeded_db(tmp_path)

    priced = _cli(db, "price-counterfactuals", "--agent-id", AGENT, "--persist")
    assert priced["status"] == "ok"
    assert priced["count"] == 3

    meta = [r for r in priced["receipts"] if r["belief_type"] == "underdetermination"]
    assert len(meta) == 1
    assert len(meta[0]["items"]) == 2
    assert meta[0]["items"][0]["dose"] == 5
    assert len(meta[0]["declined"]) == 1

    # A second process reads what the first one wrote.
    read = _cli(db, "counterfactuals", "--agent-id", AGENT)
    assert read["status"] == "ok"
    assert read["count"] == 3


def test_cli_does_not_persist_by_default(tmp_path):
    db = _seeded_db(tmp_path)
    _cli(db, "price-counterfactuals", "--agent-id", AGENT)
    read = _cli(db, "counterfactuals", "--agent-id", AGENT)
    assert read["count"] == 0, "pricing persisted without being asked to"


def test_mcp_surface_carries_both_tools():
    """Experiment 1 found `manyu_run_probe` missing from MCP after the CLI and
    core had carried it for two versions. Checked rather than assumed.
    """
    from manyu.mcp_adapter import ManyuMCPAdapter

    assert hasattr(ManyuMCPAdapter, "price_counterfactuals")
    assert hasattr(ManyuMCPAdapter, "read_counterfactuals")


def test_replay_is_deliberately_not_surfaced():
    """Requirements section 14.1 — replay is an instrument, not a deliverable.

    Asserted so that its absence reads as a decision rather than an oversight,
    and so that adding it later is a deliberate act.
    """
    from manyu.core import ManyuCore
    from manyu.mcp_adapter import ManyuMCPAdapter

    result = subprocess.run(
        [sys.executable, "-m", "manyu", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert "price-counterfactuals" in result.stdout

    # `replay` already exists as an unrelated event-replay command, so the check
    # is on the counterfactual surface specifically rather than on the word.
    counterfactual_commands = {c for c in ("price-counterfactuals", "counterfactuals") if c in result.stdout}
    assert counterfactual_commands == {"price-counterfactuals", "counterfactuals"}
    assert "replay-counterfactual" not in result.stdout
    assert not [name for name in dir(ManyuCore) if "replay" in name and "counterfactual" in name]
    assert not [name for name in dir(ManyuMCPAdapter) if "replay" in name and "counterfactual" in name]
