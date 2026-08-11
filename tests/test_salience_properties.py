"""Experiment 4 section 5.3 — properties, not expected values.

A test that asserts an expected number encodes the author's arithmetic; if the
arithmetic is wrong the test agrees with it. These assert *invariants* over
webs nobody authored — relabelling a belief must not change which pairs are in
tension, insertion order must not change the signal, an isolated belief must
change nothing.

The insertion-order property is the one with history. Experiment 3 section 3.5
found that **46% of correctly-identified edges were destroyed by emission
order**, invisible in the extractor output and invisible in the store, appearing
only when the two were compared. That is precisely a property test's shape.

Seeded generation, no `hypothesis` dependency. Entirely offline.
"""

from __future__ import annotations

import random

import pytest

from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.salience import derange_supports, implicated_beliefs, reading_of, spread

AGENT = "agent_demo"
CASES = 40


def _web(rng: random.Random, size: int) -> list[BeliefSpec]:
    keys = [f"b{index}" for index in range(size)]
    specs = []
    for index, key in enumerate(keys):
        others = [other for other in keys if other != key]
        specs.append(
            BeliefSpec(
                key=key,
                proposition=f"Claim {index}.",
                valence=round(rng.uniform(-1.0, 1.0), 3),
                confidence=round(rng.uniform(0.05, 1.0), 3),
                salience=round(rng.uniform(0.05, 1.0), 3),
                evidence_count=rng.randint(1, 3),
                contradicts=tuple(rng.sample(others, k=rng.randint(0, min(2, len(others))))),
                supports=tuple(rng.sample(others, k=rng.randint(0, min(2, len(others))))),
            )
        )
    return specs


def _signal(specs: list[BeliefSpec]):
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, specs)
    reverse = {bid: key for key, bid in ids.items()}
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "properties")
    return core, signal, reverse


def _pairs(signal, reverse) -> set[tuple[str, str]]:
    if signal is None:
        return set()
    return {tuple(sorted((reverse[c.belief_id_a], reverse[c.belief_id_b]))) for c in signal.carriers}


def _raw(signal) -> float:
    return 0.0 if signal is None else signal.magnitude_raw


# --- invariance --------------------------------------------------------------

@pytest.mark.parametrize("seed", range(CASES))
def test_insertion_order_does_not_change_the_signal(seed: int) -> None:
    """Experiment 3 section 3.5's defect shape, as a property.

    Every edge the live extractor emits names a sibling in the same batch, and
    single-pass resolution destroyed 46% of them purely by the order the model
    happened to state things in.
    """
    rng = random.Random(seed)
    specs = _web(rng, rng.randint(2, 7))
    shuffled = list(specs)
    random.Random(seed + 9000).shuffle(shuffled)

    _, first, first_map = _signal(specs)
    _, second, second_map = _signal(shuffled)

    assert _raw(first) == pytest.approx(_raw(second), abs=1e-9), f"seed {seed}: raw tension moved with order"
    assert _pairs(first, first_map) == _pairs(second, second_map), f"seed {seed}: implicated pairs moved with order"


@pytest.mark.parametrize("seed", range(CASES))
def test_relabelling_beliefs_does_not_change_which_pairs_are_in_tension(seed: int) -> None:
    """Isomorphism invariance. Catches dependence on the `sorted()` and
    `belief_id`-ascending tiebreaks the code uses throughout — a real hazard,
    since the tie-break in the *selector* turned out to run on `uuid4`.
    """
    rng = random.Random(1000 + seed)
    specs = _web(rng, rng.randint(2, 6))
    mapping = {spec.key: f"z{index}" for index, spec in enumerate(reversed(specs))}
    relabelled = [
        BeliefSpec(
            key=mapping[spec.key],
            proposition=spec.proposition,
            valence=spec.valence,
            confidence=spec.confidence,
            salience=spec.salience,
            evidence_count=spec.evidence_count,
            contradicts=tuple(mapping[k] for k in spec.contradicts),
            supports=tuple(mapping[k] for k in spec.supports),
        )
        for spec in specs
    ]

    _, original, original_map = _signal(specs)
    _, renamed, renamed_map = _signal(relabelled)

    assert _raw(original) == pytest.approx(_raw(renamed), abs=1e-9)
    translated = {tuple(sorted((mapping[a], mapping[b]))) for a, b in _pairs(original, original_map)}
    assert translated == _pairs(renamed, renamed_map), f"seed {seed}"


@pytest.mark.parametrize("seed", range(CASES))
def test_adding_an_isolated_belief_changes_nothing(seed: int) -> None:
    """Locality. A belief with no edges cannot participate in any tension."""
    rng = random.Random(2000 + seed)
    specs = _web(rng, rng.randint(2, 6))
    extended = specs + [BeliefSpec(key="lonely", proposition="Unrelated.", valence=0.9, confidence=0.9, salience=0.9)]

    _, before, before_map = _signal(specs)
    _, after, after_map = _signal(extended)

    assert _raw(before) == pytest.approx(_raw(after), abs=1e-9), f"seed {seed}: an isolated belief moved tension"
    assert _pairs(before, before_map) == _pairs(after, after_map)


@pytest.mark.parametrize("seed", range(CASES))
def test_adding_a_conflict_never_lowers_raw_tension(seed: int) -> None:
    """Monotonicity. `magnitude_raw` sums over a set that can only grow."""
    rng = random.Random(3000 + seed)
    specs = _web(rng, rng.randint(2, 6))
    added = specs + [
        BeliefSpec(key="new_pos", proposition="Newly claimed.", valence=0.8, confidence=0.8, salience=0.8),
        BeliefSpec(
            key="new_neg",
            proposition="Newly denied.",
            valence=-0.8,
            confidence=0.8,
            salience=0.8,
            contradicts=("new_pos",),
        ),
    ]
    _, before, _ = _signal(specs)
    _, after, _ = _signal(added)
    assert _raw(after) >= _raw(before) - 1e-9, f"seed {seed}: {_raw(before)} -> {_raw(after)}"


@pytest.mark.parametrize("seed", range(CASES))
def test_scaling_every_stake_scales_raw_tension_proportionally(seed: int) -> None:
    """`_tension` is linear in the minimum stake, so halving every confidence
    must halve the total. Catches an accidental nonlinearity in aggregation —
    and would catch a saturating transform leaking into the raw channel.
    """
    rng = random.Random(4000 + seed)
    specs = _web(rng, rng.randint(2, 6))
    halved = [BeliefSpec(**{**spec.__dict__, "confidence": spec.confidence / 2}) for spec in specs]

    _, full, _ = _signal(specs)
    _, half, _ = _signal(halved)
    if _raw(full) == 0.0:
        pytest.skip("no tension to scale")
    # Absolute tolerance at the storage granularity, not a relative one.
    # `DissonanceSignal.magnitude_raw` is `round(raw, 6)`, so the exact half of a
    # 6dp value need not itself be representable at 6dp — half of 0.388581 is
    # 0.1942905, stored as 0.194291. A tighter tolerance fails on the rounding
    # rather than on the property.
    assert _raw(half) == pytest.approx(_raw(full) / 2, abs=1e-6), f"seed {seed}"


# --- the derangement used as Stage 3's null ----------------------------------

@pytest.mark.parametrize("seed", range(20))
def test_derangement_preserves_out_degree_and_leaves_conflicts_alone(seed: int) -> None:
    """The null must differ from the real web in exactly one way.

    Deleting edges instead of rewiring them would confound "the structure was
    meaningful" with "there was less of it" — the family experiment 1's shuffle
    baseline exists to avoid.
    """
    rng = random.Random(5000 + seed)
    specs = _web(rng, rng.randint(3, 8))
    deranged = derange_supports(specs, seed)

    assert [len(s.supports) for s in deranged] == [len(s.supports) for s in specs], "out-degree changed"
    assert [s.contradicts for s in deranged] == [s.contradicts for s in specs], "conflicts were rewired"
    assert [s.confidence for s in deranged] == [s.confidence for s in specs]
    assert not any(s.key in s.supports for s in deranged), "a derangement produced a self-edge"


def test_derangement_actually_rewires_something() -> None:
    """A null identical to the real web is not a null.

    Over a spread of seeds on a web with real structure, at least one derangement
    must differ — otherwise Stage 3 compares a thing to itself and its p-value is
    meaningless.
    """
    from manyu.salience import load_web, web_specs

    specs = web_specs(load_web("distractor_web"))
    variants = {tuple(tuple(s.supports) for s in derange_supports(specs, seed)) for seed in range(20)}
    original = tuple(tuple(s.supports) for s in specs)
    assert len(variants) > 1, "every derangement produced the same graph"
    assert variants - {original}, "no derangement differed from the real web"


def test_spread_is_zero_on_a_web_with_no_conflict() -> None:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_beliefs(core, [BeliefSpec(key="a", proposition="A."), BeliefSpec(key="b", proposition="B.")])
    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "properties"), agent_id=AGENT)
    assert reading is None


def test_spread_counts_beliefs_not_pairs() -> None:
    """A conflict names two beliefs, so a two-belief web is fully implicated —
    the ceiling case Stage 3 must exclude rather than report.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_beliefs(
        core,
        [
            BeliefSpec(key="pos", proposition="It holds.", valence=0.6),
            BeliefSpec(key="neg", proposition="It does not.", valence=-0.6, contradicts=("pos",)),
        ],
    )
    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "properties"), agent_id=AGENT)
    assert reading is not None
    assert len(implicated_beliefs(reading.view)) == 2
    assert spread(reading.view, 2) == pytest.approx(1.0)
    assert spread(reading.view, 0) == 0.0, "an empty web must not divide by zero"
