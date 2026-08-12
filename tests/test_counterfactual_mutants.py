"""The mutant battery — can the checks catch each defect family?

Experiment 5's best catch was a check *in its own battery* that was random,
catching its target about half the time because belief ids come from `uuid4`. So
every check here is asserted three ways:

1. it passes on the real mechanism,
2. it fails on the mutant it names, and
3. it is deterministic across repeated construction.

(3) is not ceremony. A check that passes half the time goes green on the run that
matters, and this sequence has now found that family in production (experiment 4's
`uuid4` tie-break) and in a test (experiment 5's battery).
"""

from __future__ import annotations

import pytest

from manyu import counterfactual as cf
from manyu import counterfactual_mutants as mut
from manyu import underdetermination as ud
from manyu.schemas import BeliefType

import test_counterfactual_substrate as T


def _standoff():
    core = T._core()
    minted = ud.seed_fixture(core, "symmetric_rivals", agent_id=T.AGENT)
    ud.derive(core, T.AGENT)
    held = core.store.list_beliefs(T.AGENT, belief_type=BeliefType.UNDERDETERMINATION.value, include_inactive=True)
    return core, minted, held[0]


def _rivals(core):
    return sorted(
        (b for b in core.store.list_beliefs(T.AGENT, include_inactive=True) if b.belief_type is not BeliefType.UNDERDETERMINATION),
        key=lambda b: b.belief_id,
    )


def test_catalogue_names_a_check_for_every_mutant():
    """Every mutant is claimed to be caught by a named check, and every name resolves.

    Experiment 5 documented no mutant as equivalent and neither does this. A
    mutant with no check is a defect family nobody is watching.
    """
    module = globals()
    for mutant in mut.CATALOGUE:
        assert mutant.caught_by in module, f"{mutant.name} names {mutant.caught_by}, which does not exist in this file"


# --- the checks, each run on the real mechanism and on its mutant ------------


def test_already_held_prices_exactly_zero():
    """Catches `constant_price` and `ignores_new_evidence_guard`.

    The correct answer is exactly 0.000 because `_revise` returns the belief
    untouched. Both mutants produce a plausible movement instead, which is why an
    exact-zero check catches what a tolerance would not.
    """
    core, minted, _ = _standoff()
    left = _rivals(core)[0]
    held = cf.HypotheticalEvidence(
        summary="A record the belief already cites.",
        confidence=0.7,
        attaches_to=(left.belief_id,),
        evidence_id=minted["obs_redshift"],
    )

    real = cf.price(core.store, left, held)
    assert real.delta == 0.0
    assert real.mechanism is cf.Mechanism.GUARD_NOOP

    assert mut.price_constant(core.store, left, held).delta != 0.0, "constant_price should have moved it"
    assert mut.price_ignoring_guard(core.store, left, held).delta != 0.0, "ignores_new_evidence_guard should have moved it"


def test_dose_rises_with_entrenchment():
    """Catches `dose_ignores_stability`.

    The real dose reads the belief's stability, so a more entrenched standoff
    takes strictly more records. The mutant holds inertia fixed and returns the
    same dose at every entrenchment — a number about the record alone.
    """
    low = cf.dose_for_standoff(2, stability=0.10).records
    high = cf.dose_for_standoff(2, stability=0.90).records
    assert low is not None and high is not None
    assert high > low, f"real dose did not rise with entrenchment ({low} -> {high})"

    mut_low = mut.dose_ignoring_stability(2, stability=0.10).records
    mut_high = mut.dose_ignoring_stability(2, stability=0.90).records
    assert mut_high == mut_low, (
        f"dose_ignores_stability should be flat across entrenchment, got {mut_low} -> {mut_high}. "
        "A mutant that reproduces the behaviour it is meant to break tests nothing."
    )


def test_enumerator_declines_the_non_separating_candidate():
    """Catches `enumerator_returns_everything`.

    A record entering both rivals raises numerator and denominator together and
    cannot retire the standoff. The real enumerator declines it *and records the
    decline* (FR-11); the mutant emits it, reaching perfect recall with degraded
    precision — which is why precision is checked and not only recall.
    """
    core, _, meta = _standoff()
    rivals = sorted(meta.rivals)

    real = cf.enumerate_changers(core.store, meta)
    emitted = {frozenset(i.attaches_to) for i in real.items}
    assert emitted == {frozenset([rivals[0]]), frozenset([rivals[1]])}
    assert frozenset(rivals) not in emitted, "the non-separating pattern was emitted"
    assert any(d.get("reason") == "non_separating" for d in real.declined), "the decline was not recorded"

    mutated = mut.enumerate_everything(core.store, meta)
    mutated_patterns = {frozenset(i.attaches_to) for i in mutated.items}
    assert frozenset(rivals) in mutated_patterns, "enumerator_returns_everything should emit the non-separating pattern"
    assert len(mutated.declined) == 0, "the mutant should decline nothing — that is its defect"


# --- the check on the checks -------------------------------------------------


@pytest.mark.parametrize("_run", range(5))
def test_checks_are_deterministic(_run):
    """The lesson from experiment 5's battery, applied to this one.

    Belief ids come from `uuid4`, so anything reading them by position or by
    sort order can differ between constructions. Every quantity the checks above
    assert on is recomputed here across five independent seedings and must be
    identical each time.
    """
    core, minted, meta = _standoff()
    left = _rivals(core)[0]

    held = cf.HypotheticalEvidence(summary="held", confidence=0.7, attaches_to=(left.belief_id,), evidence_id=minted["obs_redshift"])
    assert cf.price(core.store, left, held).delta == 0.0

    enumeration = cf.enumerate_changers(core.store, meta)
    assert len(enumeration.items) == 2
    assert len(enumeration.declined) == 1
    assert {frozenset(i.attaches_to) for i in enumeration.items} == {frozenset([r]) for r in meta.rivals}

    # The dose is independent of which uuid4 the rivals happened to get.
    assert cf.dose_for_standoff(2, start=meta.confidence, stability=meta.stability).records == 5


def test_hypothetical_id_is_content_derived_not_random():
    """No `uuid4` anywhere near a price.

    Experiment 4 found a `uuid4` tie-break in production and experiment 5 found
    the same family in a test. A price that differs between the run that
    predicted it and the run that checked it cannot be calibrated at all.
    """
    first = cf.HypotheticalEvidence(summary="a record", confidence=0.5, attaches_to=("bel_x",))
    second = cf.HypotheticalEvidence(summary="a record", confidence=0.5, attaches_to=("bel_x",))
    assert first.hypothetical_id == second.hypothetical_id

    different = cf.HypotheticalEvidence(summary="a record", confidence=0.5, attaches_to=("bel_y",))
    assert different.hypothetical_id != first.hypothetical_id
