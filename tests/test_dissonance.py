"""Stage 2: D3 — does dissonance fall out of structure, or must it be stipulated?

Entirely offline. No provider is constructed anywhere in this file, which is
what lets the whole discriminator run for free and be deterministic.

The tests fall into four groups:

- **Semantics** — the merged query means what its docstring says (`min` not
  `sum`, traversal not adjacency).
- **Sensitivity** — the signal fires where a conflict exists.
- **Specificity** — and does not where one does not. Without this, transfer is
  passable by a mechanism that fires on everything, which four positive
  fixtures and no negatives would never have caught.
- **The control** — `StipulatedDissonanceQuery` must fail the held-out set, or
  nothing shows the held-out set can fail anything.
"""

from __future__ import annotations

import pytest

from manyu.capability import MIN_USEFUL_RESOLUTION
from manyu.core import ManyuCore
from manyu.dissonance import (
    LADDER_STAKES,
    AdjacentConflictRule,
    AppraisalView,
    MergedDissonanceQuery,
    SplitDissonanceAppraiser,
    SplitWithSourceTable,
    StipulatedDissonanceQuery,
    TraversingConflictRule,
    ValenceOnlyDissonanceQuery,
    fixture_specs,
    ladder_specs,
    load_dissonance_fixture,
)
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.gate import GateFailure, assert_has_range, assert_not_noop

AGENT = "agent_demo"
HELD_OUT = ["transitive", "transitive_depth2", "value_conflict", "source_conflict"]
DISCRIMINATING = ["transitive", "transitive_depth2"]
NEGATIVE = ["distractor", "near_miss"]


def _seeded(specs) -> ManyuCore:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    if specs:
        seed_beliefs(core, specs)
    return core


def _detect(fixture_name: str, build: str):
    fx = load_dissonance_fixture(fixture_name)
    core = _seeded(fixture_specs(fx))
    return _run(core, build, fx["contradiction_type"])


def _run(core: ManyuCore, build: str, contradiction_type: str):
    """Dispatch, and note the asymmetry in the call shapes.

    Merged is handed the store. Split is handed an `AppraisalView` — a scalar —
    because that is all its affect layer holds. The signatures differ because
    the architectures differ; making them uniform would have hidden the very
    thing D3 measures.
    """
    if build == "merged":
        return MergedDissonanceQuery(core.store).detect(AGENT, contradiction_type)
    if build == "stipulated":
        return StipulatedDissonanceQuery(core.store).detect(AGENT, contradiction_type)
    if build == "split":
        appraiser = SplitDissonanceAppraiser(core.profile, core.clock)
        return appraiser.detect(appraiser.view(core.store, AGENT), contradiction_type)
    if build in ("split_table_adjacent", "split_table_traversing"):
        rule = AdjacentConflictRule() if build.endswith("adjacent") else TraversingConflictRule()
        return SplitWithSourceTable(core.profile, core.clock, rule).detect_with_sources(
            core.store, AGENT, contradiction_type
        )
    raise ValueError(build)


def _ladder(build: str, pairs: int, stake: str) -> float:
    core = _seeded(ladder_specs(pairs, stake) if pairs else [])
    signal = _run(core, build, "ladder")
    return 0.0 if signal is None else signal.magnitude


# --- semantics ---------------------------------------------------------------

def test_dissonance_requires_both_sides_to_matter():
    """`min(stake_a, stake_b)`. A heavy belief conflicting with a trivial one is
    a correction, not a tension — and `sum` or `max` would let one heavy belief
    manufacture dissonance against anything it touched.
    """
    balanced = _seeded([
        BeliefSpec(key="a", proposition="It holds.", valence=0.6, salience=0.8, confidence=0.8),
        BeliefSpec(key="b", proposition="It does not hold.", valence=-0.6, salience=0.8, confidence=0.8, contradicts=("a",)),
    ])
    lopsided = _seeded([
        BeliefSpec(key="a", proposition="It holds.", valence=0.6, salience=0.8, confidence=0.8),
        BeliefSpec(key="b", proposition="It does not hold.", valence=-0.6, salience=0.05, confidence=0.2, contradicts=("a",)),
    ])
    heavy = MergedDissonanceQuery(balanced.store).detect(AGENT, "direct").magnitude
    light = MergedDissonanceQuery(lopsided.store).detect(AGENT, "direct").magnitude
    assert light < heavy / 4, f"lopsided conflict scored {light}, near the balanced {heavy}"


def test_merged_traverses_supports_to_find_derived_pairs():
    """The discriminating measurement (methodology §3.2.1).

    A transitive fixture *necessarily* contains an adjacent leaf pair, so
    magnitude cannot tell a graph query from an adjacency scan. What separates
    them is whether the signal also implicates the pair reachable only through
    `supports` — a carrier with a non-empty path.
    """
    signal = _detect("transitive", "merged")
    derived = [c for c in signal.carriers if c.path]
    assert derived, f"no derived carriers; got {[(c.belief_id_a, c.path) for c in signal.carriers]}"
    assert any(not c.path for c in signal.carriers), "the leaf pair should still be reported"


def test_traversal_reaches_depth_two():
    """`transitive` needs one supports hop per side; this needs two. A mechanism
    that traverses exactly one level passes the first and fails here.
    """
    fx = load_dissonance_fixture("transitive_depth2")
    signal = _detect("transitive_depth2", "merged")
    longest = max(len(c.path) for c in signal.carriers)
    assert longest >= fx["min_path_length"], f"longest path {longest} < required {fx['min_path_length']}"


def test_magnitude_counts_leaf_conflicts_not_reachable_pairs():
    """Traversal multiplies who is implicated, not how much tension exists.

    `transitive_depth2` turns one `contradicts` edge into nine reachable pairs.
    Summing every carrier would make magnitude report graph size, so magnitude
    comes from the stated conflicts alone — visible here as depth2 and
    transitive scoring the same despite very different carrier counts.
    """
    shallow = _detect("transitive", "merged")
    deep = _detect("transitive_depth2", "merged")
    assert len(deep.carriers) > len(shallow.carriers)
    assert deep.magnitude == pytest.approx(shallow.magnitude, abs=1e-6)


def test_mechanisms_are_not_no_ops():
    """Instrument gate #5, on both builds: a dissonant store and a consistent
    one must not produce the same thing.
    """
    for build in ("merged", "split"):
        conflict = _detect("direct", build)
        clean = _detect("distractor", build)
        assert_not_noop(
            conflict.magnitude if conflict else None,
            clean.magnitude if clean else None,
            label=f"{build} dissonance detector",
        )


# --- sensitivity -------------------------------------------------------------

@pytest.mark.parametrize("fixture", HELD_OUT)
def test_merged_fires_on_every_held_out_type(fixture):
    signal = _detect(fixture, "merged")
    assert signal is not None and signal.magnitude > 0.0


@pytest.mark.parametrize("fixture", DISCRIMINATING)
def test_merged_finds_derived_carriers_on_discriminating_types(fixture):
    signal = _detect(fixture, "merged")
    assert [c for c in signal.carriers if c.path], f"{fixture}: no derived carrier"


@pytest.mark.parametrize("fixture", HELD_OUT + ["direct"])
def test_split_can_report_tension_but_never_its_sources(fixture):
    """**The redesigned discriminator.** Split names nothing, on anything.

    Not because its rule declines to look — because `AppraisalView` is a scalar
    and a baseline, and there is no belief id anywhere in it to report. Split
    knows *that* it is in tension and *how much*; it cannot say *between what*.

    The first version of this test asserted merely that split found no
    *derived* carriers, which was true only because the implementer had not
    written a traversal loop. This holds for a reason in the types.
    """
    signal = _detect(fixture, "split")
    assert signal is not None, "split should still register the tension"
    assert signal.magnitude > 0.0
    assert signal.carriers == []


def test_split_detector_cannot_reach_the_store():
    """The constraint is structural, so state it as one.

    `SplitDissonanceAppraiser.detect` takes an `AppraisalView`. If a future
    change gives it the store back, this fails and the architectural claim in
    results.md §2 has to be re-argued rather than quietly lost.
    """
    import inspect

    params = inspect.signature(SplitDissonanceAppraiser.detect).parameters
    assert "store" not in params
    assert params["view"].annotation in (AppraisalView, "AppraisalView")


# --- specificity -------------------------------------------------------------

@pytest.mark.parametrize("fixture", NEGATIVE)
@pytest.mark.parametrize("build", ["merged", "split", "stipulated"])
def test_no_build_fires_on_a_negative_control(fixture, build):
    assert _detect(fixture, build) is None


def test_near_miss_would_catch_a_valence_only_detector():
    """The near-miss fixture is aimed at a specific way merged could be wrong.

    Its pairs have large valence gaps and no edges. Merged's `(1 + |dv|)/2`
    term is a weighting on pairs that already conflict; an implementation that
    iterated all pairs and keyed on valence difference would fire on every line
    here while still scoring 4/4 on the held-out set. This asserts the fixture
    actually has the property that makes it dangerous, so the negative result
    above means something.
    """
    fx = load_dissonance_fixture("near_miss")
    specs = fixture_specs(fx)
    assert not any(s.contradicts or s.supports for s in specs), "near-miss must have no edges"
    gaps = [
        abs(a.valence - b.valence)
        for i, a in enumerate(specs)
        for b in specs[i + 1:]
    ]
    assert max(gaps) >= 1.2, f"near-miss valence gaps too small to be a trap: {max(gaps)}"


# --- the control on the test -------------------------------------------------

def test_stipulated_build_ceilings_on_the_development_fixture():
    """The control has to be a working detector, or its held-out failure would
    just mean it is broken.
    """
    signal = _detect("direct", "stipulated")
    assert signal is not None
    assert signal.magnitude == pytest.approx(_detect("direct", "merged").magnitude)


@pytest.mark.parametrize("fixture", DISCRIMINATING)
def test_steelman_split_matches_merged_when_given_both_pieces(fixture):
    """The steelman succeeds, and what it takes is the finding.

    Split can name its sources exactly as well as merged — given a hand-written
    traversal rule *and* a hand-maintained `SourceTable` to hold the ids its
    affect scalar cannot. So the answer to "can split do this?" is yes, and the
    experiment's question becomes what it cost.

    Kept as a passing assertion deliberately: if a future change makes this
    fail, split has been weakened rather than merged strengthened, and the
    comparison is no longer fair.
    """
    merged = _detect(fixture, "merged")
    steelman = _detect(fixture, "split_table_traversing")
    assert steelman is not None
    assert len([c for c in steelman.carriers if c.path]) == len([c for c in merged.carriers if c.path])


@pytest.mark.parametrize("fixture", DISCRIMINATING)
def test_source_table_coverage_is_bounded_by_its_rule(fixture):
    """A side-table only knows what the rule filling it knows.

    With the natural adjacent rule, split-with-a-table names the directly-stated
    pair and stays blind to every derived one — the affect layer is irrelevant
    to that. Reaching merged's coverage means writing merged's traversal, which
    is to say writing merged.
    """
    adjacent = _detect(fixture, "split_table_adjacent")
    assert adjacent is not None
    assert adjacent.carriers, "the adjacent rule should still name the stated pair"
    assert not [c for c in adjacent.carriers if c.path]


def test_naming_sources_costs_merged_nothing_and_split_two_components():
    """The measurement D3 actually supports, stated as a test.

    Merged reports carriers from the same query that produces the magnitude.
    Split needs a `BeliefConflictRule` (to reach the graph at all) and a
    `SourceTable` (to hold what the scalar cannot), neither of which the
    architecture provides.
    """
    core = _seeded(fixture_specs(load_dissonance_fixture("transitive")))

    merged = MergedDissonanceQuery(core.store).detect(AGENT, "transitive")
    assert merged.carriers, "merged names sources from its own query"

    bare = SplitDissonanceAppraiser(core.profile, core.clock)
    assert bare.detect(bare.view(core.store, AGENT), "transitive").carriers == []

    with_table = SplitWithSourceTable(core.profile, core.clock, TraversingConflictRule())
    assert with_table.detect_with_sources(core.store, AGENT, "transitive").carriers


def test_valence_only_mutant_fires_where_the_real_builds_do_not():
    """Makes `near_miss` non-vacuous.

    Both real builds return `None` on that fixture *before* the valence term is
    reached — no `contradicts` edges, so they bail at `_leaf_conflicts`. Their
    silence is therefore evidence about the fixture, not about them, and
    "specificity 2/2" would mean nothing on its own. The mutant is the
    mechanism the fixture was built to catch: it fires, so the trap works, and
    merged's silence is a real pass.
    """
    core = _seeded(fixture_specs(load_dissonance_fixture("near_miss")))
    mutant = ValenceOnlyDissonanceQuery(core.store).detect(AGENT, "none")
    assert mutant is not None and mutant.magnitude > 0.5
    assert _detect("near_miss", "merged") is None


def test_valence_only_mutant_is_not_simply_always_on():
    """A mutant that fired on everything would prove nothing about the fixture."""
    core = _seeded(fixture_specs(load_dissonance_fixture("distractor")))
    assert ValenceOnlyDissonanceQuery(core.store).detect(AGENT, "none") is None


def test_traversal_stops_at_supports_max_depth():
    """The closure must have a boundary, or `supports_max_depth` is decoration.

    A chain four hops long puts the leaf conflict out of a depth-3 root's reach
    while leaving it inside the next node's, so the cutoff is observable rather
    than merely configured.
    """
    core = _seeded([
        BeliefSpec(key="root", proposition="Root.", supports=("m1",)),
        BeliefSpec(key="m1", proposition="Mid one.", supports=("m2",)),
        BeliefSpec(key="m2", proposition="Mid two.", supports=("m3",)),
        BeliefSpec(key="m3", proposition="Mid three.", supports=("leaf_a",)),
        BeliefSpec(key="leaf_a", proposition="The claim holds.", valence=0.6),
        BeliefSpec(key="leaf_b", proposition="The claim does not hold.", valence=-0.6, contradicts=("leaf_a",)),
    ])
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "depth_boundary")
    beliefs = {b.belief_id: b.belief_key for b in core.store.list_beliefs(AGENT)}
    reached = {
        tuple(sorted((beliefs[c.belief_id_a], beliefs[c.belief_id_b])))
        for c in signal.carriers
    }
    assert ("leaf_b", "m1") in reached, "depth-3 reach from m1 should find the conflict"
    assert ("leaf_b", "root") not in reached, "root is four hops out and must not be reached"


@pytest.mark.parametrize("fixture", HELD_OUT)
def test_stipulated_build_fails_every_held_out_type(fixture):
    """Requirements §8.2's precondition. If this ever passes, the held-out set
    does not discriminate structural from stipulated and no D3 verdict may be
    read from it — a merged 4/4 would then mean only that the fixtures were
    passable.
    """
    assert _detect(fixture, "stipulated") is None


# --- the ladder: FR-D3.4 -----------------------------------------------------

@pytest.mark.parametrize("build", ["merged", "split"])
def test_ladder_is_monotone_in_conflict_count(build):
    for stake in LADDER_STAKES:
        values = [_ladder(build, pairs, stake) for pairs in (0, 1, 2, 3)]
        assert values == sorted(values), f"{build}/{stake} not monotone in pairs: {values}"


@pytest.mark.parametrize("build", ["merged", "split"])
def test_ladder_is_monotone_in_stake(build):
    for pairs in (1, 2, 3):
        values = [_ladder(build, pairs, stake) for stake in ("low", "medium", "high")]
        assert values == sorted(values), f"{build}/{pairs} pairs not monotone in stake: {values}"


def test_merged_signal_is_graded_across_the_whole_ladder():
    """The §8.2 gate on the winner: experiment #4 modulates arbitration
    thresholds with this signal, and a boolean cannot do that.
    """
    values = [_ladder("merged", p, s) for s in LADDER_STAKES for p in (1, 2, 3)]
    assert len(set(values)) >= MIN_USEFUL_RESOLUTION, f"only {len(set(values))} distinct values: {values}"
    assert_has_range(values, label="merged dissonance ladder")
    assert max(values) < 0.95, f"saturated at the top rung: {max(values)}"


def test_split_signal_saturates_at_its_channel_bound():
    """A real architectural consequence, pinned as a finding rather than left to
    be discovered during analysis.

    Split's affect channels are bounded per event — that bounding is what makes
    them stable — so a dissonance signal routed through one inherits the bound
    and flattens above it. Note this does not depend on the particular
    `max_delta_per_event` chosen here: every existing channel in
    `default_profile.json` caps between 0.25 and 0.35, and a single high-stake
    conflicting pair already produces ~0.75 of raw tension.
    """
    values = [_ladder("split", p, s) for s in LADDER_STAKES for p in (1, 2, 3)]
    ceiling = max(values)
    assert sum(1 for v in values if v == ceiling) >= 4, f"expected saturation, got {values}"
    with pytest.raises(GateFailure):
        assert_has_range([v for v in values if v == ceiling], label="split saturated region")
