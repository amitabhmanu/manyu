# Experiment 4 — Dissonance as a Control Signal: Requirements

**Status:** spec (no code)
**Backlog entry:** [../../experiments_backlog.md](../../experiments_backlog.md)
**Related:** [crux #4](../../Manyu_experiments_crux.md) · [experiment 3](../03-foundationalism-quinean-web/requirements.md) · [experiment 3 retrospective](../03-foundationalism-quinean-web/retrospective.md) · [ADR-002 merged substrate](../../adr-002-merged-substrate.md)

## 1. Purpose

Manyu can hold beliefs that contradict each other. Experiment 2 built the
detector that notices — [`dissonance.py`](../../../src/manyu/dissonance.py) —
and experiment 3 showed the signal is dynamically coupled to revision:
retracting a supporter eases it through the confidence pathway, with valences
provably untouched.

**The signal is a readout. Nothing in the system reads it.**

This experiment asks whether anything should: when Manyu is holding beliefs
that cannot both be right, does that change what it does next — what it
revisits, whether it pauses, whether it goes looking — or is the number only
reported?

Why it sits here: the crux's founding claim is that affect is the **salience
filter**, the mechanism deciding which of a million beliefs matter right now.
If discomfort never changes behaviour, that claim is decoration. This is where
affect is promoted from a display to a mechanism, or is shown not to be one.

**Publish gate.** The backlog holds publication until this lands. #1–#3
describe a system; #4 is where it acts.

## 2. The question as chartered is settled by wiring

The backlog asks whether dissonance "actually *change[s] what Manyu does next*
— arbitration thresholds, attention, slow-appraisal triggers." Taken
literally that is not an experiment. If we write the branch that reads the
signal, the signal changes behaviour, because we wrote the branch.

This is [experiment 3 §1](../03-foundationalism-quinean-web/retrospective.md)
in a new place: an answer that follows from a design decision rather than from
an observation, with the alternative never available to observe. Experiment 3
caught it only because someone noticed an impossible number.

There is a nearer precedent still. Experiment 1 found that the mood →
`rank_causes` coupling was **arithmetically a no-op on every probed target** —
affect wired to control, doing nothing, across several versions, with the knob
that drove it turning out to be three system-message sentences. That is why
[`gate.py`](../../../src/manyu/gate.py) carries `assert_not_noop`, and a
dissonance → control branch is precisely the shape of risk it exists for.

**So the headline question is reframed.** Three things are falsifiable where
"does it control behaviour" is not:

1. **Distinctness.** Does the signal carry information the existing control
   inputs do not already carry? If tension is recoverable from arousal,
   confidence, goal impact and event type, wiring it in is a recoding.
2. **Efficacy against matched controls.** Does acting on the signal beat
   acting *always*, and acting *at random at the same rate*?
3. **Targeting, and whether it tracks truth.** Does the action land on the
   beliefs the signal named? And when tension can be quieted either by
   resolving a conflict or by discarding the better-evidenced side, which does
   it take?

(3) is the result worth publishing. "Dissonance is a control signal" is a
demo; "dissonance is a control signal and it is not truth-tracking unless X"
is a finding, and it feeds #7 directly.

## 3. Scope

### In scope

- **Stage 0** — base rate and branch-disagreement, offline, no coupling built.
  It can end the experiment (§8).
- **A surface for the signal** — computed in-loop, persisted, reachable from
  `ManyuCore`, CLI and MCP. Prerequisite, not a result (§6).
- **One primary coupling: dissonance → belief attention → revision.** Which
  beliefs get revisited is selected by the signal.
- **Three arms, pre-registered:** driven, always-escalate, random-at-matched-rate.
- **Targeting measurement** against a deranged baseline.
- **The adversarial arm** — a fixture where the cheapest tension reduction
  requires discarding the better-grounded belief.
- **Arbitration as a secondary read**: record the disposition that *would*
  have changed, without acting on it.

### Out of scope (deferred)

- **Acting on arbitration.** Recorded, not wired. See §5 — the Arbiter is a
  fixed if/elif ladder, so adding a branch there produces a foregone
  conclusion at the primary-outcome level.
- **Changing the honesty scorer.** Frozen at 1.6.0. Citation metrics are
  usable; failure-mode labels are not (§12).
- **Multi-agent dissonance propagation** — experiment 9.
- **Underdetermination as a stable non-resolving state** — experiment 5. Here,
  a web that declines to resolve is an outcome to record, not a shape to build.
- **Scheming and hidden goals** — experiment 7, which inherits §11's result.

## 4. The reframed question

> Does the dissonance signal carry information the system does not already
> have, does acting on it beat acting indiscriminately, and does the resulting
> behaviour track truth or merely reduce discomfort?

## 5. What exists to control, and what does not

Surveyed from [`services.py`](../../../src/manyu/services.py) before scoping,
because the backlog's three named surfaces are not three.

| Surface | Where | State |
|---|---|---|
| Arbitration disposition | [`Arbiter.arbitrate`](../../../src/manyu/services.py) | Exists. Fixed if/elif ladder; `high_arousal = max(state.emotions.values()) >= 0.75` is its only affect input |
| Slow-appraisal trigger | `FastAppraiser.appraise` | Exists. `event_type == CORRECTION or confidence < 0.5 or abs(goal_impact) > 0.75` |
| Action class | `FastAppraiser.appraise` | Exists, and mood already flips it — the precedent for an affect → control coupling |
| Attention over beliefs | — | **Does not exist** |

`BeliefReflectionService.reflect_emotional_triggers(threshold=0.24)` is *not*
attention over the belief web, despite reading like it. It scans **event
traces** for affect trigger strength and mints self-model beliefs from them.
Nothing anywhere selects which existing beliefs get revisited.

**So the primary coupling requires new construction**, and that cost is
accepted deliberately: the two surfaces that already exist are both fixed
decision ladders where the outcome would be decided by writing the branch,
whereas whether a revision loop *converges* is an empirical property that
wiring cannot settle. The loop may settle, thrash, or resolve the wrong
beliefs.

### 5.1 The affect vocabulary is closed

`EMOTIONS` in [`schemas.py:10`](../../../src/manyu/schemas.py) is a fixed
eight-channel tuple, enforced by four validators, and `ManyuProfile` requires
every channel to be present. Experiment 2 therefore added its `dissonance`
channel to a **copy** of the profile rather than to
`config/default_profile.json`.

Any design that routes dissonance through `AffectState` inherits that
decision and must justify it, because adding a ninth channel invalidates the
default profile and adds a series to experiment 1's visualiser. See §14,
open question 2.

## 6. The signal has no surface

`MergedDissonanceQuery` is imported by exactly two places: its own module and
[`tests/test_dissonance.py`](../../../tests/test_dissonance.py). There is no
`save_*` for `DissonanceSignal` in [`store.py`](../../../src/manyu/store.py),
nothing on `ManyuCore`, nothing on the CLI or MCP, and no computation of it
during `submit_event` or `process_reflective_turn`.

This is exactly the state `RevisionEngine` was in before experiment 3 §13, and
`manyu_run_probe` before experiment 1 found it missing from MCP entirely.
Stage 1 fixes it. **It is a prerequisite and must not be written up as
progress.**

## 7. Stage 0 cannot run on existing artifacts

Checked before specifying it, and the result changes the staging.

Across every stored run in `evals/analysis/`: **620 `contradicts` fields, of
which 4 are non-empty. Zero `supports` fields anywhere.** And
`evals/analysis/exp03/stage4.jsonl` is summary-only — 30 rows of
`belief_count`, `footprint`, `share_values` — carrying neither a belief store
nor an affect state, so it cannot be joined against control inputs.

Both are explained: those runs predate `supports` entering the extractor
schema ([experiment 3 §3.5](../03-foundationalism-quinean-web/retrospective.md))
and predate experiment 3 §14, which made ingest price contradictions. Both
edge fields are in `BeliefExtractor._schema` now, so live webs *can* carry
them — no stored run does.

Two consequences:

1. **Stage 0 needs its own generation step.** Offline, scenario provider, no
   API spend — but a build, not an analysis.
2. **Stage 0 acquires a prior question (0a).** If contradictions stay as rare
   live as 4-in-620 suggests, "dissonance as a control signal" is a
   fixture-only claim and the headline must say so. That has to be *measured*
   before efficacy, not discovered afterwards — it is the difference between a
   mechanism experiment and a null nobody can interpret.

## 8. Staging — the ladder, cheapest rung first

Each rung can end the experiment. That ordering is the design.

| Stage | LLM | n | Establishes | Can end it? |
|---|---|---|---|---|
| 0a — base rate | none | 1 | How often a non-null signal occurs on a naturalistic reflective run, against an authored positive control | Yes — reframes to fixture-only |
| 0b — distinctness | none | 1 | Whether the signal produces a control decision the incumbents do not | **Yes — kills it** |
| 1 — surface | none | 1 | Signal computed in-loop, persisted, on core/CLI/MCP. *Prerequisite* | No |
| 2 — coupling | none | pilot first | Dissonance → attention → revision, three arms | Yes — if driven ≈ always |
| 3 — targeting | none | 1 | Carriers name the beliefs acted on, above a deranged baseline | Yes |
| 4 — adversarial | none | 1 | Which side is dropped when tension can be quieted either way | No — both outcomes are results |
| 5 — live confirmation | yes | 10 | Naturalistic webs behave as characterised | No |

Stages 0–4 are deterministic under `FrozenClock` where they consume no
provider, so `n=1` is correct — repetition re-measures the same arithmetic
([experiment 2 methodology §1](../02-merge-split-fork/methodology.md)). Stage
2 takes a variance pilot before committing to *n*, per experiment 1, where two
of four fixtures sat at ceiling.

**What may be authored, and what may not**, carried from experiment 3 §4:
topology, starting confidences and which beliefs conflict are the independent
variable, and authoring them is manipulation rather than rigging. The
dependent variables — which beliefs the loop selects, whether it converges,
which side it drops — must never pass back through anything typed into a
fixture. The check before any fixture is admitted: *does the DV pass back
through anything I typed?*

## 9. Functional requirements

**FR-1 — The signal is computed in the loop and persisted.** A dissonance read
is taken at a defined point in `process_reflective_turn` and written to the
store, with `magnitude_raw`, carriers, and the saturation baseline (§12).

**FR-2 — The signal is reachable across a process boundary.** `ManyuCore`, CLI
and MCP, verified by driving it in one process and reading it in the next —
the property experiment 3 §13 pinned, because a surface that only works
in-process is not a surface.

**FR-3 — Attention is selective and recorded.** The coupling selects a subset
of beliefs for revisiting, and every selection records *why* — which carrier,
at what tension — so a selection nobody can audit is not a result.

**FR-4 — Arms are selectable and none is default.** `driven`,
`always`, `random_matched`. The harness refuses a run that does not name one.
Experiment 3 §13's rule: a silent default settles the question by whichever
branch a caller happened not to think about.

**FR-5 — The random arm is rate-matched, not rate-free.** It escalates as
often as the driven arm did on the same fixture, so the comparison isolates
*which* beliefs were chosen rather than *how many*.

**FR-6 — The loop terminates.** Selection → revision → re-read is a cycle.
Bounded iterations, with the termination reason recorded: settled, bound
reached, or oscillating.

**FR-7 — Convergence is measurable.** Per run: tension trajectory across
iterations, which beliefs moved at which iteration, and whether the trajectory
is monotone, oscillating, or flat.

**FR-8 — The escalation threshold is derived, not chosen.** See §13.

**FR-9 — Targeting is measured against a null.** The overlap between beliefs
named by carriers and beliefs acted on is compared to a derangement baseline,
reusing experiment 1's `mutations.py` machinery rather than a fresh one.

**FR-10 — Grounding quality is recorded on both sides of every conflict**, so
§11's adversarial question is answerable from the run rather than by
inspection.

## 10. Pre-registered predictions

To be recorded **before any coupling code exists**, and dated. Left
deliberately unfilled at this revision — writing them after Stage 0's numbers
are visible would be experiment 1's failure mode #1, a mock tuned to its own
criterion.

What each must state before Stage 2 runs:

| Question | Prediction to fix in advance |
|---|---|
| 0a base rate | The rate below which the claim becomes fixture-only |
| 0b distinctness | The disagreement-set size below which the signal is redundant |
| 2 efficacy | What separation between `driven` and `always` counts as an effect |
| 3 targeting | The overlap above derangement that counts as targeting |
| 4 adversarial | Which side we expect to be dropped, *and why* |

**The honest risk, stated in advance:** predictions 2 and 3 are partly
predictions about our own hand, since we write the selection rule. The
constraint is that the rule must be the most natural thing to write for *a
graph of weighted evidential conflict*, not the thing that makes the driven
arm win. If that argument comes to feel strained, this is where to say so, and
the result stops being about salience and starts being about our arithmetic.
Experiment 3 §7 carried the same clause and it earned its place.

## 11. The adversarial arm

**Tension reduction is not truth-tracking.** A system acting to quiet its own
dissonance may drop whichever belief is cheapest to drop rather than whichever
is wrong — motivated reasoning, built into the architecture.

The fixture makes the two come apart: a conflict where the *cheaper* side to
discard, by whatever the loop's own arithmetic prices, is the better-grounded
one. Experiment 3 §12.1 supplies the mechanism that makes this constructible —
a contradictor's weight is `1/(supporters + own evidence + contradictors)`, so
a thinly-grounded belief moves 0.400 against the same objection that moves a
thickly-grounded one 0.133. A loop minimising total tension per unit of
movement has a standing incentive to go after the thin belief; whether that is
the *right* belief is exactly what the fixture controls.

Both outcomes are results:

- **It discards the better-grounded side.** Dissonance-as-control is a hazard,
  and naming it is the stronger finding. #7 inherits it directly.
- **It does not.** Then something in the substrate resists, and the experiment
  must say *what* — which is a claim about mandatory provenance again, of the
  same family as experiment 3 §11.1.

**A third outcome must be anticipated:** the loop resolves neither and stalls.
That is not a failure of the run. It is the shape experiment 5 is chartered to
study, and it should be recorded as such rather than tuned away.

## 12. Measurement constraints inherited

Non-negotiable, from [experiment 3 §3.3](../03-foundationalism-quinean-web/retrospective.md):

- **`DissonanceSignal.magnitude` may not be read as a measure of belief
  dynamics.** Report `magnitude_raw` and carriers, and the saturation baseline
  alongside every delta. `magnitude` is concave in raw tension, so the same raw
  change reads larger from a lower baseline — a delta confounds *how much
  tension changed* with *where on the curve the web was sitting*. That is
  experiment 1's gate #3, a truncation constant read as a curve, in a new
  place.
- **`_tension` takes `min(stake_a, stake_b)`**, so it reads the weaker party
  and is blind above that floor. Raw tension moved *identically* under both
  contradiction arms while the underlying beliefs sat at materially different
  confidences.

  **This is worse for control than for readout.** A loop driven by a signal
  that plateaus at the weaker party's stake can stop while real tension
  remains. Whether `_tension` changes must be decided before Stage 2 — and if
  it does, that is a mechanism change requiring experiment 3's treatment: no
  free constant, with the alternative retained as a labelled ablation pinned
  by a test showing it *fail*.

Also inherited:

- **Live webs are one hop deep** (§3.4 there): depth-2 propagation in 7 of 20
  structured runs. Non-empty carrier paths — the thing distinguishing a graph
  query from adjacency — will be rare live. Either elicit depth deliberately or
  scope the targeting claim to direct conflicts and say so.
- **About 1 extraction in 10 over-merges** into a single belief with no edges.
  Any *n* must absorb it.
- **Provider transfer** (§3.2 there): a specificity result established on one
  provider is provisional until re-run on the provider carrying the finding.
  Budget a pilot.
- **Honesty scorer** (experiment 1): citation metrics validated; failure-mode
  labels are **not** decision-grade (SC-5 at 67.9%, inter-rater agreement
  unmeasured). Any read on whether Manyu reports its revisions honestly uses
  citation metrics only.

## 13. The escalation threshold must be derived, not chosen

Open, and it blocks Stage 2.

A dissonance coupling needs a level at which it fires. Choosing that level
after seeing Stage 0's distribution is experiment 1's failure mode #1 — the
mock whose own comment said its output was tuned to sit just below the ceiling
— and `assert_constants_pinned` exists to catch it.

Worse, a free constant here sits at the centre of the decision, which is
exactly what experiment 3 removed twice: `attenuation = 0.6` in §11, where in
a chain the constant *was* the hypothesis, and `contradiction_penalty = 0.3`
in §12. Both were replaced by quantities read off the store, and both kept a
`FIXED` ablation pinned by a test showing it fail.

The same discipline applies. A candidate shape, to be decided with evidence
rather than adopted here: fire when raw tension exceeds a quantity already in
the store — the median stake across the current web, say — so the level is
read rather than authored, and a `FIXED` ablation is retained to show a
constant cannot represent what the derived form does.

**Whatever is chosen, it is pinned in methodology before the run that consumes
it, and changing it afterwards voids that arm.**

### 13.1 Resolved (2026-08-10): the constant was removed, not chosen

No threshold exists anywhere in the built mechanism, and none was picked.

- **The loop needs none.** Selection is by *ranking* — attend to the most tense
  conflict — so there is no level at which anything fires. The section above
  assumed a graded firing rule; a ranking does not have one.
- **Stage 0b needs none.** Its dissonance predicate is "the web contains a
  stated contradiction", which contains no constant. If that already fails to
  separate from the incumbent branches, no threshold would rescue it.

This follows experiment 3 §§11 and 12, which removed `attenuation` and
`contradiction_penalty` rather than tuning them: **removing a constant beats
choosing one well.** There is no `FIXED` ablation because there is nothing to
ablate — a `ThresholdMode` enum was sketched and then not built, since a mode
selector over a single mode is the `ContradictionArm` defect waiting to happen.

Reopen this only if a *graded* coupling is added — one where dissonance
modulates a continuous quantity rather than choosing among conflicts. At that
point the level returns and §13's discipline applies unchanged.

## 14. Open questions for the design phase

1. **Where in the turn is the signal read?** Before belief update, after, or
   both. Reading after means the turn's own contradictions count; reading
   before means the loop responds to the web it entered with. The two are
   different experiments and the choice is not obvious.
2. **Does dissonance become a ninth affect channel?** §5.1 says the cost is an
   invalidated default profile and a shared mutation across builds. Experiment
   2 declined it and recorded the deviation. The alternative is a first-class
   signal outside `AffectState`, which is cleaner but weakens the "affect is
   the salience filter" reading, since the filter would not be affect.
3. **Should the loop select beliefs, or select *conflicts*?** Carriers name
   pairs. Acting on a pair is better defined; acting on a belief is what an
   attention mechanism does.
4. **What does "resolved" mean?** Confidence separation between the two sides,
   status transition, or the conflict leaving the carrier set. These can
   disagree, and the choice must precede Stage 2.
5. **Does the arbitration secondary read need `slow_required` too**, or is
   disposition alone enough to show the signal would have changed something?
6. Whether Stage 5 runs at all, given §7's base rate. If contradictions are
   near-absent live, a live stage confirms nothing and the budget is better
   spent on §12's provider-transfer pilot.

## 15. Carried-over method

Standing practice from experiments 1–3, not restated per stage:

- **Write the criterion a decision rests on before running what could settle
  it.** Experiment 3 found four defects this way, including one that broke the
  standard its own §5 was decided on.
- **Probe inputs the author did not have in mind** — self-reference, mutual
  relations, repeated application, zero-valued operands.
- **Treat an impossible value as a defect report.** Chasing `share = 1.0`,
  which mandatory provenance forbids, is the only reason experiment 3 did not
  publish a foundationalist result as a Quinean one.
- **Assert a mechanism can change its output before reading what it says.**
  `ContradictionArm` was stored, stamped onto results, and consulted by no
  branch.
- **Every arm ships a positive control in the same run.** A null without a
  passing control is a bug, not a finding.
- **Pilot for variance before committing to full *n*.**
- **Drop-one robustness runs inside analysis, not after it.**
- Run [`gate.py`](../../../src/manyu/gate.py) before any stage's numbers are
  readable — specifically `assert_has_range` on `magnitude_raw` (a constant
  signal makes everything downstream unreadable) and `assert_not_noop` on the
  coupling (§2's precedent).

**The reason this section exists:** experiment 3 shipped sixteen defects and
its own test suite caught none of them. The cause was structural rather than
careless — each test was written minutes after the mechanism it covered, by
the same author, sharing its assumptions, so it agreed with the code precisely
where the code was wrong. Every one was the same shape: **a quantity that
looked right and meant something else.**

## 16. Prerequisites from experiment 3, unclosed

Both from its retrospective §6, and neither is this experiment's work:

1. **Rotate the API key** used for experiment 3 Stage 4 — it was pasted into a
   chat transcript.
2. **Retry `/code-review ultra exp03-base`.** The cloud review failed and was
   never re-run, so every fix in the engine this experiment consumes was
   verified by its author alone.
