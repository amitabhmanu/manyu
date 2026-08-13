# Experiment 8 — Pre-registration (stages −1 through 3)

**Written:** 2026-08-12
**Status:** written before any experiment code exists, before any corpus is
transcribed, and before any provider call.
**Requirements:** [requirements.md](requirements.md)
**Methodology:** [methodology.md](methodology.md)

This file is append-only. Predictions are not edited after a run; §9 records
amendments with their dates and reasons, and an amendment written after seeing
the result it concerns is marked as such.

## 0. Not predictions — three things derived by hand from the substrate

These are not registered as forecasts because they are settled by reading the
code. They are recorded so a later reader can tell what was known in advance from
what was learned.

### 0.1 Every source in the corpus lands on `UNTRUSTED_TEXT`

> **Amended by [A1](#a1--2026-08-12-01-states-a-value-the-substrate-does-not-produce).**
> The stated value is wrong — `_trust_from_source` maps `OPERATOR_NOTE` to
> `OPERATOR_INPUT`, and no branch returns `UNTRUSTED_TEXT`. The conclusion below
> (zero discrimination across the corpus) is unaffected. Left unedited on
> purpose: this file is append-only, and what was believed in advance is part of
> the record.

`TrustClass` ([schemas.py:30](../../../src/manyu/schemas.py)) enumerates seven
values, all describing how a record reached the agent:
`TRUSTED_SYSTEM`, `VERIFIED_TOOL`, `OPERATOR_INPUT`, `USER_REPORT`,
`AGENT_SELF_REPORT`, `MEMORY_SUMMARY`, `UNTRUSTED_TEXT`.

A 1945 government dietary recommendation, a 1981 journal letter, a 2010 paper
disputing it, and an anonymous web repetition have exactly one applicable value
between them. **`trust_class` therefore contributes zero discrimination across
this entire corpus**, in all five slots, for both arms. This is arithmetic over
an enum, not a finding, and any later result that appears to turn on
`trust_class` is a bug.

The same holds for `BeliefEvidenceSourceType`
([schemas.py:83](../../../src/manyu/schemas.py)): no value denotes an external
document, and `OPERATOR_NOTE` is the least-wrong slot rather than a correct one.

### 0.2 The bare arm cannot price a prediction

FR-6 requires at least one edge per scored slot to carry a priced prediction made
before the supporting document is consulted, consuming experiment 6's
`CounterfactualReceipt`. That mechanism reads a store. The bare arm has no store.

This is registered as **structurally unavailable, never as a score of zero**
(methodology §5). Any artifact that reports the bare arm's FR-6 column as `0.0`
rather than `unavailable` is void, because a zero would enter an average and
manufacture a difference that no measurement produced.

### 0.3 Identity is delegated, so the corpus's mutation count is authored

`_normalize_belief_key` ([schemas.py:400](../../../src/manyu/schemas.py))
collapses case and whitespace and nothing else; identity is declared, never
inferred. Whoever supplies `belief_key` decides whether two statements are one
mutated claim or two claims — which is the dependent variable
(requirements §5.3).

Derived consequence, recorded now: **the answer key's mutation count is a
property of how the key's author drew the boundaries.** FR-2 puts that author's
hand on paper before any run, which does not remove the choice but does make it
inspectable and prevents it moving after a result is seen.

## 1. Stage −1 — what the substrate forces

Offline, deterministic, `n = 1`.

**P1 — a claim-instance is representable with no new production code.**
Registered: **representable**, via a declared per-instance `belief_key` plus
`metadata` on `BeliefEvidence` carrying the source and locus. Following
experiment 6's stage −1, which passed 7/7 with no new production code, the null
hypothesis is that something already fits.

*Falsifier:* a field the claim-instance requires — source locus, statement text
as it appears, or the descent edge itself — has no home that survives a process
boundary. If P1 fails, requirements §9 ends the experiment here and it becomes a
schema project first, which is a legitimate outcome and must be reported as the
result rather than routed around.

> **Amended by [A2](#a2--2026-08-12-p1s-falsifier-contradicts-2s-escape-and-the-contradiction-decides-whether-the-experiment-ends-at-stage-1).**
> "The descent edge itself" is withdrawn from this falsifier. The edge is a
> derived relation over evidence records, not a stored field, because a stored
> edge is a declared edge and a declared edge makes reconstruction a read-back.
> P1 is assessed against the metadata leg only.

**P2 — testimony and textual descent separate on existing records.** Registered:
**they separate**, on `evidence_ids` cardinality together with `source_id`
distinctness. A testimony edge yields one record (the assertion); a textual-descent
edge yields records in both documents with distinct `source_id`s.

This is the riskiest registered prediction in the file and the one with the most
riding on it, because **FR-1 binds only if it holds**. If P2 fails, no edge type
may be authored to rescue slot E until requirements §12.3 is applied, and slot
E's result is thereafter reported as a design statement — *the design admits this
distinction when given a type for it* — never as a discovery.

*Falsifier:* a hand-encoded testimony edge and a hand-encoded textual edge that
are indistinguishable on those two fields.

## 2. Stage 0 — reconstruction over hand-encoded fixtures

Offline, deterministic, `n = 1`. Extraction is bypassed entirely.

**P3 — slot A is recovered exactly.** Registered: precision **1.0** and recall
**1.0**, direction-sensitive, against the committed key.

The prediction is deliberately absolute. Claim-instances are hand-fed here, so
anything below 1.0 is a defect in the reconstruction procedure rather than a
finding about genealogy, and requirements §9 ends the stage on it. An algorithm
that cannot recover a hand-fed graph will not recover a read one.

**P4 — slot D draws exactly zero spurious edges, offline.** Registered:
**0**, as a raw count.

The reasoning is structural rather than empirical. `BeliefUpdater._rejection_reason`
refuses any candidate without evidence of its own
([experiment 3 retrospective](../03-foundationalism-quinean-web/retrospective.md)),
and slot D's two source families share no evidence record by construction (FR-8).
An edge would therefore require a record that the generator never emits.

*Falsifier:* any spurious edge at all. A non-zero count here means the
reconstructor is inferring edges from something other than evidence — most likely
textual similarity — and that must be found and named before stage 2, because it
is precisely the failure the whole experiment is built to detect in the *bare*
arm.

## 3. Stage 1 — extraction fidelity and identity stability

Paid, pilot only, slot A only. Nothing is scored at this stage.

**P5 — declared identity is unstable across re-extraction.** Registered: the same
source extracted ten times yields **at least one disagreement** in identity
granularity — two runs disagreeing about whether a pair of statements is one
mutated claim or two.

Registered as instability because §0.3 shows nothing in the substrate constrains
the declaration, and because an LLM asked to draw a boundary that the code does
not fix has no anchor to be consistent against.

*Falsifier:* ten of ten agreement. That would be a genuinely good and slightly
surprising result about extractor determinism, and it would let stage 2 proceed
without the identity-variance correction that P5 otherwise forces into the
metric.

**No pass/fail threshold is set at this stage**, and none may be back-filled.
The pilot's job is to produce the variance from which stage 2's *n* is chosen
(methodology §8.3), and a threshold chosen here would be chosen from data.

## 4. Stage 2 — both arms, slots A and D

Paid. The first rung where the control arm means anything.

**P6 — the arms tie on slot A.** Registered: **a tie**, with neither arm's
precision or recall differing from the other's by more than the pilot's measured
run-to-run variance.

Registered as a tie deliberately, and it is the most important prediction in the
file for the experiment's credibility. Calibration is a reading task, and reading
is the model's contribution rather than the substrate's. An experiment that
predicted Manyu winning everywhere would be an experiment designed to win.

*Falsifier either way:* if Manyu loses slot A, the instrument is worse at the
easy case and stages 3's differences describe the instrument. If Manyu wins slot
A, the substrate is doing something in plain recovery that §8 did not anticipate,
and that is a finding requiring its own explanation before stage 3 runs.

**P7 — the arms diverge on slot D.** Registered: the bare arm draws **at least
one** spurious edge; the Manyu arm draws **zero**, carrying P4 forward from
offline to live.

This is the headline candidate. Slot D is the only slot whose key is certain
(requirements §7.4), so it is the only place a difference cannot be argued away
as disagreement about history.

*Falsifier:* the bare arm draws zero. That would be a strong and clean negative —
restraint without a substrate — and under §7 it is published as such.

## 5. Stage 3 — both arms, slots B, C and E

Paid. The discriminating cases. This is the experiment.

**P8 — slot B separates on suspension.** Registered: the Manyu arm marks the
Einstein-attribution edge `undetermined`; the bare arm produces a confident
attribution with no marker of the record's silence.

Registered because experiment 5 built and validated a belief shape that refuses
to collapse under equal evidence, and because a model asked "who said this" is
under strong pressure to answer.

*Falsifier:* the bare arm hedges in prose *and* that hedge is machine-separable
in its output. A prose hedge that cannot be read as a state does **not** falsify
P8, and the scoring function must not credit one — that distinction is the
substance of the claim and §8 fixes it as binary before either arm runs.

**P9 — slot C degrades in both arms, and degrades together.** Registered:
neither arm exceeds **0.6** recall, and the gap between arms is **smaller** than
the gap measured on slot D.

Registered because with hostile witnesses the hard part is reading polemical
prose, which is again the model's contribution. Slot C is where this experiment
is expected to be least flattering to the substrate, and saying so in advance is
what makes the slot worth running.

**P10 — slot E separates, conditional on P2.** Registered **only if P2 held at
stage −1**: the Manyu arm keeps the testimony-only edge separable from the
textually supported edges; the bare arm conflates them.

If P2 failed, P10 is withdrawn rather than restated against an authored edge
type, and slot E is reported under requirements §12.3. This conditional structure
is registered now precisely so that the decision cannot be made after seeing
stage 3's output.

## 6. What would make this experiment uninteresting

Registered in advance so that none of these can be discovered late and presented
as a nuance.

1. **The arms tie on every slot.** The substrate contributes bookkeeping. §7
   governs.
2. **Extraction noise exceeds every between-arm difference.** Then this is an
   extraction experiment wearing an archaeology costume, and stage 1 is designed
   to catch it before any scoring spend.
3. **Slot D is trivial for both arms.** If neither arm ever draws a spurious
   edge, the null was too easy and proves nothing about restraint. Note the
   asymmetry with P7's falsifier: a bare arm scoring zero is informative only if
   the slot could have caught it, so slot D's generator must be shown at stage 0
   to be *capable* of eliciting a spurious edge from a similarity-based
   reconstructor. That check is stage 0's second job and is registered here
   rather than left to judgement.
4. **The key's author and the arm agree because they read alike.** Unfalsifiable
   from inside. FR-2's hand-authored key bounds it; it does not eliminate it, and
   the retrospective must say so.

## 7. If the arms tie — the pre-registered response

Written before any result, because this is the decision most vulnerable to being
made after one.

If stage 2 shows a tie on both slot A and slot D:

- The tie is **published as the headline**, in the same table as everything else
  (FR-10).
- Stage 3 still runs. A tie on calibration and restraint does not predict a tie
  on suspension and discrimination, which are the slots where the substrate's
  contribution is hypothesised to live.
- The requirements §1.1 deliverable — cross-source provenance tooling — is
  **reconsidered rather than shipped**. Building tooling whose measured
  contribution is zero would be building it because it was promised.

What is forbidden: adding a sixth slot, re-cutting the existing slots, or
adjusting the metric in search of a difference. A slot may be *added* to a future
experiment; it may not be added to this one after a result.

## 8. Fixed constants

Pinned here and enforced by an `assert_constants_pinned`-pattern test
(methodology §4). Changing any of these after a run is an amendment under §9 and
must be dated.

| Constant | Value | Why this value |
|---|---|---|
| Slot C recall ceiling (P9) | 0.6 | Set from expectation, not data — no slot C output exists |
| Identity re-extraction count (P5) | 10 | Smallest run count that makes "at least one disagreement" a weak claim rather than a coin flip |
| Direction sensitivity | on | A reversed edge scores one false positive and one false negative, never partial credit (methodology §6) |
| Slot D restraint reporting | raw count | A rate's denominator is the node-pair count, which is arbitrary and would flatter every arm |
| Aggregate score | **forbidden** | Requirements §11 — one number lets recovery hide a restraint failure |

## 9. Amendments

All three below were written on 2026-08-12, **before any experiment code existed
and before any corpus was transcribed**, following a design review that read the
substrate rather than the spec. None was written after seeing a result, because
no result exists yet. That is the only circumstance under which an amendment to
this file is cheap, and it is why the review happened before implementation
rather than during it.

### A1 — 2026-08-12: §0.1 states a value the substrate does not produce

**What was wrong.** §0.1 asserts that every source in the corpus lands on
`TrustClass.UNTRUSTED_TEXT`, and presents this as arithmetic over an enum rather
than as a forecast. The arithmetic is over the wrong function.

`BeliefEvidenceService._trust_from_source`
([services.py:496](../../../src/manyu/services.py)) maps source types to trust
classes, and `OPERATOR_NOTE` — the least-wrong source type for an external
historical document, per §0.1 itself — maps to **`TrustClass.OPERATOR_INPUT`**:

```python
if source_type == BeliefEvidenceSourceType.OPERATOR_NOTE:
    return TrustClass.OPERATOR_INPUT
```

`UNTRUSTED_TEXT` is reached by no branch of that function at all. A corpus record
carries `UNTRUSTED_TEXT` only if the loader passes `trust_class` explicitly
rather than letting it be derived.

**What survives.** The conclusion, entirely. §0.1's claim is that `trust_class`
contributes **zero discrimination across this corpus**, and that holds under
either value, because whichever value is chosen is constant across all five
slots and both arms. Nothing that depends on §0.1 changes.

**What changes.** The stated value, and the epistemic status of the statement.
It was recorded as derived-by-hand; it was in fact an unverified assumption about
a function nobody had read. Stage −1's census now **measures** the value the
corpus actually carries and reports it, rather than asserting it — which is what
§0 should have done in the first place for a claim of this kind.

The `BeliefEvidenceSourceType` half of §0.1 is unaffected: no value denotes an
external document, and `OPERATOR_NOTE` remains the least-wrong slot rather than
a correct one.

### A2 — 2026-08-12: P1's falsifier contradicts §2's escape, and the contradiction decides whether the experiment ends at stage −1

**The inconsistency.** P1's falsifier names *"the descent edge itself"* as a
field that must have a home surviving a process boundary. Requirements §2's
escape, and P2 with it, describe an edge as something **derived** — *"an edge
asserted by testimony yields one evidence record; an edge supported by textual
descent yields records in both documents, with distinct `source_id`s."*

Read the first way, P1 is trivially false and the experiment ends at stage −1 as
a schema project. Read the second way, P1 is trivially true and its falsifier is
unreachable. The spec as written does not say which, and **the reading decides
the outcome of the stage.** Resolving it after seeing stage −1's artifact would
be choosing the answer.

**Resolution: the derived reading.** A descent edge is not a stored object. It is
a relation over the evidence records two claim-instances cite, plus the
publication dates in those records' metadata.

**The reason, which is not convenience.** A stored edge is a *declared* edge, and
a declared edge makes reconstruction a read-back — the reconstructor's job
collapses to reading the field a fixture wrote. This is exactly the discipline
experiment 5 applied when it put `rivals` on `Belief` and deliberately **off**
`BeliefCandidate` ([schemas.py:481](../../../src/manyu/schemas.py)), so that no
fixture could declare underdetermination into existence. Storing descent edges
would invert that precedent for this experiment's central dependent variable.

Two further reasons, both verified against source, recorded so the decision is
not re-opened on aesthetic grounds:

- **`Belief.supports` is not free.** `RevisionEngine` walks `supports` to
  propagate confidence ([revision.py:495](../../../src/manyu/revision.py)) and
  derives contradiction strength from a count of supporters
  ([revision.py:680](../../../src/manyu/revision.py)). Loading descent edges into
  it would make confidence a function of how long a genealogy is — a free
  parameter entering through graph shape, which is what §12.2 forbids.
- **`supports` cannot carry edge attributes.** FR-5 needs "what supports this
  edge, or explicitly nothing"; §11 needs a mutation operator and an
  `undetermined` marker per edge. The field is `list[str]`.

**Consequence for P1.** P1 is assessed against the metadata leg only — locus,
date, excerpt, content hash, citation, and document identity. The edge leg is
withdrawn from its falsifier. P1 therefore reads: *a claim-instance is
representable with no new production code.*

### A3 — 2026-08-12: P3's absolute prediction, and slot C's key shape

Two decisions that FR-3 requires be made now, because it bars adjusting a metric
after a result.

**P3 stays at precision 1.0 and recall 1.0.** The bar is not softened and no
tolerance is added.

But the registered *response* to a miss is recorded here rather than left to
judgement. Slot A's key is hand-authored (FR-2) and its instances are hand-encoded
at stage 0, so P3 tests agreement between two acts of the same author's judgement
— which §6.4 already names as unfalsifiable from inside. A miss is therefore at
least as likely to be a key-authoring choice as an algorithm defect.

> **On a P3 miss, the first action is a recorded re-read of the key**, with the
> re-reading and its outcome written into the stage 0 artifact. Only if the key
> survives the re-read does requirements §9 end the stage.

The alternative — ending the stage automatically — would end the experiment over
a disagreement about how one edge should have been keyed. The alternative in the
other direction, adding a tolerance, would soften the one rung whose absoluteness
is what makes stage 0 meaningful. Neither is taken. What is forbidden, and what
this amendment exists to prevent, is *drifting* into the re-read without having
said in advance that it was permitted.

**Slot C is keyed partially, on settleable edges only.** §7.3 says slot C's
answer-key certainty is "low, and that is the point," while methodology §3 step 5
permits marking unsettleable edges `undetermined` in the key. Between those, the
slot could be keyed two ways, and the choice was undetermined.

Decided: transcribe and key **only the commentarial links the documents actually
settle**, and score slot C on those. The reason is that a full key's
`undetermined` count would be an **authored quantity** — the key author decides
how many edges are unknowable — and slot C's job is to measure how reconstruction
degrades under heavy mutation and hostile witnesses, not to measure how much the
author marked unknown. Suspension is already scored in slot B, where the record's
silence is externally established rather than chosen.

This also materially reduces what must be transcribed in the most expensive slot
in the corpus, which is a real benefit but is not the reason.
