"""Belief revision and propagation — experiment #3's engine.

The question this exists to answer is whether retracting a supported belief
collapses a foundational chain or ripples through a coherent net. Both
hypotheses were previously untestable against this codebase, for two reasons
fixed here and in `services.py`:

- **Confidence was a ratchet.** `_revise` took `max(belief.confidence, blended)`,
  so disconfirming evidence moved a belief by exactly zero. A web whose nodes
  cannot weaken cannot ripple, and both hypotheses predicted "nothing moves".
- **`supports` edges carried nothing.** They accumulated in the store and were
  walked by `dissonance.py`, but no confidence change had ever crossed one.

Design commitments, each pinned in
`docs/experiments/03-foundationalism-quinean-web/requirements.md`:

- **Fractional support (FR-7).** A belief with three supporters loses a third
  as much per retraction as one with a single supporter. This is the whole
  discriminator: a chain and a net differ precisely in how much of a node's
  grounding any one edge carries. It is also the commitment most at risk of
  being our own hand rather than a finding — see requirements §7.
- **Attenuation per hop.** Support weakens with distance, so a ripple decays.
- **Inertia strictly below 1.** Entrenched beliefs move slowly; none is
  unfalsifiable. The backlog's proposed `0.5 + 0.5 * stability` reaches 1.0 at
  full stability, which would make a maximally corroborated belief immovable —
  reintroducing the ratchet under another name at exactly the point the
  experiment cares about.
- **Retraction never deletes.** Confidence collapses; the belief and its
  provenance remain. An experiment about revision that destroys its own
  evidence has nothing to audit afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from .schemas import Belief, BeliefRevision, BeliefStatus

if TYPE_CHECKING:  # pragma: no cover
    from .clock import Clock
    from .store import ManyuStore


class DecayMode(str, Enum):
    """Where the decay across a hop comes from.

    `FIXED` was the first implementation and is kept only as an ablation,
    because it does not survive scrutiny as a default. In a chain every node
    has exactly one supporter, so `support_share` is 1.0 and the attenuation
    constant is the *only* thing producing decay — set it to 1.0 and a chain
    collapses foundationally, set it below 1 and it grades. In the topology
    where the two hypotheses most sharply disagree, the constant **is** the
    hypothesis, and reporting a graded ripple would be reporting the constant
    back.

    `PROVENANCE` removes the constant. A belief is grounded by two things the
    store already records — its own evidence and its supporters — so
    retracting one supporter removes that supporter's share of the total. Decay
    across depth then emerges from each node's own provenance instead of being
    imposed by distance, and both collapse and flex become *available*
    behaviours selected by what a belief's grounding actually looks like.
    """

    PROVENANCE = "provenance"
    FIXED = "fixed"


class ContradictionPricing(str, Enum):
    """How hard a contradiction pushes — the same question `DecayMode` settled
    for support, asked for conflict.

    `FIXED` multiplies by a constant (`contradiction_penalty`). It was the
    first implementation, and requirements §5 was decided while it was in
    place — which left an unjustified constant at the centre of a decision.
    `DIRECT` won because `EVIDENTIAL` failed a standard, never because 0.3 was
    shown correct.

    `PROVENANCE` removes it. A contradictor is one more voice in the target's
    epistemic field, competing with the grounds the target already holds, so
    its share is `1/(supporters + own evidence + contradictors)` — the direct
    analogue of `_support_share`. A belief corroborated five times over shrugs
    off a lone objection; a thinly-grounded one does not. Nothing is tuned:
    every term is read off the store.
    """

    PROVENANCE = "provenance"
    FIXED = "fixed"


class ContradictionArm(str, Enum):
    """The open design question, built as two arms rather than decided.

    Requirements §5: *should a contradiction lower confidence directly, or
    only through the evidence that carries it?* This is the
    foundationalism/Quine fork rendered in code, so it is settled with
    **Decided: `DIRECT`** (requirements §5.1). While the question was open
    there was deliberately no default, so that it could not be settled by
    whichever branch a caller forgot to think about. Now that it is settled,
    `DIRECT` *is* the default and `EVIDENTIAL` is the labelled alternative —
    the same shape as `DecayMode` and `ContradictionPricing`. Changing this
    default reverses a recorded decision.

    The arms differ in one observable way, and it is the sign of what happens
    to a belief when its *contradictor* is retracted:

    - `DIRECT` treats a contradiction as active suppression. Q is held back by
      P, so retracting P **lifts** the suppression and Q recovers. Support and
      contradiction are opposite-signed edges.
    - `EVIDENTIAL` treats a contradiction as bookkeeping. Retracting P leaves
      Q's confidence untouched; only `status` ever recorded the conflict.

    Contradiction propagates **one hop only** under `DIRECT`, where support
    propagates to depth. That asymmetry is a design choice, not an oversight:
    support is transitive (grounds of grounds are still grounds), while
    "the enemy of my enemy" is not an epistemic relation we want to assert.
    """

    #: A `contradicts` edge applies its own confidence penalty, scaled by the
    #: contradicting belief's confidence.
    DIRECT = "direct"
    #: `contradicts` changes status only. Confidence moves when the evidence
    #: under a belief is undermined, and propagates from there.
    EVIDENTIAL = "evidential"


@dataclass(frozen=True)
class RevisionConfig:
    """Constants pinned before the run that consumes them.

    Changing one after its run has started voids that arm — the
    pre-registration rule carried over from experiment 2 requirements §14.
    """

    #: Where per-hop decay comes from. `PROVENANCE` is the default and uses no
    #: free constant at all; see `DecayMode`.
    decay_mode: DecayMode = DecayMode.PROVENANCE

    #: **Ablation only** — ignored unless `decay_mode` is `FIXED`. Retained so
    #: Stage 2 can show the graded result does not depend on a free decay
    #: parameter, by running the arm that has one.
    attenuation: float = 0.6

    #: Traversal stops when a propagated delta falls below this. Magnitude-
    #: limited rather than depth-limited, so a wide shallow net and a narrow
    #: deep chain are cut off by the same rule rather than by a hop count that
    #: happens to favour one shape.
    epsilon: float = 0.001

    #: Hard stop regardless of magnitude. Guards against a dense web where
    #: attenuation alone would walk most of the store.
    max_depth: int = 6

    #: **Ablation** — treat beliefs as if they carried no evidence of their
    #: own, so grounding comes from supporters alone.
    #:
    #: The substrate refuses any candidate without `evidence_ids`
    #: (`INSUFFICIENT_PROVENANCE`), so a purely derivative belief — the
    #: foundationalist's load-bearing case — is unrepresentable, share can
    #: never exceed 1/(1+1), and nothing can collapse with its supporter. That
    #: makes "revision ripples" a fact about the *provenance requirement*
    #: rather than a discovered property, because the alternative was never
    #: available (requirements §11.1).
    #:
    #: Setting this lifts the requirement for propagation arithmetic only,
    #: making the foundationalist limb reachable so the comparison has two
    #: possible outcomes instead of one. It does **not** relax the write-path
    #: rule: beliefs still cannot be stored without provenance.
    ignore_own_evidence: bool = False

    #: Inertia = base + span * stability, capped strictly below 1.0 so that
    #: no belief is unfalsifiable. At stability 0 a belief blends evenly with
    #: the candidate; at stability 1 it still yields 10%.
    inertia_base: float = 0.5
    inertia_span: float = 0.4

    #: How a contradiction's weight is set. `PROVENANCE` uses no constant.
    contradiction_pricing: ContradictionPricing = ContradictionPricing.PROVENANCE

    #: **Ablation only** — ignored unless `contradiction_pricing` is `FIXED`.
    #: Retained so the §5 verdict can be shown not to depend on it.
    contradiction_penalty: float = 0.3


@dataclass
class PropagationStep:
    """One belief moved by one retraction. The unit of FR-5's footprint."""

    belief_id: str
    depth: int
    before: float
    after: float
    #: Belief whose change caused this one; None for the retraction target.
    caused_by: str | None
    #: Share of this belief's total support carried by the edge that moved it.
    support_share: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass
class PropagationResult:
    """The shape of a single retraction — FR-5.

    A collapse and a ripple are distinguished by this object, not by any
    single number: which beliefs moved, how far from the origin, and by how
    much at each remove.
    """

    origin_id: str
    arm: ContradictionArm
    steps: list[PropagationStep] = field(default_factory=list)

    @property
    def moved(self) -> list[PropagationStep]:
        return [s for s in self.steps if abs(s.delta) > 0.0]

    @property
    def max_depth_reached(self) -> int:
        return max((s.depth for s in self.steps), default=0)

    def by_depth(self) -> dict[int, list[PropagationStep]]:
        out: dict[int, list[PropagationStep]] = {}
        for step in self.steps:
            out.setdefault(step.depth, []).append(step)
        return out

    def total_movement(self) -> float:
        """Summed absolute movement, excluding the origin.

        The origin is excluded because it is the manipulation, not the
        response — including it would let a larger shock masquerade as a
        larger ripple.
        """
        return sum(abs(s.delta) for s in self.steps if s.depth > 0)


def blend_confidence(belief: Belief, candidate_confidence: float, config: RevisionConfig) -> float:
    """Bidirectional confidence update — FR-1.

    Replaces `max(belief.confidence, blended)`. Stability supplies the damping
    it already existed to provide, so an entrenched belief moves slowly while
    remaining movable.
    """
    inertia = config.inertia_base + config.inertia_span * belief.stability
    return _clamp(belief.confidence * inertia + candidate_confidence * (1.0 - inertia))


class RevisionEngine:
    """Propagates a confidence change across `supports` edges.

    `arm` defaults to the value requirements §5.1 decided on. The experiment
    surfaces (`manyu retract-belief`, `manyu_retract_belief`) still require it
    explicitly, because there the choice is the point.
    """

    def __init__(self, store: ManyuStore, clock: Clock, arm: ContradictionArm = ContradictionArm.DIRECT, config: RevisionConfig | None = None):
        self.store = store
        self.clock = clock
        self.arm = ContradictionArm(arm)
        self.config = config or RevisionConfig()

    def retract(self, agent_id: str, belief_id: str, to_confidence: float = 0.0) -> PropagationResult:
        """Drive one belief's confidence down and let the consequence spread.

        Retraction is a confidence collapse, never a deletion: the belief and
        its provenance survive so the revision remains auditable afterwards.
        """
        origin = self.store.get_belief(belief_id)
        result = PropagationResult(origin_id=belief_id, arm=self.arm)

        after = _clamp(to_confidence)
        if after > origin.confidence:
            # Retraction is a weakening. Raising a belief through this entry
            # point used to propagate a *drop* to everything it supports —
            # `abs(shock)` made any change, in either direction, weaken
            # downstream (raising a supporter 0.4 -> 0.9 pushed its target
            # 0.8 -> 0.55). Strengthening propagation is a separate mechanism
            # with its own semantics; it is not this one misused.
            raise ValueError(
                f"retract must not raise confidence: {belief_id} is at {origin.confidence}, asked for {after}"
            )
        result.steps.append(
            PropagationStep(
                belief_id=belief_id,
                depth=0,
                before=origin.confidence,
                after=after,
                caused_by=None,
                support_share=1.0,
            )
        )
        self._apply(agent_id, origin, after, depth=0, caused_by=None)
        seen = {belief_id}
        self._propagate(agent_id, belief_id, origin.confidence - after, depth=0, result=result, seen=seen)

        # Relief runs after propagation, over *every* belief that weakened —
        # not just the retraction target. The first version only checked the
        # target's own `contradicts`, which meant nothing fired whenever the
        # contradiction sat on a belief reached by propagation rather than on
        # the origin itself. That is the common case and it made the whole
        # arm inert; the Stage 2 instrument gate caught it.
        relieved: set[str] = set()
        for step in list(result.steps):
            if step.delta < 0:
                self._relieve_contradictions(agent_id, step.belief_id, abs(step.delta), result, relieved, seen)
        return result

    def assert_contradiction(
        self,
        agent_id: str,
        contradictor_id: str,
        target_id: str,
        contradictor_confidence: float | None = None,
    ) -> PropagationResult:
        """Record that one belief contradicts another, and price it.

        The counterpart of the relief in `_relieve_contradictions`, and it was
        missing: relief existed while suppression did not, so `DIRECT` handed
        a belief confidence for the removal of something that had never cost
        it anything. Retract-then-check left the target *above* where it
        started — confidence manufactured from nothing.

        Under `DIRECT` the penalty is `_contradiction_share(target) *
        contradictor.confidence`. Relief prices against the same product at
        the contradictor's current confidence, so the round trip closes at any
        magnitude rather than only at full retraction — and closes regardless
        of the path the contradictor took to get there.

        Under `EVIDENTIAL` this records the edge and the status and stops —
        which is the arm's whole claim, that a contradiction is bookkeeping
        until evidence moves.
        """
        contradictor = self.store.get_belief(contradictor_id)
        target = self.store.get_belief(target_id)
        result = PropagationResult(origin_id=contradictor_id, arm=self.arm)

        if target_id not in contradictor.contradicts:
            self.store.save_belief(
                contradictor.model_copy(update={"contradicts": sorted(set([*contradictor.contradicts, target_id]))})
            )

        if self.arm is not ContradictionArm.DIRECT:
            if target.status is not BeliefStatus.CONTESTED:
                self.store.save_belief(target.model_copy(update={"status": BeliefStatus.CONTESTED}))
            return result

        charged, _ = self._suppression_ledger(target_id, contradictor_id)
        if charged > 0.0:
            # Idempotent. Asserting the same contradiction twice previously
            # charged twice (0.8 -> 0.56 -> 0.32), so any harness that
            # re-applied a fixture's declared edges — or any re-processing of
            # the same web — compounded the penalty without bound.
            self.store.audit("system", "contradiction_already_priced", {"agent_id": agent_id, "contradictor": contradictor_id, "target": target_id})
            return result

        share = self._contradiction_share(agent_id, target)
        # `contradictor_confidence` lets a caller price a whole batch against
        # the state at the batch's start. Without it, mutual contradictions
        # were order-dependent: charging A→B first weakened B, so B→A was then
        # priced against a weaker opponent and the pair settled at 0.6/0.4 —
        # with which belief got the 0.6 decided by extractor emission order.
        strength = contradictor.confidence if contradictor_confidence is None else _clamp(contradictor_confidence)
        penalty = share * strength
        before = target.confidence
        after = _clamp(before - penalty)
        contested = target.model_copy(update={"status": BeliefStatus.CONTESTED})
        result.steps.append(
            PropagationStep(
                belief_id=target_id,
                depth=0,
                before=before,
                after=after,
                caused_by=contradictor_id,
                support_share=share,
            )
        )
        self._apply(agent_id, contested, after, depth=0, caused_by=contradictor_id, reason=_asserted_by(contradictor_id))
        return result

    def _relieve_contradictions(self, agent_id: str, origin_id: str, shock: float, result: PropagationResult, relieved: set[str], seen: set[str]) -> None:
        """`DIRECT` arm only — retracting a suppressor lets its target recover.

        Under `DIRECT` a contradiction actively holds a belief down, so
        weakening the contradictor lifts the suppression and the contradicted
        belief rises. Under `EVIDENTIAL` this does nothing at all, which is
        the entire observable difference between the arms.

        One hop, and **directional**: relief mirrors suppression exactly.
        `assert_contradiction(Q, P)` charges P and leaves Q alone, so only a
        weakening of Q may refund P. An earlier version treated conflict as
        symmetric — relieving anything that contradicted the weakened belief
        as well — which ran the refund backwards: weakening the *suppressed*
        belief paid its suppressor.
        """
        if self.arm is not ContradictionArm.DIRECT or abs(shock) < self.config.epsilon:
            return

        origin = self.store.get_belief(origin_id)
        opposed = set(origin.contradicts)
        opposed.discard(origin_id)

        for target_id in sorted(opposed):
            if target_id in relieved or target_id in seen:
                # Already relieved, or itself weakened by this retraction —
                # a belief cannot both lose grounding and gain from the loss.
                continue
            charged, refunded = self._suppression_ledger(target_id, origin_id)
            if charged <= 0.0:
                # Relief may only ever undo a suppression that was applied.
                # Contradictions arriving through `BeliefUpdater` — the
                # extractor path, and every seeded fixture — set `status` and
                # never touch confidence, so relieving them credits a belief
                # for a cost it never paid. Measured before this guard: a
                # target seeded at 0.8 finished at 0.92 having been
                # contradicted and then un-contradicted.
                self.store.audit("system", "unpriced_contradiction_not_relieved", {"agent_id": agent_id, "contradictor": origin_id, "target": target_id})
                continue
            if self._retracted_since_assertion(target_id, origin_id):
                self.store.audit("system", "refund_withheld_target_retracted", {"agent_id": agent_id, "contradictor": origin_id, "target": target_id})
                continue
            try:
                target = self.store.get_belief(target_id)
            except KeyError:
                continue
            # Refund to the balance the contradictor's *current* confidence
            # justifies, rather than by the size of this particular weakening.
            #
            # Incremental refunds were both unbounded above and lossy below.
            # Lossy, because any weakening the `seen` guard skipped was gone
            # for good: a contradictor that lost grounding alongside its target
            # and was then fully retracted left the target permanently
            # suppressed by something that no longer existed — breaking the
            # round-trip standard the arm was chosen on. Pricing against the
            # current balance is self-correcting and path-independent: however
            # the contradictor got to its confidence, the suppression
            # outstanding is always what that confidence warrants.
            still_owed = self._contradiction_share(agent_id, target) * origin.confidence
            delta = (charged - refunded) - still_owed
            if delta < self.config.epsilon:
                continue
            before = target.confidence
            after = _clamp(before + delta)
            if after == before:
                continue
            relieved.add(target_id)
            result.steps.append(
                PropagationStep(
                    belief_id=target_id,
                    depth=1,
                    before=before,
                    after=after,
                    caused_by=origin_id,
                    support_share=self._contradiction_share(agent_id, target),
                )
            )
            self._apply(agent_id, target, after, depth=1, caused_by=origin_id, reason=_relieved_by(origin_id))

    def _propagate(self, agent_id: str, source_id: str, shock: float, depth: int, result: PropagationResult, seen: set[str]) -> None:
        """Walk `supports` outward from a belief that just moved.

        `A.supports == [B]` means A lends support to B, so a drop in A is a
        drop in B's grounding. Cycles terminate via `seen` (FR-4); magnitude
        terminates via epsilon, so shape rather than hop count decides the
        cutoff.
        """
        if depth >= self.config.max_depth or abs(shock) < self.config.epsilon:
            return

        source = self.store.get_belief(source_id)
        for target_id in source.supports:
            if target_id in seen:
                continue
            try:
                target = self.store.get_belief(target_id)
            except KeyError:
                # Resolution drops dangling edges at write time, so this means
                # the target was removed after the edge was formed. Skipping is
                # correct; recording it keeps the gap countable.
                self.store.audit("system", "propagation_target_missing", {"agent_id": agent_id, "source": source_id, "target": target_id})
                continue

            share = self._support_share(agent_id, target)
            attenuation = 1.0 if self.config.decay_mode is DecayMode.PROVENANCE else self.config.attenuation
            # Signed, not `abs`. `shock` is `before - after`, so it is positive
            # for a weakening and the target drops. Using the magnitude made
            # every change weaken downstream regardless of direction.
            delta = -shock * attenuation * share
            if abs(delta) < self.config.epsilon:
                continue

            before = target.confidence
            after = _clamp(before + delta)
            seen.add(target_id)
            result.steps.append(
                PropagationStep(
                    belief_id=target_id,
                    depth=depth + 1,
                    before=before,
                    after=after,
                    caused_by=source_id,
                    support_share=share,
                )
            )
            self._apply(agent_id, target, after, depth=depth + 1, caused_by=source_id)
            self._propagate(agent_id, target_id, before - after, depth=depth + 1, result=result, seen=seen)

    def _support_share(self, agent_id: str, target: Belief) -> float:
        """Fraction of `target`'s grounding carried by any one supporter — FR-7.

        Under `PROVENANCE` a belief's grounding is its own evidence *plus* its
        supporters, so retracting one supporter removes `1/(supporters +
        evidence)` of it. Nothing here is tuned: both terms are read off the
        store.

        Three consequences worth stating, because they decide the experiment:

        - A node with three supporters and its own evidence yields share 0.25;
          one with a single supporter and its own evidence yields 0.5. The net
          absorbs what the chain transmits (SC-3) **without** a decay constant.
        - Depth decays for the same reason, at each node's own rate rather
          than a global one (SC-2).
        - A belief resting *entirely* on one supporter would yield share 1.0
          and collapse with it — genuine foundationalist behaviour. See
          `_grounding` for why the substrate never actually permits this.
        """
        supporters, own_evidence = self._grounding(agent_id, target)
        if self.config.decay_mode is DecayMode.FIXED:
            return 1.0 / supporters if supporters else 1.0
        total = supporters + own_evidence
        return 1.0 / total if total else 1.0

    def _contradiction_share(self, agent_id: str, target: Belief) -> float:
        """Weight one contradictor carries against `target` — the §5 analogue of
        `_support_share`.

        Under `PROVENANCE` a contradictor is one more voice in the target's
        epistemic field: `1/(supporters + own evidence + contradictors)`. All
        contradictors sit in the denominator, so a second objection dilutes the
        first rather than stacking on top of it.

        Scaled at the call site by the contradictor's own confidence, which is
        what keeps a tentative objection from landing as hard as a confident
        one.
        """
        if self.config.contradiction_pricing is ContradictionPricing.FIXED:
            return self.config.contradiction_penalty
        supporters, own_evidence = self._grounding(agent_id, target)
        contradictors = sum(
            1 for belief in self.store.list_beliefs(agent_id, include_inactive=True) if target.belief_id in belief.contradicts
        )
        total = supporters + own_evidence + max(contradictors, 1)
        return 1.0 / total if total else 1.0

    def _retracted_since_assertion(self, target_id: str, contradictor_id: str) -> bool:
        """Was `target` explicitly retracted after this contradiction was priced?

        An explicit retraction is a deliberate statement about a belief, and a
        refund must not quietly undo it. Without this guard, retracting both
        halves of a mutual contradiction left a belief that had been driven to
        0.0 sitting back at 0.4, with the final state depending on the order
        the two retractions happened to run in.
        """
        seen_assert = False
        for rev in self.store.list_belief_revisions(target_id):
            if rev.reason == _asserted_by(contradictor_id):
                seen_assert = True
            elif seen_assert and rev.reason == "retraction":
                return True
        return False

    def _suppression_ledger(self, target_id: str, contradictor_id: str) -> tuple[float, float]:
        """`(charged, refunded)` for one contradiction, read from the revision trail.

        Reconstructed rather than stored in a side-table, so the ledger cannot
        drift from the confidence changes it accounts for.

        This exists because relief was previously unbounded. Refunds fired on
        every weakening of the contradictor with no memory of what had been
        charged, so a contradictor that weakened, recovered, and weakened again
        refunded twice over: a target charged 0.24 finished 0.12 *above* the
        confidence it held before it was ever contradicted.
        """
        asserted, relieved = _asserted_by(contradictor_id), _relieved_by(contradictor_id)
        charged = refunded = 0.0
        for rev in self.store.list_belief_revisions(target_id):
            if rev.previous_confidence is None:
                continue
            movement = rev.new_confidence - rev.previous_confidence
            if rev.reason == asserted:
                charged += -movement
            elif rev.reason == relieved:
                refunded += movement
        return charged, refunded

    def _grounding(self, agent_id: str, target: Belief) -> tuple[int, int]:
        """`(supporters, own evidence records)` for a belief.

        **The count of own evidence is never zero in practice**, because
        `BeliefUpdater._rejection_reason` refuses any candidate without
        `evidence_ids` (`INSUFFICIENT_PROVENANCE`). Every belief therefore has
        independent grounding, share can never exceed 0.5, and no belief can
        collapse entirely when a supporter is retracted.

        That is a finding about the substrate rather than a property of this
        engine, and it is a large one: **the belief core's mandatory-provenance
        rule forecloses foundationalism by construction.** A purely derivative
        belief — one holding no evidence of its own — is unrepresentable here,
        so the foundationalist limb of the hypothesis has no way to occur. See
        the Stage 1 note in requirements §10.
        """
        supporters = sum(1 for belief in self.store.list_beliefs(agent_id, include_inactive=True) if target.belief_id in belief.supports)
        own_evidence = 0 if self.config.ignore_own_evidence else len(target.evidence_ids)
        return supporters, own_evidence

    def _apply(self, agent_id: str, belief: Belief, confidence: float, depth: int, caused_by: str | None, reason: str | None = None) -> None:
        """Persist a moved belief and record why it moved — FR-3.

        Status follows confidence downward but is never silently upgraded:
        a belief marked CONTESTED by a contradiction stays contested until
        something other than arithmetic clears it.
        """
        status = belief.status
        if confidence < 0.45 and status == BeliefStatus.ACTIVE:
            status = BeliefStatus.TENTATIVE

        updated = belief.model_copy(update={"confidence": round(confidence, 6), "status": status, "updated_at": self.clock.now()})
        self.store.save_belief(updated)
        self.store.save_belief_revision(
            BeliefRevision(
                revision_id=_id("brev"),
                belief_id=belief.belief_id,
                agent_id=agent_id,
                previous_status=belief.status,
                new_status=status,
                previous_confidence=belief.confidence,
                new_confidence=updated.confidence,
                evidence_ids=[],
                reason=reason or ("retraction" if depth == 0 else f"propagated_depth_{depth}_from_{caused_by}"),
                candidate_proposition=belief.proposition,
            )
        )


FIXTURE_DIR = Path("evals/fixtures/exp03")


def load_topology(name: str) -> dict:
    """Read one Stage 2 topology fixture.

    Fixtures are JSON on disk rather than inline in tests so that "the
    mechanism was not developed against this structure" is a checkable claim
    about a file, not a recollection. See results.md for the honest limit on
    how much blinding this actually buys.
    """
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def topology_specs(fixture: dict) -> list:
    """Convert a fixture's belief list into `fork.BeliefSpec`s.

    `evidence_count` is carried through explicitly: under
    `DecayMode.PROVENANCE` it is part of the mechanism, so a fixture that left
    it implicit would be varying the independent variable by accident.
    """
    from .fork import BeliefSpec

    return [
        BeliefSpec(
            key=entry["key"],
            proposition=entry["proposition"],
            confidence=entry.get("confidence", 0.8),
            valence=entry.get("valence", 0.0),
            evidence_count=entry.get("evidence_count", 1),
            supports=tuple(entry.get("supports", ())),
            contradicts=tuple(entry.get("contradicts", ())),
        )
        for entry in fixture["beliefs"]
    ]


def _asserted_by(contradictor_id: str) -> str:
    """Revision reason marking a *priced* contradiction.

    Relief keys off this string rather than off a side-table, so the record
    that a penalty was applied lives in the same audit trail as the penalty
    itself and cannot drift from it.
    """
    return f"contradiction_asserted_by_{contradictor_id}"


def _relieved_by(contradictor_id: str) -> str:
    """Revision reason marking a refund, so the ledger can be reconstructed."""
    return f"contradiction_relieved_by_{contradictor_id}"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _id(prefix: str) -> str:
    from .services import _id as services_id

    return services_id(prefix)
