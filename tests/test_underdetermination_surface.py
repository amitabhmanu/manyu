"""FR-5 — the derivation is reachable, and reachable from another process.

`MergedDissonanceQuery` before experiment 4 §6 and `RevisionEngine` before
experiment 3 §13 were both imported by nothing but their own module and their own
test file. Experiment 1 found `manyu_run_probe` missing from MCP entirely after
the CLI and core had carried it for two versions. A surface that only works
in-process is not a surface, and "it is wired up" is checkable rather than
something to assert.

Entirely offline.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.underdetermination import apply_then, seed_fixture

REPO = Path(__file__).resolve().parents[1]
AGENT = "agent_demo"


def _seeded_db(tmp_path, fixture: str = "symmetric_rivals") -> str:
    db = str(tmp_path / "ud_surface.sqlite3")
    core = ManyuCore.from_paths(db_path=db, frozen=True)
    seed_fixture(core, fixture, agent_id=AGENT)
    core.store.close()
    return db


def _run_cli(db: str, *args: str) -> subprocess.CompletedProcess:
    """A genuinely separate interpreter.

    `--db` is global and must precede the subcommand, and the entry point is
    `python -m manyu` — `manyu.cli` has no `__main__` guard, so invoking it that
    way exits 0 having done nothing. Experiment 4 recorded three tests that
    asserted nothing for exactly that reason.
    """
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


# --- core --------------------------------------------------------------------


def test_the_core_surface_derives_and_reads_back(tmp_path) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "core.sqlite3"), frozen=True)
    seed_fixture(core, "symmetric_rivals", agent_id=AGENT)

    derived = core.derive_underdetermination({"agent_id": AGENT})
    assert derived["status"] == "ok"
    assert len(derived["derived"]) == 1

    held = core.read_underdetermination(AGENT)
    assert held["count"] == 1
    assert len(held["underdetermined"][0]["rivals"]) == 2


def test_reading_derives_nothing(tmp_path) -> None:
    """`read` is read-only. A reader with a side effect makes every later
    measurement depend on how often somebody looked.
    """
    core = ManyuCore.from_paths(db_path=str(tmp_path / "core.sqlite3"), frozen=True)
    seed_fixture(core, "symmetric_rivals", agent_id=AGENT)

    assert core.read_underdetermination(AGENT)["count"] == 0
    assert core.read_underdetermination(AGENT)["count"] == 0


@pytest.mark.parametrize(
    "payload,fragment",
    [
        ({"agent_id": AGENT, "mode": "nonsense"}, "unknown mode"),
        ({"agent_id": AGENT, "mode": "STRICT"}, "unknown mode"),
    ],
)
def test_errors_are_returned_not_raised(tmp_path, payload: dict, fragment: str) -> None:
    """Matching `retract_belief` and `run_attention_loop`: an MCP caller gets a
    payload, not a traceback.
    """
    core = ManyuCore.from_paths(db_path=str(tmp_path / "core.sqlite3"), frozen=True)
    result = core.derive_underdetermination(payload)
    assert result["status"] == "error"
    assert fragment in result["error"]


def test_the_mode_defaults_to_strict_rather_than_to_the_ablation(tmp_path) -> None:
    """The asymmetry with `--arm` is deliberate and worth pinning.

    There, both arms were live candidates. Here `graded` carries a tolerance
    constant that experiment 3 §§11–12's discipline exists to avoid, so it must
    never become the default by omission.
    """
    core = ManyuCore.from_paths(db_path=str(tmp_path / "core.sqlite3"), frozen=True)
    seed_fixture(core, "symmetric_rivals", agent_id=AGENT)
    assert core.derive_underdetermination({"agent_id": AGENT})["mode"] == "strict"
    assert core.derive_underdetermination()["mode"] == "strict"


# --- CLI, across a process boundary -----------------------------------------


def test_a_cli_derivation_is_visible_to_the_next_process(tmp_path) -> None:
    """The property experiment 3 §13 pinned. Three interpreters: one seeds, one
    derives, one reads.
    """
    db = _seeded_db(tmp_path)

    derived = _cli(db, "derive-underdetermination", "--agent-id", AGENT)
    assert derived["status"] == "ok"
    assert len(derived["derived"]) == 1

    held = _cli(db, "underdetermination", "--agent-id", AGENT)
    assert held["count"] == 1
    assert len(held["underdetermined"][0]["rivals"]) == 2
    assert held["underdetermined"][0]["confidence"] == derived["derived"][0]["confidence"]


def test_the_cli_collapse_survives_a_process_boundary(tmp_path) -> None:
    """The whole arm, driven from outside the process that built the store."""
    db = str(tmp_path / "collapse.sqlite3")
    core = ManyuCore.from_paths(db_path=db, frozen=True)
    minted = seed_fixture(core, "discriminating", agent_id=AGENT)
    core.store.close()

    before = _cli(db, "derive-underdetermination", "--agent-id", AGENT)["derived"][0]["confidence"]

    core = ManyuCore.from_paths(db_path=db, frozen=True)
    apply_then(core, "discriminating", minted, agent_id=AGENT)
    core.store.close()

    after = _cli(db, "derive-underdetermination", "--agent-id", AGENT)
    assert after["derived"] == []
    assert after["weakened"][0]["confidence"] < before


def test_the_cli_helper_would_notice_a_command_that_did_nothing(tmp_path) -> None:
    """The helper's own positive control. `python -m manyu.cli` exits 0 having done
    nothing, so a helper that only checked the return code would pass while
    testing nothing — which is how experiment 4 shipped three empty tests.
    """
    db = _seeded_db(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "manyu.cli", "--db", db, "underdetermination"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert result.returncode == 0
    assert not result.stdout.strip(), "the no-op invocation produced output; this control is stale"


def test_cli_refuses_an_unknown_mode(tmp_path) -> None:
    db = _seeded_db(tmp_path)
    result = _run_cli(db, "derive-underdetermination", "--agent-id", AGENT, "--mode", "nonsense")
    assert result.returncode != 0


# --- MCP ---------------------------------------------------------------------


def test_the_mcp_adapter_exposes_the_surface() -> None:
    from manyu.mcp_adapter import ManyuMCPAdapter

    for name in ("derive_underdetermination", "read_underdetermination"):
        assert hasattr(ManyuMCPAdapter, name), f"MCP adapter is missing {name}"


def test_the_mcp_server_registers_the_tools() -> None:
    source = (REPO / "src" / "manyu" / "mcp_server.py").read_text(encoding="utf-8")
    for tool in ("manyu_derive_underdetermination", "manyu_read_underdetermination"):
        assert f"def {tool}(" in source, f"{tool} is not registered on the MCP server"


def test_the_mcp_adapter_round_trips_against_a_real_core(tmp_path) -> None:
    """Registration is not reachability. Experiment 1's `manyu_run_probe` was
    absent for two versions with core and CLI both working.

    **`use_anthropic_api=False` is not optional here.** The adapter's default is
    `True`, so constructing one the obvious way builds an
    `AnthropicAPIJSONProvider` — a paid path reached from a test that has no
    business touching one. Every stage before Stage 5 is offline by design and
    the default quietly undoes that.
    """
    from manyu.mcp_adapter import ManyuMCPAdapter

    db = str(tmp_path / "mcp.sqlite3")
    adapter = ManyuMCPAdapter(db_path=db, use_anthropic_api=False)
    seed_fixture(adapter.core, "symmetric_rivals", agent_id=AGENT)

    assert adapter.derive_underdetermination({"agent_id": AGENT})["status"] == "ok"
    assert adapter.read_underdetermination({"agent_id": AGENT})["count"] == 1
