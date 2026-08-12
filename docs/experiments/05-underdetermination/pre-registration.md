# Experiment 5 — Pre-registration

**Written:** 2026-08-11
**State at writing:** Stage −1 complete (15 substrate tests). **No mechanism
exists** — `src/manyu/underdetermination.py` has not been created, no criterion
has been written, and no fixture has been authored.
**Requirements:** [requirements.md](requirements.md) §10 · **Plan gate:** written
before the criterion, hashed into `evals/analysis/exp05/freeze.json`.

Why this file exists: choosing a threshold after seeing the distribution is
experiment 1's failure mode #1 — the mock whose own comment said its output was
tuned to sit just below the ceiling — and `assert_constants_pinned` exists to
catch it. Experiments 3 §7 and 4 §10 both carried this discipline.

**Changing any number below after the run it governs voids that arm.** Amending
is allowed; amending silently is not. Every amendment is appended to §8 with a
date and a reason.

---

## 0. Not a prediction — a measurement already taken

Requirements §10 asks for "what confidence gap counts as collapsed rather than
standoff." Stage −1 measured this before the question could be asked as a
prediction, so it is recorded as a fact rather than dressed up as a forecast.

| Topology | Gap | Verdict |
|---|---|---|
| Mutual edge, equal grounding | **0.000** | standoff |
| One-way edge, otherwise identical | **0.2333** | collapse |

The operational rule for every later stage, fixed here: **gap ≤ 0.01 is a
standoff, gap ≥ 0.10 is a collapse, and anything between is reported as neither
rather than rounded into one.** The middle band is deliberately left as an
outcome; experiment 1's v4 correlations collapsed under drop-one precisely
because a marginal reading was reported as an effect.

## 1. Base rate (Stage 5, paid)

The claim becomes **fixture-only** if fewer than **1 in 20 naturalistic turns**
produces two beliefs that share evidence *and* carry a `contradicts` edge.

Recorded in advance because experiment 4's Stage 0a produced a base rate of zero
that read exactly like a finding and described the instrument instead. This
number is what stops the same reading being negotiated after the fact.

**Secondary, and it decides how much §6.1 shrinks the claim:** of the rival pairs
found, the fraction carrying a **mutual** edge rather than a one-way edge. If
mutual pairs are rarer than **1 in 4**, the substrate's standoff is a laboratory
artifact and the headline says so.

## 2. Collapse — `discriminating` (Stage 2)

The meta-belief's confidence must fall by **≥ 0.15 absolute** from its value on
`symmetric_rivals`, and must fall **strictly further** than on `near_miss`.

A smaller fall is not a pass. If the meta-belief survives separating evidence
substantially intact, §2 flavour A has occurred — we built a state that cannot
be disconfirmed — and the experiment stops until the exemption is found and
removed (FR-2).

## 3. Near-miss — `near_miss` (Stage 2)

**Prediction: it holds**, with the meta-belief's confidence within **0.05** of
its value on `symmetric_rivals`, despite `near_miss` carrying strictly more
evidence records.

**Why the criterion cannot see the difference**, stated before the criterion is
written so the reasoning cannot be retrofitted: the criterion consults *set
membership only* — whether the symmetric difference of two `evidence_ids` lists
is empty. Cardinality enters nowhere in it. A criterion that reads volume would
have to consult `len()` somewhere, and there is no term for it in the definition.

**The honest risk, per requirements §10.** This is partly a prediction about our
own hand, because we write the criterion. The constraint accepted here: the
criterion must be the most natural thing to write for *evidence that does not
separate two hypotheses*, not the thing that makes this fixture pass. If that
argument comes to feel strained when the code is written, it is recorded in §8
and the result stops being about underdetermination and starts being about our
arithmetic.

## 4. Stability (Stage 3)

**Prediction: the attention loop does not break the state at any budget**, and
the meta-belief's confidence is unchanged (≤ 0.01 movement) across the whole
sweep.

The mechanism is already measured: a mutual pair priced at ingest is inert when
the loop arrives (Stage −1), so there is nothing for the loop to charge. The
prediction is therefore *cheap* and its failure is the informative outcome — if
the state moves, something reaches it that Stage −1 did not find.

**Second threat, predicted separately:** accumulating further non-separating
evidence must not move the meta-belief by more than **0.05**. If it does, the
state decays under evidence that by construction says nothing about it.

## 5. Expression (Stage 4)

For the report to count as *expressing* the state rather than hedging, it must:

1. name **both** rivals,
2. cite the shared evidence records, and
3. **not** assert either rival as the case.

All three, scored on citation metrics only — failure-mode labels are not
decision-grade (SC-5 at 67.9%, inter-rater agreement unmeasured). A report
satisfying (1) and (2) but not (3) is recorded as *hedging*, which is a distinct
outcome and not a partial pass.

**Fixed here because Stage −1 made it necessary:** the meta-belief must be
created at confidence **≥ 0.45** or `BeliefUpdater._create` stamps it `TENTATIVE`
and `WorldviewSynthesizer` drops it silently. A Stage 4 null below that threshold
measures the threshold, not the experiment.

**The synthesizer decision** (requirements §14 q4), fixed before the run: when a
meta-belief names the rivals, the synthesizer **emits the meta-belief's stance
alongside the rivals' averaged stance** rather than suppressing either. Rationale:
suppression would make §5.1's averaging finding unobservable in the same run that
is supposed to demonstrate it, and "the mediocre stance is still there" is itself
the thing Stage 4 is measuring.

## 6. What would make this experiment uninteresting

Recorded in advance so it cannot be argued away later. Any of these means the
result is reported as small rather than inflated:

- The criterion never fires on anything but the authored fixtures (§13's risk —
  experiment 4's void base rate in a new place).
- Mutual edges are so rare live that §6.1's standoff never occurs outside the lab.
- The meta-belief holds only because nothing in the system reads it — the
  `MergedDissonanceQuery`-before-experiment-4 shape.

## 7. Fixed constants

| Constant | Value | Where it binds |
|---|---|---|
| Standoff band | gap ≤ 0.01 | every stage |
| Collapse band | gap ≥ 0.10 | every stage |
| Collapse magnitude | ≥ 0.15 | Stage 2 |
| Near-miss tolerance | 0.05 | Stage 2 |
| Stability tolerance | 0.01 (loop), 0.05 (evidence) | Stage 3 |
| Fixture-only base rate | 1 in 20 turns | Stage 5 |
| Mutual-edge share | 1 in 4 pairs | Stage 5 |

**The criterion itself contains no constant** and none is registered for it. That
is the requirement (§13, FR-8), not a convenience: `attenuation` and
`contradiction_penalty` were both *removed* in experiment 3 §§11–12 rather than
tuned. The `GRADED(epsilon)` alternative is built only as a labelled ablation,
pinned by a test showing it fail, and is never promoted to rescue a null.

## 8. Amendments

_none yet_
