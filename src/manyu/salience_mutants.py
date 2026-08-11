"""Deliberately broken couplings, each reproducing a defect that really happened.

**Why this exists.** Experiment 3 shipped sixteen defects and its own test suite
caught none of them. The cause was structural rather than careless: each test
was written minutes after the mechanism it covered, by the author who had just
written it, so it agreed with the code precisely where the code was wrong. A
suite in that condition looks exactly like a suite that works.

The only way to tell the two apart is to break the mechanism on purpose and
check that something goes red. Every mutant below is a *historical* defect
family, not an invented one, so what the battery demonstrates is coverage of the
failures this project actually has — and a mutant nothing catches is a hole in
the suite, reported as such rather than discovered in a retrospective.

Experiment 2 made the same move with `StipulatedDissonanceQuery` and
`ValenceOnlyDissonanceQuery`, which is why these live in a production module
rather than in the tests.

**Injected, never patched.** Each mutant is a `Selector` or a `AttentionLoop`
subclass, installed through a constructor parameter. Monkeypatching a module
attribute does not reach a caller that did `from module import name`, so a
patch-based battery reports mutants as caught when they were never installed —
observed while validating the substrate tests, and the reason for the design.

**A mutant must be a working mechanism.** One that merely crashes proves nothing
about the suite, so the battery asserts each still runs on the development
fixture before asking whether it is caught.
"""

from __future__ import annotations

import math
from typing import Any

from manyu.architecture import ArchConfig
from manyu.salience import (
    Arm,
    AttentionLoop,
    AttentionStep,
    LoopResult,
    Selector,
    TensionView,
    TerminationReason,
)

# --- selector mutants --------------------------------------------------------


class NoOpSelector:
    """Ignores the view entirely and always returns the same thing.

    **Experiment 1 failure mode #5.** `rank_causes`' mood branch applied the same
    multiplier to every cause, and sorting is invariant to uniform scaling, so it
    could not reorder anything on any probed target. It survived several versions
    looking like a mechanism. `gate.assert_not_noop` exists because of it.
    """

    name = "no_op"
    defect = "exp1 #5 — a mechanism whose output cannot depend on its input"

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = sorted(conflict for conflict in view.conflicts if conflict not in inert)
        return live[0] if live else None


class SaturatedSelector:
    """Ranks by the concave magnitude transform instead of by raw tension.

    **Experiment 3 retrospective section 3.3.** `magnitude` is
    `1 - exp(-raw/tau)`, so the same raw change reads larger from a lower
    baseline and a delta confounds how much tension changed with where on the
    curve the web sat. Requirements section 12 forbids reading it.

    Retained even though it is expected to be **behaviourally equivalent** for
    selection, because that equivalence is worth pinning: the transform is
    strictly monotone, so it cannot reorder anything. The section 12 constraint
    therefore binds on *analysis*, where deltas are compared, and not on
    *control*, where only the ranking matters. A battery that quietly dropped
    this mutant would lose the distinction.
    """

    name = "saturated"
    defect = "exp3 section 3.3 — saturated magnitude read as belief dynamics"

    def __init__(self, tau: float | None = None):
        self.tau = tau if tau is not None else ArchConfig().dissonance_tau

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = [conflict for conflict in view.conflicts if conflict not in inert]
        if not live:
            return None
        return max(live, key=lambda c: (1.0 - math.exp(-view.tension_of(c) / self.tau), c))


class GreedyCheapestSelector:
    """Attends to whichever conflict is cheapest to quieten.

    The motivated-reasoning mutant requirements section 11 is about: a system
    that reduces its own discomfort by going after whatever yields most relief
    per unit of effort, rather than whatever is most wrong. Ranks by *lowest*
    tension on the reasoning that a thinly-staked conflict is closest to silent.
    """

    name = "greedy_cheapest"
    defect = "requirements section 11 — tension reduction that is not truth-tracking"

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = [conflict for conflict in view.conflicts if conflict not in inert]
        if not live:
            return None
        return min(live, key=lambda c: (view.tension_of(c), c))


class DerivedCarrierSelector:
    """Selects from every implicated pair, including ones reached by traversal.

    A pair reached through `supports` carries real tension and has **no edge
    beneath it**, so there is nothing to price. Acting on one is acting on a
    conflict that does not exist — the shape of experiment 3's `supports` field
    that was present, unreachable, and silently empty.
    """

    name = "derived_carrier"
    defect = "exp3 section 3.5 — acting on structure that is not there"

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = [pair for pair in view.implicated if pair not in inert]
        if not live:
            return None
        return max(live, key=lambda pair: (pair not in view.conflicts, pair))


class StaleViewSelector:
    """Decides from the first view it ever saw, ignoring every later one.

    Carriers computed before a revision name a state that no longer holds. The
    loop re-reads the signal each iteration precisely so this cannot happen; the
    mutant keeps the first reading and shows what it would cost.
    """

    name = "stale_view"
    defect = "acting on carriers computed before the revision"

    def __init__(self) -> None:
        self._first: TensionView | None = None

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        if self._first is None:
            self._first = view
        live = [conflict for conflict in self._first.conflicts if conflict not in inert]
        if not live:
            return None
        return max(live, key=lambda c: (self._first.tension_of(c), c))  # type: ignore[union-attr]


# --- loop mutants ------------------------------------------------------------


class TruncatingLoop(AttentionLoop):
    """Reports a spent budget as a settled web.

    **Experiment 1 failure mode #3**, a truncation constant read as a curve. Here
    it is a loop that ran out of attention being written up as one that finished.
    """

    name = "truncating"
    defect = "exp1 #3 — a truncation reported as a convergence"

    def run(self, *, max_iterations: int) -> LoopResult:
        result = super().run(max_iterations=max_iterations)
        if result.termination is TerminationReason.BOUND_REACHED:
            return LoopResult(
                arm=result.arm,
                max_iterations=result.max_iterations,
                steps=result.steps,
                trajectory=result.trajectory,
                termination=TerminationReason.EXHAUSTED,
                inert=result.inert,
            )
        return result


class RepeatingLoop(AttentionLoop):
    """Never excludes what it has already attended to.

    **The defect this loop was actually built with.** Pricing is idempotent and
    tension falls by exactly what was charged, so the conflict just handled is
    frequently still the highest — and the loop re-selected it, spending half of
    every budget on `already_priced` no-ops. Because the budget is Stage 2's
    independent variable, an arm comparison under a tight bound would have been
    measuring the waste rather than the selection.
    """

    name = "repeating"
    defect = "the shipped-then-fixed defect — budget spent re-attending handled conflicts"

    def run(self, *, max_iterations: int) -> LoopResult:
        from manyu.dissonance import stake_of

        steps: list[AttentionStep] = []
        inert: set[tuple[str, str]] = set()
        trajectory: list[float] = []
        termination = TerminationReason.BOUND_REACHED

        for iteration in range(max_iterations):
            reading = self._read()
            if reading is None:
                trajectory.append(0.0)
                termination = TerminationReason.NO_SIGNAL if not steps else TerminationReason.EXHAUSTED
                break
            trajectory.append(reading.magnitude_raw)

            # The defect: `inert` rather than everything attended.
            conflict = self.selector.select(reading.view, frozenset(inert))
            if conflict is None:
                termination = TerminationReason.NO_SIGNAL if not steps else TerminationReason.EXHAUSTED
                break

            selected_tension = reading.view.tension_of(conflict)
            contradictor_id, target_id, direction = self._direction(conflict)
            contradictor = self.core.store.get_belief(contradictor_id)
            target = self.core.store.get_belief(target_id)
            before = target.confidence
            result = self.core.assert_contradiction(
                {"agent_id": self.agent_id, "contradictor_id": contradictor_id, "target_id": target_id, "arm": "direct"}
            )
            after = self.core.store.get_belief(target_id).confidence
            moved = round(before - after, 6)
            steps.append(
                AttentionStep(
                    iteration=iteration,
                    conflict=conflict,
                    contradictor_id=contradictor_id,
                    target_id=target_id,
                    direction=direction,
                    tension_before=selected_tension,
                    raw_before=reading.magnitude_raw,
                    tied_with=1,
                    best_available_tension=selected_tension,
                    outcome=str(result.get("outcome", "unknown")),
                    moved=moved,
                    target_evidence_count=len(target.evidence_ids),
                    target_stake=round(stake_of(self.core.store, target), 6),
                    contradictor_evidence_count=len(contradictor.evidence_ids),
                    contradictor_stake=round(stake_of(self.core.store, contradictor), 6),
                )
            )
            if moved <= 0.0:
                inert.add(conflict)

        reading = self._read()
        trajectory.append(0.0 if reading is None else reading.magnitude_raw)
        return LoopResult(
            arm=self.arm,
            max_iterations=max_iterations,
            steps=tuple(steps),
            trajectory=tuple(trajectory[: len(steps) + 1]),
            termination=termination,
            inert=tuple(sorted(inert)),
        )


class ChosenDirectionLoop(AttentionLoop):
    """Charges whichever side is weaker, instead of the direction the graph declares.

    **The trap this whole experiment is built to avoid.** Choosing to weaken the
    lower-staked party *builds* the motivated-reasoning result rather than
    measuring it — experiment 3 section 1, where the answer followed from a
    design decision and the alternative was never available to observe. Which
    belief pays must be a property of the web.
    """

    name = "chosen_direction"
    defect = "exp3 section 1 — building the result instead of measuring it"

    def _direction(self, conflict: tuple[str, str]) -> tuple[str, str, str]:
        from manyu.dissonance import stake_of

        left, right = conflict
        stakes = {bid: stake_of(self.core.store, self.core.store.get_belief(bid)) for bid in (left, right)}
        target = min(stakes, key=lambda bid: (stakes[bid], bid))
        contradictor = right if target == left else left
        return contradictor, target, "declared"


class PostActionRecordLoop(AttentionLoop):
    """Records the capitulation evidence *after* charging, not before.

    **Experiment 1 failure mode #6 in a new place.** `seed_mood` set the
    projections and left the structure the consumer actually reads at its
    default, so four very different moods produced byte-identical appraisals —
    the summary looked populated while the substance was blank. Here the same
    shape: grounding and stake both move the instant the charge lands, so a
    record taken afterwards describes the *consequence* of the choice while
    appearing to describe the choice.
    """

    name = "post_action_record"
    defect = "exp1 #6 — a record that describes something other than what it names"

    def run(self, *, max_iterations: int) -> LoopResult:
        result = super().run(max_iterations=max_iterations)
        from manyu.dissonance import stake_of

        rewritten = []
        for step in result.steps:
            target = self.core.store.get_belief(step.target_id)
            contradictor = self.core.store.get_belief(step.contradictor_id)
            rewritten.append(
                AttentionStep(
                    **{
                        **{field: getattr(step, field) for field in step.__dataclass_fields__},
                        "target_evidence_count": len(target.evidence_ids) + 1,
                        "target_stake": round(stake_of(self.core.store, target), 6),
                        "contradictor_evidence_count": len(contradictor.evidence_ids),
                        "contradictor_stake": round(stake_of(self.core.store, contradictor), 6),
                    }
                )
            )
        return LoopResult(
            arm=result.arm,
            max_iterations=result.max_iterations,
            steps=tuple(rewritten),
            trajectory=result.trajectory,
            termination=result.termination,
            inert=result.inert,
        )


class PhantomConflictLoop(AttentionLoop):
    """Acts on a web that holds no conflict at all.

    **Experiment 2's `ValenceOnlyDissonanceQuery` family** — a detector that
    fires on the negative control. Its specificity result would have read 2/2
    while it was keying on valence difference rather than on any edge. Here the
    loop treats an absent signal as licence to act on whatever two beliefs are
    at hand.
    """

    name = "phantom_conflict"
    defect = "exp2 near_miss — firing where no conflict exists"

    def _read(self):
        reading = super()._read()
        if reading is not None:
            return reading
        from manyu.schemas import DissonanceCarrier

        from manyu.salience import TensionReading

        beliefs = sorted(
            self.core.store.list_beliefs(self.agent_id), key=lambda belief: belief.belief_id
        )
        if len(beliefs) < 2:
            return None
        left, right = beliefs[0], beliefs[1]
        return TensionReading(
            agent_id=self.agent_id,
            magnitude_raw=0.5,
            magnitude=0.5,
            saturation_baseline=0.0,
            carriers=(
                DissonanceCarrier(belief_id_a=left.belief_id, belief_id_b=right.belief_id, path=[], tension=0.5),
            ),
        )

    def _direction(self, conflict: tuple[str, str]) -> tuple[str, str, str]:
        try:
            return super()._direction(conflict)
        except ValueError:
            left, right = conflict
            return left, right, "declared"


#: Every mutant, with the historical defect it reproduces. The battery asserts
#: this catalogue covers each named family, so it cannot quietly shrink.
CATALOGUE: dict[str, Any] = {
    NoOpSelector.name: NoOpSelector,
    SaturatedSelector.name: SaturatedSelector,
    GreedyCheapestSelector.name: GreedyCheapestSelector,
    DerivedCarrierSelector.name: DerivedCarrierSelector,
    StaleViewSelector.name: StaleViewSelector,
    TruncatingLoop.name: TruncatingLoop,
    RepeatingLoop.name: RepeatingLoop,
    ChosenDirectionLoop.name: ChosenDirectionLoop,
    PostActionRecordLoop.name: PostActionRecordLoop,
    PhantomConflictLoop.name: PhantomConflictLoop,
}

#: Mutants expected to be behaviourally *equivalent* to the real mechanism, with
#: the reason. A battery that treated these as holes would be wrong, and one that
#: dropped them would lose the finding.
EXPECTED_EQUIVALENT: dict[str, str] = {
    SaturatedSelector.name: (
        "the saturation transform is strictly monotone, so it cannot reorder a ranking. "
        "Requirements section 12 therefore binds on analysis, where deltas are compared, "
        "and not on control, where only the ordering matters."
    ),
}


def build(name: str, core: Any, *, agent_id: str, arm: Arm = Arm.DRIVEN) -> AttentionLoop:
    """Install a mutant, whether it replaces the selector or the loop."""
    mutant = CATALOGUE[name]
    if isinstance(mutant, type) and issubclass(mutant, AttentionLoop):
        return mutant(core, arm=arm, agent_id=agent_id)
    selector: Selector = mutant()
    return AttentionLoop(core, arm=arm, agent_id=agent_id, selector=selector)
