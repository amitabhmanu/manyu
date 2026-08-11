"""Experiment 4, Stages 2-4 on authored webs. Offline; no provider calls.

Deterministic under `FrozenClock`, so `n=1` is correct wherever no randomness is
involved — repetition would re-measure the same arithmetic. The two places that
*are* stochastic say so and repeat: the random arm draws a conflict, and Stage
3's derangement rewires a graph.

**Stage 2 — efficacy.** Sweeps the attention budget rather than fixing it,
because the budget turned out to be the real independent variable: driven,
inverted and random converge exactly when the budget covers every conflict, and
differ only while attention is scarce.

**Stage 3 — is the signal pointing at anything?** Measures `spread`, the
fraction of the web the carrier set implicates, against a degree-preserving
derangement of the `supports` edges. "Do the carriers name the beliefs acted on"
is settled by wiring and is not asked.

**Stage 4 — adversarial.** On a multi-conflict web where grounding and tension
are anti-correlated, what fraction of a scarce budget lands on well-grounded
targets.

Usage:
    python evals/analysis/exp04/run_stages.py --out evals/analysis/exp04/stages.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from manyu.core import ManyuCore  # noqa: E402
from manyu.dissonance import MergedDissonanceQuery  # noqa: E402
from manyu.fork import seed_beliefs  # noqa: E402
from manyu.salience import (  # noqa: E402
    Arm,
    AttentionLoop,
    derange_supports,
    load_web,
    reading_of,
    spread,
    verify_fixture_freeze,
    web_specs,
)

AGENT = "agent_demo"

#: Pinned before the run. Stage 2 sweeps the budget; the top of the range is one
#: past the conflict count of the widest web, so the convergence point is inside
#: the swept range rather than assumed.
BUDGET_SWEEP = (1, 2, 3, 4)
RANDOM_SEEDS = tuple(range(20))
DERANGEMENT_SEEDS = tuple(range(50))

STAGE2_WEBS = ("multi_conflict_web", "hub_web", "adversarial_multi")
STAGE3_WEBS = ("distractor_web", "depth_carrier_web", "hub_web")
STAGE4_WEBS = ("adversarial_multi",)


def _seeded(name: str, specs: list[Any] | None = None) -> tuple[ManyuCore, dict[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, specs if specs is not None else web_specs(load_web(name)))
    return core, ids


def _run(name: str, arm: Arm, budget: int, seed: int | None = None):
    core, ids = _seeded(name)
    result = AttentionLoop(core, arm=arm, agent_id=AGENT, seed=seed).run(max_iterations=budget)
    return result, {bid: key for key, bid in ids.items()}


# --- Stage 2 -----------------------------------------------------------------


def stage2(name: str) -> list[dict[str, Any]]:
    records = []
    for budget in BUDGET_SWEEP:
        driven, _ = _run(name, Arm.DRIVEN, budget)
        inverted, _ = _run(name, Arm.INVERTED, budget)
        randoms = [_run(name, Arm.RANDOM_MATCHED, budget, seed=s)[0].trajectory[-1] for s in RANDOM_SEEDS]
        records.append(
            {
                "stage": 2,
                "fixture": name,
                "budget": budget,
                "driven_remaining": driven.trajectory[-1],
                "inverted_remaining": inverted.trajectory[-1],
                "random_mean": round(statistics.mean(randoms), 6),
                "random_min": min(randoms),
                "random_max": max(randoms),
                "driven_steps": len(driven.steps),
                "driven_termination": driven.termination.value,
                "converged": abs(driven.trajectory[-1] - inverted.trajectory[-1]) < 1e-9,
                "had_arbitrary_choice": driven.had_arbitrary_choice,
            }
        )
    return records


# --- Stage 3 -----------------------------------------------------------------


def _spread_of(name: str, specs: list[Any] | None = None) -> tuple[float, int, int]:
    core, _ = _seeded(name, specs)
    beliefs = core.store.list_beliefs(AGENT)
    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "stage3"), agent_id=AGENT)
    if reading is None:
        return 0.0, 0, len(beliefs)
    view = reading.view
    return spread(view, len(beliefs)), len(view.carriers), len(beliefs)


def stage3(name: str) -> dict[str, Any]:
    real_spread, carriers, belief_count = _spread_of(name)
    specs = web_specs(load_web(name))
    deranged = []
    for seed in DERANGEMENT_SEEDS:
        value, _, _ = _spread_of(name, derange_supports(specs, seed))
        deranged.append(value)

    mean = statistics.mean(deranged)
    # Where the real value sits in the null distribution. A one-sided empirical
    # p: the fraction of deranged webs at or below the real spread. Small means
    # the real web implicates less of itself than rewiring would.
    at_or_below = sum(1 for value in deranged if value <= real_spread + 1e-9)
    p_value = at_or_below / len(deranged)

    # A web whose signal already names every belief is at the ceiling, and
    # nothing below the ceiling is measurable. Experiment 1's failure mode #3 —
    # a metric pinned at the end of its range reporting its own constant — and
    # `gate.assert_has_range` exists for exactly this.
    measurable = real_spread < 1.0 - 1e-9

    if not measurable:
        verdict = "unmeasurable_at_ceiling"
    elif p_value <= 0.05:
        verdict = "more_specific_than_chance"
    else:
        verdict = "indistinguishable_from_chance"

    return {
        "stage": 3,
        "fixture": name,
        "belief_count": belief_count,
        "carriers": carriers,
        "real_spread": round(real_spread, 6),
        "deranged_mean": round(mean, 6),
        "deranged_min": round(min(deranged), 6),
        "deranged_max": round(max(deranged), 6),
        "p_at_or_below": round(p_value, 4),
        "measurable": measurable,
        "verdict": verdict,
        # Kept deliberately, and deliberately *not* the verdict. Comparing the
        # real value to the null's mean says only which side of centre it fell
        # on; at p = 0.48 that reads as "more specific" while the value sits
        # squarely mid-distribution. A quantity that looks right and means
        # something else — the family every experiment-3 defect belonged to.
        "below_deranged_mean": real_spread < mean - 1e-9,
    }


# --- Stage 4 -----------------------------------------------------------------


def stage4(name: str) -> list[dict[str, Any]]:
    records = []
    for budget in BUDGET_SWEEP:
        row: dict[str, Any] = {"stage": 4, "fixture": name, "budget": budget}
        for arm in (Arm.DRIVEN, Arm.INVERTED):
            result, reverse = _run(name, arm, budget)
            hits = result.weakened_the_better_grounded_side
            row[f"{arm.value}_targets"] = [reverse[step.target_id] for step in result.steps]
            row[f"{arm.value}_target_evidence"] = [step.target_evidence_count for step in result.steps]
            row[f"{arm.value}_well_grounded_hits"] = sum(hits)
            row[f"{arm.value}_steps"] = len(hits)
        drawn = []
        for seed in RANDOM_SEEDS:
            result, _ = _run(name, Arm.RANDOM_MATCHED, budget, seed=seed)
            drawn.append(sum(result.weakened_the_better_grounded_side))
        row["random_well_grounded_mean"] = round(statistics.mean(drawn), 4)
        records.append(row)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="evals/analysis/exp04/stages.jsonl")
    args = parser.parse_args()

    verify_fixture_freeze()

    records: list[dict[str, Any]] = []
    for name in STAGE2_WEBS:
        records.extend(stage2(name))
    for name in STAGE3_WEBS:
        records.append(stage3(name))
    for name in STAGE4_WEBS:
        records.extend(stage4(name))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    print(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
