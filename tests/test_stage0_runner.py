"""The Stage 0 instrument gate, and the fact it caught.

`run_stage0.py` measures how often a naturalistic reflective run produces a
dissonance signal. The first version reported a base rate of **0.0 across 35
turns** with the authored positive control firing 3/3 — which reads exactly like
a finding, and is not one.

`ScenarioJSONProvider._belief_candidates` hardcodes `"contradicts": []`, so the
offline extraction path **cannot represent a contradiction at all**. A base rate
of zero from that path describes the instrument, not the webs. This is experiment
1's v2 failure in a new place: mood came back `null`, the `affect_influence` knob
had nothing to bite on, and the flat line survived a full pilot looking like a
result.

The authored control did not catch it, and could not have: it exercises the
*detector*, while the defect is in the *generation* path. A positive control has
to sit on the path that could be broken.

Offline. No provider calls.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "analysis" / "exp04"))

from run_stage0 import analyse, generation_path_can_contradict  # noqa: E402

from manyu.providers import ScenarioJSONProvider  # noqa: E402


class _Contradicting:
    """A provider that can emit an edge. Exists so the gate is shown able to pass."""

    def generate_json(self, prompt: str, schema: dict, system: str | None = None, temperature: float = 0.0) -> dict:
        return {
            "candidates": [
                {"proposition": "It worked.", "belief_key": "a", "contradicts": []},
                {"proposition": "It did not work.", "belief_key": "b", "contradicts": ["a"]},
            ]
        }


class _Silent:
    def generate_json(self, prompt: str, schema: dict, system: str | None = None, temperature: float = 0.0) -> dict:
        return {"candidates": [{"proposition": "It worked.", "belief_key": "a", "contradicts": []}]}


class _Broken:
    def generate_json(self, prompt: str, schema: dict, system: str | None = None, temperature: float = 0.0) -> dict:
        raise RuntimeError("provider down")


class _Empty:
    def generate_json(self, prompt: str, schema: dict, system: str | None = None, temperature: float = 0.0) -> dict:
        return {"candidates": []}


# --- the gate ----------------------------------------------------------------

def test_the_offline_provider_cannot_emit_a_contradiction() -> None:
    """The fact that voids Stage 0a, pinned so it cannot be forgotten.

    If this ever starts passing, `ScenarioJSONProvider` has gained the ability to
    declare edges — and at that point the base rate becomes readable offline and
    Stage 0a should be re-run rather than left marked void.
    """
    assert generation_path_can_contradict(ScenarioJSONProvider()) is False


def test_the_gate_passes_a_provider_that_can_contradict() -> None:
    """A gate that cannot pass is as useless as one that cannot fail."""
    assert generation_path_can_contradict(_Contradicting()) is True


@pytest.mark.parametrize("provider", [_Silent(), _Broken(), _Empty()], ids=["silent", "broken", "empty"])
def test_the_gate_refuses_every_way_the_path_can_be_unable(provider: Any) -> None:
    assert generation_path_can_contradict(provider) is False


# --- the verdict the gate produces -------------------------------------------

def _records(fires: bool, turns: int = 4) -> list[dict[str, Any]]:
    return [
        {
            "kind": "naturalistic",
            "fixture": "f",
            "turn": index,
            "dissonance": {"fires": fires, "magnitude_raw": 0.3 if fires else 0.0, "conflicts": int(fires), "belief_count": 3},
            "incumbents": {},
            "incumbent_escalates": [],
        }
        for index in range(turns)
    ] + [
        {
            "kind": "authored",
            "fixture": "control",
            "turn": 0,
            "dissonance": {"fires": True, "magnitude_raw": 1.0, "conflicts": 3, "belief_count": 6},
            "incumbents": {},
            "incumbent_escalates": [],
        }
    ]


def test_a_zero_base_rate_is_marked_void_when_the_path_cannot_contradict() -> None:
    """The whole point: the number is still reported, and it is labelled unreadable.

    Experiment 3's standing method calls this "treat an impossible value as a
    defect report" — chasing one rather than publishing seven passing predictions
    is the only reason a foundationalist result was not written up as a Quinean
    one.
    """
    summary = analyse(_records(fires=False), generation_can_contradict=False)
    assert summary["base_rate"] == 0.0
    assert summary["verdict"]["base_rate_status"] == "VOID"
    assert "not answerable offline" in summary["verdict"]["reason"]


def test_the_same_zero_is_readable_when_the_path_could_have_contradicted() -> None:
    """The counterfactual. Identical data, different verdict, because the
    difference is whether the phenomenon was reachable.
    """
    summary = analyse(_records(fires=False), generation_can_contradict=True)
    assert summary["base_rate"] == 0.0
    assert summary["verdict"]["base_rate_status"] == "readable"
    assert "reason" not in summary["verdict"]


def test_a_positive_base_rate_is_computed_over_naturalistic_turns_only() -> None:
    """The authored control must not inflate the base rate it exists to validate."""
    summary = analyse(_records(fires=True), generation_can_contradict=True)
    assert summary["turns"] == 4, "the authored control leaked into the denominator"
    assert summary["base_rate"] == 1.0
    assert summary["authored_control_fires"] is True
    assert summary["authored_control_n"] == 1


def test_the_disagreement_set_separates_the_three_cases() -> None:
    """0b's measurable: which turns each channel would flag, and which only one does."""
    records = [
        {"kind": "naturalistic", "fixture": "f", "turn": 0, "dissonance": {"fires": True, "belief_count": 2}, "incumbents": {}, "incumbent_escalates": []},
        {"kind": "naturalistic", "fixture": "f", "turn": 1, "dissonance": {"fires": True, "belief_count": 2}, "incumbents": {}, "incumbent_escalates": ["high_arousal"]},
        {"kind": "naturalistic", "fixture": "f", "turn": 2, "dissonance": {"fires": False, "belief_count": 2}, "incumbents": {}, "incumbent_escalates": ["slow_required"]},
        {"kind": "naturalistic", "fixture": "f", "turn": 3, "dissonance": {"fires": False, "belief_count": 2}, "incumbents": {}, "incumbent_escalates": []},
    ]
    summary = analyse(records, generation_can_contradict=True)
    assert summary["disagreement"] == {"only_dissonance": 1, "only_incumbent": 1, "both": 1}
