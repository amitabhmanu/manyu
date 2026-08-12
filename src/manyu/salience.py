"""Experiment 4: is dissonance a control signal, or only a readout?

**What this module is not.** It is not an argument that dissonance controls
behaviour. Wiring a branch that reads the signal would settle that by
construction — experiment 3 section 1 in a new place, where the answer follows
from a design decision rather than from an observation. What is measurable is
narrower: whether the signal carries information the existing control inputs do
not, whether acting on it beats acting indiscriminately, and whether the
resulting behaviour tracks truth or merely reduces discomfort.

**What the substrate forces, established before this module existed**
(``tests/test_salience_substrate.py``):

- ``contradicts`` edges are only ever added. ``_leaf_conflicts`` never shrinks,
  so **a conflict can never be retired** and tension can only fall by weakening
  a party.
- ``_tension`` takes ``min(stake_a, stake_b)``, so the only move that changes
  the signal is weakening whichever side is *already weaker*. There is never a
  choice about which side.
- ``stake_of`` averages evidence salience rather than summing it, so **stake is
  blind to how well grounded a belief is.**

Together those mean the substrate has a standing gradient toward exactly the
motivated-reasoning failure this experiment was chartered to look for, and that
"tension fell" is never evidence that anything was resolved. The one thing that
survives is the carrier set: a conflict is still *named* when its tension reads
zero, which is what makes capitulation distinguishable from resolution at all.

Everything here is offline and deterministic. No provider is constructed.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from manyu.schemas import DissonanceCarrier, DissonanceSignal

FIXTURE_DIR = Path("evals/fixtures/exp04")


# --- what the loop is allowed to see -----------------------------------------


@dataclass(frozen=True)
class TensionView:
    """The control loop's entire input. Deliberately not the signal.

    **`magnitude` is absent, and that is the point.** Experiment 3 retrospective
    section 3.3 established that ``DissonanceSignal.magnitude`` is concave in raw
    tension, so the same raw change reads larger from a lower baseline and a
    magnitude delta confounds *how much tension changed* with *where on the
    saturation curve the web was sitting*. Requirements section 12 forbids
    reading it as a measure of belief dynamics.

    A docstring saying "the loop does not use magnitude" is not enough. Experiment
    2 learned that the hard way: ``SplitDissonanceAppraiser`` originally took the
    store and merely *declined* to walk ``supports``, which made the
    architectural claim a property of the implementer's restraint rather than of
    the code, and the steelman test correctly exposed it. So the constraint is a
    type here: a selector handed this cannot reach the saturated channel, cannot
    reach the store, and cannot reach anything else about the agent.

    `saturation_baseline` is deliberately *not* carried either. It is required in
    the analysis record (requirements section 12 says to report it alongside every
    delta) and it would leak curve position into the control path, so it lives on
    `TensionReading` instead.
    """

    agent_id: str
    magnitude_raw: float
    carriers: tuple[DissonanceCarrier, ...]

    @property
    def conflicts(self) -> tuple[tuple[str, str], ...]:
        """The pairs that can actually be acted on: those joined by a stated edge.

        A carrier's `path` is empty exactly when the pair *is* the leaf conflict
        rather than something reached through `supports`. Derived carriers are
        real tension and are reported, but there is no edge under them to price,
        so they are not selectable.
        """
        direct = {
            tuple(sorted((carrier.belief_id_a, carrier.belief_id_b)))
            for carrier in self.carriers
            if not carrier.path
        }
        return tuple(sorted(direct))  # type: ignore[arg-type]

    @property
    def implicated(self) -> tuple[tuple[str, str], ...]:
        """Every pair named at all, derived ones included. For reporting."""
        seen = {tuple(sorted((carrier.belief_id_a, carrier.belief_id_b))) for carrier in self.carriers}
        return tuple(sorted(seen))  # type: ignore[arg-type]

    def tension_of(self, conflict: tuple[str, str]) -> float:
        """Tension on a stated conflict. Raises if it is not one."""
        for carrier in self.carriers:
            if not carrier.path and tuple(sorted((carrier.belief_id_a, carrier.belief_id_b))) == tuple(sorted(conflict)):
                return carrier.tension
        raise KeyError(f"{conflict} is not a stated conflict in this view")


@dataclass(frozen=True)
class TensionReading:
    """The analysis record. Carries what the view withholds, for reporting only.

    Never handed to a selector. `magnitude` and `saturation_baseline` are here so
    that a published delta can be reported against the curve position it was
    measured at, which requirements section 12 requires and the control path must
    not see.
    """

    agent_id: str
    magnitude_raw: float
    magnitude: float
    saturation_baseline: float
    carriers: tuple[DissonanceCarrier, ...]

    @property
    def view(self) -> TensionView:
        return TensionView(agent_id=self.agent_id, magnitude_raw=self.magnitude_raw, carriers=self.carriers)


def reading_of(signal: DissonanceSignal | None, *, agent_id: str, baseline: float = 0.0) -> TensionReading | None:
    """Wrap a raw signal for analysis. `baseline` is the prior magnitude, if any."""
    if signal is None:
        return None
    return TensionReading(
        agent_id=agent_id,
        magnitude_raw=signal.magnitude_raw,
        magnitude=signal.magnitude,
        saturation_baseline=baseline,
        carriers=tuple(signal.carriers),
    )


# --- fixtures ----------------------------------------------------------------


def load_web(name: str, *, directory: Path | str = FIXTURE_DIR) -> dict[str, Any]:
    """Read one experiment 4 fixture.

    On disk rather than inline in tests so that "the mechanism was not developed
    against this structure" is a checkable claim about a file with a recorded
    hash, rather than a recollection. Experiment 3 section 5 named the absence of
    this as one of the things standing between it and "done".
    """
    return json.loads((Path(directory) / f"{name}.json").read_text(encoding="utf-8"))


def web_specs(fixture: dict[str, Any]) -> list[Any]:
    """Convert a fixture's belief list into `fork.BeliefSpec`s.

    **Not `revision.topology_specs`, and the difference matters.** That function
    drops `salience`, because experiment 3 varied grounding and confidence only.
    Here `stake_of` is `mean(evidence salience) x confidence`, so salience is
    half of the quantity this entire experiment turns on — a fixture that left it
    implicit would pin every belief at `fork.DEFAULT_SALIENCE` and make the
    adversarial case unconstructible.

    Reusing `topology_specs` and adding salience to it was the alternative. It
    was rejected because experiment 3 is closed and its published numbers were
    produced by that function; a behaviour-neutral edit is still an edit to the
    code a closed result rests on.
    """
    from manyu.fork import BeliefSpec
    from manyu.schemas import BeliefScope, BeliefType

    return [
        BeliefSpec(
            key=entry["key"],
            proposition=entry["proposition"],
            valence=entry.get("valence", 0.0),
            confidence=entry.get("confidence", 0.7),
            salience=entry.get("salience", 0.5),
            weight=entry.get("weight", 0.7),
            belief_type=BeliefType(entry.get("belief_type", "world_model")),
            scope=BeliefScope(entry.get("scope", "general")),
            contradicts=tuple(entry.get("contradicts", ())),
            supports=tuple(entry.get("supports", ())),
            evidence_count=entry.get("evidence_count", 1),
        )
        for entry in fixture["beliefs"]
    ]


#: Fixtures are seeded through `fork.seed_beliefs`, which writes edges straight
#: to the store and therefore does **not** price contradictions. That is
#: deliberate: pricing moves confidence, confidence moves stake, and stake is the
#: independent variable. A priced fixture would start from a state the fixture
#: did not specify.
SEEDS_ARE_UNPRICED = True


# --- freeze ------------------------------------------------------------------


# --- Stage 3: is the signal pointing at anything? -----------------------------


def implicated_beliefs(view: TensionView) -> set[str]:
    """Every belief named by any carrier, derived pairs included."""
    named: set[str] = set()
    for carrier in view.carriers:
        named.add(carrier.belief_id_a)
        named.add(carrier.belief_id_b)
        named.update(carrier.path)
    return named


def spread(view: TensionView, belief_count: int) -> float:
    """Fraction of the web the signal implicates.

    **The Stage 3 measurable, and it is the honest form of the targeting
    question.** "Do the carriers name the beliefs acted on?" is settled by
    wiring: the loop selects a conflict *from* the carrier set, so the overlap is
    100% by construction — experiment 3 section 1 in a new place.

    What can fail is whether the signal points at a *part* of the web. Traversal
    across `supports` multiplies who is implicated by a single conflict, so on a
    densely connected store the carrier set can grow until it names nearly
    everything, at which point it is reporting graph size rather than tension
    structure. That is experiment 1's gate #3 — a constant read as a curve — in
    the shape of a set.
    """
    if belief_count <= 0:
        return 0.0
    return len(implicated_beliefs(view)) / belief_count


def derange_supports(specs: list[Any], seed: int) -> list[Any]:
    """Rewire every `supports` edge at random, preserving each belief's out-degree.

    The null for `spread`. `contradicts` is left untouched, so the deranged web
    holds exactly the same conflicts carrying exactly the same tension — the only
    thing destroyed is which beliefs entail which. If the real web implicates no
    less of itself than a deranged one does, the traversal is following
    connectivity rather than structure.

    Degree-preserving on purpose. Deleting edges instead would confound "the
    structure was meaningful" with "there was less of it", which is the family of
    confound experiment 1's shuffle baseline exists to avoid.

    Self-edges are excluded because the store refuses them (experiment 3 review
    finding 1), so a derangement that produced one would be measuring a rejection
    rather than a rewiring.
    """
    import random as _random

    rng = _random.Random(seed)
    keys = [spec.key for spec in specs]
    rewired = []
    for spec in specs:
        degree = len(spec.supports)
        if degree:
            candidates = [key for key in keys if key != spec.key]
            targets = tuple(rng.sample(candidates, k=min(degree, len(candidates))))
        else:
            targets = ()
        rewired.append(replace(spec, supports=targets))
    return rewired


# --- the coupling ------------------------------------------------------------


class Arm(str, Enum):
    """Which conflict the loop attends to. **No default at any layer.**

    Experiment 3 section 13's rule: a silent default settles an open question by
    whichever branch a caller happened not to think about. The harness refuses a
    run that does not name an arm.
    """

    #: Attend to the conflict carrying the most tension. The mechanism under test.
    DRIVEN = "driven"
    #: Attend to the *least* tense conflict first. The floor: if ordering matters
    #: at all, this is the worst the same actions can do.
    INVERTED = "inverted"
    #: Attend to a conflict drawn uniformly at random, as many times as `driven`
    #: did on the same web. Isolates *which* was chosen from *how many* were.
    RANDOM_MATCHED = "random_matched"

    # **`always` was specified and then dropped, and the reason is worth
    # keeping.** The plan named an "always escalate" baseline, to ask whether the
    # signal was doing the work or the acting was. But this loop acts on exactly
    # one conflict per step and never declines to act, so "escalate regardless of
    # tension" has no way to differ from "pick one without consulting tension" —
    # which is `random_matched`. Running both would have reported one arm twice,
    # the exact defect experiment 2 found when `ContradictionArm` was stored,
    # stamped onto every result, and consulted by no branch. `INVERTED` replaces
    # it because it is genuinely a different ordering rather than the same one
    # relabelled, and it brackets the driven arm from below.


class TerminationReason(str, Enum):
    """Why the loop stopped. Every value is reachable — see the loop tests.

    There is deliberately no ``OSCILLATING``. Pricing lowers a target's
    confidence and nothing in the loop raises it, so tension is monotone
    non-increasing and the loop cannot thrash. A termination reason that cannot
    occur is decoration, and experiment 2 spent a stage discovering that a
    stored-but-unconsulted enum makes everything downstream unreadable.
    """

    #: No conflict anywhere in the web.
    NO_SIGNAL = "no_signal"
    #: Every conflict has been attended to and none moves any further.
    EXHAUSTED = "exhausted"
    #: The attention budget ran out with work still available.
    BOUND_REACHED = "bound_reached"


@dataclass(frozen=True)
class AttentionStep:
    """One act of attention, and everything needed to judge it afterwards."""

    iteration: int
    conflict: tuple[str, str]
    contradictor_id: str
    target_id: str
    #: Whether the graph declared this direction, both, or neither.
    direction: str
    tension_before: float
    raw_before: float
    #: How many live conflicts shared the selected tension. Greater than one
    #: means the choice was a coin flip — and **not a reproducible one**: the
    #: tie-break runs on `belief_id`, which is `uuid4`, so the same logical web
    #: seeded into a fresh store can break the tie the other way. Recorded rather
    #: than hidden, because a silent arbitrary choice inside the mechanism under
    #: test is precisely the kind of thing that reads as a finding later.
    tied_with: int
    #: The highest tension available among conflicts not yet attended, read off
    #: the **live** web at selection time. Makes the record self-auditing: a
    #: driven arm must have `tension_before == best_available_tension`, and any
    #: gap means the selection was made from stale or otherwise wrong
    #: information. Without it, a loop deciding from an outdated reading records
    #: a live tension beside a stale choice and looks entirely correct.
    best_available_tension: float
    #: What the action actually did — `assert_contradiction`'s own outcome.
    outcome: str
    moved: float
    #: The capitulation record. Recorded *at selection time*, because the whole
    #: question is whether attention lands on well-grounded beliefs, and both
    #: quantities change the moment the action runs.
    target_evidence_count: int
    target_stake: float
    contradictor_evidence_count: int
    contradictor_stake: float


@dataclass(frozen=True)
class LoopResult:
    arm: Arm
    max_iterations: int
    steps: tuple[AttentionStep, ...]
    #: Raw tension before each iteration, plus the final value. Length is
    #: `len(steps) + 1`, so a trajectory is readable without re-deriving it.
    trajectory: tuple[float, ...]
    termination: TerminationReason
    #: Conflicts that were attended to and did not move. Derived from observed
    #: behaviour rather than from bookkeeping the loop assumed.
    inert: tuple[tuple[str, str], ...]

    @property
    def attended(self) -> tuple[tuple[str, str], ...]:
        return tuple(step.conflict for step in self.steps)

    @property
    def had_arbitrary_choice(self) -> bool:
        """True if any selection was a tie, and therefore not reproducible.

        **Methodology consequence, not a nicety.** Arms cannot be compared across
        separately-seeded stores on a web where this is true, because the tie
        breaks on `uuid4` belief ids. Either compare on webs with distinct
        tensions, or report over enough seeds that the coin flip averages out.
        """
        return any(step.tied_with > 1 for step in self.steps)

    @property
    def total_movement(self) -> float:
        return round(sum(step.moved for step in self.steps), 6)

    @property
    def weakened_the_better_grounded_side(self) -> tuple[bool, ...]:
        """Per step: did attention land on the *better*-grounded of the two?

        The dependent variable Stage 4 turns on. `None`-free by construction —
        ties count as False, since a tie is not a case of the worse-grounded
        belief being spared.
        """
        return tuple(
            step.target_evidence_count > step.contradictor_evidence_count for step in self.steps
        )


class Selector(Protocol):
    """Chooses the next conflict from what the loop is allowed to see.

    Takes a `TensionView`, never a `DissonanceSignal` and never the store. The
    saturated `magnitude` channel is unreachable from here by construction
    rather than by convention — see `TensionView`.
    """

    name: str

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None: ...


class CarrierDrivenSelector:
    """Attend to the conflict carrying the most tension.

    Ties broken by the sorted belief-id pair, so the choice is deterministic and
    reproducible from the record. **Consults no randomness at all**, which is
    asserted rather than assumed — a driven arm that quietly randomised would
    beat the random arm for the wrong reason.
    """

    name = "carrier_driven"

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = [conflict for conflict in view.conflicts if conflict not in inert]
        if not live:
            return None
        return max(live, key=lambda conflict: (view.tension_of(conflict), conflict))


class InvertedSelector:
    """Attend to the *least* tense conflict first — the floor.

    The same actions in the worst order the signal could recommend. If the driven
    arm does no better than this, tension ordering carries no information and the
    signal is decoration; experiment 1's shuffle baseline and experiment 3's
    ablations serve the same purpose.

    Note this is a *stronger* control than "pick without consulting tension",
    because it consults tension and then does the opposite. A mechanism can beat
    random by luck on a small web; beating the inverted arm requires the ordering
    to be real.
    """

    name = "inverted"

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = [conflict for conflict in view.conflicts if conflict not in inert]
        if not live:
            return None
        return min(live, key=lambda conflict: (view.tension_of(conflict), conflict))


class RandomMatchedSelector:
    """Attend at random, seeded so a run is reproducible from its record.

    Rate matching is enforced by the *harness*, not here: the driven arm runs
    first and its step count becomes this arm's budget. A selector cannot
    rate-match itself without knowing a result it has not produced yet.
    """

    name = "random_matched"

    def __init__(self, seed: int):
        self.seed = seed
        self._rng = random.Random(seed)

    def select(self, view: TensionView, inert: frozenset[tuple[str, str]]) -> tuple[str, str] | None:
        live = sorted(conflict for conflict in view.conflicts if conflict not in inert)
        return self._rng.choice(live) if live else None


def selector_for(arm: Arm, *, seed: int | None = None) -> Selector:
    if arm is Arm.DRIVEN:
        return CarrierDrivenSelector()
    if arm is Arm.INVERTED:
        return InvertedSelector()
    if arm is Arm.RANDOM_MATCHED:
        if seed is None:
            raise ValueError("random_matched requires an explicit seed, so the run is reproducible from its record")
        return RandomMatchedSelector(seed)
    raise ValueError(f"unknown arm {arm!r}")


class AttentionLoop:
    """Dissonance selects what gets revisited; revising eases dissonance.

    **The action is to price the selected conflict**, through experiment 3's
    `RevisionEngine.assert_contradiction`. That choice is load-bearing and worth
    stating plainly:

    - It introduces **no new constant.** Experiment 3 section 12 derived a
      contradictor's weight as `1/(supporters + own evidence + contradictors)`,
      read off the store. Inventing a fresh "attention strength" here would put
      a free parameter at the centre of the result, which is exactly what
      sections 11 and 12 removed from decay and from pricing.
    - It is **idempotent**, so attending twice to one conflict cannot compound.
      That is what makes `EXHAUSTED` a real terminal state rather than a loop
      running to its bound every time.
    - The **direction is read off the graph, not chosen by the loop.** Charging
      whichever side is weaker would build the motivated-reasoning result rather
      than measure it — experiment 3 section 1 in a new place. Which belief pays
      is a property of the web; which conflict gets attention is the loop's
      decision, and that is the only thing under test.

    What the loop cannot do, and this is the substrate rather than the design:
    it cannot retire a conflict, and it cannot lower tension except by weakening
    a party. See `tests/test_salience_substrate.py`.
    """

    def __init__(
        self,
        core: Any,
        *,
        arm: Arm,
        agent_id: str,
        seed: int | None = None,
        selector: Selector | None = None,
    ):
        """`selector` overrides the implementation while `arm` still names the intent.

        The injection point exists for `salience_mutants`, and it is a constructor
        parameter rather than a patch target on purpose. Monkeypatching a module
        attribute does **not** reach a caller that did `from module import name` —
        the import bound the original function object — so a battery built on
        patching reports mutants as "caught" when the mutant was never installed.
        That happened while validating the substrate tests, and it is the reason
        every mutant here is injected rather than patched.

        `arm` stays required and undefaulted regardless.
        """
        self.core = core
        self.arm = arm
        self.agent_id = agent_id
        self.selector = selector if selector is not None else selector_for(arm, seed=seed)

    def _read(self) -> TensionReading | None:
        from manyu.dissonance import MergedDissonanceQuery

        signal = MergedDissonanceQuery(self.core.store).detect(self.agent_id, "attention_loop")
        return reading_of(signal, agent_id=self.agent_id)

    def _direction(self, conflict: tuple[str, str]) -> tuple[str, str, str]:
        """Contradictor, target, and how the direction was decided.

        Declared by the graph wherever the graph declares one. A mutual conflict
        has no declared direction, so it is broken by sorted belief id and
        labelled — analysis can then exclude mutual cases rather than discover
        them in the residuals.
        """
        left, right = conflict
        left_belief = self.core.store.get_belief(left)
        right_belief = self.core.store.get_belief(right)
        left_declares = right in left_belief.contradicts
        right_declares = left in right_belief.contradicts

        if left_declares and right_declares:
            return left, right, "mutual"
        if left_declares:
            return left, right, "declared"
        if right_declares:
            return right, left, "declared"
        # Unreachable from a carrier, which is built from `_leaf_conflicts`.
        raise ValueError(f"{conflict} carries no contradicts edge in either direction")

    def run(self, *, max_iterations: int) -> LoopResult:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        from manyu.dissonance import stake_of

        steps: list[AttentionStep] = []
        attended: set[tuple[str, str]] = set()
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

            # Exclude what this run has already attended to. Pricing is
            # idempotent, so re-selecting a handled conflict spends a step of
            # the budget and moves nothing — and because tension only falls by
            # the amount just charged, the highest-tension conflict is often
            # still the one just handled. The first version of this loop lacked
            # the exclusion and burnt **half of every budget** on `already_priced`
            # no-ops, which would have corrupted Stage 2: the attention budget is
            # that stage's independent variable, so an arm comparison under a
            # tight bound would have been measuring the waste rather than the
            # selection. Remembering what you just did is the minimum coherence
            # for an attention mechanism, not an assumption about the engine.
            conflict = self.selector.select(reading.view, frozenset(attended))
            if conflict is None:
                termination = TerminationReason.NO_SIGNAL if not steps else TerminationReason.EXHAUSTED
                break

            selected_tension = reading.view.tension_of(conflict)
            available = [
                reading.view.tension_of(candidate)
                for candidate in reading.view.conflicts
                if candidate not in attended
            ]
            tied_with = sum(1 for value in available if abs(value - selected_tension) <= 1e-9)
            best_available = max(available) if available else selected_tension

            contradictor_id, target_id, direction = self._direction(conflict)
            contradictor = self.core.store.get_belief(contradictor_id)
            target = self.core.store.get_belief(target_id)
            before = target.confidence

            result = self.core.assert_contradiction(
                {
                    "agent_id": self.agent_id,
                    "contradictor_id": contradictor_id,
                    "target_id": target_id,
                    "arm": "direct",
                }
            )
            if result.get("status") != "ok":
                raise RuntimeError(f"attention step failed: {result}")

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
                    tied_with=tied_with,
                    best_available_tension=round(best_available, 6),
                    outcome=str(result.get("outcome", "unknown")),
                    moved=moved,
                    target_evidence_count=len(target.evidence_ids),
                    target_stake=round(stake_of(self.core.store, target), 6),
                    contradictor_evidence_count=len(contradictor.evidence_ids),
                    contradictor_stake=round(stake_of(self.core.store, contradictor), 6),
                )
            )
            attended.add(conflict)
            if moved <= 0.0:
                # Recorded, not assumed. A conflict already priced before the
                # loop began — by ingest, per experiment 3 section 14 — moves
                # nothing when attended, and that is a fact about the web worth
                # reporting rather than a step to hide.
                inert.add(conflict)
        else:
            reading = self._read()
            trajectory.append(0.0 if reading is None else reading.magnitude_raw)
            return LoopResult(
                arm=self.arm,
                max_iterations=max_iterations,
                steps=tuple(steps),
                trajectory=tuple(trajectory),
                termination=TerminationReason.BOUND_REACHED,
                inert=tuple(sorted(inert)),
            )

        return LoopResult(
            arm=self.arm,
            max_iterations=max_iterations,
            steps=tuple(steps),
            trajectory=tuple(trajectory),
            termination=termination,
            inert=tuple(sorted(inert)),
        )


FREEZE_PATH = Path("evals/analysis/exp04/freeze.json")


def _frozen_digest(path: Path | str) -> str:
    """SHA-256 of a frozen file, over bytes with CRLF normalized to LF.

    Every freeze hash in this repo was taken over LF bytes. A Windows checkout
    with `core.autocrlf=true` and no `.gitattributes` rewrites text files to
    CRLF on the way out: the committed bytes are untouched and `git status`
    stays clean, but the working-tree bytes hash differently and all eleven
    fixtures report as drifted at once. The `.gitattributes` at the repo root
    pins these paths to LF so that should not arise; normalizing here covers
    what it cannot — clones made before it existed, and copies that reached the
    tree without passing through git.

    **This does not weaken the gate.** The gate exists to prove a held-out file
    was not edited after freezing, and every edit that changes what a file
    *says* still changes these bytes and still fires. What is discarded is only
    the distinction between the two spellings of a line break:

    - Fixtures are JSON, where a raw CR or LF byte cannot occur inside a string
      — RFC 8259 requires them escaped as ``\\r`` / ``\\n``, two characters. So
      every CRLF in a valid fixture is whitespace between tokens, and rewriting
      it cannot change the parsed web by any amount.
    - The frozen criterion tests and methodology are read through universal
      newlines, which applies this same translation before the interpreter or a
      reader ever sees the text.

    So the bytes this ignores are bytes that provably carry no content. The
    alternative — re-freezing to match a CRLF tree — is the move that would
    actually void the guarantee, because it re-freezes whatever the tree
    happens to hold at that moment.
    """
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def mechanism_digest() -> str:
    """SHA-256 of this module — the thing that must not change after freeze."""
    return _frozen_digest(Path(__file__))


def fixture_digest(name: str, *, directory: Path | str = FIXTURE_DIR) -> str:
    return _frozen_digest(Path(directory) / f"{name}.json")


def _drift(entries: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    drifted, missing = [], []
    for relative, entry in entries.items():
        candidate = Path(relative)
        if not candidate.exists():
            missing.append(relative)
            continue
        actual = _frozen_digest(candidate)
        if actual != entry["sha256"]:
            drifted.append(f"{relative} (frozen {entry['sha256'][:12]}, now {actual[:12]})")
    return sorted(drifted), sorted(missing)


def _raise_on_drift(label: str, drifted: list[str], missing: list[str], *, experiment: str = "4") -> None:
    if not drifted and not missing:
        return
    parts = []
    if drifted:
        parts.append("changed after freeze: " + ", ".join(drifted))
    if missing:
        parts.append("absent: " + ", ".join(missing))
    raise RuntimeError(
        f"experiment {experiment} {label} freeze violated — {'; '.join(parts)}. "
        f"Any held-out claim resting on these files is void and must restart from a new freeze."
    )


def verify_fixture_freeze(path: Path | str = FREEZE_PATH, *, experiment: str = "4") -> dict[str, Any]:
    """Refuse to proceed if any held-out **web** changed after it was frozen.

    `experiment` names the caller in the failure message and nothing else.
    Experiment 5 reuses this guard rather than writing a second one — the logic
    is identical and a duplicated freeze check is a freeze check that drifts.

    Convention is not enough. Experiment 1's retraction history is a list of
    things that were meant to be true and were not checked, and experiment 2
    wrote this same guard for `dissonance.py` after learning it.

    **Fixtures only.** The criterion tests are frozen too, under `standards`,
    but are deliberately not enforced here — see `verify_standards_freeze`.
    `salience.py` is not frozen at all at this stage: the selector and the loop
    are built on top of what existed when the webs were authored, and a
    mechanism freeze is a separate step taken before the scored run.
    """
    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    _raise_on_drift("fixture", *_drift(freeze["files"]), experiment=experiment)
    return freeze


def verify_standards_freeze(path: Path | str = FREEZE_PATH, *, experiment: str = "4") -> dict[str, Any]:
    """Refuse to proceed if a **criterion test** changed after it was frozen.

    Called by the runner before a scored run, and deliberately *not* by the test
    suite. The distinction is not bureaucratic:

    - A **fixture** edit invalidates results, so it is checked continuously.
    - A **criterion test** edit is usually someone strengthening the standard,
      which is the thing we want to encourage. Enforcing it on every run would
      make adding a check painful, and the predictable response to a guard that
      fires constantly is to delete the guard.

    What must not happen is a standard being *weakened* after a result is
    visible. That risk lives at the scored run, so the check lives there, and
    re-freezing is an explicit act with a recorded reason — the shape experiment
    3 used when its Stage 4 pilot forced a re-freeze and it recorded which
    predictions stayed blind.
    """
    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    _raise_on_drift("standards", *_drift(freeze.get("standards", {})), experiment=experiment)
    return freeze


def standards_drift(path: Path | str = FREEZE_PATH) -> list[str]:
    """Report criterion-test drift without raising. For reporting in a run record."""
    freeze = json.loads(Path(path).read_text(encoding="utf-8"))
    drifted, missing = _drift(freeze.get("standards", {}))
    return drifted + [f"{name} (absent)" for name in missing]
