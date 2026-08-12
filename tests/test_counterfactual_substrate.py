"""Experiment 6 Stage -1 — executing the requirements document against the substrate.

Written *before* `src/manyu/counterfactual.py` exists, and covering no mechanism
of this experiment's. Same category as `tests/test_underdetermination_substrate.py`
and `tests/test_salience_substrate.py`, and for the same reason: experiment 3's
suite caught none of sixteen defects because every test was written minutes after
the mechanism, by the author who had just written it, so it agreed with the code
precisely where the code was wrong.

**The specific risk this file exists for.** Pre-registration section 0 reproduces
experiment 5 results section 3.1's published collapse trajectory from the
substrate's constants alone -- and it was worked out *by hand*, on paper, before
any pricer existed. Every number this experiment predicts descends from that
model: the k=5 versus k=10 dose in section 4.1, and the phase transition at
r* = 11/9 in section 4.4.

One quantity in it was **inferred rather than read**: the meta-belief's starting
stability of 0.10, solved for from the k=1 step. If it is not 0.10, the model is
wrong and so is every downstream number.

A failure in this file is never a bug in this file. It is a defect report against
`pre-registration.md`, and correcting the document is this stage's output.

Entirely offline. Deterministic under `FrozenClock`. No provider is constructed.
"""

from __future__ import annotations

import pytest

from manyu import underdetermination as ud
from manyu.core import ManyuCore
from manyu.revision import RevisionConfig, blend_confidence
from manyu.schemas import BeliefScope, BeliefType

AGENT = "agent_demo"

#: Experiment 5 results section 3.1, table "separating records / meta-belief
#: confidence". The only published dose figure in the project.
EXP5_PUBLISHED = (0.847, 0.694, 0.571, 0.476, 0.404, 0.348)

#: Pre-registration section 1.3.
REDERIVATION_TOLERANCE = 0.001

#: `BeliefUpdater._create` stamps TENTATIVE below this, and
#: `WorldviewSynthesizer` composes only {ACTIVE, CONTESTED}. Pre-registration
#: section 4.2 fixes it as the "changed my mind" line.
EXPRESSION_THRESHOLD = 0.45


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _capture(core: ManyuCore, source_id: str, *, salience: float = 0.5, weight: float = 0.7, summary: str | None = None) -> str:
    captured = core.capture_belief_evidence(
        {
            "agent_id": AGENT,
            "source_type": "operator_note",
            "source_id": source_id,
            "summary": summary if summary is not None else f"observation {source_id}",
            "affective_salience": salience,
            "epistemic_weight": weight,
        }
    )
    return captured["evidence_id"]


def _repropose(core: ManyuCore, key: str, proposition: str, evidence_ids: list[str], *, contradicts: tuple[str, ...] = ()) -> None:
    """Re-propose a rival carrying one more evidence record.

    Goes through `core.update_beliefs`, so it takes the priced ingest path and
    `BeliefUpdater._revise` -- the same path a live web takes. Writing to the
    store directly would bypass the arithmetic under test.
    """
    result = core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": f"bcand_{key}_{len(evidence_ids)}",
                    "agent_id": AGENT,
                    "proposition": proposition,
                    "belief_key": key,
                    "belief_type": BeliefType.WORLD_MODEL.value,
                    "scope": BeliefScope.GENERAL.value,
                    "confidence": 0.7,
                    "stability": 0.1,
                    "valence": 0.0,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": evidence_ids,
                    "contradicts": list(contradicts),
                }
            ],
        }
    )
    rejected = result.get("rejected") or []
    assert not rejected, f"re-proposal rejected: {rejected}"


def _meta(core: ManyuCore):
    """The single underdetermination belief, or None."""
    held = core.store.list_beliefs(AGENT, belief_type=BeliefType.UNDERDETERMINATION.value, include_inactive=True)
    return held[0] if held else None


def _seed_symmetric(core: ManyuCore) -> dict[str, str]:
    minted = ud.seed_fixture(core, "symmetric_rivals", agent_id=AGENT)
    ud.derive(core, AGENT)
    return minted


def _rival_keys(core: ManyuCore) -> list[str]:
    return sorted(
        b.belief_key
        for b in core.store.list_beliefs(AGENT, include_inactive=True)
        if b.belief_type is not BeliefType.UNDERDETERMINATION and b.belief_key
    )


def _model_trajectory(shared: int, steps: int, *, stability0: float = 0.10, start: float = 1.0, config: RevisionConfig | None = None) -> list[float]:
    """Pre-registration section 0's model, expressed once.

    `c` is the Jaccard overlap after `k` separating records have arrived, which
    for a pair whose evidence sets began identical is `shared / (shared + k)`.
    Stability rises 0.05 per revision carrying new evidence, exactly as
    `BeliefUpdater._revise` sets it.
    """
    config = config or RevisionConfig()
    out: list[float] = []
    confidence, stability = start, stability0
    for k in range(1, steps + 1):
        overlap = shared / (shared + k)
        confidence = _blend(confidence, stability, overlap, config)
        out.append(confidence)
        stability = min(1.0, stability + 0.05)
    return out


def _blend(confidence: float, stability: float, candidate: float, config: RevisionConfig) -> float:
    """`blend_confidence` without needing a Belief instance to call it."""

    class _Stub:
        pass

    stub = _Stub()
    stub.confidence = confidence  # type: ignore[attr-defined]
    stub.stability = stability  # type: ignore[attr-defined]
    return blend_confidence(stub, candidate, config)  # type: ignore[arg-type]


# --- section 1.3: the re-derivation, and the one inferred quantity ------------


def test_meta_belief_is_created_at_stability_0_10():
    """Pre-registration section 0's single inferred quantity, read off the store.

    Solved for from the k=1 step rather than observed, and everything downstream
    rests on it. If this fails, section 0's table is wrong, section 4.1's k=5 /
    k=10 prediction is wrong, and section 4.4's r* = 11/9 is wrong -- and the
    correct response is to re-derive the model, not to refit it.
    """
    core = _core()
    _seed_symmetric(core)

    meta = _meta(core)
    assert meta is not None, "symmetric_rivals derived no meta-belief; experiment 5 Stage 2 says it must"
    assert meta.stability == pytest.approx(0.10, abs=1e-9), (
        f"meta-belief created at stability {meta.stability}, not the 0.10 pre-registration section 0 inferred. "
        "Every number in sections 4.1 and 4.4 descends from that value."
    )
    assert meta.confidence == pytest.approx(1.0, abs=1e-9)


def test_model_reproduces_experiment5_published_trajectory():
    """Section 0's hand-worked table, checked against experiment 5's published one.

    Pure arithmetic -- no store. This pins the *model*; the next test pins that
    the substrate actually behaves that way.
    """
    predicted = _model_trajectory(shared=2, steps=6)
    for k, (got, published) in enumerate(zip(predicted, EXP5_PUBLISHED), start=1):
        assert got == pytest.approx(published, abs=REDERIVATION_TOLERANCE), (
            f"k={k}: model gives {got:.4f}, experiment 5 results section 3.1 published {published}"
        )


def test_substrate_trajectory_matches_the_model():
    """The real gate: drive the substrate and compare it to the model.

    The previous test could pass while the model described nothing -- it checks
    arithmetic against a table, and both could be wrong in the same way. This one
    seeds `symmetric_rivals`, delivers separating records one at a time through
    the priced ingest path, re-derives after each, and reads the meta-belief.

    Experiment 5 produced its trajectory by a different route. If these disagree,
    one of the two is not measuring what its document says.
    """
    core = _core()
    minted = _seed_symmetric(core)
    left_key, _ = _rival_keys(core)
    base_evidence = [minted["obs_redshift"], minted["obs_isotropy"]]

    observed: list[float] = []
    for k in range(1, 7):
        new_id = _capture(core, f"obs_separating_{k}")
        base_evidence = base_evidence + [new_id]
        _repropose(core, left_key, f"Reading {left_key}, now citing {len(base_evidence)} records.", base_evidence)
        ud.derive(core, AGENT)
        meta = _meta(core)
        assert meta is not None, f"meta-belief vanished at k={k} instead of weakening"
        observed.append(meta.confidence)

    for k, (got, published) in enumerate(zip(observed, EXP5_PUBLISHED), start=1):
        assert got == pytest.approx(published, abs=REDERIVATION_TOLERANCE), (
            f"k={k}: substrate gives {got:.4f}, experiment 5 published {published}"
        )

    crossed = next((k for k, c in enumerate(observed, start=1) if c < EXPRESSION_THRESHOLD), None)
    assert crossed == 5, f"expression threshold crossed at k={crossed}, not the k=5 pre-registration section 4.1 registered"


# --- section 1.2 and FR-9: what the price can and cannot see ------------------


def test_already_held_evidence_moves_the_belief_by_exactly_zero():
    """FR-9, and the substrate half of pre-registration section 2's `already_held`.

    `BeliefUpdater._revise` returns the belief untouched when the candidate
    carries no evidence it does not already hold. This is the one prediction
    whose correct answer is exactly 0.000, so any nonzero price is a defect
    rather than an approximation.
    """
    core = _core()
    minted = _seed_symmetric(core)
    left_key, _ = _rival_keys(core)
    base_evidence = [minted["obs_redshift"], minted["obs_isotropy"]]

    before = {b.belief_key: b.confidence for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    _repropose(core, left_key, "The same reading, re-proposed on the same records.", base_evidence)
    after = {b.belief_key: b.confidence for b in core.store.list_beliefs(AGENT, include_inactive=True)}

    assert after[left_key] == before[left_key], (
        f"re-proposing on already-held evidence moved the belief by {after[left_key] - before[left_key]}; "
        "the `new_evidence` guard should have returned it untouched"
    )


def test_price_is_blind_to_what_a_record_says():
    """Pre-registration section 1.2 -- expected to pass, registered because failing is the defect.

    Two separating records identical in confidence and salience and differing
    only in prose. If they price differently, something is reading content that
    `blend_confidence` cannot see.

    The consequence accepted in advance: "specific evidence" in the crux's
    framing means specific in its *edges*, not in what it says.
    """
    outcomes = []
    for summary in ("the calibration drifted upward", "an entirely unrelated remark about tea"):
        core = _core()
        minted = _seed_symmetric(core)
        left_key, _ = _rival_keys(core)
        new_id = _capture(core, "obs_separating", summary=summary)
        _repropose(core, left_key, "Reading, now citing a third record.", [minted["obs_redshift"], minted["obs_isotropy"], new_id])
        ud.derive(core, AGENT)
        outcomes.append(_meta(core).confidence)

    assert outcomes[0] == pytest.approx(outcomes[1], abs=1e-12), (
        f"two records differing only in prose priced differently ({outcomes[0]} vs {outcomes[1]}); "
        "something is reading content the pricing arithmetic cannot see"
    )


def test_salience_does_not_reach_the_price():
    """Requirements section 14.7 question 1, resolved here where it is free.

    Section 12 bars the pricer from the `stake_of` channel, because stake
    averages evidence salience rather than summing it and is therefore blind to
    grounding. If salience reached the confidence price by some other route, the
    hypothetical record's salience field would be a back door into a channel the
    pricer is barred from.
    """
    outcomes = []
    for salience in (0.05, 0.95):
        core = _core()
        minted = _seed_symmetric(core)
        left_key, _ = _rival_keys(core)
        new_id = _capture(core, "obs_separating", salience=salience)
        _repropose(core, left_key, "Reading, now citing a third record.", [minted["obs_redshift"], minted["obs_isotropy"], new_id])
        ud.derive(core, AGENT)
        outcomes.append(_meta(core).confidence)

    assert outcomes[0] == pytest.approx(outcomes[1], abs=1e-12), (
        f"salience changed the price ({outcomes[0]} vs {outcomes[1]}); requirements section 14.7 q1 resolves "
        "the other way and `HypotheticalEvidence.salience` is a back door into the stake channel"
    )


# --- section 4.4: the sharpest registered claim, checked early ---------------


def test_one_for_one_corroboration_never_crosses_the_threshold():
    """Pre-registration section 4.4 prediction 1, driven against the real substrate.

    At r = 1 -- one shared record per separating record -- the Jaccard overlap
    converges to `(s + n) / (s + 2n)` -> 0.5, and `blend_confidence` converges to
    its candidate. Since 0.5 > 0.45 the meta-belief never crosses the expression
    threshold: the dose is infinite, not merely large.

    This is the experiment's sharpest claim and it is checked at the cheapest
    rung. Twenty pairs is far past the k=5 that pure separating evidence needs;
    if it were going to cross, it would have.
    """
    core = _core()
    minted = _seed_symmetric(core)
    left_key, right_key = _rival_keys(core)
    left_evidence = [minted["obs_redshift"], minted["obs_isotropy"]]
    right_evidence = list(left_evidence)

    lowest = 1.0
    for n in range(1, 21):
        separating = _capture(core, f"obs_sep_{n}")
        left_evidence = left_evidence + [separating]
        _repropose(core, left_key, f"Left reading at step {n}.", left_evidence)

        # The shared record goes to both rivals; the separating one never does.
        # Handing the separating record to both makes it non-separating, the
        # overlap stays at 1.0, and the test passes while measuring nothing.
        shared = _capture(core, f"obs_shared_{n}")
        left_evidence = left_evidence + [shared]
        right_evidence = right_evidence + [shared]
        _repropose(core, left_key, f"Left reading at step {n}, corroborated.", left_evidence)
        _repropose(core, right_key, f"Right reading at step {n}, corroborated.", right_evidence)

        ud.derive(core, AGENT)
        meta = _meta(core)
        assert meta is not None, f"meta-belief vanished at pair {n}"
        lowest = min(lowest, meta.confidence)

    assert lowest >= EXPRESSION_THRESHOLD, (
        f"one-for-one corroboration drove the meta-belief to {lowest:.4f}, below the {EXPRESSION_THRESHOLD} "
        "threshold. Pre-registration section 4.4's convergence argument is wrong, and with it the r* = 11/9 "
        "phase transition."
    )
    assert lowest == pytest.approx(0.5, abs=0.06), (
        f"converged to {lowest:.4f}; section 4.4 predicts the 1/(1+r) limit, which at r=1 is 0.500"
    )
