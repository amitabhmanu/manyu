"""Experiment 5 stages 2-4 — collapse, stability, expression.

Offline and deterministic under `FrozenClock`, so `n=1` is correct: repetition
re-measures the same arithmetic (experiment 2 methodology section 1).

- **Stage 2** runs the frozen control set. `discriminating` must collapse; without
  it "the state held" is not evidence of anything, because a state that cannot
  break is a state we wrote (requirements section 2 flavour A).
- **Stage 3** sweeps the attention budget rather than the arm, on experiment 4
  section 3's finding that the budget was the real independent variable, and
  separately accumulates non-separating evidence.
- **Stage 4** records what the system *says*: what `WorldviewSynthesizer` emits and
  whether the meta-belief satisfies pre-registration section 5's three parts.

**What Stage 4 deliberately does not do offline.** Pre-registration section 5 asks
for an honesty-scorer read on a generated report. A *templated* report is authored
by us, so scoring one measures our template rather than Manyu, and the honesty
scorer's failure-mode labels are not decision-grade in any case (SC-5 at 67.9%).
The scored report belongs to Stage 5, where a real reporter runs. Recorded here
as a gap rather than filled with something that looks like a result.

Entirely offline. No provider call, no spend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from manyu.core import ManyuCore  # noqa: E402
from manyu.salience import Arm, AttentionLoop  # noqa: E402
from manyu.services import WorldviewSynthesizer  # noqa: E402
from manyu.underdetermination import (  # noqa: E402
    EXPRESSION_THRESHOLD,
    EvidenceSpec,
    OverlapConfig,
    OverlapMode,
    RivalBeliefSpec,
    apply_then,
    derive,
    load_web,
    read,
    seed_fixture,
    seed_web,
    verify_freeze,
)

AGENT = "agent_demo"
OUT = REPO / "evals" / "analysis" / "exp05" / "stages.jsonl"

CONTROL_SET = (
    "symmetric_rivals",
    "symmetric_rivals_oneway",
    "near_miss",
    "shared_evidence_no_conflict",
    "conflict_disjoint_evidence",
    "three_way",
)


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _seeded(fixture: str) -> tuple[ManyuCore, dict[str, str]]:
    core = _core()
    return core, seed_fixture(core, fixture, agent_id=AGENT)


# --- stage 2 -----------------------------------------------------------------


def stage2_control_set() -> list[dict[str, Any]]:
    rows = []
    for fixture in CONTROL_SET:
        core, _ = _seeded(fixture)
        result = derive(core, AGENT).as_dict()
        expected = load_web(fixture)["role"]
        rows.append(
            {
                "kind": "stage2",
                "fixture": fixture,
                "role": expected,
                "rival_sets": len(result["rival_sets"]),
                "derived": len(result["derived"]),
                "confidences": [row["confidence"] for row in result["derived"]],
                "overlaps": [row["derived_overlap"] for row in result["derived"]],
                "below_threshold": [row["below_expression_threshold"] for row in result["derived"]],
            }
        )
    return rows


def stage2_collapse() -> list[dict[str, Any]]:
    """The arm that licenses reading anything else."""
    core, minted = _seeded("discriminating")
    before = derive(core, AGENT).as_dict()["derived"][0]

    apply_then(core, "discriminating", minted, agent_id=AGENT)
    after = derive(core, AGENT).as_dict()

    weakened = after["weakened"][0]
    return [
        {
            "kind": "stage2_collapse",
            "fixture": "discriminating",
            "phase_1_confidence": before["confidence"],
            "phase_1_overlap": before["derived_overlap"],
            "phase_2_overlap": weakened["derived_overlap"],
            "phase_2_confidence": weakened["confidence"],
            "moved": weakened["moved"],
            "still_admitted": len(after["derived"]),
            "still_expressed": not weakened["below_expression_threshold"],
        }
    ]


def stage2_collapse_trajectory() -> list[dict[str, Any]]:
    """How much separating evidence it takes to stop the state being expressed.

    The single-record collapse above clears pre-registration section 2 and leaves
    the meta-belief at 0.847 — still above the expression threshold, so Manyu goes
    on saying it cannot tell the readings apart while holding evidence that
    separates them. Whether that is inertia working as designed or a state
    surviving its own disconfirmation is not answerable from one record, so the
    trajectory is measured rather than argued.

    The damping is `blend_confidence`'s, which is experiment 3's mechanism and
    carries experiment 3's constants. **It is not tuned here.** Reporting how slow
    it is beats making it faster.
    """
    core, minted = _seeded("symmetric_rivals")
    derive(core, AGENT)
    fixture = load_web("symmetric_rivals")
    props = {entry["key"]: entry for entry in fixture["beliefs"]}
    evidence_keys = ["obs_redshift", "obs_isotropy"]
    rows = []

    for index in range(6):
        key = f"obs_separating_{index}"
        evidence_keys = evidence_keys + [key]
        spec = RivalBeliefSpec(
            key="reading_a",
            proposition=props["reading_a"]["proposition"],
            evidence=tuple(evidence_keys),
            confidence=props["reading_a"]["confidence"],
            valence=props["reading_a"]["valence"],
            contradicts=tuple(props["reading_a"].get("contradicts", ())),
        )
        minted, _ = seed_web(
            core,
            [EvidenceSpec(key=key, summary=f"An observation only the first reading accommodates ({index}).")],
            [spec],
            agent_id=AGENT,
            evidence_ids=minted,
        )
        derive(core, AGENT)
        held = read(core, AGENT)[0]
        rows.append(
            {
                "kind": "stage2_trajectory",
                "fixture": "symmetric_rivals",
                "separating_records": index + 1,
                "meta_confidence": held["confidence"],
                "still_expressed": not held["below_expression_threshold"],
            }
        )
    return rows


def stage2_ablation() -> list[dict[str, Any]]:
    """`GRADED` must be seen behaving differently, or it demonstrates nothing.

    A mode selector over a single behaviour is the `ContradictionArm` defect —
    stored, stamped onto every result, consulted by no branch — waiting to happen.
    """
    core, minted = _seeded("discriminating")
    apply_then(core, "discriminating", minted, agent_id=AGENT)
    rows = []
    for mode, tolerance in ((OverlapMode.STRICT, 0.0), (OverlapMode.GRADED, 0.4)):
        probe, probe_minted = _seeded("discriminating")
        apply_then(probe, "discriminating", probe_minted, agent_id=AGENT)
        result = derive(probe, AGENT, config=OverlapConfig(mode=mode, tolerance=tolerance)).as_dict()
        rows.append(
            {
                "kind": "stage2_ablation",
                "mode": mode.value,
                "tolerance": tolerance,
                "admits_after_separation": len(result["rival_sets"]),
            }
        )
    return rows


# --- stage 3 -----------------------------------------------------------------


def stage3_attention_budget() -> list[dict[str, Any]]:
    """Sweep the budget, not the arm. Experiment 4 section 3."""
    rows = []
    for budget in (1, 2, 3, 4, 8):
        for arm in (Arm.DRIVEN, Arm.INVERTED):
            core, _ = _seeded("symmetric_rivals")
            derive(core, AGENT)
            before = read(core, AGENT)[0]["confidence"]
            loop = AttentionLoop(core, arm=arm, agent_id=AGENT).run(max_iterations=budget)
            derive(core, AGENT)
            after = read(core, AGENT)[0]["confidence"]
            rows.append(
                {
                    "kind": "stage3_budget",
                    "fixture": "symmetric_rivals",
                    "arm": arm.value,
                    "budget": budget,
                    "meta_before": before,
                    "meta_after": after,
                    "meta_moved": round(before - after, 6),
                    "loop_steps": len(loop.steps),
                    "loop_moved_total": round(sum(step.moved for step in loop.steps), 6),
                }
            )
    return rows


def stage3_non_separating_evidence() -> list[dict[str, Any]]:
    """Evidence that says nothing about the separation must not retire the state.

    Added to *both* rivals, so the overlap stays 1.0 by construction and any
    movement is the substrate reacting to volume — which is the confound
    `near_miss` guards statically and this guards dynamically.
    """
    core, minted = _seeded("symmetric_rivals")
    derive(core, AGENT)
    rows = []
    shared_keys = ["obs_redshift", "obs_isotropy"]
    fixture = load_web("symmetric_rivals")
    props = {entry["key"]: entry for entry in fixture["beliefs"]}

    for index in range(4):
        key = f"obs_corroborating_{index}"
        shared_keys = shared_keys + [key]
        specs = [
            RivalBeliefSpec(
                key=name,
                proposition=props[name]["proposition"],
                evidence=tuple(shared_keys),
                confidence=props[name]["confidence"],
                valence=props[name]["valence"],
                contradicts=tuple(props[name].get("contradicts", ())),
            )
            for name in ("reading_a", "reading_b")
        ]
        minted, _ = seed_web(
            core,
            [EvidenceSpec(key=key, summary=f"A further observation both readings accommodate ({index}).")],
            specs,
            agent_id=AGENT,
            evidence_ids=minted,
        )
        result = derive(core, AGENT).as_dict()
        held = read(core, AGENT)[0]
        rows.append(
            {
                "kind": "stage3_evidence",
                "fixture": "symmetric_rivals",
                "records_added": index + 1,
                "shared_records": len(shared_keys),
                "overlap": result["rival_sets"][0]["overlap"] if result["rival_sets"] else None,
                "meta_confidence": held["confidence"],
                "still_expressed": not held["below_expression_threshold"],
            }
        )
    return rows


# --- stage 4 -----------------------------------------------------------------


def stage4_expression() -> list[dict[str, Any]]:
    rows = []
    for fixture in ("symmetric_rivals", "near_miss"):
        core, _ = _seeded(fixture)
        stances_before = _stances(core)
        derive(core, AGENT)
        stances_after = _stances(core)
        held = read(core, AGENT)[0]
        rivals = [core.store.get_belief(bid) for bid in held["rivals"]]
        proposition = held["proposition"].lower()

        # Pre-registration §5's three parts, computed rather than eyeballed.
        names_both = all(r.proposition.rstrip(".").lower() in proposition for r in rivals)
        cites_shared = set(held["evidence_ids"]) >= (set(rivals[0].evidence_ids) & set(rivals[1].evidence_ids))
        asserts_neither = held["confidence"] >= EXPRESSION_THRESHOLD and len(held["rivals"]) == 2

        rows.append(
            {
                "kind": "stage4",
                "fixture": fixture,
                "stances_before_derivation": stances_before,
                "stances_after_derivation": stances_after,
                "rival_stance_still_averaged": any(s["theme"] == "world_model" and s["beliefs"] == 2 for s in stances_after),
                "meta_stance_emitted": any(s["theme"] == "underdetermination" for s in stances_after),
                "names_both_rivals": names_both,
                "cites_shared_evidence": cites_shared,
                "asserts_neither": asserts_neither,
                "expresses_the_state": names_both and cites_shared and asserts_neither,
            }
        )
    return rows


def _stances(core: ManyuCore) -> list[dict[str, Any]]:
    return [
        {"theme": s.theme, "confidence": s.confidence, "beliefs": len(s.supporting_belief_ids)}
        for s in WorldviewSynthesizer(core.store, core.clock).synthesize(AGENT)
    ]


# --- verdict -----------------------------------------------------------------


def analyse(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Recomputed from the rows, so `results.md` cannot drift from its evidence."""
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        by_kind.setdefault(row["kind"], []).append(row)

    control = {row["fixture"]: row for row in by_kind.get("stage2", [])}
    collapse = by_kind.get("stage2_collapse", [{}])[0]
    trajectory = by_kind.get("stage2_trajectory", [])
    retired = [row["separating_records"] for row in trajectory if not row["still_expressed"]]
    ablation = {row["mode"]: row for row in by_kind.get("stage2_ablation", [])}
    budgets = by_kind.get("stage3_budget", [])
    evidence = by_kind.get("stage3_evidence", [])
    expression = by_kind.get("stage4", [])

    return {
        "kind": "verdict",
        # Stage 2 — pre-registration §2 requires a fall of at least 0.15.
        "collapse_moved": collapse.get("moved"),
        "collapse_meets_prereg": (collapse.get("moved") or 0) >= 0.15,
        "collapse_still_expressed_after": collapse.get("still_expressed"),
        "separating_records_to_stop_expressing": min(retired) if retired else None,
        "collapse_trajectory": [row["meta_confidence"] for row in trajectory],
        # Pre-registration §3 — near_miss within 0.05 of symmetric_rivals.
        "near_miss_delta": round(
            abs((control.get("near_miss", {}).get("confidences") or [0])[0] - (control.get("symmetric_rivals", {}).get("confidences") or [0])[0]),
            6,
        ),
        "negatives_declined": all(
            control.get(name, {}).get("derived") == 0 for name in ("shared_evidence_no_conflict", "conflict_disjoint_evidence")
        ),
        "three_way_sets": control.get("three_way", {}).get("rival_sets"),
        "ablation_diverges": ablation.get("strict", {}).get("admits_after_separation")
        != ablation.get("graded", {}).get("admits_after_separation"),
        # Stage 3 — pre-registration §4: loop ≤ 0.01, evidence ≤ 0.05.
        "max_meta_moved_by_loop": max((abs(row["meta_moved"]) for row in budgets), default=None),
        "loop_stability_meets_prereg": all(abs(row["meta_moved"]) <= 0.01 for row in budgets),
        "max_meta_moved_by_evidence": max(
            (abs(row["meta_confidence"] - 1.0) for row in evidence), default=None
        ),
        "evidence_stability_meets_prereg": all(abs(row["meta_confidence"] - 1.0) <= 0.05 for row in evidence),
        # Stage 4.
        "expresses_the_state": all(row["expresses_the_state"] for row in expression),
        "rival_stance_still_averaged": all(row["rival_stance_still_averaged"] for row in expression),
    }


def main() -> int:
    verify_freeze()

    records: list[dict[str, Any]] = []
    records += stage2_control_set()
    records += stage2_collapse()
    records += stage2_collapse_trajectory()
    records += stage2_ablation()
    records += stage3_attention_budget()
    records += stage3_non_separating_evidence()
    records += stage4_expression()

    verdict = analyse(records)
    records.append(verdict)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")

    print(json.dumps(verdict, indent=2))
    print(f"\n{len(records)} rows -> {OUT.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
