"""The two Stage 4 runner helpers that decide what a paid run measures.

`pick_retraction_target` chooses which belief a live run retracts, and
methodology §9 voids any run whose target was chosen other than by that rule.
`web_depth` reports the structure the whole stage exists to measure. Both run
against live, model-built webs that may be cyclic or edgeless, so they are
tested here rather than trusted.

Offline; the runner's provider is never constructed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.fork import BeliefSpec, seed_beliefs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "analysis" / "exp03"))
from run_stage4 import load_scenarios, pick_retraction_target, web_depth  # noqa: E402

AGENT = "agent_demo"


def _web(specs) -> tuple[dict, dict]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, specs)
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    return beliefs, ids


def test_web_depth_counts_hops_not_nodes() -> None:
    beliefs, _ = _web([
        BeliefSpec(key="gen", proposition="General.", confidence=0.8),
        BeliefSpec(key="mid", proposition="Mid.", confidence=0.8, supports=("gen",)),
        BeliefSpec(key="s1", proposition="S1.", confidence=0.8, supports=("mid",)),
    ])
    assert web_depth(beliefs) == 2, "s1 -> mid -> gen is two hops"


def test_web_depth_is_zero_on_an_edgeless_web() -> None:
    beliefs, _ = _web([BeliefSpec(key="a", proposition="A.", confidence=0.8)])
    assert web_depth(beliefs) == 0


def test_web_depth_terminates_on_a_cycle() -> None:
    """The extractor is not required to produce an acyclic graph, and a live
    run that hung here would burn the budget before failing."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, [
        BeliefSpec(key="a", proposition="A.", confidence=0.8),
        BeliefSpec(key="b", proposition="B.", confidence=0.8, supports=("a",)),
    ])
    a = core.store.get_belief(ids["a"])
    core.store.save_belief(a.model_copy(update={"supports": [ids["b"]]}))
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    assert web_depth(beliefs) >= 1


def test_target_is_the_highest_support_out_degree() -> None:
    beliefs, ids = _web([
        BeliefSpec(key="gen", proposition="General.", confidence=0.8),
        BeliefSpec(key="mid", proposition="Mid.", confidence=0.8, supports=("gen",)),
        BeliefSpec(key="wide", proposition="Wide.", confidence=0.8, supports=("mid", "gen")),
    ])
    assert pick_retraction_target(beliefs) == ids["wide"]


def test_target_selection_is_deterministic_under_ties() -> None:
    """Methodology §4 breaks ties by belief_id ascending, so a voided-run
    challenge can be settled from the record alone."""
    beliefs, _ = _web([
        BeliefSpec(key="t", proposition="T.", confidence=0.8),
        BeliefSpec(key="a", proposition="A.", confidence=0.8, supports=("t",)),
        BeliefSpec(key="b", proposition="B.", confidence=0.8, supports=("t",)),
    ])
    chosen = {pick_retraction_target(beliefs) for _ in range(5)}
    assert len(chosen) == 1
    tied = sorted(bid for bid, b in beliefs.items() if b.supports)
    assert chosen.pop() == tied[0]


def test_no_target_on_an_edgeless_web() -> None:
    """Recorded as `no_structure` and counted toward the structural-null rate,
    never retried — a retry would quietly select for webs that happened to
    have structure."""
    beliefs, _ = _web([
        BeliefSpec(key="a", proposition="A.", confidence=0.8),
        BeliefSpec(key="b", proposition="B.", confidence=0.8),
    ])
    assert pick_retraction_target(beliefs) is None


def test_the_three_pinned_scenarios_load_and_author_no_beliefs() -> None:
    """Stage 4's whole point is that structure arrives from the extractor.

    A scenario file that authored a belief, edge or confidence would be
    Stage 2 with extra steps.
    """
    scenarios = load_scenarios()
    assert set(scenarios) == {"verification", "incident_review", "flat"}
    for name, spec in scenarios.items():
        assert spec["evidence"], name
        for entry in spec["evidence"]:
            kind, text = entry
            assert kind in {"trace", "outcome", "event", "correction", "operator_note", "reflection"}
            assert isinstance(text, str) and text
        assert "beliefs" not in spec and "supports" not in spec, f"{name} must not author structure"
