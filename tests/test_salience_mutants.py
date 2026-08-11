"""Experiment 4 section 5.6 — proving the suite can catch defects.

The direct answer to "many defects were encountered in previous experiments that
the tests did not catch." Experiment 3's own tally: sixteen defects, and its test
suite found **zero** of them. A suite in that condition is indistinguishable from
one that works, and no amount of adding tests changes that — the tests share the
author's assumptions, so they agree with the code exactly where it is wrong.

So the mechanism is broken on purpose, eight ways, each reproducing a defect that
really happened, and the checks below must go red. Three properties make the
battery mean something:

1. **Every mutant is caught** by at least one named check, or the gap is
   reported as a hole rather than discovered later.
2. **Every mutant is a working mechanism** on the development fixture. One that
   merely crashes proves nothing about coverage — experiment 2 made the same move
   for `StipulatedDissonanceQuery`.
3. **Every check passes on the real mechanism.** A check that fires on everything
   catches nothing.

The checks here deliberately restate properties that `test_salience_loop.py` also
asserts. That duplication is the point: two independent statements of one
property, in the same spirit as the reference implementation in `_reference.py`.

Entirely offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from manyu.core import ManyuCore
from manyu.fork import seed_beliefs
from manyu.salience import Arm, AttentionLoop, LoopResult, TerminationReason, load_web, web_specs
from manyu.salience_mutants import CATALOGUE, EXPECTED_EQUIVALENT, build

AGENT = "agent_demo"


def _core(name: str) -> tuple[ManyuCore, dict[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, web_specs(load_web(name)))
    return core, {bid: key for key, bid in ids.items()}


Runner = Callable[[str, int], tuple[LoopResult, dict[str, str]]]


def _real_runner(fixture: str, bound: int) -> tuple[LoopResult, dict[str, str]]:
    core, reverse = _core(fixture)
    return AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=bound), reverse


def _mutant_runner(name: str) -> Runner:
    def run(fixture: str, bound: int) -> tuple[LoopResult, dict[str, str]]:
        core, reverse = _core(fixture)
        return build(name, core, agent_id=AGENT).run(max_iterations=bound), reverse

    return run


# --- the checks --------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    describes: str
    run: Callable[[Runner], None]


def _budget_is_not_wasted(runner: Runner) -> None:
    result, _ = runner("multi_conflict_web", 8)
    attended = result.attended
    assert len(attended) == len(set(attended)), f"a conflict was attended twice: {attended}"
    assert all(step.outcome != "already_priced" for step in result.steps), "a step was spent on a no-op"


def _truncation_is_not_convergence(runner: Runner) -> None:
    result, _ = runner("multi_conflict_web", 1)
    assert result.termination is TerminationReason.BOUND_REACHED, (
        f"a spent budget reported {result.termination.value}"
    )


#: How many independent stores an id-sensitive check runs over.
#:
#: Belief ids are `uuid4`, so a mutant that ignores tension picks an *arbitrary*
#: conflict — and on a three-conflict web it lands on the tension-optimal order
#: by luck often enough that a single run makes "is this mutant caught?" a coin
#: flip. `no_op` passed the battery in isolation and failed in the full suite for
#: exactly that reason. A probabilistic catch is not a catch, so the id-sensitive
#: checks repeat and fail if *any* store exposes the mutant. Two three-conflict
#: webs give a per-store miss probability near 1/36, so eight stores put a false
#: pass below one in a trillion.
ID_SENSITIVE_REPEATS = 8


def _ordering_carries_information(runner: Runner) -> None:
    """The candidate must beat the worst ordering of the same actions.

    Compared against `inverted` run on the real loop, so a mutant cannot pass by
    dragging its own baseline down with it.
    """
    core, _ = _core("multi_conflict_web")
    floor = AttentionLoop(core, arm=Arm.INVERTED, agent_id=AGENT).run(max_iterations=2).trajectory[-1]
    for _ in range(ID_SENSITIVE_REPEATS):
        result, _ = runner("multi_conflict_web", 2)
        assert result.trajectory[-1] < floor, f"left {result.trajectory[-1]} against a floor of {floor}"


def _acts_only_on_stated_conflicts(runner: Runner) -> None:
    for fixture in ("depth_carrier_web", "multi_conflict_web"):
        result, _ = runner(fixture, 6)
        for step in result.steps:
            contradictor = step.contradictor_id
            target = step.target_id
            assert contradictor != target, "a belief was made to contradict itself"
            assert step.direction in {"declared", "mutual"}, step.direction


def _direction_is_read_off_the_graph(runner: Runner) -> None:
    """`counter_direction` is load-bearing here and was added because of this check.

    On the minimal pair the declared target *is* the weaker party, so a loop
    choosing to charge whichever side is weaker behaves identically to one
    reading the graph. The battery caught that: `chosen_direction` passed every
    check. `counter_direction` pulls the two apart.
    """
    for fixture in ("counter_direction", "adversarial_grounding", "aligned_grounding"):
        result, reverse = runner(fixture, 4)
        declared = {(p["contradictor"], p["target"]) for p in load_web(fixture)["contradictions"]}
        for step in result.steps:
            pair = (reverse[step.contradictor_id], reverse[step.target_id])
            assert pair in declared, f"{fixture}: charged {pair}, which the fixture never declared"


def _selection_uses_the_live_maximum(runner: Runner) -> None:
    """A driven arm must take the best conflict *currently* available.

    `hub_web` is load-bearing here and was added because of this check. On every
    other frozen web the conflicts are disjoint, so tensions fall independently,
    the ranking never reorders, and a loop deciding from the first reading it
    ever saw is behaviourally identical to one re-reading each step. On the hub
    the ordering genuinely flips after the first action.
    """
    for fixture in ("hub_web", "multi_conflict_web"):
        for _ in range(ID_SENSITIVE_REPEATS):
            result, _ = runner(fixture, 4)
            assert result.steps, f"nothing was attended on {fixture}"
            for step in result.steps:
                assert step.tension_before == pytest.approx(step.best_available_tension, abs=1e-6), (
                    f"{fixture} step {step.iteration} took tension {step.tension_before} while "
                    f"{step.best_available_tension} was available — the choice was not made from the live web"
                )


def _the_trajectory_never_rises(runner: Runner) -> None:
    for fixture in ("multi_conflict_web", "mutual_contradiction"):
        result, _ = runner(fixture, 8)
        pairs = list(zip(result.trajectory, result.trajectory[1:]))
        assert all(b <= a + 1e-9 for a, b in pairs), f"{fixture}: tension rose — {result.trajectory}"


def _a_tie_is_recorded(runner: Runner) -> None:
    result, _ = runner("tied_tension_web", 1)
    assert result.steps, "nothing was attended on a web with two live conflicts"
    assert result.steps[0].tied_with == 2, f"tied_with={result.steps[0].tied_with}, expected 2"


def _a_mutual_conflict_is_counted_once(runner: Runner) -> None:
    result, _ = runner("mutual_contradiction", 6)
    assert len(result.attended) == 1, f"one deduplicated conflict was attended {len(result.attended)} times"
    assert all(step.direction == "mutual" for step in result.steps)


def _grounding_is_recorded_before_the_action(runner: Runner) -> None:
    result, _ = runner("adversarial_grounding", 4)
    assert result.steps
    step = result.steps[0]
    assert step.target_evidence_count == 5, f"target grounding recorded as {step.target_evidence_count}"
    assert step.contradictor_evidence_count == 1


def _a_negative_web_is_left_alone(runner: Runner) -> None:
    result, _ = runner("no_conflict_web", 4)
    assert result.termination is TerminationReason.NO_SIGNAL
    assert result.steps == ()


CHECKS: tuple[Check, ...] = (
    Check("budget_is_not_wasted", "no step re-attends a handled conflict", _budget_is_not_wasted),
    Check("truncation_is_not_convergence", "a spent budget is reported as spent", _truncation_is_not_convergence),
    Check("ordering_carries_information", "the ranking beats the worst ordering", _ordering_carries_information),
    Check("acts_only_on_stated_conflicts", "no action on a pair with no edge", _acts_only_on_stated_conflicts),
    Check("direction_is_read_off_the_graph", "the loop does not choose who pays", _direction_is_read_off_the_graph),
    Check("selection_uses_the_live_maximum", "the choice is made from the current web", _selection_uses_the_live_maximum),
    Check("trajectory_never_rises", "tension is monotone", _the_trajectory_never_rises),
    Check("a_tie_is_recorded", "an arbitrary choice is visible", _a_tie_is_recorded),
    Check("mutual_counted_once", "two edges, one conflict", _a_mutual_conflict_is_counted_once),
    Check("grounding_recorded_pre_action", "the capitulation record describes the choice", _grounding_is_recorded_before_the_action),
    Check("negative_web_left_alone", "no conflict, no action", _a_negative_web_is_left_alone),
)


def _failures(runner: Runner) -> list[str]:
    caught = []
    for check in CHECKS:
        try:
            check.run(runner)
        except Exception:
            caught.append(check.name)
    return caught


# --- the battery -------------------------------------------------------------

def test_every_check_passes_on_the_real_mechanism() -> None:
    """A check that fires on everything catches nothing."""
    assert _failures(_real_runner) == []


@pytest.mark.parametrize("name", sorted(CATALOGUE))
def test_every_mutant_is_a_working_mechanism(name: str) -> None:
    """A mutant that merely crashes proves nothing about the suite.

    Experiment 2's `test_stipulated_build_ceilings_on_the_development_fixture`
    made the same argument: the control has to be a working detector, or its
    failure means only that it is broken.
    """
    result, _ = _mutant_runner(name)("multi_conflict_web", 4)
    assert isinstance(result, LoopResult)
    assert result.trajectory, f"{name} produced no trajectory at all"
    if name not in {"derived_carrier"}:
        assert result.steps, f"{name} never acted, so it cannot be compared with anything"


@pytest.mark.parametrize("name", sorted(set(CATALOGUE) - set(EXPECTED_EQUIVALENT)))
def test_every_mutant_is_caught_by_at_least_one_check(name: str) -> None:
    """The battery's headline. A mutant nothing catches is a hole in the suite."""
    runner = _mutant_runner(name)
    try:
        caught = _failures(runner)
    except Exception as exc:  # a mutant that cannot run at all is caught trivially
        caught = [f"crashed: {type(exc).__name__}"]
    assert caught, (
        f"mutant {name!r} reproduces {CATALOGUE[name].defect!r} and **no check catches it**. "
        f"That is a gap in the suite, not a passing test"
    )


@pytest.mark.parametrize("name", sorted(EXPECTED_EQUIVALENT))
def test_an_equivalent_mutant_is_equivalent_for_the_stated_reason(name: str) -> None:
    """Some mutants cannot be caught because they cannot differ.

    `SaturatedSelector` ranks by `1 - exp(-raw/tau)` instead of by raw tension.
    The transform is strictly monotone, so it cannot reorder anything, and the
    mutant is behaviourally identical. That is a finding rather than a hole:
    **requirements section 12's ban on reading `magnitude` binds on analysis,
    where deltas are compared against a saturation baseline, and not on control,
    where only the ordering matters.**

    Asserted rather than assumed, because if the transform ever stops being
    monotone this becomes a real defect and the reasoning above stops holding.
    """
    real, _ = _real_runner("multi_conflict_web", 8)
    mutated, _ = _mutant_runner(name)("multi_conflict_web", 8)
    assert real.trajectory == mutated.trajectory, EXPECTED_EQUIVALENT[name]
    assert _failures(_mutant_runner(name)) == [], (
        f"{name} was expected to be behaviourally equivalent but a check caught it; "
        f"the reasoning in EXPECTED_EQUIVALENT no longer holds"
    )


def test_the_catalogue_covers_every_historical_defect_family() -> None:
    """The catalogue cannot quietly shrink.

    Each family below cost this project a real retraction or a real rebuild. If a
    mutant is deleted, this fails and whoever deleted it has to say why the
    family no longer needs covering.
    """
    families = {mutant.defect for mutant in CATALOGUE.values()}
    required = {
        "exp1 #5",  # a mechanism that cannot change its output
        "exp1 #3",  # a truncation read as a curve
        "exp3 section 3.3",  # saturated magnitude read as dynamics
        "exp3 section 3.5",  # structure that is not there
        "exp3 section 1",  # building the result instead of measuring it
        "requirements section 11",  # tension reduction that is not truth-tracking
    }
    for marker in required:
        assert any(marker in family for family in families), f"no mutant covers {marker!r}"


#: Checks no mutant can trip, with the reason. A check that is idle for a
#: *known* reason is different from one that is idle because nothing exercises
#: it, and collapsing the two would let real gaps hide behind a green counter.
UNREACHABLE_BY_MUTATION: dict[str, str] = {
    "trajectory_never_rises": (
        "No action available to the loop can raise tension. Its only move is "
        "`assert_contradiction`, which lowers a target's confidence and never raises it, and "
        "`_leaf_conflicts` cannot shrink. Relief exists but fires only when a contradictor is "
        "retracted, which drives that contradictor's stake toward zero and so lowers `min(...)` "
        "further. Monotonicity is a property of the substrate rather than of the loop — which is "
        "also why `TerminationReason` has no `OSCILLATING` value."
    ),
}


def test_each_check_is_load_bearing() -> None:
    """No check is dead weight: every one catches a mutant, or says why it cannot.

    A check that no mutant trips is either testing nothing or testing something
    the battery cannot reach. The two are very different and the distinction has
    to be explicit, so an idle check must be listed in `UNREACHABLE_BY_MUTATION`
    with a reason — and a check that stops being idle fails here too, because
    the reason has then stopped being true.
    """
    caught_by: dict[str, list[str]] = {check.name: [] for check in CHECKS}
    for name in sorted(set(CATALOGUE) - set(EXPECTED_EQUIVALENT)):
        for check_name in _failures(_mutant_runner(name)):
            caught_by[check_name].append(name)

    idle = {name for name, mutants in caught_by.items() if not mutants}
    unexplained = sorted(idle - set(UNREACHABLE_BY_MUTATION))
    assert not unexplained, f"these checks catch no mutant and have no recorded reason: {unexplained}"

    stale = sorted(set(UNREACHABLE_BY_MUTATION) - idle)
    assert not stale, (
        f"these checks are documented as untrippable but a mutant tripped them: {stale}. "
        f"The recorded reason no longer holds"
    )


def test_the_untrippable_check_is_untrippable_for_the_stated_reason() -> None:
    """`trajectory_never_rises` is idle because monotonicity is structural.

    Asserted rather than argued: across every frozen web and every arm, no
    target's confidence ever rises. If an action is added that can raise one,
    this fails, the reason in `UNREACHABLE_BY_MUTATION` stops applying, and
    `TerminationReason` needs an oscillating state after all.
    """
    for fixture in sorted(CATALOGUE) and ("hub_web", "mutual_contradiction", "multi_conflict_web"):
        for arm in (Arm.DRIVEN, Arm.INVERTED):
            core, _ = _core(fixture)
            before = {b.belief_id: b.confidence for b in core.store.list_beliefs(AGENT)}
            AttentionLoop(core, arm=arm, agent_id=AGENT).run(max_iterations=8)
            after = {b.belief_id: b.confidence for b in core.store.list_beliefs(AGENT)}
            risen = {bid: (before[bid], after[bid]) for bid in before if after[bid] > before[bid] + 1e-9}
            assert not risen, f"{fixture}/{arm.value}: confidence rose for {risen}"
