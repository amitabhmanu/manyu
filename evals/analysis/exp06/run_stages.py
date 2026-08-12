"""Experiment 6 stages 0 through 3 — enumeration, calibration, dose, receipts.

Records, as artifacts, what `tests/test_exp06_rederivation.py` re-derives. The
pre-registration is the standard; this is the evidence `results.md` rests on, and
the two must agree or one of them is wrong.

**The two pricers, and why both exist.** The analytic pricer is the deliverable:
a pure function that never touches the store. Replay is the instrument that
grades it -- it drives the real `core.update_beliefs` path and reads what
actually happened. Stage 1 is the comparison.

**Replay re-seeds rather than copies, and that is a recorded amendment.**
Methodology section 5 described replay as copying the agent into a scratch
`:memory:` store. `ManyuStore` has `export_agent` and no import, so there is no
copy path; replay instead re-seeds the fixture under `FrozenClock` and applies
the delivery. Deterministic and faithful for these fixtures, and weaker in
general -- it can only replay histories a fixture can express.

Entirely offline. No provider call, no spend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from manyu import underdetermination as ud  # noqa: E402
from manyu.counterfactual import (  # noqa: E402
    DEFAULT_DOSE_BOUND,
    EdgeIntent,
    HypotheticalEvidence,
    Mechanism,
    build_receipt,
    critical_arrival_ratio,
    dose_for_standoff,
    enumerate_changers,
    price,
)
from manyu.schemas import BeliefType  # noqa: E402

import test_counterfactual_substrate as T  # noqa: E402

OUT = REPO / "evals" / "analysis" / "exp06" / "stages.jsonl"
EXP06_FIXTURES = REPO / "evals" / "fixtures" / "exp06"

THRESHOLD = 0.45
#: Amended from 1e-9 (pre-registration section 7, A1). `_revise` stores
#: `round(confidence, 6)`, so an observation is quantised to six places and exact
#: agreement is bounded below by 5e-7 -- 1e-9 could only ever have failed.
DIRECT_PATH_TOLERANCE = 1e-6
CALIBRATED = 0.05
UNCALIBRATED = 0.15


def _seed(name: str, directory: Path | None = None) -> tuple[Any, dict[str, str]]:
    core = T._core()
    minted = ud.seed_fixture(core, name, agent_id=T.AGENT, directory=directory or ud.FIXTURE_DIR)
    ud.derive(core, T.AGENT)
    return core, minted


def _meta(core: Any):
    held = core.store.list_beliefs(T.AGENT, belief_type=BeliefType.UNDERDETERMINATION.value, include_inactive=True)
    return held[0] if held else None


def _rival_beliefs(core: Any) -> list[Any]:
    return sorted(
        (b for b in core.store.list_beliefs(T.AGENT, include_inactive=True) if b.belief_type is not BeliefType.UNDERDETERMINATION),
        key=lambda b: b.belief_id,
    )


# --- Stage 0: enumeration against structural ground truth --------------------


def _stage0() -> list[dict[str, Any]]:
    """Ground truth is `separating_evidence`'s definition, written for experiment 5.

    A record entering exactly one rival separates the pair; a record entering
    both cannot, whatever it says. So the target is the set of single-rival
    attachment patterns, and nobody typed it into a fixture.
    """
    rows: list[dict[str, Any]] = []

    for name in ("symmetric_rivals", "near_miss"):
        core, _ = _seed(name)
        meta = _meta(core)
        rivals = sorted(meta.rivals)
        target = {frozenset([r]) for r in rivals}

        enumeration = enumerate_changers(core.store, meta, threshold=THRESHOLD)
        emitted = {frozenset(item.attaches_to) for item in enumeration.items}

        true_positive = len(emitted & target)
        precision = true_positive / len(emitted) if emitted else 0.0
        recall = true_positive / len(target) if target else 0.0
        declined_patterns = [sorted(d.get("attaches_to", [])) for d in enumeration.declined]

        rows.append(
            {
                "stage": 0,
                "check": "enumeration_vs_structural_truth",
                "fixture": name,
                "target": [sorted(p) for p in target],
                "emitted": [sorted(p) for p in emitted],
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "declined": declined_patterns,
                "declined_reasons": [d.get("reason") for d in enumeration.declined],
                "agrees": precision == 1.0 and recall == 1.0,
                "note": (
                    "Target is derived from `separating_evidence`'s definition, written before this "
                    "experiment existed and for another purpose. Precision and recall are exact set "
                    "agreement, not a graded score -- a graded score here would be a way of passing "
                    "while wrong."
                ),
            }
        )

    # Negatives: the criterion must decline where no standoff exists.
    for name in ("shared_evidence_no_conflict", "conflict_disjoint_evidence"):
        core, _ = _seed(name)
        meta = _meta(core)
        rows.append(
            {
                "stage": 0,
                "check": "no_standoff_no_enumeration",
                "fixture": name,
                "meta_belief_derived": meta is not None,
                "agrees": meta is None,
                "note": "No rival set, so nothing structural to enumerate. Both halves of experiment 5's criterion are load-bearing here too.",
            }
        )

    rows.extend(_stage0_controls())
    return rows


def _stage0_controls() -> list[dict[str, Any]]:
    """`irrelevant_evidence` and `already_held`, both halves each."""
    rows: list[dict[str, Any]] = []

    core, _ = _seed("irrelevant_evidence", EXP06_FIXTURES)
    meta = _meta(core)
    loose = HypotheticalEvidence(summary="A record bearing on nothing in the web.", confidence=0.7, attaches_to=())
    predicted = price(core.store, meta, loose)
    before = meta.confidence
    # Observed: deliver a record that enters no belief's provenance.
    T._capture(core, "obs_kettle_delivered")
    ud.derive(core, T.AGENT)
    observed = _meta(core).confidence
    rows.append(
        {
            "stage": 0,
            "check": "irrelevant_evidence",
            "fixture": "irrelevant_evidence",
            "predicted_delta": round(predicted.delta, 9),
            "observed_delta": round(observed - before, 9),
            "mechanism": predicted.mechanism.value,
            "tolerance": 0.01,
            "agrees": abs(predicted.delta) <= 0.01 and abs(observed - before) <= 0.01,
            "note": "Both halves required. A prediction of zero never checked against a delivery is a readout nobody reads.",
        }
    )

    core, minted = _seed("already_held", EXP06_FIXTURES)
    meta = _meta(core)
    left = _rival_beliefs(core)[0]
    held = HypotheticalEvidence(
        summary="A record the belief already cites.",
        confidence=0.7,
        attaches_to=(left.belief_id,),
        evidence_id=minted["obs_redshift"],
    )
    predicted = price(core.store, left, held)
    before = left.confidence
    T._repropose(core, left.belief_key, left.proposition, list(left.evidence_ids))
    observed = core.store.get_belief(left.belief_id).confidence
    rows.append(
        {
            "stage": 0,
            "check": "already_held",
            "fixture": "already_held",
            "predicted_delta": round(predicted.delta, 12),
            "observed_delta": round(observed - before, 12),
            "mechanism": predicted.mechanism.value,
            "agrees": predicted.delta == 0.0 and observed == before and predicted.mechanism is Mechanism.GUARD_NOOP,
            "note": "FR-9. The correct price is exactly 0.000, not approximately -- `_revise` returns the belief untouched.",
        }
    )
    return rows


# --- Stage 1: calibration -----------------------------------------------------


def _stage1() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for name, shared in (("symmetric_rivals", 2), ("near_miss", 6)):
        for k in range(1, 7):
            # Analytic: price the k-th separating record against the state the
            # model says the belief is in after k-1 of them.
            core, minted = _seed(name)
            meta = _meta(core)
            left = _rival_beliefs(core)[0]
            evidence = list(left.evidence_ids)

            predicted_delta = observed_delta = None
            for step in range(1, k + 1):
                meta_now = _meta(core)
                hypothetical = HypotheticalEvidence(
                    summary=f"A separating observation, number {step}.",
                    confidence=meta_now.confidence,
                    attaches_to=(left.belief_id,),
                )
                predicted = price(core.store, meta_now, hypothetical)
                before = meta_now.confidence

                new_id = T._capture(core, f"obs_sep_{step}")
                evidence = evidence + [new_id]
                T._repropose(core, left.belief_key, f"Reading citing {len(evidence)} records.", evidence)
                ud.derive(core, T.AGENT)
                after = _meta(core).confidence

                predicted_delta = predicted.predicted_confidence
                observed_delta = after

            rows.append(
                {
                    "stage": 1,
                    "check": "calibration_direct",
                    "fixture": name,
                    "shared": shared,
                    "k": k,
                    "predicted_confidence": round(predicted_delta, 9),
                    "observed_confidence": round(observed_delta, 9),
                    "abs_error": round(abs(predicted_delta - observed_delta), 12),
                    "path": "direct",
                    "topology": "mutual",
                    "agrees": abs(predicted_delta - observed_delta) < DIRECT_PATH_TOLERANCE,
                    "note": (
                        "Reported as a regression test, never as calibration. Both sides call "
                        "`blend_confidence` with the same arguments, so agreement is construction "
                        "(requirements section 5.1)."
                    ),
                }
            )

    rows.append(_stage1_topology())
    return rows


def _stage1_topology() -> dict[str, Any]:
    """Where the prediction stops being a tautology: the pricer assumes mutual edges.

    `symmetric_rivals_oneway` is the same web with one edge instead of two.
    Experiment 5 section 6.1 measured that this separates an otherwise identical
    pair by 0.2333 through the confidence channel. The pricer reads the rivals'
    evidence sets and not their edge direction, so it is blind to it -- and this
    row is the measurement of that blindness rather than an argument about it.
    """
    mutual_core, _ = _seed("symmetric_rivals")
    oneway_core, _ = _seed("symmetric_rivals_oneway")

    def _first_delta(core: Any) -> tuple[float, float]:
        meta = _meta(core)
        left = _rival_beliefs(core)[0]
        hypothetical = HypotheticalEvidence(summary="A separating observation.", confidence=meta.confidence, attaches_to=(left.belief_id,))
        predicted = price(core.store, meta, hypothetical)
        before = meta.confidence
        new_id = T._capture(core, "obs_sep_1")
        T._repropose(core, left.belief_key, "Reading citing a third record.", list(left.evidence_ids) + [new_id])
        ud.derive(core, T.AGENT)
        return predicted.predicted_confidence - before, _meta(core).confidence - before

    mutual_pred, mutual_obs = _first_delta(mutual_core)
    oneway_pred, oneway_obs = _first_delta(oneway_core)

    return {
        "stage": 1,
        "check": "calibration_topology",
        "path": "extractor_proxy",
        "mutual": {"predicted": round(mutual_pred, 6), "observed": round(mutual_obs, 6), "abs_error": round(abs(mutual_pred - mutual_obs), 9)},
        "oneway": {"predicted": round(oneway_pred, 6), "observed": round(oneway_obs, 6), "abs_error": round(abs(oneway_pred - oneway_obs), 9)},
        "calibrated_band": CALIBRATED,
        "uncalibrated_band": UNCALIBRATED,
        "attributable": True,
        "agrees": abs(mutual_pred - mutual_obs) < DIRECT_PATH_TOLERANCE and abs(oneway_pred - oneway_obs) < DIRECT_PATH_TOLERANCE,
        "note": (
            "The one-way arm is the nearest offline proxy for the extractor path: the topology differs and "
            "the pricer was not told. Pre-registration section 3 predicted mispredictions concentrate in "
            "topology, and this row is where that becomes checkable offline. A real extractor is stage 4."
        ),
    }


# --- Stage 2: dose and the entrenchment census -------------------------------


def _stage2() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for name, shared, registered in (("symmetric_rivals", 2, 5), ("near_miss", 6, 10)):
        core, _ = _seed(name)
        meta = _meta(core)
        dose = dose_for_standoff(shared, start=meta.confidence, stability=meta.stability, threshold=THRESHOLD)
        rows.append(
            {
                "stage": 2,
                "check": "dose",
                "fixture": name,
                "shared_records": shared,
                "dose": dose.records,
                "registered": registered,
                "trajectory": [round(v, 4) for v in dose.trajectory[:12]],
                "agrees": dose.records == registered,
                "note": (
                    "Experiment 5 established that a ratio cancels cardinality -- near_miss carries three "
                    "times the evidence and lands at the identical confidence. The MARGINAL record does not "
                    "cancel it, because the overlap after k records is shared/(shared+k), a function of "
                    "shared. Volume is invisible to detection and dominates the dose."
                ),
            }
        )

    rows.append(_stage2_census())
    return rows


def _stage2_census() -> dict[str, Any]:
    """Dose against entrenchment, with the fixture-built control alongside.

    Entrenchment is accumulated by delivering non-separating records through the
    priced ingest path, so stability is what the substrate reached rather than a
    value typed into a fixture. Methodology section 3: a fixture that sets
    stability authors a large part of the answer, so this arm is a positive
    control and never evidence for the dose result.
    """
    observations = []
    for corroborations in (0, 2, 4, 6, 8):
        core, _ = _seed("entrenched", EXP06_FIXTURES)
        left, right = _rival_beliefs(core)
        left_ev, right_ev = list(left.evidence_ids), list(right.evidence_ids)
        for i in range(corroborations):
            shared_id = T._capture(core, f"obs_corr_{i}")
            left_ev, right_ev = left_ev + [shared_id], right_ev + [shared_id]
            T._repropose(core, left.belief_key, f"Left corroborated {i}.", left_ev)
            T._repropose(core, right.belief_key, f"Right corroborated {i}.", right_ev)
        ud.derive(core, T.AGENT)
        meta = _meta(core)
        dose = dose_for_standoff(len(set(left_ev) & set(right_ev)), start=meta.confidence, stability=meta.stability, threshold=THRESHOLD)
        observations.append(
            {
                "corroborations": corroborations,
                "shared_records": len(set(left_ev) & set(right_ev)),
                "meta_stability": round(meta.stability, 6),
                "meta_confidence": round(meta.confidence, 6),
                "dose": dose.records,
            }
        )

    doses = [o["dose"] for o in observations]
    monotone = all(a <= b for a, b in zip(doses, doses[1:]) if a is not None and b is not None)
    return {
        "stage": 2,
        "check": "entrenchment_census",
        "fixture": "entrenched",
        "observations": observations,
        "monotone_nondecreasing": monotone,
        "agrees": monotone,
        "note": (
            "A dose that FALLS as entrenchment rises is an impossible value and a defect report, not "
            "variance. Positive control only -- the dose claim lives in a census over naturally "
            "accumulated stability, which needs a live web."
        ),
    }


# --- Stage 2b: dose under corroboration, and the phase transition ------------


def _stage2b() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    registered = {1.0: None, 1.2: None, 1.222: None, 1.25: 223, 1.3: 88, 1.5: 38, 2.0: 18, 3.0: 11}

    for ratio, expected in registered.items():
        dose = dose_for_standoff(2, arrival_ratio=ratio, threshold=THRESHOLD, bound=DEFAULT_DOSE_BOUND)
        rows.append(
            {
                "stage": "2b",
                "check": "arrival_ratio",
                "arrival_ratio": ratio,
                "asymptote": round(1.0 / (1.0 + ratio), 6),
                "dose": dose.records,
                "registered": expected,
                "bound": dose.bound,
                "final_confidence": round(dose.trajectory[-1], 6),
                "agrees": dose.records == expected,
            }
        )

    r_star = critical_arrival_ratio(THRESHOLD)
    rows.append(
        {
            "stage": "2b",
            "check": "critical_ratio",
            "r_star": round(r_star, 6),
            "registered": round(11 / 9, 6),
            "threshold": THRESHOLD,
            "agrees": abs(r_star - 11 / 9) < 1e-9,
            "note": (
                "r* = (1 - t)/t, a function of the registered threshold and nothing else. Below it the "
                "overlap's limit 1/(1+r) never falls under the threshold, so the dose is infinite rather "
                "than large -- and the substrate does not control the ratio at which evidence arrives."
            ),
        }
    )
    return rows


# --- Stage 3: receipts --------------------------------------------------------


def _stage3() -> list[dict[str, Any]]:
    """Citation metrics only. Failure-mode labels are not decision-grade (SC-5 at 67.9%)."""
    rows: list[dict[str, Any]] = []

    for name in ("symmetric_rivals", "near_miss"):
        core, _ = _seed(name)
        meta = _meta(core)
        receipt = build_receipt(core.store, T.AGENT, meta, threshold=THRESHOLD)

        rivals = set(meta.rivals)
        evidence = set(meta.evidence_ids)
        consulted = set(receipt.consulted)
        rows.append(
            {
                "stage": 3,
                "check": "receipt_citations",
                "fixture": name,
                "receipt_id": receipt.receipt_id,
                "names_both_rivals": rivals <= consulted,
                "cites_shared_evidence": evidence <= consulted,
                "asserts_neither_rival": all(i.attaches_to != sorted(rivals) for i in receipt.items),
                "items": len(receipt.items),
                "declined": len(receipt.declined),
                "agrees": rivals <= consulted and evidence <= consulted and len(receipt.items) == 2,
                "note": (
                    "Scored on citation metrics only. The receipt's provenance is the rivals it consulted "
                    "and the records they share, which is exactly what a scorer can check against the log."
                ),
            }
        )

    core, _ = _seed("symmetric_rivals")
    before = core.store.export_agent(T.AGENT)
    build_receipt(core.store, T.AGENT, _meta(core), threshold=THRESHOLD)
    core.price_counterfactuals({"agent_id": T.AGENT})
    after = core.store.export_agent(T.AGENT)
    rows.append(
        {
            "stage": 3,
            "check": "pricing_never_mutates",
            "store_identical": before == after,
            "agrees": before == after,
            "note": "FR-1, verified by comparing `export_agent` either side rather than by inspection.",
        }
    )

    core, _ = _seed("symmetric_rivals")
    persisted = core.price_counterfactuals({"agent_id": T.AGENT, "persist": True})
    read_back = core.read_counterfactuals(T.AGENT)
    rows.append(
        {
            "stage": 3,
            "check": "receipts_persist_and_read_back",
            "written": persisted["count"],
            "read": read_back["count"],
            "agrees": persisted["count"] == read_back["count"] == 3,
            "note": "Stored on the DissonanceSignal/LoopTrace pattern so experiment 7 can audit claims over time (requirements section 14.3).",
        }
    )
    return rows


# --- the gap worth reporting --------------------------------------------------


def _enumerable_shape() -> dict[str, Any]:
    """How much of the registered census line the enumerator can actually use.

    Pre-registration section 1.1 fixed the structural line as beliefs carrying a
    `contradicts` OR `supports` edge. Requirements section 13 registered the
    enumeration rule as rivals plus supporters. A belief carrying only
    `contradicts` therefore counts toward the census and yields nothing --
    the census line and the enumerator disagree about what "structural" means.

    Recorded rather than fixed by widening the rule mid-build, which is the
    failure this project guards against.
    """
    core, _ = _seed("symmetric_rivals")
    by_reason: dict[str, int] = {}
    enumerable = 0
    for belief in core.store.list_beliefs(T.AGENT, include_inactive=True):
        enumeration = enumerate_changers(core.store, belief, threshold=THRESHOLD)
        if enumeration.items:
            enumerable += 1
        for entry in enumeration.declined:
            by_reason[entry.get("reason", "?")] = by_reason.get(entry.get("reason", "?"), 0) + 1

    return {
        "stage": 0,
        "check": "enumerable_shape_gap",
        "beliefs": 3,
        "enumerable": enumerable,
        "declined_by_reason": by_reason,
        "note": (
            "On `symmetric_rivals` the two rivals carry `contradicts` edges and no `supports`, so they "
            "count toward pre-registration section 1.1's census line and yield no enumeration. Only the "
            "meta-belief is enumerable. The registered line counts edges the rule cannot use, and the "
            "honest reading is that structural enumeration is narrower than the census suggested."
        ),
    }


def main() -> int:
    # Every runner verifies the freeze before doing anything. A fixture edit
    # invalidates every result resting on it, and experiment 1's retraction
    # history is a list of things meant to be true that were never checked.
    from manyu.salience import verify_fixture_freeze

    verify_fixture_freeze(REPO / "evals" / "analysis" / "exp06" / "freeze.json", experiment="6")

    rows: list[dict[str, Any]] = []
    rows.extend(_stage0())
    rows.append(_enumerable_shape())
    rows.extend(_stage1())
    rows.extend(_stage2())
    rows.extend(_stage2b())
    rows.extend(_stage3())

    checks = [r for r in rows if "agrees" in r]
    failed = [f"{r['stage']}:{r['check']}:{r.get('fixture', r.get('arrival_ratio', ''))}" for r in checks if not r["agrees"]]
    rows.append(
        {
            "stage": "all",
            "check": "verdict",
            "checks_run": len(checks),
            "checks_agreeing": len(checks) - len(failed),
            "failed": failed,
            "passed": not failed,
        }
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    for row in rows[:-1]:
        if "agrees" in row:
            label = f"{row['stage']}  {row['check']}"
            detail = row.get("fixture") or row.get("arrival_ratio") or ""
            print(f"  [{'ok' if row['agrees'] else 'FAIL'}] {label} {detail}")
    verdict = rows[-1]
    print(f"\n  passed = {verdict['passed']}  ({verdict['checks_agreeing']}/{verdict['checks_run']})")
    if failed:
        print("  failed:", failed)
    print(f"  wrote {OUT.relative_to(REPO)}")
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
