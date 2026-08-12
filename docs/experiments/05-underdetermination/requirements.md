# Experiment 5 — Underdetermination as a First-Class Belief: Requirements

**Status:** spec (no code)
**Date:** 2026-08-11
**Backlog entry:** [../../experiments_backlog.md](../../experiments_backlog.md)
**Related:** [crux #5](../../Manyu_experiments_crux.md) · [experiment 3](../03-foundationalism-quinean-web/requirements.md) · [experiment 4](../04-dissonance-control-signal/requirements.md) · [experiment 4 results](../04-dissonance-control-signal/results.md) · [ADR-002 merged substrate](../../adr-002-merged-substrate.md)

## 1. Purpose

Manyu can hold two beliefs that cannot both be right — experiment 2 built the
detector, experiment 3 coupled it to revision, experiment 4 asked whether it
controls anything. All three assume the conflict is *resolvable*: one side is
wrong, and evidence will eventually say which.

This experiment is about the case where it will not.

> **Underdetermination is not low confidence.** Low confidence says *one of
> these is probably right and I am not sure which yet*. Underdetermination says
> *no amount of the evidence I have could separate them*. Today both leave the
> substrate as the same middling number.

The question: can Manyu represent "these two are indistinguishable given what I
have" as a stable state it holds **from the evidence**, rather than collapsing
to whichever side the arithmetic happens to favour?

**Why it sits here.** It is strictly harder than #3. Revision must fire when
warranted and *not fire* when it is not, and #4 must be operational so we can
show the system is not simply ignoring the tension. It also inverts into #6:
once Manyu can say *I cannot tell these apart*, the next question is *what would
tell them apart*.

**Decided 2026-08-11: underdetermination is a belief in its own right**, not a
relation over a set of beliefs. See §5.3 — the choice is what makes the state
falsifiable, and it is the reason the rest of this spec has a dependent variable
at all.

## 2. The trap, in three flavours

The chartered question — "can Manyu hold underdetermination?" — is not an
experiment as stated. Add an `UNDERDETERMINED` status and the branch that
refuses to collapse, and of course it holds; we wrote it.

This is the third time. It is worth naming the flavours separately, because they
are guarded at different stages and only one of them is the familiar one.

**Flavour A — the answer is forced by what we are about to write.** Experiment 4
§2: write the branch that reads the signal and the signal changes behaviour.
Caught at spec time there. Here it is the representation itself.

**Flavour B — the answer is forced by the architecture, before anyone writes
anything.** Experiment 3 §11.1: mandatory provenance makes total foundationalist
collapse *unrepresentable*, so "revision ripples" could not have come out
otherwise. Caught late, and it demoted the headline from an observation to a
consequence — rescued only by the `ignore_own_evidence` ablation, which made the
counterfactual measured rather than argued. Here the live risk is the mirror
image: symmetric contradiction pricing may mean rival beliefs *cannot* diverge,
in which case "Manyu holds underdetermination" is true and empty. §6 is that
check.

**Flavour C — the mechanism cannot fire at all.** Experiment 1's mood →
`rank_causes` coupling was arithmetically a no-op on every probed target, across
several versions, and that is why [`gate.py`](../../../src/manyu/gate.py) carries
`assert_not_noop`. Experiment 4's Stage 0a was voided by the same family: a base
rate of zero with a passing control, because
`ScenarioJSONProvider._belief_candidates` hardcodes `"contradicts": []`
([providers.py:438](../../../src/manyu/providers.py)) and the offline generation
path could not represent a contradiction at all.

> Wiring that cannot fail and wiring that cannot fire are the same mistake. In
> both, the number on the page is decided by something other than the world.

## 3. The reframed question

> Can Manyu derive from evidence alone that two rivals are indistinguishable,
> hold that while the rest of the machinery pushes against it, **break it when
> evidence arrives that does separate them**, and express it rather than
> asserting one side?

Four things can fail there, where "can it hold underdetermination" cannot:

1. **Detection.** Given evidence that genuinely fails to separate two rivals,
   does the system notice *that* — without the fixture saying so? The hard one.
2. **Stability.** Does the state survive contact with the rest of the machinery?
   Two named threats, both real and both measured: the attention loop (§5.2,
   experiment 4 §5.1) and ordinary evidence accumulation.
3. **Correct collapse.** Hand it evidence that *does* discriminate and it must
   pick. A system that never collapses is not humble, it is broken. Without this
   arm, "it held" is not evidence of anything (§11).
4. **Expression.** Does the state change what Manyu says and does, or is it
   another readout nobody reads — `MergedDissonanceQuery` before experiment 4
   §6, `RevisionEngine` before experiment 3 §13.

(1) and (3) together are the result worth publishing. "Manyu can represent its
own ignorance" is a demo; "Manyu derives underdetermination from the evidence
pattern, and gives it up exactly when the evidence separates" is a finding, and
#6 consumes it directly.

## 4. Scope

### In scope

- **Stage 0** — what the substrate already does to a symmetric rival pair, with
  nothing new built. It can end the experiment (§8).
- **The representation** — underdetermination as a belief, with a
  machine-readable rival set, subject to every rule any other belief obeys (§5.3,
  FR-2).
- **Derivation from the evidence pattern**, never from a fixture declaration
  (§7).
- **The three-fixture control set**: symmetric, discriminating, and the near-miss
  (§11).
- **Stability against the experiment-4 attention loop** (§5.2).
- **Expression** — what a report says when a rival set is live, scored on
  citation metrics only (§12).

### Out of scope (deferred)

- **Enumerating what evidence would separate the rivals.** That is #6, and it is
  the whole of #6. Here the state is represented and held; there it is
  interrogated.
- **The cosmology domain as anything but a live confirmation.** Stages 0–4 run on
  cheap synthetic pairs. See §14, open question 5.
- **Changing `_tension` or the dissonance detector.** Experiment 4 §12's
  constraint stands and this experiment inherits it, not re-opens it.
- **Changing the honesty scorer.** Frozen at 1.6.0.
- **Multi-agent disagreement about what is underdetermined** — experiment 9.
- **Acting on the state** — choosing to go looking for separating evidence is
  #6 territory; here the state is held, not acted on.

## 5. What exists to represent it, and what does not

Surveyed in code before scoping, on the experiment 4 §5 pattern.

| Surface | Where | State |
|---|---|---|
| `contradicts` edge | [schemas.py:463](../../../src/manyu/schemas.py) | Exists. Records *conflict*, not *indistinguishability* — it cannot say the conflict is unresolvable |
| `BeliefStatus.CONTESTED` | [schemas.py:116](../../../src/manyu/schemas.py) | Exists. A per-belief flag, not a relation between rivals, and it says nothing about whether evidence could settle it |
| `BeliefType.UNCERTAINTY` | [schemas.py:101](../../../src/manyu/schemas.py) | Exists in the enum and in the extractor schema. **Nothing populates it** except `fork.py`'s D2 harness ([fork.py:242](../../../src/manyu/fork.py)) |
| `Belief.uncertainty` | [schemas.py:467](../../../src/manyu/schemas.py) | Free text. Merged last-writer-wins (`candidate.uncertainty or belief.uncertainty`, [services.py:877](../../../src/manyu/services.py)) and **parsed by nothing** |
| A rival set | — | **Does not exist** |

So the backlog is right that this is a schema change and not a service change.
Two further findings from the survey are load-bearing enough to have their own
sections.

### 5.1 A contested belief still speaks with full voice, averaged

`WorldviewSynthesizer.synthesize`
([services.py:890](../../../src/manyu/services.py)) composes stances from
beliefs whose status is in `{ACTIVE, CONTESTED}`, groups them by theme, and sets
the stance confidence to the **arithmetic mean** of the group.

Two rivals at 0.5 each therefore become one stance at 0.5. The standoff is not
suppressed, not flagged, and not visible — it is *averaged into a mediocre
opinion*, which is the one output shape that cannot be distinguished from
ordinary uncertainty by anything downstream.

**Confirmed by Stage −1, with a qualification that is a trap for Stage 4.**
`BeliefUpdater._create` ([services.py:835](../../../src/manyu/services.py))
stamps `TENTATIVE` on any candidate created below 0.45 confidence, and
`synthesize` filters on `{ACTIVE, CONTESTED}`. A rival created below that
threshold is therefore not averaged into a mediocre stance — it is **excluded
from composition entirely, and silently**.

The consequence for this experiment: *the meta-belief must be created at or
above 0.45 or it is invisible to the synthesizer*, and Stage 4 would measure
nothing for a reason that has nothing to do with underdetermination.

**And the threshold does not track what a belief currently is.** Status is set
once at creation and by contradiction, and never recomputed from confidence, so
a belief charged down to 0.1 stays `CONTESTED` and stays composed while one
created at 0.4 and never touched does not. Whether a belief is *expressed* is a
function of its creation confidence and its contradiction history. Any Stage 3
reading that treats "still composed" as "still believed" is reading the wrong
thing.

Pinned in
[`tests/test_underdetermination_substrate.py`](../../../tests/test_underdetermination_substrate.py).

### 5.2 The tie is already broken, alphabetically

`AttentionLoop._direction`
([salience.py:546](../../../src/manyu/salience.py)) resolves which side of a
conflict gets charged. Where the graph declares a direction it is used; where
both sides declare — a *mutual* conflict, which is what a symmetric rival pair
is — there is no declared direction, so it is **broken by sorted belief id** and
labelled `"mutual"`.

The label is honest and deliberate: analysis can exclude mutual cases rather
than discover them in the residuals. But the loop still acts. Collapse-to-a-guess,
by alphabetical order, is already shipped.

**With one mitigation already in place, which Stage 0 must account for.**
`assert_contradiction` is idempotent via `_was_asserted`
([revision.py:377](../../../src/manyu/revision.py)), and ingest already prices
every extractor-declared contradiction
(`ManyuCore._price_contradictions`, [core.py:337](../../../src/manyu/core.py)).
So a mutual pair charged at ingest is *inert* by the time the loop reaches it —
the loop records `moved = 0` and moves on. The alphabetical tie-break bites only
where the pair reaches the loop unpriced, or where only one side declares the
edge. Which of those a real web produces is a Stage 0 measurement, not a guess.

**Stage −1 confirms both halves**, with a positive control so that "inert" cannot
mean "the loop is broken": a pair reaching the loop through `fork.seed_beliefs`,
which does not price (`SEEDS_ARE_UNPRICED`), *does* move. So the alphabetical
tie-break is real and reachable — it is simply not on the path a live web takes.
Its practical significance is now smaller than §6.1's one-way collapse, which
needs no loop at all.

### 5.3 Why a belief and not a relation

The alternative — an `UnderdeterminedSet` object holding member belief ids — is
easier to compute over and stays outside everything experiments 1–3 built. The
decision goes the other way, and the reason is falsifiability rather than
elegance:

- **It gets provenance for free, and provenance is the point.** A belief cannot
  be stored without evidence of its own (`INSUFFICIENT_PROVENANCE`). The
  underdetermination belief's evidence is *precisely the evidence that fails to
  separate the rivals* — so the claim carries its own receipts, and the reason
  the state exists is auditable rather than asserted.
- **It can be wrong, through the ordinary pathway.** `blend_confidence`
  ([revision.py:250](../../../src/manyu/revision.py)) is bidirectional since
  experiment 3. Evidence that separates the rivals is disconfirming evidence
  *for the meta-belief*, so it loses confidence with no bespoke rule anywhere.
  **That is the experiment's cleanest dependent variable** (FR-6), and the
  relational version does not have one — a set object has no confidence to move.
- **The honesty scorer and the revision engine already work on it.** "Why do you
  think you cannot tell these apart?" is scoreable against the log by the
  existing instrument, which is the strongest possible test of experiment 1's
  deliverable and costs nothing to obtain.

**The rule this implies, and it is not negotiable:** the underdetermination
belief is **subject to every rule any other belief obeys**. No special-casing, no
exemption from pricing, no bypass of provenance, no protection from revision. The
moment it needs an exemption to survive, flavour A of §2 has occurred and the
result is about our exemption rather than about Manyu.

## 6. What the substrate may already force

Stage 0's job, and it can end the experiment.

Contradiction pricing is `1/(supporters + own evidence + contradictors)` scaled
by the contradictor's confidence
(`_contradiction_share`, [revision.py:568](../../../src/manyu/revision.py)). For
a mutual pair with equal grounding both shares are equal — and ingest snapshots
every contradictor's strength **before charging any of them**
([core.py:355](../../../src/manyu/core.py)), so the batch is atomic and the two
charges are symmetric.

That mitigation exists for a reason worth quoting, because it is this
experiment's question found and fixed in another guise:

> Charging sequentially made mutual contradictions order-dependent: the first
> charge weakened its target, and if that target was itself a contradictor its
> own charge then landed softer, settling the pair at 0.6/0.4 **with the split
> decided by extractor emission order**.

A symmetric pair may therefore already sit in a stable standoff — charged once,
equally, and then inert. If so, "Manyu holds underdetermination" is already true
and the experiment shrinks: what remains is that the state is **indistinguishable
from two mediocre beliefs** (§5.1), which is a smaller and much cheaper claim.
Either outcome is worth having. Neither may be assumed.

### 6.1 Measured (Stage −1): the standoff holds, but only for mutual edges

Two readings of the same two evidence records, both at confidence 0.7, each
declaring the contradiction. Both are charged `1/3 × 0.7 = 0.2333`, both land at
**0.4667, and the gap is exactly zero** — unchanged when the candidate order is
reversed, and inert when the attention loop arrives. So for a *mutual* pair the
substrate does hold the tie, and §5.2's alphabetical tie-break never gets to bite.

**With one edge instead of two, the same pair separates by the full penalty.**
Same beliefs, same shared evidence, same confidences: only the target is charged,
the declaring side keeps 0.7, and the gap is 0.2333.

> **So which reading survives at full confidence is decided by which one the
> extractor happened to phrase as contradicting the other.** That is not an
> epistemic fact about the evidence, and it is a worse mechanism than the
> alphabetical tie-break — that one is at least labelled `"mutual"` where it fires.

The consequence for staging: §6's question is answered **only for mutual pairs**,
so the claim shrinks only to the extent that live webs produce them. Whether they
do is an empirical question, it is not answerable offline (§7), and it belongs to
the paid stage. Stage 0 must therefore run both edge topologies, not one.

**This is flavour B and it must be measured before anything is built on top of
it**, exactly as experiment 3's ablation was needed to say whether ripple was a
finding or a consequence.

## 7. The authoring constraint

Carried from experiment 4 §8 and it is the hardest constraint in this spec.

**A fixture may author which beliefs exist, what evidence they hold, and how that
evidence is shared. It may not author that they are underdetermined.**

The moment a fixture declares a rival set — a `belief_type: underdetermination`
candidate, an `underdetermined: true` field, a hand-written meta-belief — the
dependent variable has passed back through something typed in, and detection
becomes a read-back of the fixture. The state must be **derived from the evidence
pattern** by a mechanism that could have failed to derive it.

The check before any fixture is admitted, unchanged from experiment 3 §4: *does
the DV pass back through anything I typed?*

Corollary that constrains the offline path: the scenario provider must be able to
emit two candidates that share evidence records and contradict each other,
**without** emitting the meta-belief. Verify that before reading any Stage 0
number — the generation-path check that experiment 4's authored control could not
have performed, because it exercised the detector while the defect was upstream.

## 8. Staging — the ladder, cheapest rung first

Each rung can end the experiment. The ordering is the design.

| Stage | LLM | n | Establishes | Can end it? |
|---|---|---|---|---|
| 0 — what the substrate already does | none | 1 | Confidence-gap trajectory on a symmetric rival pair through existing ingest + the experiment-4 loop, with nothing new built. Which side the tie-break takes. What the synthesizer emits (§5.1) | **Yes** — a stable standoff shrinks the claim to §6's smaller one |
| 0b — base rate | none | 1 | How often shared-evidence rivals occur on a naturalistic run, against a generation-path check that runs *first* (§7) | **Yes** — reframes to fixture-only |
| 1 — the representation | none | 1 | The meta-belief exists, is derived, is persisted, and is reachable on core/CLI/MCP. *Prerequisite* | No |
| 2 — correct collapse | none | 1 | The three-fixture control set (§11). The discriminating arm **must** collapse | **Yes** — a state that never breaks is not a result |
| 3 — stability | none | 1 | Survives the experiment-4 attention loop under scarce attention, and survives non-separating evidence accumulation | Yes |
| 4 — expression | none | 1 | What a report says with a live rival set; scored on citation metrics only | No |
| 5 — live confirmation | yes | 10 | Does a real model produce shared-evidence rivals on the cosmology case, or just pick one? Does the state hold across turns? | No |

Stages 0–4 are deterministic under `FrozenClock` where they consume no provider,
so `n=1` is correct — repetition re-measures the same arithmetic (experiment 2
methodology §1). Stage 5 takes a variance pilot before committing to *n*.

**Stage 2 before stage 3 is deliberate.** Collapse is the arm that can fail
cheaply and it is the one that licenses reading stability at all. Running
stability first would risk a whole stage of "it held" with nothing establishing
that breaking was available.

## 9. Functional requirements

**FR-1 — Underdetermination is derived, never declared.** The mechanism reads the
evidence pattern off the store and emits the meta-belief, or does not. No fixture
field, no extractor flag, no candidate type may assert it directly (§7).

**FR-2 — The meta-belief obeys every rule any other belief obeys.** Mandatory
provenance, ordinary pricing, ordinary revision, ordinary status transitions. Any
exemption required for it to survive is a defect report, not a fix (§5.3).

**FR-3 — Its evidence is the evidence that fails to separate.** The
`evidence_ids` of the meta-belief are exactly the records the criterion consulted
— so the claim is auditable, and the honesty scorer can be pointed at it without
new machinery.

**FR-4 — The rival set is machine-readable.** Belief ids, not prose. Experiment
4 §6's lesson: a signal readable only by a human is not a surface.

**FR-5 — Reachable across a process boundary.** `ManyuCore`, CLI and MCP,
verified by driving it in one process and reading it in the next — experiment 3
§13's property, because an in-process-only surface is not a surface.

**FR-6 — The meta-belief's own confidence is the primary dependent variable.**
Its trajectory is recorded per turn across every arm. Collapse is that confidence
falling as separating evidence arrives; stability is it not falling when
non-separating evidence arrives.

**FR-7 — Arms are selectable and none is default.** Experiment 3 §13's rule: a
silent default settles the question by whichever branch a caller happened not to
think about, and `ContradictionArm` is the pinned precedent for what happens when
an arm is stored, stamped onto every result, and consulted by no branch.

**FR-8 — The criterion is derived, not chosen.** See §13.

**FR-9 — Grounding and evidence overlap are recorded on both rivals**, so §11's
near-miss arm is answerable from the run rather than by inspection.

**FR-10 — Every arm records what the synthesizer emitted** (§5.1), so expression
is measured rather than inferred from the store.

**FR-11 — The tie-break disposition is recorded on every mutual conflict**,
including whether the loop found the pair already inert (§5.2). Analysis must be
able to separate "the loop declined" from "the loop had nothing left to charge".

## 10. Pre-registered predictions

To be recorded **before any derivation code exists**, and dated. Left
deliberately unfilled at this revision — writing them after Stage 0's numbers are
visible is experiment 1's failure mode #1, the mock tuned to its own criterion,
and `assert_constants_pinned` exists to catch it.

What each must state before its stage runs:

| Question | Prediction to fix in advance |
|---|---|
| 0 substrate | What confidence gap counts as "collapsed" rather than "standoff" |
| 0b base rate | The rate below which the claim becomes fixture-only |
| 2 collapse | How far the meta-belief's confidence must fall on the discriminating arm to count as broken |
| 2 near-miss | That the near-miss arm holds, **and why the criterion cannot see the difference in volume** |
| 3 stability | The budget at which the attention loop is expected to break the state, if it does |
| 4 expression | What the report must contain to count as expressing the state rather than hedging |

**The honest risk, stated in advance:** prediction 2's near-miss is partly a
prediction about our own hand, since we write the criterion. The constraint is
that the criterion must be the most natural thing to write for *evidence that
does not separate two hypotheses*, not the thing that makes the near-miss pass.
If that argument comes to feel strained, this is where to say so. Experiments 3
§7 and 4 §10 carried the same clause and both earned it.

## 11. The control set — three fixtures, and the middle one is the experiment

| Fixture | Evidence shape | Required outcome | What it rules out |
|---|---|---|---|
| `symmetric_rivals` | Two hypotheses resting on the **same** evidence records, differing only in interpretation | Meta-belief derived and held | Nothing on its own |
| `discriminating` | Evidence that separates the rivals — present for one, absent for the other | Meta-belief **collapses** through the ordinary confidence pathway | Flavour A: a state that cannot break is a state we wrote |
| `near_miss` | *Plentiful* evidence, none of it separating — more records than `symmetric_rivals`, same non-separating structure | Meta-belief held, at comparable confidence | A criterion that counts evidence rather than reading whether evidence separates |

`near_miss` is the load-bearing one, and it is the direct descendant of
experiment 3's near-miss negative (same topic, near-identical wording, no edges →
zero movement) and experiment 4's `distractor_web`. A criterion that quietly
tracks evidence *volume* passes `symmetric_rivals` and `discriminating` and fails
here, and there is no other fixture in the set that could tell.

Both outcomes on `discriminating` are results, and the second is the stronger:

- **It collapses.** The state is falsifiable, and stage 3's stability reading
  means something.
- **It does not.** Then we built a state that survives its own disconfirmation,
  which is §2 flavour A caught in the act — reportable, and the experiment stops
  until the exemption is found and removed.

**A third outcome must be anticipated:** the meta-belief is derived on
`discriminating` too, because the criterion cannot see the separation. That is
not a failed run; it is the criterion being too coarse, and it is §13's problem
surfacing where it can be measured.

## 12. Measurement constraints inherited

Non-negotiable, from experiments 1, 3 and 4:

- **Honesty scorer**: citation metrics validated (sensitivity 0.79–0.90,
  specificity 1.00, chance floor 0.000 by derangement); failure-mode labels are
  **not** decision-grade (SC-5 at 67.9%, inter-rater agreement unmeasured). Stage
  4's expression read uses citation metrics only.
- **`DissonanceSignal.magnitude` may not be read as a measure of belief
  dynamics** — report `magnitude_raw`, carriers, and the saturation baseline
  alongside every delta (experiment 4 §12).
- **`_tension` takes `min(stake_a, stake_b)`**, so it reads the weaker party and
  is blind above that floor. For a *symmetric* pair the two parties are equal by
  construction, so this constraint bites less here than in experiment 4 — but
  `near_miss` and `discriminating` are asymmetric and it bites there. Do not read
  a tension delta as a read on the rival set.
- **Stake is blind to grounding** (experiment 4 §1): `stake_of` averages evidence
  salience rather than summing it, so one evidence record and five produce
  identical stake. `near_miss` is therefore invisible to the dissonance channel
  by construction — which is exactly why detection must not be built on it.
- **Under scarce attention the loop targets the best-corroborated beliefs**
  (experiment 4 §5.1). Stage 3 must sweep the attention budget rather than fix
  it; experiment 4 found the budget, not the arm, was the real independent
  variable.
- **Live webs are one hop deep** and about 1 extraction in 10 over-merges into a
  single belief with no edges (experiment 3 §3.4). Stage 5's *n* must absorb
  both, and an over-merge destroys a rival pair outright — it is a dropped
  sample, not a null.

## 13. What counts as "non-discriminating" must be derived, not chosen

Open, and it blocks Stage 1.

The criterion needs to say when evidence fails to separate two rivals. Choosing a
threshold after seeing Stage 0's distribution is experiment 1's failure mode #1,
and a free constant sitting at the centre of the decision is exactly what
experiment 3 removed twice — `attenuation = 0.6` in §11, where in a chain the
constant *was* the hypothesis, and `contradiction_penalty = 0.3` in §12. Both
were replaced by quantities read off the store, and both kept a `FIXED` ablation
pinned by a test showing it fail.

**A candidate shape with no constant in it**, to be decided with evidence rather
than adopted here: two rivals are underdetermined when every evidence record in
the union of their `evidence_ids` lies in the **intersection** — they rest on the
same records and differ only in what they make of them. Separating evidence is
then, structurally, a record held by one and not the other. Nothing is tuned; it
is read off the store.

**Its weakness is real and must be faced before Stage 1.** Perfect intersection
is strict, and live webs will rarely produce it — which sets up experiment 4's
Stage 0a all over again: a detection rate of zero that describes the criterion
rather than the world. The graded alternative (*mostly* shared evidence, or a
confidence gap below some epsilon) reintroduces the constant, and the epsilon
would *be* the hypothesis.

Stage 0b measures which risk is real before the criterion is fixed. Whatever is
chosen is pinned in methodology before the run that consumes it, **and changing
it afterwards voids that arm.**

## 14. Open questions for the design phase

1. **When is the meta-belief derived** — at ingest, at reflective turn, or on
   demand? Deriving at ingest means it competes with the rivals it describes in
   the same batch, and §6's atomic-pricing snapshot may or may not cover it.
2. **Does it need a new `BeliefType`?** `UNCERTAINTY` exists and is unused, but
   it means generic hedging, and overloading it would make the two
   indistinguishable in every downstream query. A new member costs an extractor
   schema change and an enum migration.
3. **What happens to the rivals' own status?** They are `CONTESTED` already.
   Whether they *also* need marking, or whether the meta-belief pointing at them
   is sufficient, decides how much of the substrate this touches.
4. **How does the synthesizer express it** (§5.1)? Suppressing the averaged
   stance, emitting both, or emitting the meta-belief in its place are three
   different behaviours and the choice must precede Stage 4.
5. **Cosmology, and when.** The time-dependent vs. location-dependent case on a
   single light cone is the crux's standout tie-in and the hardest thing to
   author without leaking the answer into the fixture (§7). Proposed: synthetic
   pairs for stages 0–4, cosmology for Stage 5 only, where the model produces the
   rivals and we do not.
6. **Does the meta-belief participate in dissonance?** It contradicts nothing, so
   the detector will not see it — but a belief describing a conflict, sitting
   outside the conflict, may be the wrong shape. Decide before Stage 3.

## 15. Carried-over method

Standing practice from experiments 1–4, not restated per stage:

- **Write the criterion a decision rests on before running what could settle
  it.** Experiment 3 found four defects this way, including one that broke the
  standard its own §5 was decided on.
- **Check the generation path before reading any number off it.** Experiment 4's
  Stage 0a was void because the positive control sat on the detector while the
  defect was upstream. A control has to sit on the path that could be broken.
- **Probe inputs the author did not have in mind** — self-reference, mutual
  relations, repeated application, zero-valued operands.
- **Treat an impossible value as a defect report.**
- **Assert a mechanism can change its output before reading what it says.**
- **Every arm ships a positive control in the same run.** A null without a
  passing control is a bug, not a finding.
- **Pilot for variance before committing to full *n*.**
- **Drop-one robustness runs inside analysis, not after it.**
- Run [`gate.py`](../../../src/manyu/gate.py) before any stage's numbers are
  readable — `assert_not_noop` on the derivation (§2 flavour C) and
  `assert_has_range` on the meta-belief's confidence, since a state pinned at one
  value makes every downstream reading unreadable.
- **Extend the mutant battery.** Experiment 4's
  [`test_salience_mutants.py`](../../../tests/test_salience_mutants.py) holds ten
  catalogued mutants, each reproducing a historical defect family. This
  experiment adds at least: a criterion reading evidence *volume* instead of
  overlap, a meta-belief exempt from pricing, and a derivation that cannot fire.

**The reason this section exists:** experiment 3 shipped sixteen defects and its
own test suite caught none. Experiment 4 caught eight, **none by a test written
after the code**. The cause is structural rather than careless — a test written
minutes after the mechanism, by the same author, shares its assumptions and
agrees with the code precisely where the code is wrong. Every defect in both
experiments was the same shape: **a quantity that looked right and meant
something else.**

## 16. Prerequisites, unclosed

1. **Experiment 4 stages 0a and 0b remain blocked** on a provider that can emit
   `contradicts`, which makes its base-rate question a paid one. This experiment
   inherits the same gap at Stage 0b and the two should be answered by one spend,
   not two.
2. **Rotate the API key** used for experiment 3 Stage 4 — it was pasted into a
   chat transcript. Carried from experiment 3 §6 and still open.
3. **Retry `/code-review ultra exp03-base`.** The cloud review failed and was
   never re-run, so every fix in the revision engine this experiment consumes was
   verified by its author alone.
