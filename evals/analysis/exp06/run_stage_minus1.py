"""Experiment 6 Stage -1 — executing the pre-registration against the substrate.

Records, as artifacts, what `tests/test_counterfactual_substrate.py` asserts. The
tests are the standard; this is the evidence `results.md` is re-derived from, and
the two must agree or one of them is wrong.

**The gate this stage exists for.** Pre-registration section 0 reproduces
experiment 5 results section 3.1's published collapse trajectory from the
substrate's constants alone, worked out by hand before any pricer existed. Every
number this experiment predicts descends from that model -- section 4.1's k=5
versus k=10 dose, and section 4.4's phase transition at r* = 11/9. One quantity in
it was inferred rather than read: the meta-belief's starting stability of 0.10.

Three things are therefore recorded here rather than assumed:

1. the starting stability, read off the store;
2. the model's trajectory against experiment 5's published one; and
3. the *substrate's* trajectory, driven through the priced ingest path, against
   both -- because (2) alone could agree with a table while describing nothing.

**The shape census is reported and deliberately not given a verdict.**
Pre-registration section 1.1 fixes 1-in-4 as the line below which structural
enumeration is fixture-only. Both available corpora are unfit to decide it, in
opposite directions, and saying so is this stage's output rather than picking the
flattering one.

Entirely offline. No provider call, no spend.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))

from manyu import underdetermination as ud  # noqa: E402
from manyu.revision import RevisionConfig  # noqa: E402
from manyu.schemas import BeliefType  # noqa: E402

import test_counterfactual_substrate as T  # noqa: E402

OUT = REPO / "evals" / "analysis" / "exp06" / "stage_minus1.jsonl"

#: Experiment 5 results section 3.1.
EXP5_PUBLISHED = (0.847, 0.694, 0.571, 0.476, 0.404, 0.348)
EXPRESSION_THRESHOLD = 0.45
CENSUS_LINE = 0.25


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.append(_starting_stability())
    rows.append(_model_vs_published())
    rows.append(_substrate_vs_model())
    rows.append(_already_held())
    rows.append(_content_blindness())
    rows.append(_salience_reach())
    rows.append(_one_for_one())
    rows.extend(_shape_census())
    rows.append(_verdict(rows))
    return rows


# --- 1. the inferred quantity, read ------------------------------------------


def _starting_stability() -> dict[str, Any]:
    core = T._core()
    T._seed_symmetric(core)
    meta = T._meta(core)
    return {
        "stage": -1,
        "check": "starting_stability",
        "pins": "pre-registration section 0",
        "inferred": 0.10,
        "read": round(meta.stability, 6),
        "meta_confidence": round(meta.confidence, 6),
        "agrees": abs(meta.stability - 0.10) < 1e-9,
        "note": (
            "Solved for from the k=1 step, not observed, when the pre-registration was written. "
            "Read off the store here. `underdetermination._write` hardcodes stability 0.1 and "
            "`BeliefUpdater._create` copies it verbatim, so the value is a harness constant rather "
            "than an emergent property -- which is worth knowing before any claim rests on it."
        ),
    }


# --- 2. the model against experiment 5's published table ---------------------


def _model_vs_published() -> dict[str, Any]:
    predicted = T._model_trajectory(shared=2, steps=6)
    return {
        "stage": -1,
        "check": "model_vs_published",
        "pins": "pre-registration section 1.3",
        "shared_records": 2,
        "predicted": [round(v, 4) for v in predicted],
        "published": list(EXP5_PUBLISHED),
        "max_abs_error": round(max(abs(a - b) for a, b in zip(predicted, EXP5_PUBLISHED)), 6),
        "tolerance": 0.001,
        "agrees": all(abs(a - b) < 0.001 for a, b in zip(predicted, EXP5_PUBLISHED)),
    }


# --- 3. the substrate against both -------------------------------------------


def _substrate_vs_model() -> dict[str, Any]:
    core = T._core()
    minted = T._seed_symmetric(core)
    left_key, _ = T._rival_keys(core)
    evidence = [minted["obs_redshift"], minted["obs_isotropy"]]

    observed, overlaps = [], []
    for k in range(1, 7):
        evidence = evidence + [T._capture(core, f"obs_separating_{k}")]
        T._repropose(core, left_key, f"Reading citing {len(evidence)} records.", evidence)
        ud.derive(core, T.AGENT)
        meta = T._meta(core)
        observed.append(round(meta.confidence, 6))
        overlaps.append(round(2 / (2 + k), 6))

    crossed = next((k for k, c in enumerate(observed, start=1) if c < EXPRESSION_THRESHOLD), None)
    return {
        "stage": -1,
        "check": "substrate_vs_model",
        "pins": "pre-registration section 1.3 -- the real gate",
        "observed": observed,
        "published": list(EXP5_PUBLISHED),
        "overlap_per_step": overlaps,
        "max_abs_error": round(max(abs(a - b) for a, b in zip(observed, EXP5_PUBLISHED)), 6),
        "crossed_expression_threshold_at_k": crossed,
        "registered_k": 5,
        "agrees": crossed == 5 and all(abs(a - b) < 0.001 for a, b in zip(observed, EXP5_PUBLISHED)),
        "note": (
            "Driven through `core.update_beliefs` -- the priced ingest path a live web takes -- and "
            "re-derived after each record. Experiment 5 produced its trajectory by a different route."
        ),
    }


# --- 4-6. what the price can and cannot see ----------------------------------


def _one_separating(*, salience: float = 0.5, summary: str | None = None) -> float:
    core = T._core()
    minted = T._seed_symmetric(core)
    left_key, _ = T._rival_keys(core)
    new_id = T._capture(core, "obs_separating", salience=salience, summary=summary)
    T._repropose(core, left_key, "Reading citing a third record.", [minted["obs_redshift"], minted["obs_isotropy"], new_id])
    ud.derive(core, T.AGENT)
    return T._meta(core).confidence


def _already_held() -> dict[str, Any]:
    core = T._core()
    minted = T._seed_symmetric(core)
    left_key, _ = T._rival_keys(core)
    evidence = [minted["obs_redshift"], minted["obs_isotropy"]]
    before = {b.belief_key: b.confidence for b in core.store.list_beliefs(T.AGENT, include_inactive=True)}
    T._repropose(core, left_key, "The same reading on the same records.", evidence)
    after = {b.belief_key: b.confidence for b in core.store.list_beliefs(T.AGENT, include_inactive=True)}
    return {
        "stage": -1,
        "check": "already_held_moves_zero",
        "pins": "FR-9, pre-registration section 2",
        "delta": round(after[left_key] - before[left_key], 12),
        "agrees": after[left_key] == before[left_key],
        "note": "`BeliefUpdater._revise` returns the belief untouched when the candidate carries no new evidence.",
    }


def _content_blindness() -> dict[str, Any]:
    a = _one_separating(summary="the calibration drifted upward")
    b = _one_separating(summary="an entirely unrelated remark about tea")
    return {
        "stage": -1,
        "check": "price_blind_to_content",
        "pins": "pre-registration section 1.2",
        "confidence_a": round(a, 12),
        "confidence_b": round(b, 12),
        "delta": round(a - b, 12),
        "agrees": a == b,
        "note": (
            "Expected to pass, and registered because failing would be the defect. Consequence accepted "
            "in advance: 'specific evidence' means specific in its edges, not in what it says."
        ),
    }


def _salience_reach() -> dict[str, Any]:
    low = _one_separating(salience=0.05)
    high = _one_separating(salience=0.95)
    return {
        "stage": -1,
        "check": "salience_does_not_reach_price",
        "pins": "requirements section 14.7 q1",
        "confidence_low_salience": round(low, 12),
        "confidence_high_salience": round(high, 12),
        "delta": round(low - high, 12),
        "agrees": low == high,
        "resolves": (
            "`HypotheticalEvidence.salience` is not a back door into the stake channel section 12 bars "
            "the pricer from. It may carry salience without the price reading it."
        ),
    }


# --- 7. the sharpest registered claim ----------------------------------------


def _one_for_one(pairs: int = 20) -> dict[str, Any]:
    core = T._core()
    minted = T._seed_symmetric(core)
    left_key, right_key = T._rival_keys(core)
    left = [minted["obs_redshift"], minted["obs_isotropy"]]
    right = list(left)

    trajectory = []
    for n in range(1, pairs + 1):
        left = left + [T._capture(core, f"obs_sep_{n}")]
        T._repropose(core, left_key, f"Left at {n}.", left)
        shared = T._capture(core, f"obs_shared_{n}")
        left, right = left + [shared], right + [shared]
        T._repropose(core, left_key, f"Left at {n}, corroborated.", left)
        T._repropose(core, right_key, f"Right at {n}, corroborated.", right)
        ud.derive(core, T.AGENT)
        trajectory.append(round(T._meta(core).confidence, 6))

    return {
        "stage": -1,
        "check": "one_for_one_corroboration",
        "pins": "pre-registration section 4.4 prediction 1",
        "pairs": pairs,
        "trajectory_sampled": {str(n): trajectory[n - 1] for n in (1, 2, 3, 5, 10, 15, 20) if n <= pairs},
        "lowest": round(min(trajectory), 6),
        "analytic_limit": 0.5,
        "expression_threshold": EXPRESSION_THRESHOLD,
        "crossed": min(trajectory) < EXPRESSION_THRESHOLD,
        "agrees": min(trajectory) >= EXPRESSION_THRESHOLD,
        "note": (
            "At r = 1 the Jaccard overlap is (2+n)/(2+2n) -> 0.5 and `blend_confidence` converges to its "
            "candidate, so the limit is 0.500 > 0.45 and the dose is infinite rather than large. Checked "
            "against the real substrate at the cheapest rung because it is the experiment's sharpest claim."
        ),
    }


# --- 8. the shape census, reported without a verdict -------------------------


def _census_authored() -> dict[str, Any]:
    total = edged = 0
    per_dir: collections.Counter[str] = collections.Counter()
    per_dir_total: collections.Counter[str] = collections.Counter()
    for path in sorted((REPO / "evals" / "fixtures").rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        beliefs: list[Any] = []
        for block in (doc, doc.get("then") or {}):
            if isinstance(block, dict) and isinstance(block.get("beliefs"), list):
                beliefs += block["beliefs"]
        if not beliefs:
            continue
        group = path.parent.name
        for belief in beliefs:
            if not isinstance(belief, dict):
                continue
            total += 1
            per_dir_total[group] += 1
            if belief.get("contradicts") or belief.get("supports"):
                edged += 1
                per_dir[group] += 1
    return {
        "stage": -1,
        "check": "shape_census_authored",
        "pins": "pre-registration section 1.1",
        "corpus": "evals/fixtures/**",
        "beliefs": total,
        "carrying_an_edge": edged,
        "rate": round(edged / total, 4) if total else None,
        "by_group": {k: f"{per_dir[k]}/{per_dir_total[k]}" for k in sorted(per_dir_total)},
        "fit_to_decide": False,
        "why_not": (
            "These are authored fixtures, written by experiments 2-5 specifically to carry edges. The rate "
            "measures what we wrote, not what a web produces. It is an upper bound and nothing else."
        ),
    }


def _census_naturalistic() -> dict[str, Any]:
    total = contradicts = supports = 0

    def walk(node: Any) -> None:
        nonlocal total, contradicts, supports
        if isinstance(node, dict):
            if ("contradicts" in node or "supports" in node) and any(k in node for k in ("proposition", "belief_id", "belief_key")):
                total += 1
                if node.get("contradicts"):
                    contradicts += 1
                if node.get("supports"):
                    supports += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    root = REPO / "evals" / "analysis"
    for path in sorted(list(root.rglob("*.jsonl")) + list(root.rglob("*.json"))):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = text.splitlines() if path.suffix == ".jsonl" else [text]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                walk(json.loads(line))
            except Exception:
                continue

    return {
        "stage": -1,
        "check": "shape_census_naturalistic",
        "pins": "pre-registration section 1.1",
        "corpus": "evals/analysis/**",
        "belief_shaped_objects": total,
        "non_empty_contradicts": contradicts,
        "non_empty_supports": supports,
        "rate": round((contradicts + supports) / total, 6) if total else None,
        "line": CENSUS_LINE,
        "fit_to_decide": False,
        "why_not": (
            "Reproduces experiment 4 Stage 0's count exactly (620 / 4 / 0). Every one of these runs predates "
            "`supports` entering the extractor schema (experiment 3 Stage 0) and predates section 14's "
            "contradiction pricing, so a zero here describes the instrument rather than the world -- which is "
            "the defect that voided experiment 4's Stage 0a. Reading it as a base rate would repeat it."
        ),
    }


def _shape_census() -> list[dict[str, Any]]:
    authored = _census_authored()
    naturalistic = _census_naturalistic()
    return [
        authored,
        naturalistic,
        {
            "stage": -1,
            "check": "shape_census_verdict",
            "pins": "pre-registration section 1.1",
            "verdict": "unmeasurable_offline",
            "authored_rate": authored["rate"],
            "naturalistic_rate": naturalistic["rate"],
            "line": CENSUS_LINE,
            "note": (
                "The two available corpora bracket the line from opposite sides and neither can decide it: "
                f"{authored['rate']} on fixtures written to carry edges, {naturalistic['rate']} on runs that "
                "predate the schema that would let them. Pre-registration section 1.1's 1-in-4 stands "
                "unresolved and is settled by the live measurement in methodology section 7.1 item 2. "
                "Recorded as unmeasurable rather than answered with whichever number was convenient."
            ),
        },
    ]


def _verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [r for r in rows if "agrees" in r]
    failed = [r["check"] for r in checks if not r["agrees"]]
    return {
        "stage": -1,
        "check": "verdict",
        "checks_run": len(checks),
        "checks_agreeing": len(checks) - len(failed),
        "failed": failed,
        "gate_passed": not failed,
        "census_verdict": "unmeasurable_offline",
        "note": (
            "The gate is pre-registration section 1.3: the model reproduces experiment 5's published "
            "trajectory, the substrate reproduces both, and the starting stability is 0.10 as inferred. "
            "A failure here is a defect report against `pre-registration.md`, not against this runner."
        ),
    }


def main() -> int:
    rows = _rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    verdict = rows[-1]
    for row in rows:
        if "agrees" in row:
            print(f"  [{'ok' if row['agrees'] else 'FAIL'}] {row['check']}")
        elif row["check"].startswith("shape_census"):
            print(f"  [--] {row['check']}: {row.get('rate', row.get('verdict'))}")
    print(f"\n  gate_passed = {verdict['gate_passed']}  ({verdict['checks_agreeing']}/{verdict['checks_run']} checks)")
    print(f"  census      = {verdict['census_verdict']}")
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    return 0 if verdict["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
