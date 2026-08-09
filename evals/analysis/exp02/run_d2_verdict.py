"""Stage 4 of discriminator D2 — the verdict run (requirements §8.1).

Stage 3 verified the plumbing against authored belief candidates and is
explicitly *not* a result: authoring the valences chooses merged's answer
(design §6.1). This is the arm that answers D2's actual question — with the
live `BeliefExtractor` in the loop, does an object-less uncertainty stream
produce a **carrier** without anyone having written one?

Usage::

    python evals/analysis/exp02/run_d2_verdict.py --mode dry
    python evals/analysis/exp02/run_d2_verdict.py --mode pilot --model claude-opus-5
    python evals/analysis/exp02/run_d2_verdict.py --mode live  --model claude-opus-5 \
        --out evals/analysis/exp02/d2_verdict.jsonl

Two deliberate departures from `fork.run_d2_condition`, both recorded as a
dated amendment in methodology §4.4:

- **Beliefs come from the extractor.** That is the stage.
- **The inner voice is switched off on both builds.** `process_reflective_turn`
  composes an inner voice every turn — a second provider call per event, and
  the only LLM in split's mood path. Neither measured channel reads it (merged
  reads `max(0, -valence)` over the belief window; split reads
  `AffectState.emotions["fear"]`, written by `FastAppraiser`), so leaving it on
  would double the spend to move a quantity the analysis never consults. It
  also makes LLM exposure symmetric — after this change both builds make
  exactly one provider call per turn, the extraction — which is the confound
  NFR-3 was written about, now removed by construction rather than controlled
  for by a third arm.

Nothing here decides the verdict. `classify_merged` reports an M-class and
dumps every carrier it read so the judgement is re-checkable by hand, and
`UNDECIDED` is a real outcome that must not be reported as a win for either
build (requirements §8.1).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from manyu.architecture import Arch  # noqa: E402
from manyu.core import ManyuCore  # noqa: E402
from manyu.fork import (  # noqa: E402
    D2_CONDITIONS,
    D2_SHAPE_KEYS,
    INTER_EVENT_SECONDS,
    uncertainty_events,
)
from manyu.gate import (  # noqa: E402
    GateFailure,
    assert_iv_moves,
    assert_shape_comparable,
)
from manyu.providers import AnthropicAPIJSONProvider, ScenarioJSONProvider  # noqa: E402
from manyu.schemas import BeliefType  # noqa: E402

SCHEMA_VERSION = "manyu.exp02.d2_verdict.v0.1"

#: Events per condition. Matches Stage 3 so the two stages differ only in where
#: beliefs come from.
N_EVENTS = 20

#: `n_live` from methodology §1. 3 conditions x 2 builds x 10.
N_LIVE = 10

#: Words that name a *specific harm*. Used only to separate M-b (fabricated
#: threat carrier) from M-c (aggregate uncertainty carrier), and only ever in
#: combination with the check that the word appears nowhere in the run's own
#: event stream — a carrier that echoes a threat the `control` condition really
#: did state is not a fabrication. The list is deliberately blunt: every
#: carrier is dumped into the record, so a wrong call here is visible and
#: correctable without a re-run.
THREAT_TERMS = (
    "destroy", "destruct", "unrecoverable", "irrecoverable", "data loss",
    "lose data", "corrupt", "damage", "harm", "danger", "catastroph",
    "breach", "outage", "crash", "delete", "drop rows", "wipe",
)

#: A carrier that names an indexed occurrence — "Check 19", "Query 3" — is a
#: belief about that occurrence. A carrier that names none is a belief about the
#: class of them. This is the mechanical half of the M-c generalisation test
#: (methodology §4.6); the propositions are dumped into every record so the call
#: is re-checkable by eye.
INSTANCE_REF_RE = re.compile(
    r"\b(?:check|query|step|attempt|call|run|turn|event|iteration)\s*#?\s*\d+\b",
    re.IGNORECASE,
)


class MClass:
    """Outcome classes from requirements §8.1, plus the one it did not name."""

    M0 = "M-0"          # undecidable: empty window, or provider errors in the run
    MA = "M-a"          # no affect, non-empty window — merged loses cleanly
    MB = "M-b"          # affect carried by a fabricated threat — merged loses worse
    MC = "M-c"          # affect carried by an aggregate-uncertainty belief — merged wins
    UNDECIDED = "M-x"   # affect present, carrier neither uncertainty-typed nor threat-naming


# --- provider metering -------------------------------------------------------


@dataclass
class MeteredProvider:
    """Wrap a provider to count what the run actually spent.

    `BeliefExtractor` drops `_provider_info` on the floor, so usage is
    unrecoverable from the records downstream. Gate #5 asks for a cost
    estimate; this is what makes the estimate a measurement rather than an
    arithmetic guess, and it is also how gate #2 counts provider errors
    (which must be tagged and excluded, never scored as "no affect").
    """

    inner: Any
    calls: int = 0
    errors: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error_details: list[str] = field(default_factory=list)

    def generate_json(self, prompt: str, output_schema: dict, system_message: str | None = None, temperature: float = 0.2) -> dict:
        self.calls += 1
        result = self.inner.generate_json(prompt, output_schema, system_message=system_message, temperature=temperature)
        if result.get("status") == "provider_error":
            self.errors += 1
            detail = result.get("detail") or result.get("error") or "unknown"
            self.error_details.append(str(detail)[:300])
            return result
        info = result.get("_provider_info") or {}
        self.input_tokens += int(info.get("input_tokens") or 0)
        self.output_tokens += int(info.get("output_tokens") or 0)
        return result

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "errors": self.errors,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "error_details": self.error_details[:5],
        }


# --- one condition, one build ------------------------------------------------


def build_core(arch: Arch, provider: Any) -> ManyuCore:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, belief_provider=provider, arch=arch)
    # See the module docstring: the inner voice is not a measured channel on
    # either build, and switching it off is what makes LLM exposure symmetric.
    core.inner_voice.provider = None
    return core


def run_condition(
    *,
    arch: Arch,
    condition: str,
    provider: Any,
    replicate: int,
    n_events: int = N_EVENTS,
    agent_id: str = "agent_demo",
    seed_mood: str | None = None,
) -> dict:
    """Drive one condition on one build with the live extractor.

    Returns a flat record. Everything the M-class rests on is in it — the
    carriers with their propositions, types and evidence — so a reader can
    disagree with `classify_merged` without re-running anything.
    """
    meter = MeteredProvider(provider)
    core = build_core(arch, meter)
    if seed_mood:
        core.moods.seed_mood(agent_id, seed_mood)
    events = uncertainty_events(n_events, condition=condition, agent_id=agent_id)

    turn_errors = 0
    for event in events:
        result = core.process_reflective_turn({"event": event.model_dump(mode="json")})
        update = result.get("belief_update") or {}
        if update.get("status") == "provider_error":
            turn_errors += 1
        core.clock.advance(INTER_EVENT_SECONDS)

    beliefs = core.store.list_beliefs(agent_id)
    evidence_records = core.store.list_belief_evidence(agent_id)
    untrusted = sum(1 for item in evidence_records if item.trust_class.value in ("user_report", "untrusted_text"))

    if arch is Arch.MERGED:
        projection = core.moods.project(agent_id)
        window = core.moods.window(agent_id)
        affect = round(max(0.0, -projection.valence), 6)
        channel = "merged_negative_valence"
        arousal, valence = projection.arousal, projection.valence
        window_belief_count = projection.window_belief_count
        sum_stake, floored = projection.sum_stake, projection.arousal_floored
    else:
        state = core.store.latest_state(agent_id)
        window = beliefs[:8]
        affect = round(state.emotions["fear"], 6)
        channel = "affect_state_fear"
        arousal, valence = 0.0, 0.0
        window_belief_count = len(beliefs)
        sum_stake, floored = 0.0, False

    event_text = " ".join(
        [e.summary.lower() for e in events]
        + [c.text.lower() for e in events for c in (e.claims or [])]
    )
    carriers = describe_carriers(window, evidence_records, event_text)
    classifier_inputs = {
        "arch": arch,
        "affect": affect,
        "window_belief_count": window_belief_count,
        "provider_errors": meter.errors,
        "carriers": carriers,
    }
    m_class, m_notes = classify_merged(**classifier_inputs)
    m_class_strict = classify_merged_strict(**classifier_inputs)

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "d2_verdict",
        "arch": arch.value,
        "condition": condition,
        "replicate": replicate,
        "seed_mood": seed_mood,
        "n_events": n_events,
        "beliefs_total": len(beliefs),
        # --- the measured channel -----------------------------------------
        "affect": affect,
        "affect_channel": channel,
        "arousal": arousal,
        "valence": valence,
        "arousal_floored": floored,
        "sum_stake": sum_stake,
        # --- gate #7 shape keys -------------------------------------------
        "window_belief_count": window_belief_count,
        "authored_in_window": 0,  # nothing is authored in this stage, by construction
        "evidence_count": len(evidence_records),
        "untrusted_count": untrusted,
        # --- gate #2 / M-0 -------------------------------------------------
        "provider": meter.snapshot(),
        "turn_errors": turn_errors,
        # --- the classification and its evidence ---------------------------
        "m_class": m_class,
        "m_class_strict": m_class_strict,
        "m_notes": m_notes,
        "carriers": carriers,
    }


def describe_carriers(window: Sequence[Any], evidence_records: Sequence[Any], event_text: str) -> list[dict]:
    """Every negative-valence belief in the window, with what the class rests on.

    A carrier is what merged's mood query actually reads, so "did a carrier
    arise" is a question about this list and nothing else.
    """
    by_id = {item.evidence_id: item for item in evidence_records}
    carriers = []
    for belief in window:
        valence = float(getattr(belief, "valence", 0.0) or 0.0)
        if valence >= 0:
            continue
        proposition = (belief.proposition or "").lower()
        unsupported = sorted(
            term for term in THREAT_TERMS
            if term in proposition and term not in event_text
        )
        resolved = [eid for eid in (belief.evidence_ids or []) if eid in by_id]
        instance_ref = INSTANCE_REF_RE.search(belief.proposition or "")
        carriers.append({
            "belief_id": belief.belief_id,
            "belief_key": belief.belief_key,
            "belief_type": belief.belief_type.value if hasattr(belief.belief_type, "value") else str(belief.belief_type),
            "proposition": belief.proposition,
            "valence": valence,
            "confidence": belief.confidence,
            "evidence_ids": list(belief.evidence_ids or []),
            "evidence_resolved": len(resolved),
            "unsupported_threat_terms": unsupported,
            "instance_reference": instance_ref.group(0) if instance_ref else None,
            "generalises": instance_ref is None,
        })
    return carriers


def classify_merged(
    *,
    arch: Arch,
    affect: float,
    window_belief_count: int,
    provider_errors: int,
    carriers: Sequence[dict],
) -> tuple[str | None, list[str]]:
    """Apply requirements §8.1 as amended by methodology §4.6. Split runs are
    not M-classified — the classes are about merged's carrier, and split has no
    carrier to have.

    **M-c is a property test, not a type test.** §8.1 originally gated it on
    `BeliefType.UNCERTAINTY`; the pilot showed the extractor expresses
    object-less epistemic unease as `epistemic_principle` and `world_model`
    propositions about ambiguity, so the type tag would have decided D2 on a
    technicality. A carrier is now M-c when it names no threat the events did
    not state, generalises beyond any single occurrence, and has resolved
    provenance. `classify_merged_strict` keeps the original reading on every
    record.

    M-0 absorbs both "nothing to read" and "the instrument failed", because
    experiment 1 lost a finding to exactly the second one being scored as the
    first. A single failed extraction contaminates the whole run's belief web,
    so the run is tagged rather than partially scored.
    """
    if arch is not Arch.MERGED:
        return None, []

    notes: list[str] = []
    if provider_errors:
        return MClass.M0, [f"{provider_errors} provider error(s) in the run — unscoreable, not 'no affect'"]
    if window_belief_count == 0:
        return MClass.M0, ["empty belief window — nothing for the mood query to read"]
    if affect <= 0.0 or not carriers:
        return MClass.MA, [f"window holds {window_belief_count} belief(s) and no negative valence"]

    fabricated = [c for c in carriers if c["unsupported_threat_terms"]]
    if fabricated:
        notes = [
            f"carrier {c['belief_key']!r} names {c['unsupported_threat_terms']} — absent from every event in the stream"
            for c in fabricated
        ]
        return MClass.MB, notes

    aggregate = [c for c in carriers if c["generalises"] and c["evidence_resolved"] > 0]
    if aggregate:
        notes = [
            f"carrier {c['belief_key']!r} ({c['belief_type']}) generalises beyond any single event "
            f"and has {c['evidence_resolved']} resolved evidence record(s)"
            for c in aggregate
        ]
        return MClass.MC, notes

    notes = [
        f"carrier {c['belief_key']!r} ({c['belief_type']}) names no unsupported threat but "
        f"{'refers to ' + repr(c['instance_reference']) if c['instance_reference'] else 'has no resolved provenance'}"
        " — it is about one occurrence, not the epistemic situation, so it is outside the classes §8.1 named"
        for c in carriers
    ]
    return MClass.UNDECIDED, notes


def classify_merged_strict(*, arch: Arch, affect: float, window_belief_count: int, provider_errors: int, carriers: Sequence[dict]) -> str | None:
    """§8.1 exactly as pre-registered, with M-c gated on `BeliefType.UNCERTAINTY`.

    Recorded on every run beside the amended class so a reader can apply the
    original rule themselves and see what the amendment changed. It is not the
    rule the verdict uses — see methodology §4.6 for why, and for the fact that
    the amendment was written before the scored run rather than after it.
    """
    if arch is not Arch.MERGED:
        return None
    if provider_errors or window_belief_count == 0:
        return MClass.M0
    if affect <= 0.0 or not carriers:
        return MClass.MA
    if any(c["unsupported_threat_terms"] for c in carriers):
        return MClass.MB
    if any(c["belief_type"] == BeliefType.UNCERTAINTY.value and c["evidence_resolved"] > 0 for c in carriers):
        return MClass.MC
    return MClass.UNDECIDED


# --- analysis ----------------------------------------------------------------


def cohens_d(treatment: Sequence[float], baseline: Sequence[float]) -> float | None:
    """Within-build Cohen's d. `None` when both arms are constant.

    A zero pooled SD with different means is an infinite effect and is reported
    as such rather than as a large finite number nobody can interpret; a zero
    pooled SD with equal means is no effect at all.
    """
    if len(treatment) < 2 or len(baseline) < 2:
        return None
    mean_t, mean_b = statistics.fmean(treatment), statistics.fmean(baseline)
    var_t, var_b = statistics.variance(treatment), statistics.variance(baseline)
    pooled = ((len(treatment) - 1) * var_t + (len(baseline) - 1) * var_b) / (len(treatment) + len(baseline) - 2)
    if pooled <= 0:
        return None if mean_t == mean_b else float("inf") * (1 if mean_t > mean_b else -1)
    return (mean_t - mean_b) / (pooled ** 0.5)


def bootstrap_ci(treatment: Sequence[float], baseline: Sequence[float], *, n: int = 10000, seed: int = 20260809) -> tuple[float, float] | None:
    rng = random.Random(seed)
    draws = []
    for _ in range(n):
        t = [rng.choice(treatment) for _ in treatment]
        b = [rng.choice(baseline) for _ in baseline]
        d = cohens_d(t, b)
        if d is not None and d not in (float("inf"), float("-inf")):
            draws.append(d)
    if len(draws) < n * 0.5:
        return None
    draws.sort()
    return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]


def drop_one(treatment: Sequence[float], baseline: Sequence[float]) -> list[float | None]:
    """Recompute d with each treatment observation removed.

    Built into the analysis rather than bolted on after, because two of
    experiment 1's v4 correlations collapsed under exactly this check.
    """
    out = []
    for index in range(len(treatment)):
        reduced = list(treatment[:index]) + list(treatment[index + 1:])
        out.append(cohens_d(reduced, baseline))
    return out


def analyse(records: Sequence[dict]) -> dict:
    """Within-build effect sizes, gates first, with every refusal explained."""
    summary: dict[str, Any] = {"builds": {}, "gates": {}, "verdict": None}

    for arch in ("merged", "split"):
        rows = [r for r in records if r["arch"] == arch]
        if not rows:
            continue
        clean = [r for r in rows if not r["provider"]["errors"]]
        excluded = len(rows) - len(clean)

        # Gate #2: errors are excluded, and warn if they bunch in one condition.
        by_condition_errors = {c: sum(1 for r in rows if r["condition"] == c and r["provider"]["errors"]) for c in D2_CONDITIONS}

        # Gate #7: only conditions sharing a shape are comparable.
        shape_keys = list(D2_SHAPE_KEYS[arch])
        try:
            comparable = sorted(assert_shape_comparable(clean, shape_keys=shape_keys, condition_key="condition", label=f"{arch} D2"))
            shape_error = None
        except GateFailure as exc:
            comparable, shape_error = [], str(exc)

        affect = {c: [r["affect"] for r in clean if r["condition"] == c] for c in D2_CONDITIONS}

        # Positive control (FR-D2.4): both builds must move on `control`, or the
        # `uncertainty` result is void rather than null.
        control_moves = None
        control_error = None
        if affect["control"] and affect["neutral"]:
            try:
                assert_iv_moves(statistics.fmean(affect["neutral"]), statistics.fmean(affect["control"]), label=f"{arch} positive control")
                control_moves = True
            except GateFailure as exc:
                control_moves, control_error = False, str(exc)

        entry: dict[str, Any] = {
            "n_runs": len(rows),
            "excluded_provider_error": excluded,
            "errors_by_condition": by_condition_errors,
            "shape_keys": shape_keys,
            "comparable_conditions": comparable,
            "shape_gate_error": shape_error,
            "positive_control_moves": control_moves,
            "positive_control_error": control_error,
            "mean_affect": {c: (round(statistics.fmean(v), 6) if v else None) for c, v in affect.items()},
            "affect_values": affect,
        }

        if affect["uncertainty"] and affect["neutral"]:
            d = cohens_d(affect["uncertainty"], affect["neutral"])
            entry["cohens_d"] = d
            entry["bootstrap_ci"] = bootstrap_ci(affect["uncertainty"], affect["neutral"]) if d not in (None, float("inf"), float("-inf")) else None
            entry["drop_one_d"] = drop_one(affect["uncertainty"], affect["neutral"])
            # A d computed across non-comparable conditions is experiment 1's
            # v6 failure; report it, but mark it unusable.
            entry["d_is_shape_matched"] = {"uncertainty", "neutral"}.issubset(set(comparable))

        summary["builds"][arch] = entry

    merged_uncertainty = [r for r in records if r["arch"] == "merged" and r["condition"] == "uncertainty"]
    classes = {}
    for row in merged_uncertainty:
        classes[row["m_class"]] = classes.get(row["m_class"], 0) + 1
    summary["merged_m_classes"] = classes
    strict = {}
    for row in merged_uncertainty:
        strict[row.get("m_class_strict")] = strict.get(row.get("m_class_strict"), 0) + 1
    summary["merged_m_classes_strict_8_1"] = strict
    summary["verdict"] = decide(summary, classes, len(merged_uncertainty))
    return summary


def decide(summary: dict, classes: dict, n_merged: int) -> dict:
    """Apply the §8.1 rule. Undecided is the default, not the fallback."""
    merged = summary["builds"].get("merged", {})
    split = summary["builds"].get("split", {})
    scoreable = n_merged - classes.get(MClass.M0, 0)
    if scoreable <= 0:
        return {"outcome": "undecided", "why": "every merged uncertainty run was M-0 (unscoreable)"}

    dominant = max((c for c in classes if c != MClass.M0), key=lambda c: classes[c], default=None)
    merged_d, split_d = merged.get("cohens_d"), split.get("cohens_d")
    ci = merged.get("bootstrap_ci")
    ci_excludes_zero = bool(ci) and (ci[0] > 0 or ci[1] < 0)

    # §8.1's "d >= 0.5 x split's d" assumes split's d is a finite number. The
    # pilot showed it is not: split's channel is `AffectState.fear`, written by
    # `FastAppraiser` from `event_type` deltas, which never reads a belief — so
    # every replicate returns the identical value and the pooled SD is zero.
    # `cohens_d` reports that as infinite, and `merged_d >= 0.5 * inf` is False
    # for every possible merged result. Left unguarded the rule is
    # unsatisfiable and merged could not win whatever it did, which is the
    # inert-mechanism failure experiment 3's §3.1 put on the standing list.
    # The clause is therefore marked inapplicable rather than silently failed,
    # and the remaining conditions carry the decision.
    ratio_applicable = split_d is not None and split_d not in (float("inf"), float("-inf"))
    ratio_holds = (merged_d is not None and ratio_applicable and merged_d >= 0.5 * split_d)

    if dominant == MClass.MC and merged.get("positive_control_moves") and ci_excludes_zero:
        if ratio_holds:
            return {"outcome": "merged", "why": f"M-c on {classes[MClass.MC]}/{scoreable} scoreable runs; d={merged_d} >= 0.5*{split_d}, CI excludes zero"}
        if not ratio_applicable:
            return {
                "outcome": "merged",
                "ratio_clause": "inapplicable",
                "why": f"M-c on {classes[MClass.MC]}/{scoreable} scoreable runs; merged d={merged_d} with a CI excluding zero "
                       f"and a passing positive control. The '>= 0.5 x split' clause could not be applied: split_d={split_d} "
                       "because split's channel is deterministic across replicates, so the ratio is undefined rather than failed",
            }
    if dominant in (MClass.MA, MClass.MB) and split.get("positive_control_moves"):
        split_ci = split.get("bootstrap_ci")
        if split_d is not None and split_d > 0 and split_ci and split_ci[0] > 0:
            return {"outcome": "split", "why": f"merged landed {dominant} on {classes[dominant]}/{scoreable} runs while split cleared d={split_d} with CI excluding zero"}
    return {
        "outcome": "undecided",
        "why": f"classes={classes}, merged_d={merged_d}, split_d={split_d}, ci={ci} — "
               "no §8.1 branch is satisfied; undecided is not a win for either build",
    }


# --- driving -----------------------------------------------------------------


def make_provider(mode: str, model: str) -> Any:
    if mode in ("dry", "gates"):
        return ScenarioJSONProvider()
    return AnthropicAPIJSONProvider(model=model)


def run_all(*, mode: str, model: str, replicates: int, out: Path | None, seed_mood: str | None) -> dict:
    provider = make_provider(mode, model)
    records = []
    for replicate in range(replicates):
        for arch in (Arch.MERGED, Arch.SPLIT):
            for condition in D2_CONDITIONS:
                record = run_condition(
                    arch=arch, condition=condition, provider=provider,
                    replicate=replicate, seed_mood=seed_mood,
                )
                record["mode"], record["model"] = mode, (model if mode in ("pilot", "live") else "scenario")
                records.append(record)
                print(
                    f"  {arch.value:>6} {condition:<12} rep {replicate}: "
                    f"affect={record['affect']:.4f} window={record['window_belief_count']} "
                    f"carriers={len(record['carriers'])} class={record['m_class']} "
                    f"calls={record['provider']['calls']} errors={record['provider']['errors']}",
                    flush=True,
                )
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
    return {"records": records, "summary": analyse(records)}


def cost_report(records: Sequence[dict]) -> dict:
    """What the run spent, and what the full live run would spend at that rate."""
    calls = sum(r["provider"]["calls"] for r in records)
    inp = sum(r["provider"]["input_tokens"] for r in records)
    out = sum(r["provider"]["output_tokens"] for r in records)
    runs = len(records)
    full_runs = N_LIVE * len(D2_CONDITIONS) * 2
    scale = full_runs / runs if runs else 0
    return {
        "runs": runs,
        "calls": calls,
        "input_tokens": inp,
        "output_tokens": out,
        "projected_full_run": {
            "runs": full_runs,
            "calls": round(calls * scale),
            "input_tokens": round(inp * scale),
            "output_tokens": round(out * scale),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 2, discriminator D2, Stage 4 verdict run")
    parser.add_argument("--mode", choices=("dry", "pilot", "live"), default="dry",
                        help="dry: offline ScenarioJSONProvider, no spend. pilot: 1 replicate live. live: n_live replicates.")
    parser.add_argument("--model", default="claude-opus-5")
    parser.add_argument("--replicates", type=int, default=None, help="override; defaults to 1 for dry/pilot and n_live for live")
    parser.add_argument("--seed-mood", default=None, help="NFR-3 control arm: seed a mood instead of leaving the mood path idle")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    replicates = args.replicates if args.replicates is not None else (N_LIVE if args.mode == "live" else 1)
    print(f"D2 verdict — mode={args.mode} model={args.model} replicates={replicates}")
    result = run_all(mode=args.mode, model=args.model, replicates=replicates, out=args.out, seed_mood=args.seed_mood)

    print("\n--- summary ---")
    print(json.dumps(result["summary"], indent=2, default=str))
    print("\n--- cost ---")
    print(json.dumps(cost_report(result["records"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
