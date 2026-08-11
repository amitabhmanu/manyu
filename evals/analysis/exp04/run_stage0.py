"""Experiment 4, Stage 0 — base rate and distinctness. Offline; no provider calls.

Two questions, in order, and the second can end the experiment.

**0a — base rate.** How often does a non-null dissonance signal occur on a
naturalistic reflective run? Checked before anything else because of what the
stored artifacts showed: across every run in `evals/analysis/`, 620 `contradicts`
fields and **4** non-empty. If contradictions stay that rare, "dissonance as a
control signal" is a fixture-only claim and the headline has to say so.

**0b — distinctness.** Does the signal pick out states the existing control
inputs do not already pick out? The incumbents are exactly what `Arbiter` and
`FastAppraiser` see today. If every turn dissonance flags is a turn some
incumbent already flags, wiring it in is a recoding and the experiment dies here
for the price of an offline run.

**No escalation threshold is needed, and none is used.** Requirements section 13
treats the firing level as a blocking open question, but the distinctness
question does not require one: dissonance's minimal predicate is "the web
contains a stated contradiction," which has no constant in it at all. If that
predicate already fails to separate, no threshold would rescue it. This is the
same move experiment 3 sections 11 and 12 made twice — removing the constant
beats choosing it well.

Usage:
    python evals/analysis/exp04/run_stage0.py --out evals/analysis/exp04/stage0.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from manyu.core import ManyuCore  # noqa: E402
from manyu.dissonance import MergedDissonanceQuery, _leaf_conflicts  # noqa: E402
from manyu.fork import seed_beliefs  # noqa: E402
from manyu.providers import ScenarioJSONProvider  # noqa: E402
from manyu.salience import load_web, verify_fixture_freeze, web_specs  # noqa: E402
from manyu.schemas import NormalizedEvent  # noqa: E402

#: The four experiment-1 fixtures. Naturalistic in the sense that matters here:
#: nobody authored a contradiction into them, so whether one arises is a fact
#: about what the pipeline builds from ordinary testimony.
NATURALISTIC = (
    "everyday_collaboration_mood",
    "constructive_rejection",
    "broken_promise_repair",
    "attachment_pressure",
)

#: The positive control. A null base rate means nothing without a condition where
#: the detector demonstrably fires — experiment 2's standing rule that a null
#: without a passing control is a bug, not a finding.
AUTHORED = ("multi_conflict_web", "adversarial_grounding", "hub_web")

AGENT = "agent_demo"


def _incumbents(turn: dict[str, Any]) -> dict[str, Any]:
    """Every control input the system already has, read off one reflective turn.

    These are not a chosen subset. They are the complete set of things
    `Arbiter.arbitrate` and `FastAppraiser.appraise` consult today, so
    "dissonance adds nothing" means "nothing here is missing what dissonance
    would supply."
    """
    trace = turn["trace"]
    appraisal, transition = trace["appraisal"], trace["transition"]
    emotions = transition["post_state"] or {}
    goal = next(
        (d["value"] for d in appraisal["dimensions"] if d["dimension"] == "goal_congruence"),
        0.0,
    )
    influence = (turn.get("prior_mood") or {}).get("influence") or {}
    return {
        "max_emotion": round(max(emotions.values()), 6) if emotions else 0.0,
        "confidence": appraisal["confidence"],
        "goal_impact": abs(goal),
        "event_type": trace["event"]["event_type"],
        "slow_required": bool(appraisal["slow_required"]),
        "activation": trace["interoception"]["activation"],
        "disposition": trace["arbitration"]["disposition"],
        "reason_codes": trace["arbitration"]["reason_codes"],
        "max_mood_influence": round(max(influence.values()), 6) if influence else 0.0,
    }


def _incumbent_escalates(incumbents: dict[str, Any]) -> list[str]:
    """Which incumbent branches would route this turn away from acting fast.

    Thresholds copied from the code, not invented here: `Arbiter.arbitrate` uses
    `max(state.emotions.values()) >= 0.75`; `FastAppraiser.appraise` sets
    `slow_required` on a correction, `confidence < 0.5`, or
    `abs(goal_impact) > 0.75`; and the mood branch flips `action_class` at 0.55.
    """
    fired = []
    if incumbents["max_emotion"] >= 0.75:
        fired.append("high_arousal")
    if incumbents["slow_required"]:
        fired.append("slow_required")
    if incumbents["confidence"] < 0.5:
        fired.append("low_confidence")
    if incumbents["goal_impact"] > 0.75:
        fired.append("goal_impact")
    if incumbents["event_type"] == "correction":
        fired.append("correction")
    if incumbents["max_mood_influence"] >= 0.55:
        fired.append("mood_bias")
    return fired


def generation_path_can_contradict(provider: Any) -> bool:
    """Can the extraction path emit a `contradicts` edge **at all**?

    **The gate that voids this stage's headline, and it must run before the base
    rate is read.** A base rate of zero is a finding only if a contradiction was
    reachable and did not arise. If the provider cannot represent one, the number
    describes the instrument.

    This is experiment 1's v2 failure in a new place: mood came back `null`, the
    `affect_influence` knob had nothing to bite on, and the resulting flat line
    survived a full pilot looking like a result. `gate.assert_not_noop` exists
    because of that family.

    Probed directly rather than inferred: hand the extractor two plainly opposed
    observations and see whether anything comes back with an edge on it.
    """
    opposed = [
        {
            "evidence_id": "bev_probe_a",
            "summary": "The deployment completed without errors.",
            "source_type": "operator_note",
            "trust_class": "trusted_system",
            "affective_salience": 0.6,
            "epistemic_weight": 0.8,
        },
        {
            "evidence_id": "bev_probe_b",
            "summary": "The deployment failed and rolled back with errors.",
            "source_type": "operator_note",
            "trust_class": "trusted_system",
            "affective_salience": 0.6,
            "epistemic_weight": 0.8,
        },
    ]
    prompt = "Extract Manyu worldview belief candidates from the following evidence:\n" + json.dumps(opposed)
    try:
        result = provider.generate_json(prompt, {}, None, 0.0)
    except Exception:
        return False
    candidates = result.get("candidates") if isinstance(result, dict) else None
    if not candidates:
        return False
    return any(candidate.get("contradicts") for candidate in candidates)


def _dissonance(core: ManyuCore) -> dict[str, Any]:
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "stage0")
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT)}
    conflicts = _leaf_conflicts(beliefs)
    if signal is None:
        return {"fires": False, "magnitude_raw": 0.0, "conflicts": len(conflicts), "carriers": 0, "belief_count": len(beliefs)}
    return {
        "fires": True,
        "magnitude_raw": signal.magnitude_raw,
        "conflicts": len(conflicts),
        "carriers": len(signal.carriers),
        "derived_carriers": sum(1 for c in signal.carriers if c.path),
        "belief_count": len(beliefs),
    }


def run_naturalistic(name: str) -> list[dict[str, Any]]:
    """Drive one experiment-1 fixture through the reflective loop, turn by turn."""
    fixture = json.loads((REPO / "evals" / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, belief_provider=ScenarioJSONProvider())

    records = []
    for index, raw in enumerate(fixture["events"]):
        event = NormalizedEvent.model_validate(raw)
        turn = core.process_reflective_turn({"event": event.model_dump(mode="json")})
        incumbents = _incumbents(turn)
        records.append(
            {
                "kind": "naturalistic",
                "fixture": name,
                "turn": index,
                "dissonance": _dissonance(core),
                "incumbents": incumbents,
                "incumbent_escalates": _incumbent_escalates(incumbents),
            }
        )
    return records


def run_authored(name: str) -> list[dict[str, Any]]:
    """The positive control: a web with conflicts authored into it."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_beliefs(core, web_specs(load_web(name)))
    return [{"kind": "authored", "fixture": name, "turn": 0, "dissonance": _dissonance(core), "incumbents": {}, "incumbent_escalates": []}]


def analyse(records: list[dict[str, Any]], *, generation_can_contradict: bool) -> dict[str, Any]:
    natural = [r for r in records if r["kind"] == "naturalistic"]
    authored = [r for r in records if r["kind"] == "authored"]

    fired = [r for r in natural if r["dissonance"]["fires"]]
    base_rate = len(fired) / len(natural) if natural else 0.0

    verdict: dict[str, Any] = {"generation_path_can_contradict": generation_can_contradict}
    if not generation_can_contradict:
        verdict["base_rate_status"] = "VOID"
        verdict["reason"] = (
            "The extraction path cannot emit a `contradicts` edge, so no naturalistic run on this "
            "provider could ever produce a conflict. The base rate below describes the instrument, "
            "not the webs, and must not be reported as a finding. `ScenarioJSONProvider."
            "_belief_candidates` hardcodes `contradicts: []`. **Stage 0a is therefore not answerable "
            "offline** and requires a provider that can represent the phenomenon."
        )
    else:
        verdict["base_rate_status"] = "readable"

    # 0b — the branch-disagreement set, over turns where dissonance fires.
    only_dissonance = [r for r in fired if not r["incumbent_escalates"]]
    only_incumbent = [r for r in natural if r["incumbent_escalates"] and not r["dissonance"]["fires"]]
    both = [r for r in fired if r["incumbent_escalates"]]

    return {
        "verdict": verdict,
        "turns": len(natural),
        "base_rate": round(base_rate, 4),
        "turns_with_a_conflict": len(fired),
        "authored_control_fires": all(r["dissonance"]["fires"] for r in authored),
        "authored_control_n": len(authored),
        "disagreement": {
            "only_dissonance": len(only_dissonance),
            "only_incumbent": len(only_incumbent),
            "both": len(both),
        },
        "incumbent_escalation_rate": round(
            sum(1 for r in natural if r["incumbent_escalates"]) / len(natural), 4
        )
        if natural
        else 0.0,
        "belief_counts": sorted({r["dissonance"]["belief_count"] for r in natural}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="evals/analysis/exp04/stage0.jsonl")
    args = parser.parse_args()

    # The fixtures carrying the positive control are frozen; a drifted one voids
    # the comparison rather than merely changing it.
    verify_fixture_freeze()

    # Run the instrument gate first. If the generation path cannot produce a
    # contradiction, the base rate below is unreadable and saying so is the
    # result — not the zero.
    generation_can_contradict = generation_path_can_contradict(ScenarioJSONProvider())

    records: list[dict[str, Any]] = []
    for name in NATURALISTIC:
        records.extend(run_naturalistic(name))
    for name in AUTHORED:
        records.extend(run_authored(name))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    summary = analyse(records, generation_can_contradict=generation_can_contradict)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
