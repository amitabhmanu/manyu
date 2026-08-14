"""Experiment 4 section 5.5 — loop semantics, termination, and the arm controls.

The loop is where a truncation could be reported as a convergence, where an arm
could be stored and never consulted, and where a "driven" mechanism could quietly
consult randomness and beat its own control. All three have happened before, in
this codebase, and none was caught by the suite that covered the code.

Entirely offline and deterministic under `FrozenClock`. No provider is
constructed anywhere in this file.
"""

from __future__ import annotations

import pytest

from manyu.core import ManyuCore
from manyu.fork import BeliefSpec, seed_beliefs
from manyu.salience import (
    Arm,
    AttentionLoop,
    CarrierDrivenSelector,
    InvertedSelector,
    TensionView,
    TerminationReason,
    load_web,
    selector_for,
    web_specs,
)

AGENT = "agent_demo"

# Trials for `test_a_tie_is_recorded_rather_than_silently_broken`, whose assertion is
# statistical rather than exact. The tie-break is a fair coin between two outcomes, so
# the test raises a false failure with probability 2 ** (1 - TIE_BREAK_TRIALS). At the
# original 6 that was 3.1%, roughly one full-suite run in 32; at 24 it is 1.2e-7. The
# trials are cheap (0.14s for all 24) and the reasoning is in the test's docstring.
TIE_BREAK_TRIALS = 24


def _core(name: str) -> tuple[ManyuCore, dict[str, str], dict[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, web_specs(load_web(name)))
    return core, ids, {bid: key for key, bid in ids.items()}


def _run(name: str, arm: Arm, bound: int, seed: int | None = None):
    core, ids, reverse = _core(name)
    result = AttentionLoop(core, arm=arm, agent_id=AGENT, seed=seed).run(max_iterations=bound)
    return result, reverse


# --- termination -------------------------------------------------------------

def test_every_termination_reason_is_reachable() -> None:
    """A reason that cannot occur is decoration.

    `TerminationReason` deliberately has no `OSCILLATING`: pricing only lowers
    confidence and nothing in the loop raises it, so the trajectory is monotone
    and thrashing is unrepresentable. Rather than ship an enum value that could
    never be returned, the absence is asserted in
    `test_the_trajectory_never_rises` below.
    """
    seen = {
        _run("no_conflict_web", Arm.DRIVEN, 4)[0].termination,
        _run("multi_conflict_web", Arm.DRIVEN, 1)[0].termination,
        _run("multi_conflict_web", Arm.DRIVEN, 8)[0].termination,
    }
    assert seen == set(TerminationReason), f"unreachable reasons: {set(TerminationReason) - seen}"


def test_bound_reached_is_never_reported_as_exhausted() -> None:
    """The confound that turns a truncation into a convergence claim.

    Experiment 1's failure mode #3 was a truncation constant read as a flat
    curve; the same shape here would be a loop that ran out of budget being
    written up as a web that settled.
    """
    truncated, _ = _run("multi_conflict_web", Arm.DRIVEN, 1)
    assert truncated.termination is TerminationReason.BOUND_REACHED
    assert len(truncated.steps) == truncated.max_iterations

    finished, _ = _run("multi_conflict_web", Arm.DRIVEN, 8)
    assert finished.termination is TerminationReason.EXHAUSTED
    assert len(finished.steps) < finished.max_iterations, (
        "exhausted was reported while the budget was fully spent, so it is indistinguishable from truncation"
    )


def test_a_web_with_no_conflict_terminates_without_acting() -> None:
    result, _ = _run("no_conflict_web", Arm.DRIVEN, 4)
    assert result.termination is TerminationReason.NO_SIGNAL
    assert result.steps == ()
    assert result.total_movement == 0.0


def test_the_trajectory_never_rises() -> None:
    """Monotonicity, which is why there is no oscillating state to report."""
    for name in ("multi_conflict_web", "adversarial_grounding", "mutual_contradiction", "tied_tension_web"):
        result, _ = _run(name, Arm.DRIVEN, 8)
        pairs = list(zip(result.trajectory, result.trajectory[1:]))
        assert all(later <= earlier + 1e-9 for earlier, later in pairs), f"{name}: tension rose — {result.trajectory}"


def test_the_trajectory_has_one_more_entry_than_steps() -> None:
    """So a reader can see the state before the first act and after the last
    without re-deriving either.
    """
    for bound in (1, 2, 8):
        result, _ = _run("multi_conflict_web", Arm.DRIVEN, bound)
        assert len(result.trajectory) == len(result.steps) + 1, result.trajectory


def test_a_non_positive_budget_is_refused() -> None:
    core, _, _ = _core("multi_conflict_web")
    loop = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT)
    for bound in (0, -1):
        with pytest.raises(ValueError):
            loop.run(max_iterations=bound)


# --- the loop spends its budget on real work ---------------------------------

def test_no_step_is_spent_re_attending_a_handled_conflict() -> None:
    """The defect this loop was built with, pinned so it cannot return.

    Pricing is idempotent, and tension falls by exactly what was charged, so the
    conflict just handled is frequently still the highest. The first version
    re-selected it and burnt **half of every budget** on `already_priced`
    no-ops. Since the budget is Stage 2's independent variable, an arm
    comparison under a tight bound would have been measuring the waste.
    """
    result, _ = _run("multi_conflict_web", Arm.DRIVEN, 8)
    attended = result.attended
    assert len(attended) == len(set(attended)), f"a conflict was attended twice: {attended}"
    assert all(step.outcome != "already_priced" for step in result.steps), (
        f"a step was spent on a no-op: {[s.outcome for s in result.steps]}"
    )


def test_every_step_moves_something_on_an_unpriced_web() -> None:
    """Fixtures are seeded through `fork.seed_beliefs`, which bypasses the
    updater and therefore leaves contradictions unpriced. So every conflict has
    a real charge available and `inert` should stay empty — if it does not, the
    seeding path has changed and the starting state is no longer the fixture's.
    """
    result, _ = _run("multi_conflict_web", Arm.DRIVEN, 8)
    assert result.inert == (), f"conflicts were already priced before the loop began: {result.inert}"
    assert all(step.moved > 0.0 for step in result.steps)


# --- the arms are genuinely different ----------------------------------------

@pytest.mark.parametrize("bound", [1, 2])
def test_driven_beats_inverted_while_attention_is_scarce(bound: int) -> None:
    """The efficacy comparison, at the only budgets where it can exist.

    `inverted` performs the same actions in the worst order tension recommends,
    so a driven arm that does no better is not using the signal.
    """
    driven, _ = _run("multi_conflict_web", Arm.DRIVEN, bound)
    inverted, _ = _run("multi_conflict_web", Arm.INVERTED, bound)
    assert driven.trajectory[-1] < inverted.trajectory[-1], (
        f"bound={bound}: driven left {driven.trajectory[-1]}, inverted left {inverted.trajectory[-1]}"
    )


def test_the_arms_converge_once_the_budget_covers_every_conflict() -> None:
    """The finding that qualifies the efficacy result, pinned as a test.

    Attention order cannot matter once there is enough attention to reach
    everything, because the actions are idempotent and their total is
    order-independent. **The signal's value is entirely a function of scarcity**
    — with an unbounded budget, dissonance-as-control does nothing at all.

    If this ever stops holding, some action has acquired an order-dependence and
    the efficacy result means something different.
    """
    finals = {
        arm: _run("multi_conflict_web", arm, 8, seed=0)[0].trajectory[-1]
        for arm in (Arm.DRIVEN, Arm.INVERTED, Arm.RANDOM_MATCHED)
    }
    assert len(set(finals.values())) == 1, f"the arms disagree at an unbounded budget: {finals}"


def test_random_is_bracketed_by_driven_and_inverted() -> None:
    """Sanity on the null: a uniform draw cannot beat the best ordering or lose
    to the worst. If it does, the orderings are not what they claim.
    """
    driven, _ = _run("multi_conflict_web", Arm.DRIVEN, 2)
    inverted, _ = _run("multi_conflict_web", Arm.INVERTED, 2)
    for seed in range(20):
        drawn, _ = _run("multi_conflict_web", Arm.RANDOM_MATCHED, 2, seed=seed)
        assert driven.trajectory[-1] - 1e-9 <= drawn.trajectory[-1] <= inverted.trajectory[-1] + 1e-9, (
            f"seed {seed}: random left {drawn.trajectory[-1]}, outside "
            f"[{driven.trajectory[-1]}, {inverted.trajectory[-1]}]"
        )


def test_the_driven_arm_never_consults_randomness() -> None:
    """A driven arm that quietly randomised would beat its own control for the
    wrong reason. Asserted two ways: the selector holds no RNG, and the result
    is identical whatever seed is offered.
    """
    selector = selector_for(Arm.DRIVEN)
    assert not any("rng" in name.lower() or "random" in name.lower() for name in vars(selector)), vars(selector)

    baseline, base_reverse = _run("multi_conflict_web", Arm.DRIVEN, 2)
    chosen = [base_reverse[s.target_id] for s in baseline.steps]
    for seed in (0, 1, 99):
        other, reverse = _run("multi_conflict_web", Arm.DRIVEN, 2, seed=seed)
        assert other.trajectory == baseline.trajectory
        # Compared by `belief_key`, not `belief_id`. Ids are `uuid4` and differ
        # between stores, so an id comparison here would fail for a reason that
        # has nothing to do with randomness in the selector.
        assert [reverse[s.target_id] for s in other.steps] == chosen


def test_the_random_arm_refuses_to_run_without_a_seed() -> None:
    """A run that cannot be reproduced from its own record is not evidence."""
    with pytest.raises(ValueError, match="seed"):
        selector_for(Arm.RANDOM_MATCHED)


def test_no_arm_is_the_default() -> None:
    """Experiment 3 section 13's rule, as a property of the signature."""
    import inspect

    parameters = inspect.signature(AttentionLoop.__init__).parameters
    assert parameters["arm"].default is inspect.Parameter.empty
    assert parameters["arm"].kind is inspect.Parameter.KEYWORD_ONLY


# --- direction is read off the graph, not chosen -----------------------------

def test_the_charged_direction_is_the_one_the_graph_declares() -> None:
    """The loop must not choose which belief pays.

    Charging whichever side is weaker would *build* the motivated-reasoning
    result rather than measure it — experiment 3 section 1 in a new place. Which
    belief pays is a property of the web; which conflict gets attention is the
    only thing under test.
    """
    for name in ("adversarial_grounding", "aligned_grounding"):
        result, reverse = _run(name, Arm.DRIVEN, 4)
        fixture = load_web(name)
        declared = {(pair["contradictor"], pair["target"]) for pair in fixture["contradictions"]}
        for step in result.steps:
            assert step.direction == "declared"
            assert (reverse[step.contradictor_id], reverse[step.target_id]) in declared, (
                f"{name}: charged {reverse[step.contradictor_id]} -> {reverse[step.target_id]}, "
                f"which the fixture never declared"
            )


def test_a_mutual_conflict_is_labelled_rather_than_silently_broken() -> None:
    """Both directions declared means no declared direction. The tie is broken
    deterministically and *recorded*, so analysis can exclude mutual cases
    instead of discovering them in the residuals — experiment 3 found mutual
    contradictions priced by extractor emission order, in pre-flight rather than
    in its suite.
    """
    result, _ = _run("mutual_contradiction", Arm.DRIVEN, 4)
    assert result.steps
    assert all(step.direction == "mutual" for step in result.steps)

    repeated, _ = _run("mutual_contradiction", Arm.DRIVEN, 4)
    assert [s.direction for s in repeated.steps] == [s.direction for s in result.steps]


# --- the capitulation record -------------------------------------------------

def test_the_minimal_pair_differs_only_in_who_pays_and_how_much() -> None:
    """The Stage 4 measurement, available offline and deterministically.

    The two webs are indistinguishable in the signal channel — identical raw
    tension, identical carriers — so the loop makes the same decision on both.
    What differs is the consequence, and the direction of the difference is the
    result.
    """
    adversarial, adv_reverse = _run("adversarial_grounding", Arm.DRIVEN, 4)
    aligned, ali_reverse = _run("aligned_grounding", Arm.DRIVEN, 4)

    assert adversarial.steps[0].tension_before == pytest.approx(aligned.steps[0].tension_before), (
        "the pair is no longer minimal in the signal channel"
    )
    assert adversarial.weakened_the_better_grounded_side == (True,)
    assert aligned.weakened_the_better_grounded_side == (False,)


def test_the_capitulation_record_is_taken_before_the_action() -> None:
    """Grounding and stake both change the moment the charge lands, so a record
    taken afterwards would describe the consequence rather than the choice.
    """
    core, ids, _ = _core("adversarial_grounding")
    before = {key: core.store.get_belief(bid).confidence for key, bid in ids.items()}
    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=2)

    step = result.steps[0]
    target_key = next(key for key, bid in ids.items() if bid == step.target_id)
    stake_now = core.store.get_belief(step.target_id).confidence
    assert stake_now < before[target_key], "the action did not move the target at all"
    assert step.target_stake > 0.0
    assert step.target_stake == pytest.approx(
        before[target_key] * load_web("adversarial_grounding")["beliefs"][0]["salience"], abs=1e-6
    ), "the recorded stake is not the pre-action value"


# --- what the selector can see -----------------------------------------------

def test_a_selector_cannot_reach_the_saturated_channel() -> None:
    """Requirements section 12 as a property of the types rather than a promise.

    Experiment 2 learned this exact lesson: `SplitDissonanceAppraiser` originally
    took the store and merely declined to use it, and the steelman test correctly
    called that the implementer's restraint rather than the architecture's.
    """
    fields = set(TensionView.__dataclass_fields__)
    assert "magnitude" not in fields, "the loop can see the saturated channel"
    assert "saturation_baseline" not in fields, "the loop can see its position on the curve"
    assert "store" not in fields
    assert fields == {"agent_id", "magnitude_raw", "carriers"}, fields


def test_derived_carriers_are_reported_but_not_selectable() -> None:
    """A pair reached through `supports` is real tension with no edge beneath it,
    so there is nothing to price. It must appear in `implicated` and not in
    `conflicts`, or the loop would try to act on a conflict that does not exist.
    """
    core, ids, _ = _core("depth_carrier_web")
    from manyu.dissonance import MergedDissonanceQuery
    from manyu.salience import reading_of

    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "loop"), agent_id=AGENT)
    assert reading is not None
    view = reading.view

    assert len(view.implicated) > len(view.conflicts), "the fixture produced no derived carrier"
    assert len(view.conflicts) == 1
    for conflict in view.conflicts:
        view.tension_of(conflict)  # must not raise
    derived = set(view.implicated) - set(view.conflicts)
    for pair in derived:
        with pytest.raises(KeyError):
            view.tension_of(pair)


def test_a_tie_is_recorded_rather_than_silently_broken() -> None:
    """A real defect, found by this test and fixed by making it visible.

    On `tied_tension_web` the two conflicts carry byte-identical tension, so the
    selector falls through to its tie-break — `sorted(belief_id)`. Belief ids are
    `uuid4`, so **the winner changed between runs**: an ordering that looked
    deterministic and was actually random. Exactly the family every experiment-3
    defect belonged to, a quantity that looked right and meant something else.

    The fix is not to fake a stability the substrate cannot provide. Insertion
    order would be worse (it correlates with fixture authoring), and a
    content-derived key is not reachable from a `TensionView`, which sees only
    ids. So the arbitrary choice is *recorded*, and the methodology consequence
    is carried on the result: arms may not be compared across separately-seeded
    stores on a web where `had_arbitrary_choice` is true.

    **On the trial count, which is load-bearing — do not trim it.** This assertion
    is statistical: the tie-break is a fair coin between two outcomes (measured
    52/48 over 400 trials), so `len(picks) > 1` fails whenever every trial lands
    the same way, with probability `2 ** (1 - TIE_BREAK_TRIALS)`.

        6 trials  -> 3.1%    ~1 full-suite run in 32 fails for no reason
        12 trials -> 0.05%
        24 trials -> 0.00001%

    It ran at 6 and duly failed a full run, which read as an order-dependent flake
    and is nothing of the kind — the suite has no randomising plugin and this test
    shares no state with any other. It was simply underpowered: six flips is not
    enough evidence for "this is not always the same". 24 trials cost 0.14s, so
    the power is bought for nothing.
    """
    picks = set()
    for _ in range(TIE_BREAK_TRIALS):
        core, _, reverse = _core("tied_tension_web")
        result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=1)
        step = result.steps[0]
        assert step.tied_with == 2, f"the tie was not detected: tied_with={step.tied_with}"
        assert result.had_arbitrary_choice is True
        picks.add(tuple(sorted(reverse[b] for b in step.conflict)))

    assert len(picks) > 1, (
        f"the tie broke the same way {TIE_BREAK_TRIALS} times over. At this trial count that "
        f"happens by chance about once in {2 ** (TIE_BREAK_TRIALS - 1):,} runs, so it is far "
        "likelier that the fixture no longer ties or that belief ids have become "
        "deterministic. Both change what this test is documenting"
    )


def test_a_distinct_tension_web_reports_no_arbitrary_choice() -> None:
    """The converse, and the precondition for every Stage 2 comparison.

    If this fails, the arms are being compared on a web where the winner is
    partly decided by `uuid4`.
    """
    for arm in (Arm.DRIVEN, Arm.INVERTED):
        result, _ = _run("multi_conflict_web", arm, 8)
        assert result.had_arbitrary_choice is False, (
            f"{arm.value}: selection was tied on a web whose tensions are supposed to be distinct — "
            f"{[(s.tension_before, s.tied_with) for s in result.steps]}"
        )
        assert all(step.tied_with == 1 for step in result.steps)


def test_both_orderings_agree_when_only_one_conflict_exists() -> None:
    """A single-conflict web cannot discriminate any ordering, so any Stage 2
    claim resting on one is unreadable. Stated as a test rather than left to be
    noticed during analysis.
    """
    driven, _ = _run("adversarial_grounding", Arm.DRIVEN, 4)
    inverted, _ = _run("adversarial_grounding", Arm.INVERTED, 4)
    assert driven.trajectory == inverted.trajectory
    assert [s.direction for s in driven.steps] == [s.direction for s in inverted.steps]


def test_the_two_orderings_really_are_opposites() -> None:
    """Gate #5 on the arms: feed both the same view and require different output.

    `ContradictionArm` was stored, stamped onto every result, and consulted by no
    branch — everything reported "under both arms" was one arm run twice.
    """
    from manyu.dissonance import MergedDissonanceQuery
    from manyu.salience import reading_of

    core, _, _ = _core("multi_conflict_web")
    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "loop"), agent_id=AGENT)
    assert reading is not None
    view = reading.view

    top = CarrierDrivenSelector().select(view, frozenset())
    bottom = InvertedSelector().select(view, frozenset())
    assert top != bottom, "the driven and inverted selectors chose the same conflict"
    assert view.tension_of(top) > view.tension_of(bottom)


# --- adversarial inputs ------------------------------------------------------

def test_an_empty_web_terminates_immediately() -> None:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)
    assert result.termination is TerminationReason.NO_SIGNAL
    assert result.trajectory == (0.0,)


def test_a_single_belief_web_terminates_immediately() -> None:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_beliefs(core, [BeliefSpec(key="only", proposition="Just the one.")])
    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)
    assert result.termination is TerminationReason.NO_SIGNAL


def test_a_cycle_in_supports_terminates() -> None:
    """The graph is not guaranteed acyclic, and the loop walks it every read."""
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_beliefs(
        core,
        [
            BeliefSpec(key="a", proposition="A.", valence=0.6, supports=("b",)),
            BeliefSpec(key="b", proposition="B.", valence=0.6, supports=("a",)),
            BeliefSpec(key="c", proposition="Not A.", valence=-0.6, contradicts=("a",)),
        ],
    )
    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=6)
    assert result.termination is TerminationReason.EXHAUSTED


def test_a_zero_stake_conflict_is_attended_without_moving_anything() -> None:
    """The zero-valued operand case. A belief at confidence 0 carries no stake,
    so the conflict reads zero tension while still being named — the property
    that makes capitulation visible. The loop must handle it rather than divide
    by it.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(
        core,
        [
            BeliefSpec(key="pos", proposition="It holds.", valence=0.6),
            BeliefSpec(key="neg", proposition="It does not hold.", valence=-0.6, contradicts=("pos",)),
        ],
    )
    hollow = core.store.get_belief(ids["neg"])
    core.store.save_belief(hollow.model_copy(update={"confidence": 0.0}))

    result = AttentionLoop(core, arm=Arm.DRIVEN, agent_id=AGENT).run(max_iterations=4)
    assert result.steps, "the conflict was never attended although it is still named"
    assert result.steps[0].tension_before == pytest.approx(0.0)
    assert result.total_movement == pytest.approx(0.0), "a zero-stake contradictor charged something"
