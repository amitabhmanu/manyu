# Experiment 6 — "What Would Change My Mind": Requirements

**Status:** spec (no code)
**Date:** 2026-08-11
**Backlog entry:** [../../experiments_backlog.md](../../experiments_backlog.md)
**Related:** [crux #6](../../Manyu_experiments_crux.md) · [experiment 3](../03-foundationalism-quinean-web/requirements.md) · [experiment 4](../04-dissonance-control-signal/requirements.md) · [experiment 5](../05-underdetermination/requirements.md) · [experiment 5 results](../05-underdetermination/results.md)

## 1. Purpose

Every experiment so far reads the store backwards. Provenance says *why Manyu
believes this*; revision says *what happened when evidence arrived*; experiment 5
says *why these two cannot be told apart*. All of it is retrospective.

This experiment points the same machinery forwards.

> Given a position Manyu holds, can it name the specific evidence that would
> move it, say **by how much**, and be right about the number?

The crux frames it as a steelman machine — hand it a position, have it revise
toward the strongest opposing view, logging what would move it and by how much.
The auditable core of that is narrower and is what this spec builds: a
**counterfactual pricing engine** whose predictions can be checked by delivering
the evidence and measuring.

**Why it sits here.** It inverts #5. Once Manyu can say *I cannot tell these
apart*, the next question is *what would tell them apart* — and experiment 5's
rival fixtures supply the one class of belief where the right answer is fixed by
construction rather than by our judgement (§11).

### 1.1 Two corrections to the backlog entry, before anything is built

**The backlog says this experiment "uses the counterfactual machinery built for
#5." That machinery does not exist.** Experiment 5 built detection and
derivation — `is_underdetermined`, `evidence_overlap`, `derive`
([underdetermination.py](../../../src/manyu/underdetermination.py)) — none of
which is counterfactual. `separating_evidence`
([underdetermination.py:91](../../../src/manyu/underdetermination.py)) is the
nearest thing and it is still retrospective: it names which records *already in
the store* lie in the symmetric difference. Nothing anywhere prices a record
that does not exist yet. This experiment builds that from scratch on top of
experiment 3's pricing. It is a build, not a consumption, and the effort estimate
should say so.

**The load-bearing dependency is #3, not #5.** #5 supplies the best *test
subject*; the arithmetic every prediction rests on is `blend_confidence` and
`_contradiction_share` ([revision.py](../../../src/manyu/revision.py)), which per
experiment 5 results §7 have been verified by their author alone. See §16.

## 2. The trap, for the fourth time — and the escape

Three experiments running were settled by wiring rather than by evidence:
experiment 3 by mandatory provenance making collapse unrepresentable (§11.1),
experiment 4 by "write the branch that reads the signal and the signal changes
behaviour" (§2), experiment 5 by "add the status and the branch that refuses to
collapse, and of course it holds" (§2).

The same trap is here and it is the most obvious instance yet. Write a function
that enumerates what would change Manyu's mind, and of course it enumerates
something. A list is not a finding.

**But this experiment has an escape the other three did not have, and it is the
reason it is worth running at all.**

> The prediction is checkable by doing it. `blend_confidence` plus experiment 3
> §12's `1/(supporters + own evidence + contradictors)` pricing is deterministic,
> so "record R would move belief B to 0.117" is not a judgement — it is a
> forward simulation with a number attached. We can then deliver R and measure.

Predicted Δ against observed Δ is a dependent variable that no branch we write
decides. That is what §3 is built around, and §5.1 is honest about exactly how
far it goes before it becomes a tautology.

## 3. The reframed question

> Can Manyu enumerate evidence that would move a belief it holds, price each item
> in advance, be **right** about the price when the evidence is actually
> delivered, and say how much of it would be needed — with the enumeration
> auditable against the log?

Four things can fail there, where "can it list what would change its mind" cannot.

1. **Enumeration.** Does it name evidence that would genuinely move the belief,
   rather than restating the belief's negation? The negative control does the
   work: irrelevant evidence must be priced at ~0 **and** must actually move it
   ~0 when delivered.
2. **Calibration.** Does predicted Δ match observed Δ? The prediction is near
   tautological on the direct-injection path and stops being so the moment the
   extractor is in the loop (§5.1). **The size and location of that gap is the
   finding**, not the agreement.
3. **Dose.** How *many* such records would it take to move the belief past a
   threshold that matters? Confidence movement compounds against rising
   entrenchment (§5.2), so the honest output is not a list but a list with
   counts.
4. **Receipts.** The enumeration cites the beliefs, records and mechanism it
   consulted, and experiment 1's honesty scorer reads that against the log.

**(2) and (3) are the publishable pair.** "Manyu can list what would change its
mind" is a demo. "Manyu prices the change in advance, is right to within *x*, and
tells you it would take five of them" is a finding, and #7 consumes it directly
— an agent that can price what would move *itself* is one step from pricing what
would move an observer.

### 3.1 The uncomfortable answer, pre-registered as an outcome

`RevisionConfig` caps inertia strictly below 1.0
([revision.py:174](../../../src/manyu/revision.py)) so that **no belief is
unfalsifiable**. Nothing bounds the *dose*. If entrenched beliefs need forty
records, the engine emits an honest-looking list of things that would work in
principle and never do in practice.

That is not a failed run. It is a safety-relevant result about a transparent
agent, it is the bridge to #7, and it is recorded in pre-registration §6 in
advance so it cannot be argued into a null afterwards.

## 4. Scope

### In scope

- **Stage −1** — what the substrate already does to a counterfactual, with
  nothing new built. It can end the experiment (§6).
- **A counterfactual pricing engine**: given a belief and a hypothetical evidence
  record, the confidence the belief would take, computed without mutating the
  store (§5.4, FR-1).
- **Enumeration** of candidate mind-changers for a belief, derived from the
  store's own structure, never authored (§7, §13).
- **The calibration arm**: predicted Δ versus observed Δ, on both the direct
  path and the extractor path (§8 stage 1).
- **The dose arm**: records required to cross a stated threshold, and the
  entrenchment census over a whole web (§8 stage 2).
- **Receipts** as a machine-readable structure, scored on citation metrics only
  (§12).

### Out of scope (deferred)

- **The steelman framing as anything but the paid stage.** Manyu revising toward
  the strongest opposing view is the better paper and the worse experiment: the
  opposing view is generated, so the dependent variable passes back through the
  model. Stages −1 to 2 run on pricing-verification, where it does not. See §8.
- **Acting on the enumeration** — going and looking for the evidence is agency,
  not counterfactual reasoning, and it belongs to no experiment yet scheduled.
- **Changing the honesty scorer.** Frozen at 1.6.0.
- **Changing `blend_confidence`, contradiction pricing, or `_tension`.**
  Experiments 3 and 4 fixed these and this experiment measures against them
  rather than re-opening them. If the dose result is ugly, the ugliness is the
  finding (§3.1).
- **Multi-agent "what would change *your* mind"** — experiment 9.
- **Evidence *quality* modelling.** A hypothetical record carries a confidence
  and a salience and nothing else. Modelling how believable a source is, is
  experiment 8's territory.

## 5. What exists to price a counterfactual, and what does not

Surveyed in code before scoping, on the experiment 4 §5 and experiment 5 §5
pattern.

| Surface | Where | State |
|---|---|---|
| `blend_confidence` | [revision.py:250](../../../src/manyu/revision.py) | Exists. Pure function of `(belief, candidate_confidence, config)` — **already a counterfactual pricer** for the corroboration/disconfirmation path, and nothing calls it that way |
| `_contradiction_share` | [revision.py:568](../../../src/manyu/revision.py) | Exists. Prices a contradictor from grounding. Private, and takes an `agent_id` plus live store reads |
| `_support_share` | [revision.py:543](../../../src/manyu/revision.py) | Exists. Same shape, for the propagation path |
| `RevisionEngine.retract` / `assert_contradiction` | [revision.py:275, 322](../../../src/manyu/revision.py) | Exist, and **mutate**. There is no dry-run flag anywhere |
| `separating_evidence` | [underdetermination.py:91](../../../src/manyu/underdetermination.py) | Exists, and is **retrospective** — the symmetric difference of records already stored. Not an enumeration of what could arrive |
| A hypothetical evidence record | — | **Does not exist.** `BeliefEvidence` is a stored row; nothing represents an unstored one |
| A predicted-versus-observed record | — | **Does not exist** |
| Dose / entrenchment | — | **Does not exist**, and is derivable (§5.2) |

So the parts exist and the composition does not, which is the same position
experiment 3 §13 found `RevisionEngine` in and experiment 4 §6 found
`MergedDissonanceQuery` in. Three findings from the survey are load-bearing
enough to have their own sections.

### 5.1 The prediction is nearly a tautology — and here is exactly where it stops being one

`_revise` ([services.py:850](../../../src/manyu/services.py)) computes the new
confidence with `blend_confidence(belief, candidate.confidence, config)` and
nothing else. So a "prediction" that calls the same function with the same
arguments will agree to the last bit, and reporting that agreement as calibration
would be experiment 1's mock tuned to its own criterion in a new costume.

**Say it plainly in the results rather than discovering it in review:** on the
direct-injection path, predicted equals observed by construction, the check is a
regression test, and it is reported as one.

The prediction becomes falsifiable at four named places, and each is a live
defect risk rather than a hypothetical:

1. **The `new_evidence` guard.** `_revise` returns the belief *untouched* when
   the candidate carries no evidence the belief does not already hold
   ([services.py:851](../../../src/manyu/services.py)). A pricer that ignores
   this predicts movement where the substrate delivers exactly zero.
2. **Stability, and therefore inertia, moves during the delivery.**
   `stability = clamp(max(belief.stability, candidate.stability) + 0.05)`
   ([services.py:871](../../../src/manyu/services.py)) is applied in the same
   revision, so a multi-record prediction that holds inertia fixed drifts.
3. **The extractor sits between the hypothetical and the store.** Whether a
   record lands as a fresh belief, merges via `belief_key`, or emits a
   `contradicts` edge is decided upstream of any pricing. This is experiment 4's
   void Stage 0a and experiment 5 §6.1's one-way-edge accident arriving for the
   third time, and it is why stage 1 runs both paths.
4. **Propagation.** A record that moves belief B also moves B's neighbours across
   `supports`. A single-belief prediction is silent about a web-wide effect that
   `PropagationResult.total_movement` already measures.

> The gap between the direct path and the extractor path **is** the experiment.
> Agreement on the direct path is bookkeeping.

### 5.2 The dose is derivable, and no constant needs choosing

Inertia is `inertia_base + inertia_span * stability` with `base = 0.5` and
`span = 0.4` ([revision.py:174](../../../src/manyu/revision.py)), so it rises
from 0.5 to a hard ceiling of 0.9, and `stability` rises by 0.05 per revision
that carries new evidence ([services.py:871](../../../src/manyu/services.py)).

Against a repeated disconfirming candidate at confidence *c*, each delivery moves
the belief a fraction `1 − i` of its remaining distance to *c*. Two consequences
fall straight out of the arithmetic, with nothing tuned:

- **Every belief is movable.** `i ≤ 0.9`, so the distance to *c* shrinks by at
  least 10% per record and the sequence converges. This is the cap's documented
  purpose and it now has a use.
- **The dose is a closed form, and it grows with entrenchment.** The number of
  records to carry a belief from its current confidence past a threshold is read
  off the store — current confidence, current stability, and the candidate's
  confidence — with no free parameter anywhere.

**This is the one quantity in the experiment that satisfies FR-8 by
construction**, on the pattern that removed `attenuation` and
`contradiction_penalty` in experiment 3 §§11–12.

**One caveat that must be carried into stage 2.** Where the candidate's
confidence is itself a function of the store, the closed form does not apply and
the trajectory has to be simulated. Experiment 5's collapse arm is exactly that
case — the meta-belief's candidate confidence is the Jaccard overlap, which falls
as separating evidence accumulates, which is why its deltas (0.153, 0.153, 0.123,
0.095, 0.072, 0.056) are not geometric. Do not fit a curve to that and call it
inertia.

### 5.3 Experiment 5 already ran this experiment once, by accident

Results §3.1 reports the trajectory of the underdetermination meta-belief under
accumulating separating evidence, and concludes:

> **It takes five separating observations before Manyu stops saying it cannot
> tell the readings apart.**

That is a dose answer, produced without a dose mechanism, for one belief. This
experiment generalises it — and inherits its interpretive problem intact. The
same number reads two ways (inertia working as designed, or a state that survives
its own disconfirmation at 0.847 being unfalsifiable in practice) and experiment
5 correctly said one record could not settle which. **A census over many beliefs
can**, which is stage 2's justification for existing.

**Stage −1 must reproduce that trajectory from the pricing engine before the
engine is trusted for anything else.** It is the only published dose figure in
the project, it was produced by a different code path, and a pricer that cannot
re-derive it is wrong.

### 5.4 Pricing must not mutate, and there are two ways to arrange that

`RevisionEngine`'s methods write. A counterfactual that writes is not a
counterfactual, and a counterfactual that writes and then rolls back is a defect
waiting for the first exception. Two candidate shapes, decided in design (§14
q1):

- **Analytic** — a pure function over `(Belief, hypothetical candidate, config)`,
  no store writes at all. Exact for the single-belief case, and cannot see
  propagation or the extractor.
- **Replay** — copy the agent into a scratch `:memory:` store
  (`ManyuStore.export_agent`, [store.py:665](../../../src/manyu/store.py)) and
  run the real path against the copy. Sees everything; is slower, and is only as
  faithful as the export.

They are not alternatives so much as the two arms of stage 1: **the analytic
pricer is the prediction and the replay is the observation**, and where they
disagree is where §5.1's four defect risks live.

## 6. What the substrate may already force

Stage −1's job, and it can end the experiment. Two named risks, both flavour B of
experiment 5 §2 — the answer forced by the architecture before anyone writes
anything.

**Risk one: enumeration is trivially complete.** The only evidence that moves a
belief is evidence it does not already hold (§5.1 item 1), and what such a record
would do is fully determined by its confidence and its edges. If so, "what would
change my mind" has a one-line answer for *every* belief in the store — "a
disconfirming record you don't already have" — and the interesting content is
entirely in the dose, not the enumeration. Stage −1 measures this before
enumeration is built. If it holds, §3's item 1 shrinks to a negative control and
the experiment reweights onto (2) and (3).

**Risk two: the price is blind to content.** `blend_confidence` reads the
candidate's confidence and the belief's stability. It does not read what the
record *says*. So two hypothetical records with the same confidence are priced
identically no matter how differently they bear on the proposition, and the
engine's "specific evidence" is specific only in its prose. Whether that is fatal
or merely a stated limit depends on whether the edges (`contradicts`, `supports`)
carry the content — and those are emitted by the extractor, which puts the answer
on the paid path again.

Neither may be assumed. Both are cheap to measure and both are measured first.

## 7. The authoring constraint

Carried from experiment 4 §8 and experiment 5 §7, and it bites differently here.

**A fixture may author which beliefs exist and what evidence they hold. It may
not author what would change Manyu's mind about them.**

The moment a fixture carries a `would_change_mind` block, a hand-written list of
counterfactual records, or an expected Δ, enumeration becomes a read-back and
calibration becomes a comparison of our arithmetic against our own expectation.

The check before any fixture is admitted, unchanged from experiment 3 §4: *does
the DV pass back through anything I typed?*

**Where the ground truth comes from instead.** Experiment 5's rival fixtures have
a right answer fixed by structure rather than by authorship: for a pair whose
evidence sets are identical, the records that would move the meta-belief are
exactly those cited by one rival and not the other — `separating_evidence`'s
definition, written before this experiment existed and for another purpose. So
enumeration can be graded against a target nobody typed into a fixture. That is
why stage 0 runs on `evals/fixtures/exp05/` rather than on new fixtures.

## 8. Staging — the ladder, cheapest rung first

Each rung can end the experiment. The ordering is the design.

| Stage | LLM | n | Establishes | Can end it? |
|---|---|---|---|---|
| −1 — what the substrate forces | none | 1 | Whether enumeration is trivially complete (§6 risk one); whether price is content-blind (§6 risk two); re-derivation of experiment 5 §3.1's five-record trajectory from the pricer (§5.3) | **Yes** — either risk landing reweights or ends it |
| 0 — enumeration against structural ground truth | none | 1 | Enumeration graded on `evals/fixtures/exp05/`, where the right answer is fixed by structure (§7). Negative control: irrelevant evidence priced at ~0 | **Yes** — an enumerator that cannot beat "everything" is not one |
| 1 — calibration | none | 1 | Predicted Δ (analytic) versus observed Δ (replay), on the direct path and the extractor path separately (§5.4). The direct path is reported as a regression test (§5.1) | **Yes** — an uncorrectable gap ends it |
| 2 — dose and the entrenchment census | none | 1 | Records to cross a threshold, per belief, over a whole web. Distribution, not an anecdote (§5.3) | No — §3.1's ugly answer is a result |
| 2b — dose under corroboration | none | 1 | How far stage 2's dose understates when confirming evidence arrives alongside the disconfirming records (§14.5) | No |
| 3 — receipts | none | 1 | The enumeration's citations scored against the log, citation metrics only (§12) | No |
| 4 — live steelman | yes | 10 | The model proposes the mind-changers; we price and deliver them. Does a real model name evidence the pricer agrees is separating, or restate the negation? | No |

Stages −1 to 3 are deterministic under `FrozenClock` and consume no provider, so
`n = 1` is correct — repetition re-measures the same arithmetic (experiment 2
methodology §1). Stage 4 takes a variance pilot before committing to *n*.

**Stage 0 before stage 1 is deliberate.** Calibrating a pricer against a list
nobody has shown to be non-trivial would produce a beautiful correlation between
two things we wrote.

**Stage 4 is the only paid rung and the only one where the steelman framing
appears.** Four free rungs can kill the experiment before the expensive framing
is committed to. This is the scoping decision recorded on 2026-08-11: build
against pricing-verification, hold the steelman for the paid stage.

## 9. Functional requirements

**FR-1 — Pricing never mutates.** A counterfactual evaluated against the live
store must leave it byte-identical, verified by comparing `export_agent` before
and after rather than by inspection (§5.4).

**FR-2 — Every predicted Δ is recorded with the observation that tested it, or
with an explicit note that none was taken.** A prediction without a paired
observation is not a result and must not be countable as one.

**FR-3 — Enumeration is derived from the store, never declared.** No fixture
field, no extractor flag, no authored list (§7).

**FR-4 — The enumeration is machine-readable.** Belief ids, evidence ids, and a
numeric price per item. Experiment 4 §6's lesson: a signal readable only by a
human is not a surface.

**FR-5 — Reachable across a process boundary.** `ManyuCore`, CLI and MCP,
verified by driving it in one process and reading it in the next — experiment 3
§13's property.

**FR-6 — Predicted-versus-observed Δ is the primary dependent variable**, and
the dose is the secondary. Both are recorded per belief, per path (direct and
extractor), per stage.

**FR-7 — Paths and arms are selectable and none is default.** Analytic versus
replay, direct versus extractor. Experiment 3 §13's rule, and `ContradictionArm`
is the pinned precedent for an arm that is stored, stamped onto every result and
consulted by no branch.

**FR-8 — The dose contains no free constant.** It is read off current
confidence, current stability, and the candidate's confidence (§5.2). Any
threshold that enters — what confidence counts as "changed" — is registered in
advance, not chosen from the distribution.

**FR-9 — The `new_evidence` guard is asserted, not assumed.** A test must show
the pricer returns exactly zero for a record the belief already holds
([services.py:851](../../../src/manyu/services.py)), because that is the one
prediction where the substrate's answer is exactly 0.000 and any other number is
a defect.

**FR-10 — Propagation is recorded alongside every single-belief price.** A
record that moves the target also moves its neighbours; reporting the target
alone understates the counterfactual (§5.1 item 4).

**FR-11 — Every enumeration records what it declined.** Analysis must be able to
separate "the enumerator found nothing" from "the enumerator found things and
priced them at zero" — experiment 4 §5.2's "the loop declined" versus "the loop
had nothing left to charge", in a new place.

## 10. Pre-registered predictions

Recorded in [pre-registration.md](pre-registration.md), written **before any
pricing code exists**, and covering stages −1 through 2. Stages 3 and 4 are
registered when their stage is reached and before it runs.

Choosing a threshold after seeing the distribution is experiment 1's failure mode
#1 — the mock whose own comment said its output was tuned to sit just below the
ceiling — and `assert_constants_pinned` exists to catch it.

## 11. The control set

Stages 0 and 1 run on experiment 5's fixtures, unmodified, because their ground
truth is structural (§7). Stage 2 needs its own, and the middle row is the
experiment.

| Fixture | Shape | Required outcome | What it rules out |
|---|---|---|---|
| `symmetric_rivals` (exp05) | Identical evidence sets | Enumeration returns exactly the separating records; dose reproduces §3.1's five | Nothing on its own |
| `near_miss` (exp05) | Three times the evidence, same separation structure | **Identical** enumeration price to `symmetric_rivals` | An enumerator that reads evidence volume |
| `irrelevant_evidence` (new) | A record bearing on nothing in the web | Priced at ~0 **and** observed at ~0 on delivery | An engine whose "prediction" is a constant with a story attached |
| `already_held` (new) | A record the belief already cites | Priced at exactly 0.000 (FR-9) | A pricer that ignores the `new_evidence` guard |
| `entrenched` (new) | Same proposition, same disconfirmer, high stability | Dose strictly larger than the same pair at low stability | A dose that is a function of the record rather than of the belief |

`near_miss` and `irrelevant_evidence` are the load-bearing pair, and they are the
direct descendants of experiment 3's near-miss negative, experiment 4's
`distractor_web`, and experiment 5 §11. A pricer that quietly returns a plausible
constant passes every other row.

## 12. Measurement constraints inherited

Non-negotiable, from experiments 1, 3, 4 and 5:

- **Honesty scorer**: citation metrics validated (sensitivity 0.79–0.90,
  specificity 1.00, chance floor 0.000 by derangement); failure-mode labels are
  **not** decision-grade (SC-5 at 67.9%, inter-rater agreement unmeasured). Stage
  3's receipts read uses citation metrics only.
- **`DissonanceSignal.magnitude` may not be read as a measure of belief
  dynamics** — report `magnitude_raw`, carriers, and the saturation baseline
  alongside any delta (experiment 4 §12).
- **Stake is blind to grounding** (experiment 4 §1): `stake_of`
  ([dissonance.py:86](../../../src/manyu/dissonance.py)) averages evidence
  salience rather than summing it, so one record and five produce identical
  stake. **No part of the pricer may be built on that channel** — the same
  constraint experiment 5 §12 imposed on detection, for the same reason.
- **Status is never recomputed from confidence** (experiment 5 §5.1). A belief
  charged to 0.1 stays composed. So "the dose crossed the threshold" must be
  defined on *confidence*, and any claim about whether Manyu still **says** it
  needs the synthesizer read, not the number.
- **A mutual `contradicts` edge and a one-way edge price differently** by 0.2333
  on an otherwise identical pair (experiment 5 §6.1). Every counterfactual
  involving a contradiction must record which topology it assumed.
- **Live webs are one hop deep** and about 1 extraction in 10 over-merges
  (experiment 3 §3.4). Stage 4's *n* must absorb both; an over-merge is a dropped
  sample, not a null.

## 13. What counts as a "mind-changer" must be derived, not chosen

Open, and it blocks Stage 0.

The enumerator needs a rule for which hypothetical records to emit. The
degenerate rule — "any record disconfirming the proposition" — is a restatement
of the belief's negation, is available for every belief in the store, and is what
§6 risk one predicts the substrate already forces.

**A candidate shape with no constant in it**, to be decided with evidence rather
than adopted here: a hypothetical record is a mind-changer for belief B when it
would enter B's own `evidence_ids` (so the `new_evidence` guard does not void it)
**and** the predicted post-delivery confidence crosses a threshold registered in
advance. The enumeration is then the set of such records the store's structure
implies — for a rival pair, records in the symmetric difference; for a supported
belief, retraction of each supporter, which `RevisionEngine.retract` already
prices.

**Its weakness is real and must be faced before Stage 0.** The "records the
store's structure implies" clause carries all the weight, and for a belief with
no rivals and no supporters the structure implies nothing, leaving only the
degenerate rule. If most beliefs in a live web are that shape, enumeration is a
fixture-only capability — experiment 4's void base rate and experiment 5 §13's
strictness risk, arriving for the third time. Stage −1 measures the shape
distribution over the existing webs in `evals/` before the rule is fixed.

Whatever is chosen is pinned in methodology before the run that consumes it,
**and changing it afterwards voids that arm.**

## 14. Design decisions

Decided 2026-08-11, before any code. Each is recorded with the reason, because a
decision without one is indistinguishable from a default.

### 14.1 Both pricers, and they are not peers

**Decided: analytic *and* replay (§5.4), with an asymmetry that answers the
objection to building both.**

The analytic pricer is the **deliverable** and carries FR-5 — reachable on
`ManyuCore`, CLI and MCP, verified across a process boundary. Replay is an
**instrument**, lives with the analysis machinery, and gets no CLI or MCP
surface at all.

That asymmetry is the whole of the decision. Building both was objected to on the
grounds that it doubles the surface; it does not, because only one of them is a
surface. Stage 1 keeps its two arms — analytic predicts, replay observes — and
the thing a user can call remains single.

### 14.2 A hypothetical record is a frozen dataclass, not a schema

**Decided: a frozen `HypotheticalEvidence` dataclass, deliberately *not* a
`ManyuModel`/`BaseModel`.**

`ManyuStore.save_belief_evidence` takes a `BeliefEvidence`
([store.py:376](../../../src/manyu/store.py)). A dataclass that is not one cannot
be passed to it, so **FR-1's "pricing never mutates" is enforced by the type
system rather than by discipline** — the same preference for structural over
procedural guarantees that put mandatory provenance in the substrate rather than
in a review checklist. The rejected alternatives both leaked: an unsaved
`BeliefEvidence` is one careless call away from being saved, and a
`BeliefCandidate` with a marker is one careless call away from the extractor path.

It carries: a deterministic id, a confidence, a salience, the belief ids it would
attach to, and its edge intent (`supports`, `contradicts`, or neither).

**The id is content-derived and never `uuid4`.** Experiment 4 found a `uuid4`
tie-break in production and experiment 5 found the same family inside a *test*,
where it went green about half the time. A counterfactual that prices differently
on re-run is unusable for calibration, and the fix is cheaper before the code
exists than after.

### 14.3 The enumeration is stored — as a record, not a belief

**Decided: a `CounterfactualReceipt`, persisted on the `DissonanceSignal` /
`LoopTrace` / `HonestyScore` pattern (`save_*` and `list_*`,
[store.py:620–657](../../../src/manyu/store.py)).**

It is stored because #7 needs to audit what Manyu said it would take last week
against what it says now, and a query result cannot be audited after the fact.

It is **not** a belief because it has no confidence. Making it one would import
experiment 5 §5.3's rule — subject to every rule any other belief obeys — and the
first thing it would need is an exemption from `blend_confidence`, which §5.3
says is a defect report rather than a fix. The substrate already has a shape for
"a stored artifact that is not a belief" and four things use it.

Consequence: FR-4's machine-readability and stage 3's receipts read both become
straightforward, and stage 3 needs no new persistence work.

### 14.4 "Changed my mind" is confidence below 0.45

**Decided in [pre-registration §4.2](pre-registration.md), together with its own
limitation** — status is never recomputed from confidence, so the dose measures
when the number crosses, not when Manyu stops saying it. The second claim needs a
synthesizer read and stage 2 does not take one.

### 14.5 The dose is a lower bound, and stage 2b measures by how much

**Decided: no, the dose does not account for corroboration arriving in the
meantime — and that is measured rather than caveated.**

A real web receives confirming evidence while the disconfirming records arrive,
so a dose computed against a static belief understates by an unknown amount.
Leaving that as a note in the results would be exactly the "unmeasured
qualification" that experiment 3's `ignore_own_evidence` ablation existed to
avoid.

**Stage 2b** therefore interleaves confirming records with the disconfirming ones
and reports the dose as a function of the arrival ratio. It is offline,
deterministic, and costs a loop.

**Working the arithmetic out in advance turned this from a bookkeeping arm into
the sharpest prediction in the experiment.** For the meta-belief the candidate
confidence is the Jaccard overlap, so with `r` separating records per shared
record the overlap converges to `1/(1 + r)` — and against the 0.45 threshold that
puts a **phase transition at `r* = 11/9 ≈ 1.222`**. At one confirming record per
disconfirming record the dose is not large, it is **infinite**: confidence
converges to exactly 0.500 and never crosses. Full table in
[pre-registration §4.4](pre-registration.md).

This settles, in qualified form, the reading experiment 5 results §3.1 left open.
Below `r*` the state is unfalsifiable **in principle** rather than merely slow —
and the ratio at which real evidence arrives is not something the substrate
controls.

### 14.6 Cosmology stays with experiment 5

**Decided: it does not appear in this experiment.**

Stage 4 is already the only paid rung, and it already shares a provider
prerequisite with experiment 4 stages 0a/0b and experiment 5 Stage 5. Adding
cosmology would put four unrun paid questions into one spend where three of them
belong to other experiments — and experiment 5 chartered the cosmology case
specifically as the condition where *the model produces the rivals and we do
not*, which is that experiment's dependent variable and not this one's.

Stage 4 runs the steelman on the existing fixture domains. If experiment 5's
Stage 5 runs first, this experiment reads its output rather than re-buying it.

### 14.7 Still open

1. **What `HypotheticalEvidence.salience` should be set to.** It feeds
   `stake_of`, which §12 forbids the pricer from reading — so it may be
   irrelevant, or it may be a back door into the channel the pricer is barred
   from. Resolve at stage −1, where it costs nothing to check.
2. **Whether stage 3's receipts are scored per-item or per-enumeration.** The
   honesty scorer takes a report and a snapshot; an enumeration is a list. Decide
   before stage 3 and after seeing what stage 0 emits.

## 15. Carried-over method

Standing practice from experiments 1–5, not restated per stage:

- **Write the criterion a decision rests on before running what could settle
  it.** Experiment 3 found four defects this way.
- **Check the generation path before reading any number off it.** Experiment 4's
  Stage 0a was void because the control sat on the detector while the defect was
  upstream.
- **Probe inputs the author did not have in mind** — self-reference, zero-valued
  operands, repeated application, a record that is already held.
- **Treat an impossible value as a defect report.** Here specifically: a
  predicted Δ outside [0, 1], a dose of zero, or a dose that falls as stability
  rises.
- **Assert a mechanism can change its output before reading what it says.**
- **Every arm ships a positive control in the same run.** A null without a
  passing control is a bug, not a finding.
- **Pilot for variance before committing to full *n*.**
- **Drop-one robustness runs inside analysis, not after it.**
- Run [`gate.py`](../../../src/manyu/gate.py) before any stage's numbers are
  readable — `assert_not_noop` on the pricer (§2 flavour C) and `assert_has_range`
  on predicted Δ, since a price pinned at one value makes every downstream
  reading unreadable and is the single most likely failure here.
- **Extend the mutant battery.** Experiment 5's
  [`underdetermination_mutants.py`](../../../src/manyu/underdetermination_mutants.py)
  holds eight; experiment 4's holds ten. This experiment adds at least: a pricer
  returning a plausible constant, a pricer ignoring the `new_evidence` guard, a
  dose that ignores stability, and an enumerator returning every record in the
  store.
- **Verify every check in the battery can fail.** Experiment 5's best catch was a
  check in the battery that was itself random — it went green about half the
  time, because belief ids come from `uuid4`.

**The reason this section exists:** experiment 3 shipped sixteen defects and its
test suite caught none; experiment 4 caught eight, none by a test written after
the code; experiment 5 caught six, none by a test written after the mechanism.
Every defect across all three was the same shape: **a quantity that looked right
and meant something else.** This experiment's entire output is quantities that
look right.

## 16. Prerequisites, unclosed

1. **`/code-review ultra exp03-base` has never been re-run.** Carried from
   experiment 3 §6 through experiment 5 §7 and now blocking more than before:
   every number this experiment predicts comes out of `blend_confidence` and
   `_contradiction_share`, so an unreviewed revision engine is an unreviewed
   dependent variable. **This should close before stage 1, not before stage 4.**
2. **Rotate the API key** used for experiment 3 Stage 4 — it was pasted into a
   chat transcript. Carried from experiment 3 §6 and still open.
3. **Experiment 4 stages 0a/0b and experiment 5 Stage 5 remain unrun**, all
   blocked on a provider that can emit `contradicts`. This experiment's stage 4
   needs the same thing and the three should be answered by one spend, not three.
