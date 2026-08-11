"""Experiment 4 section 5.7 — the signal has a surface, and it is real.

Before this, `MergedDissonanceQuery` was imported by its own module and its own
test file. Nothing computed it during a turn, nothing persisted it, and it was
absent from `ManyuCore`, the CLI and the MCP tools. Exactly where
`RevisionEngine` stood before experiment 3 section 13 — and there the
consequence was that the deliverable experiments 5, 7 and 8 were meant to consume
could only be driven from its own tests, and Stage 4 could not have run at all.
Experiment 1 hit the same thing when `manyu_run_probe` turned out to be missing
from MCP entirely.

**The load-bearing test here is the cross-process one.** Driving the loop and
reading it back inside one interpreter proves only that an object stayed in
memory. Experiment 3 pinned its surface with a test that ran a CLI command in one
process and asserted the *next* process saw the result, because otherwise the CLI
is only pretending to expose the engine.

Offline. No provider is constructed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.fork import seed_beliefs
from manyu.salience import load_web, web_specs

AGENT = "agent_demo"
REPO = Path(__file__).resolve().parents[1]


def _seeded(tmp_path, fixture: str = "multi_conflict_web") -> str:
    db = str(tmp_path / "surface.sqlite3")
    core = ManyuCore.from_paths(db_path=db, frozen=True)
    seed_beliefs(core, web_specs(load_web(fixture)))
    core.store.close()
    return db


def _run_cli(db: str, *args: str) -> subprocess.CompletedProcess:
    """A genuinely separate interpreter.

    `--db` is a global flag and must precede the subcommand, and the entry point
    is `python -m manyu` — `manyu.cli` has no `__main__` guard, so invoking it
    that way exits 0 having done nothing, which is indistinguishable from success
    and is how the first version of this helper passed while testing nothing.
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

def test_reading_dissonance_persists_the_signal(tmp_path) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "a.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("multi_conflict_web")))

    result = core.read_dissonance(AGENT)
    assert result["status"] == "ok"
    assert result["conflicts"] == 3
    assert core.store.list_dissonance_signals(AGENT), "the signal was read and not recorded"


def test_reading_a_web_with_no_conflict_records_nothing(tmp_path) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "b.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("no_conflict_web")))

    result = core.read_dissonance(AGENT)
    assert result["signal"] is None
    assert result["conflicts"] == 0
    assert core.store.list_dissonance_signals(AGENT) == []


def test_the_loop_persists_a_trace_that_round_trips(tmp_path) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "c.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("multi_conflict_web")))

    result = core.run_attention_loop({"agent_id": AGENT, "arm": "driven", "max_iterations": 8})
    assert result["status"] == "ok", result
    trace_id = result["trace"]["trace_id"]

    read_back = core.get_loop_trace(trace_id)
    assert read_back["status"] == "ok"
    assert read_back["trace"] == result["trace"]


def test_the_persisted_trace_is_self_auditing(tmp_path) -> None:
    """A driven arm's record must show it took the best conflict then available.

    The check that catches a loop deciding from stale information, available to
    anyone reading the stored trace without re-running anything.
    """
    core = ManyuCore.from_paths(db_path=str(tmp_path / "d.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("hub_web")))

    result = core.run_attention_loop({"agent_id": AGENT, "arm": "driven", "max_iterations": 8})
    for step in result["trace"]["steps"]:
        assert step["tension_before"] == pytest.approx(step["best_available_tension"], abs=1e-6), step


def test_a_reflective_turn_reads_dissonance_on_both_sides_of_belief_update(tmp_path) -> None:
    """FR-1, and the reason it is *both* sides rather than one.

    `update_beliefs` routes every newly declared contradiction through
    `assert_contradiction` (experiment 3 section 14), so a contradiction arriving
    this turn is already charged by the time it returns. A single read afterwards
    cannot tell "the web was calm" from "the web was disturbed and immediately
    priced" — the delta is the only thing that separates them.
    """
    from manyu.providers import ScenarioJSONProvider
    from manyu.schemas import NormalizedEvent

    fixture = json.loads((REPO / "evals" / "fixtures" / "everyday_collaboration_mood.json").read_text(encoding="utf-8"))
    core = ManyuCore.from_paths(db_path=str(tmp_path / "turn.sqlite3"), frozen=True, belief_provider=ScenarioJSONProvider())

    turn = core.process_reflective_turn(
        {"event": NormalizedEvent.model_validate(fixture["events"][0]).model_dump(mode="json")}
    )
    reading = turn["dissonance"]
    assert set(reading) == {
        "raw_before",
        "raw_after",
        "conflicts_before",
        "conflicts_after",
        "arose_this_turn",
    }, reading
    # Raw only. The saturated channel must not reach a turn record either.
    assert "magnitude" not in reading


def test_a_turn_records_a_conflict_that_arose_during_it(tmp_path) -> None:
    """The delta must actually be able to be non-zero, or `arose_this_turn` is
    decoration — gate #5 applied to the turn-level read.

    Driven through supplied candidates rather than the extractor, because the
    offline provider cannot emit a `contradicts` edge at all, which is exactly
    what voided Stage 0a.
    """
    from manyu.schemas import NormalizedEvent

    fixture = json.loads((REPO / "evals" / "fixtures" / "everyday_collaboration_mood.json").read_text(encoding="utf-8"))
    core = ManyuCore.from_paths(db_path=str(tmp_path / "arose.sqlite3"), frozen=True)
    event = NormalizedEvent.model_validate(fixture["events"][0])

    def candidate(key: str, proposition: str, contradicts: list[str]) -> dict:
        # Every candidate carries provenance of its own. `_rejection_reason`
        # refuses one without it (`INSUFFICIENT_PROVENANCE`) — the same mandatory
        # provenance rule that decided experiment 3, and the reason the first
        # version of this test silently created no beliefs at all.
        record = core.capture_belief_evidence(
            {
                "agent_id": event.agent_id,
                "source_type": "operator_note",
                "source_id": f"note_{key}",
                "summary": proposition,
                "affective_salience": 0.6,
                "epistemic_weight": 0.8,
            }
        )
        return {
            "candidate_id": f"bcand_{key}",
            "agent_id": event.agent_id,
            "proposition": proposition,
            "belief_key": key,
            "belief_type": "world_model",
            "scope": "general",
            "confidence": 0.8,
            "stability": 0.1,
            "valence": 0.6 if not contradicts else -0.6,
            "source_mix": {"operator_note": 1.0},
            "evidence_ids": [record["evidence_id"]],
            "contradicts": contradicts,
        }

    turn = core.process_reflective_turn(
        {
            "event": event.model_dump(mode="json"),
            "belief_candidates": [
                candidate("claim", "The rollout completed cleanly.", []),
                candidate("counter", "The rollout left errors behind.", ["claim"]),
            ],
        }
    )
    assert turn["dissonance"]["arose_this_turn"] == 1, turn["dissonance"]
    assert turn["dissonance"]["conflicts_before"] == 0
    assert turn["dissonance"]["conflicts_after"] == 1


# --- errors are returned, not raised -----------------------------------------

@pytest.mark.parametrize(
    "payload,fragment",
    [
        ({"max_iterations": 4}, "arm is required"),
        ({"arm": "nonsense", "max_iterations": 4}, "unknown arm"),
        ({"arm": "driven", "max_iterations": 0}, "at least 1"),
        ({"arm": "driven", "max_iterations": -3}, "at least 1"),
        ({"arm": "driven", "max_iterations": "many"}, "must be an integer"),
        ({"arm": "random_matched", "max_iterations": 4}, "seed"),
    ],
)
def test_errors_are_returned_not_raised(tmp_path, payload: dict, fragment: str) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "e.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("multi_conflict_web")))

    result = core.run_attention_loop({"agent_id": AGENT, **payload})
    assert result["status"] == "error", result
    assert fragment in result["error"], result["error"]


def test_an_unknown_trace_is_an_error_not_an_exception(tmp_path) -> None:
    core = ManyuCore.from_paths(db_path=str(tmp_path / "f.sqlite3"), frozen=True)
    result = core.get_loop_trace("loop_does_not_exist")
    assert result["status"] == "error"
    assert "unknown" in result["error"]


def test_no_arm_is_the_default_at_the_core_surface(tmp_path) -> None:
    """Experiment 3 section 13's rule, checked at the layer callers actually use."""
    core = ManyuCore.from_paths(db_path=str(tmp_path / "g.sqlite3"), frozen=True)
    seed_beliefs(core, web_specs(load_web("multi_conflict_web")))
    assert core.run_attention_loop({"agent_id": AGENT, "max_iterations": 4})["status"] == "error"


# --- across a process boundary -----------------------------------------------

def test_cli_loop_run_is_visible_to_the_next_process(tmp_path) -> None:
    """The test that makes the surface real rather than apparent.

    One process runs the loop; a **separate** process reads the trace back and
    must see the same steps. Without the second process this would pass on an
    object that never left memory — which is exactly the failure experiment 3
    pinned against when it added `retract-belief` to the CLI.
    """
    db = _seeded(tmp_path)

    ran = _cli(db, "run-attention-loop", "--agent-id", AGENT, "--arm", "driven", "--max-iterations", "8")
    assert ran["status"] == "ok", ran
    trace_id = ran["trace"]["trace_id"]
    assert ran["trace"]["steps"], "the loop acted on nothing"

    read_back = _cli(db, "loop-trace", "--trace-id", trace_id)
    assert read_back["status"] == "ok", read_back
    assert read_back["trace"] == ran["trace"], "the next process saw a different trace"


def test_cli_dissonance_reflects_what_the_loop_did(tmp_path) -> None:
    """Tension after the loop must be lower than before it, read across processes.

    Ties the two commands together: a surface where each works alone but they
    disagree about the same store is not a surface.
    """
    db = _seeded(tmp_path)

    before = _cli(db, "dissonance", "--agent-id", AGENT)
    assert before["conflicts"] == 3

    _cli(db, "run-attention-loop", "--agent-id", AGENT, "--arm", "driven", "--max-iterations", "8")

    after = _cli(db, "dissonance", "--agent-id", AGENT)
    assert after["signal"]["magnitude_raw"] < before["signal"]["magnitude_raw"], (
        f"tension did not fall across the process boundary: "
        f"{before['signal']['magnitude_raw']} -> {after['signal']['magnitude_raw']}"
    )
    # The conflicts are still there. Nothing was resolved; a party was weakened.
    assert after["conflicts"] == before["conflicts"], "a conflict was retired, which the substrate forbids"


def test_cli_refuses_a_run_that_does_not_name_an_arm(tmp_path) -> None:
    db = _seeded(tmp_path)
    result = _run_cli(db, "run-attention-loop", "--max-iterations", "4")
    assert result.returncode != 0
    assert "--arm" in result.stderr


def test_the_cli_helper_would_notice_a_command_that_did_nothing(tmp_path) -> None:
    """Guard on the harness above, not on the product.

    The first version of `_run_cli` invoked `python -m manyu.cli`, which has no
    `__main__` guard: the module imported, printed nothing, and exited 0. Three
    cross-process tests "passed" while asserting nothing. The helper now requires
    output, so a command that silently does nothing fails loudly.
    """
    result = subprocess.run(
        [sys.executable, "-m", "manyu.cli", "health"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert result.returncode == 0 and not result.stdout.strip(), (
        "manyu.cli grew a __main__ guard; the cautionary note in _run_cli is now stale"
    )


# --- MCP ---------------------------------------------------------------------

def test_the_mcp_adapter_exposes_the_whole_surface() -> None:
    """Experiment 1 found `manyu_run_probe` missing from MCP entirely, after the
    CLI and core had carried it for two versions. Checked rather than assumed.
    """
    from manyu.mcp_adapter import ManyuMCPAdapter

    for name in ("read_dissonance", "run_attention_loop", "get_loop_trace"):
        assert hasattr(ManyuMCPAdapter, name), f"MCP adapter is missing {name}"


def test_the_mcp_server_registers_the_tools() -> None:
    source = (REPO / "src" / "manyu" / "mcp_server.py").read_text(encoding="utf-8")
    for tool in ("manyu_read_dissonance", "manyu_run_attention_loop", "manyu_get_loop_trace"):
        assert f"def {tool}(" in source, f"{tool} is not registered on the MCP server"
