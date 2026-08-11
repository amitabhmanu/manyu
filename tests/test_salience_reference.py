"""Experiment 4 section 5.2 — differential testing against an independent reference.

Every one of experiment 3's sixteen defects was the same shape: **a quantity
that looked right and meant something else.** A test written from the same
understanding as the code cannot catch that, because it encodes the same
misunderstanding. Two implementations written from the *definition* can, because
they do not share a shortcut.

`_reference.py` computes stake, tension, leaf conflicts, raw magnitude and the
implicated-pair set from plain values, naively and slowly. This file asserts the
production path agrees with it — on the frozen fixtures and on several hundred
randomly generated webs.

Seeded generation, no `hypothesis` dependency. Entirely offline.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

import _reference as ref
from manyu.architecture import ArchConfig
from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery, _leaf_conflicts, stake_of
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.salience import FIXTURE_DIR, load_web, web_specs

AGENT = "agent_demo"
MAX_DEPTH = ArchConfig().supports_max_depth

FIXTURES = sorted(path.stem for path in FIXTURE_DIR.glob("*.json"))


def _build(specs: list[BeliefSpec]) -> tuple[ManyuCore, dict[str, str], dict[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, specs)
    return core, ids, {bid: key for key, bid in ids.items()}


def _production(core: ManyuCore, reverse: dict[str, str]):
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "reference")
    if signal is None:
        return 0.0, set()
    pairs = {tuple(sorted((reverse[c.belief_id_a], reverse[c.belief_id_b]))) for c in signal.carriers}
    return signal.magnitude_raw, pairs


# --- the guard that makes the rest mean anything -----------------------------

def _production_leaks(source: str) -> list[str]:
    """Names of production modules a source file reaches, by AST rather than grep.

    Parsed, not searched. The first version of the caller grepped for the
    substring `manyu.dissonance` and failed on `_reference.py`'s own docstring,
    which names the import it forbids. A check that fires on a *mention* gets
    disabled by whoever hits it next, and it would still miss
    `importlib.import_module("manyu" + ".dissonance")`. The AST sees imports.
    """
    import ast

    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    leaks = sorted(name for name in imported if name == "manyu" or name.startswith("manyu."))

    # Dynamic import would slip past the walk above, so the tools for it count too.
    if "importlib" in imported:
        leaks.append("importlib (dynamic import defeats this check)")
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if "__import__" in called:
        leaks.append("__import__ (dynamic import defeats this check)")
    return leaks


def test_the_reference_does_not_import_the_production_module() -> None:
    """A reference that calls what it checks agrees with it by construction.

    Stated as a property of the file rather than as an intention, for the same
    reason `SplitDissonanceAppraiser` takes an `AppraisalView` instead of the
    store: an implementer's restraint is not a constraint.
    """
    source = Path(__file__).with_name("_reference.py").read_text(encoding="utf-8")
    assert not _production_leaks(source), f"the reference implementation reaches production code: {_production_leaks(source)}"


@pytest.mark.parametrize(
    "source",
    [
        "from manyu.dissonance import stake_of",
        "import manyu.dissonance",
        "import manyu",
        "from manyu.dissonance import stake_of as _s",
        "import importlib\nm = importlib.import_module('manyu.dissonance')",
        "m = __import__('manyu.dissonance')",
        "def f():\n    from manyu.dissonance import _tension\n    return _tension",
    ],
)
def test_the_independence_guard_catches_every_way_in(source: str) -> None:
    """The guard, tested for its ability to fail — including from inside a
    function body, which a top-level-only walk would miss.

    `gate.py` holds every one of its assertions to this standard: "a gate that
    cannot fail is failure mode #5 wearing a lab coat."
    """
    assert _production_leaks(source), f"the guard let this through: {source!r}"


def test_the_independence_guard_passes_clean_source() -> None:
    """And does not fire on a file that merely talks about the import."""
    clean = '"""A docstring mentioning manyu.dissonance and manyu."""\nimport random\nfrom dataclasses import dataclass\n'
    assert _production_leaks(clean) == []


# --- agreement on the frozen fixtures ----------------------------------------

@pytest.mark.parametrize("name", FIXTURES)
def test_reference_and_production_agree_on_raw_tension(name: str) -> None:
    fixture = load_web(name)
    core, _, reverse = _build(web_specs(fixture))
    produced, _ = _production(core, reverse)
    expected = ref.raw_magnitude(ref.from_fixture(fixture))
    assert produced == pytest.approx(expected, abs=1e-6), f"{name}: production {produced} vs reference {expected}"


@pytest.mark.parametrize("name", FIXTURES)
def test_reference_and_production_agree_on_implicated_pairs(name: str) -> None:
    fixture = load_web(name)
    core, _, reverse = _build(web_specs(fixture))
    _, produced = _production(core, reverse)
    expected = ref.implicated_pairs(ref.from_fixture(fixture), MAX_DEPTH)
    assert produced == expected, f"{name}: only production {sorted(produced - expected)}, only reference {sorted(expected - produced)}"


@pytest.mark.parametrize("name", FIXTURES)
def test_reference_and_production_agree_on_every_stake(name: str) -> None:
    """Stake is the quantity the whole experiment turns on, so it is checked
    per belief rather than only through the aggregate it feeds.

    Experiment 1's gate #6: assert on the structure the consumer reads, not on
    the summary beside it. A sum can agree while its terms do not.
    """
    fixture = load_web(name)
    core, ids, _ = _build(web_specs(fixture))
    web = ref.from_fixture(fixture)
    for key, belief_id in ids.items():
        produced = stake_of(core.store, core.store.get_belief(belief_id))
        assert produced == pytest.approx(ref.stake(web, key), abs=1e-9), f"{name}/{key}"


# --- agreement on generated webs ---------------------------------------------

def _random_web(rng: random.Random, size: int) -> list[BeliefSpec]:
    """A web whose shape the author did not choose.

    Edges are drawn independently of the values, so most webs are uninteresting
    and a few are degenerate — self-edges are excluded because the store refuses
    them (experiment 3 review finding 1), but cycles, isolated nodes, mutual
    contradictions and multi-edge conflicts all occur.
    """
    keys = [f"b{index}" for index in range(size)]
    specs = []
    for index, key in enumerate(keys):
        others = [other for other in keys if other != key]
        specs.append(
            BeliefSpec(
                key=key,
                proposition=f"Claim {index}.",
                valence=round(rng.uniform(-1.0, 1.0), 3),
                confidence=round(rng.uniform(0.0, 1.0), 3),
                salience=round(rng.uniform(0.0, 1.0), 3),
                evidence_count=rng.randint(1, 4),
                contradicts=tuple(rng.sample(others, k=rng.randint(0, min(2, len(others))))),
                supports=tuple(rng.sample(others, k=rng.randint(0, min(2, len(others))))),
            )
        )
    return specs


@pytest.mark.parametrize("seed", range(60))
def test_reference_and_production_agree_on_random_webs(seed: int) -> None:
    """The case for generated input: the frozen fixtures were all authored by
    the same person who wrote the definitions above, so agreement on them is
    partly agreement with one reading. These webs were not authored at all.
    """
    rng = random.Random(seed)
    specs = _random_web(rng, rng.randint(2, 7))
    core, ids, reverse = _build(specs)

    web = ref.RefWeb.of(
        [
            ref.RefBelief(
                key=spec.key,
                valence=spec.valence,
                confidence=spec.confidence,
                salience=spec.salience,
                evidence_count=spec.evidence_count,
                contradicts=spec.contradicts,
                supports=spec.supports,
            )
            for spec in specs
        ]
    )

    produced_raw, produced_pairs = _production(core, reverse)
    assert produced_raw == pytest.approx(ref.raw_magnitude(web), abs=1e-6), f"seed {seed}: raw tension"
    assert produced_pairs == ref.implicated_pairs(web, MAX_DEPTH), f"seed {seed}: implicated pairs"


@pytest.mark.parametrize("seed", range(30))
def test_reference_and_production_agree_on_which_conflicts_exist(seed: int) -> None:
    """The conflict set, separately from the tension carried over it.

    A mechanism can agree on the total while disagreeing about which pairs it
    summed — the two errors cancel more often than intuition suggests, which is
    why `magnitude` and `carriers` are checked apart.
    """
    rng = random.Random(1000 + seed)
    specs = _random_web(rng, rng.randint(2, 7))
    core, _, reverse = _build(specs)

    web = ref.RefWeb.of(
        [
            ref.RefBelief(
                key=spec.key,
                valence=spec.valence,
                confidence=spec.confidence,
                salience=spec.salience,
                evidence_count=spec.evidence_count,
                contradicts=spec.contradicts,
                supports=spec.supports,
            )
            for spec in specs
        ]
    )

    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT)}
    produced = {tuple(sorted((reverse[a], reverse[b]))) for a, b in _leaf_conflicts(beliefs)}
    assert produced == ref.leaf_conflicts(web), f"seed {seed}"


# --- the generator itself ----------------------------------------------------

def test_gate_the_generator_produces_webs_worth_comparing() -> None:
    """A generator that only ever emits edgeless webs would pass everything.

    Experiment 2 made the same move for `near_miss`: assert the fixture actually
    has the property that makes it dangerous, or its negative result is evidence
    about the fixture rather than about the mechanism.
    """
    with_conflict = with_support = with_multi = 0
    for seed in range(60):
        rng = random.Random(seed)
        specs = _random_web(rng, rng.randint(2, 7))
        web = ref.RefWeb.of(
            [
                ref.RefBelief(
                    key=spec.key,
                    valence=spec.valence,
                    confidence=spec.confidence,
                    salience=spec.salience,
                    evidence_count=spec.evidence_count,
                    contradicts=spec.contradicts,
                    supports=spec.supports,
                )
                for spec in specs
            ]
        )
        conflicts = ref.leaf_conflicts(web)
        if conflicts:
            with_conflict += 1
        if len(conflicts) > 1:
            with_multi += 1
        if any(spec.supports for spec in specs):
            with_support += 1

    assert with_conflict >= 30, f"only {with_conflict}/60 generated webs contain any conflict"
    assert with_multi >= 15, f"only {with_multi}/60 generated webs contain more than one conflict"
    assert with_support >= 30, f"only {with_support}/60 generated webs contain a supports edge"
