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

### A4 — 2026-08-13: the mutation vocabulary was incomplete, and `NONE` was two facts

**What contact with real sources found.** Slot B's step 2 transcription established
that Gamow told the "biggest blunder" story twice — in 1956 and again in 1970 — and
that the second telling moves *"the cosmic repulsion idea"* to *"the introduction of
the cosmological term"*. That changes what the claim is **about**.

`classify_mutation` returned `NONE`. Identically to a verbatim copy.

**The defect.** `MutationOp.NONE` meant two different things at once:

1. the excerpt is unchanged, and
2. the excerpt changed in a way the vocabulary has no operator for.

The scored mutation dimension cannot separate those, so a corpus of substantive
rewordings and a corpus of verbatim copies produce the same numbers. For an
experiment whose dependent variable **is** mutation, that is not a gap in coverage —
it is the measurement failing on the most common case.

**The amendment.**

- `NONE` is tightened to mean **unchanged**, modulo whitespace and case — the same
  leniency `_normalize_belief_key` applies
  ([schemas.py:400](../../../src/manyu/schemas.py)), on the grounds that line breaks
  and capitalisation are accidents of transcription rather than changes a source made.
- `REWORDING` is added as the **residual**: the excerpts differ and no more specific
  operator applies.

**Why this readmits no free constant.** `REWORDING` is defined by the *absence* of the
other operators, not by a similarity score. Two excerpts are either the same string or
they are not. No threshold is introduced, and
`test_the_module_declares_no_similarity_threshold` still passes.

The named operators keep precedence — attribution shift, then deletion, then
qualification, then the residual — so nothing that carried information before now
collapses into it.

**A correction to the corpus-design guidance, recorded because it changed what slot B
must contain.** The step 1 "check 2" (*two instances with near-identical wording*) was
written as a per-slot requirement. It is a **portfolio** requirement: the
verbatim-repetition case must exist somewhere in the corpus, most naturally in slot A
where propagation is heavy. Slot B does not need downstream repeaters to satisfy it.
Recorded because the error was mine and it was actively directing transcription effort
at documents the experiment does not need.

### A5 — 2026-08-13: slot B admits a second claimed eyewitness, and gains a second question

**What transcription found.** The attribution does not rest on Gamow alone. Wheeler, in
Taylor & Wheeler's *Exploring Black Holes* (2000), claims to have **heard the remark
himself**, while placing Gamow at the same scene. That is not a repetition of Gamow — it
is a first-person claim of independent origin, made decades after the event and 44 years
after Gamow first put the phrase in print.

**Why this needs an amendment rather than a decision.** §7.2 registers slot B as a clean
single-origin suspension case. Admitting a competing independent-origin claim changes
what the slot measures: it now also tests whether the mechanism keeps an **asserted
independent origin** separable from **textual descent**. Deciding that after seeing the
reconstruction would be choosing what the slot tests once its answer is known.

**Decided: admit it.** Suspension is not displaced — it is enriched, because the corpus
now carries two edges the record cannot settle rather than one. And the competing-witness
structure is the honest historical situation; excluding it would produce a tidier slot
that misrepresents its own subject.

**How it is encoded, and this is not optional.** Wheeler is handled through an *asserted
descent*, never a shared span. Measured against the mechanism, his wording shares exactly
two tokens with Gamow's — *"biggest blunder"* — which is the name of the legend itself.
Recording that as a span produces a `TEXTUAL` edge from Gamow to Wheeler that
**contradicts Wheeler's own claim**, and any rule admitting it would admit every document
that mentions the story. Verified both ways against `reconstruct` before this amendment
was written.

`alpher1998` — a third reported recollection, on a mailing list — is **excluded** unless
the post proves retrievable. An unretrievable post is not a document.

### A6 — 2026-08-13: the graph traces descent of text, not endorsement of claim

**The confound, found independently in three slots.** Correcting a claim requires quoting
it. So a correction shares a distinctive span with the thing it corrects, and the
mechanism reads that as `TEXTUAL` descent — which by the ordinary meaning of the word it
is, and by the meaning the experiment cares about it is not.

- **Slot A** — the 1945 origin and its modern corrections share the qualifier, because
  quoting it is how the correction works.
- **Slot B** — the investigations share Einstein's own wording, because investigating the
  attribution requires quoting what he actually wrote.
- **Slot C** — a hostile witness preserves an opponent's position *only* by quoting it in
  order to demolish it. There the confound is not incidental: it is the slot's entire
  source of evidence.

**What is not done.** No polarity or stance field is added. That would author a capability
to win a slot, which is what FR-1 exists to prevent, and it would replace a measurement
with a declaration.

**What is recorded instead.**

> A reconstructed edge asserts that **text descended**. It does not assert that the
> descendant **endorsed** the claim. A refutation, a correction and a repetition are
> indistinguishable to this mechanism, and all three are real descent of text.

Consequences that bind:

1. The keys mark these edges as ordinary textual descent. They are not exceptions.
2. `results.md` must state the limitation in the headline rather than in a caveat, on
   FR-11's pattern — an unmeasurable is reported as unmeasurable, not as absent.
3. The corpus must not omit a correction in order to avoid the edge. Omitting it would
   suppress the finding, which is worse than reporting it.
4. **Slot C is reported under this limitation explicitly**, because there the mechanism
   can see a position's survival but never that it survived inside a refutation.

This is a genuine limitation of the design surfaced by transcription — which is what the
offline stages exist to surface — and not a defect to be patched before the run.

### A7 — 2026-08-13: `published` means position in the declared chain, for slot C only

**The problem.** `reconstruct` takes edge direction **only** from
`metadata["published"]`, and declines any pair sharing a date as *"direction
undecidable."* But dates for Sanskrit commentarial texts are scholarly estimates spanning
decades or centuries. They are precisely the *inferred, not held* dates the corpus
discipline rejects, and slot C cannot supply anything better.

Read strictly, slot C is untranscribable.

**The resolution.** A commentarial chain **documents its own order**. A *bhāṣya* declares
what it comments on; a *vārttika* declares which *bhāṣya*. The ordering is stated in the
documents rather than reconstructed from chronology — which makes it *better* evidence of
direction than a publication date, not worse.

> **For slot C, `published` encodes position in the declared commentarial chain, not
> calendar date.** Every slot C corpus file must carry
> `"published_semantics": "declared_chain_position"` so no later reader mistakes the field
> for chronology.

**What this does not license.** Nominal ordering dates may encode **only** relations a
document declares. Where the chain is silent — two sub-commentaries on the same *bhāṣya*,
or rival schools with no commentarial relation — they take the same nominal position and
the mechanism declines the pair. That decline is correct: the documents do not order them,
and inventing an order to force an edge would author the dependent variable through the
date field, which is the specific failure A3's convention exists to prevent.

Recorded before slot C is transcribed, and before any slot C edge has been seen.

### A8 — 2026-08-13: slot C is cut, and A7 is thereby moot

**Decision: slot C is removed from the corpus.** The scored slate is A, B, D and E.

**Why, and it is not cost.** Slot C's step 2 worksheet — written before any Sanskrit was
transcribed — established that the slot cannot measure what §7.3 charters it to measure.
Every scored dimension collapses:

| Dimension | Slot C |
|---|---|
| Edge precision / recall | Direction is **assigned** from declared relations under A7, not derived. Scoring it reads back the experimenter's own input. And the root-phrase span connects **every layer to every layer**, because glossing its root is what a commentary *is* |
| Restraint | Slot D only |
| Suspension | Slot B only |
| Discrimination | The hostile-witness span is **degenerate** — the quoted position and its refutation share a physical page, so the pair declines on a shared ordinal by construction |
| Mutation labelling | The only survivor |

So slot C reduces to a mutation-labelling test, and slot A tests mutation more cleanly:
its deletion is checkable because the ancestor survives independently.

**The decisive point is the hostile witness.** That structure was the slot's entire reason
for existing (§7.3), and it produces an **expected decline** — derivable from the design
without transcribing a word. A null you can predict from the fixture's shape is not a result
that needs running.

**What is withdrawn.**

- **P9 is withdrawn.** It registered slot C degrading with neither arm above 0.6 recall and
  a smaller between-arm gap than slot D. There will be no slot C measurement to compare it
  against. A withdrawn prediction is recorded, never deleted.
- **§7.3's charter** ("stress — heavy mutation, hostile witnesses") no longer describes any
  slot in the experiment. The stress question is unanswered, and the results must say so
  rather than let the remaining four slots imply it was covered.
- **A7 is moot**, since it governs only slot C's `published` semantics.
- **A6's fourth consequence** — slot C reported explicitly under the text-versus-endorsement
  limitation — falls away. **A6 itself stands**: slots A and B both exhibit the confound and
  it is reportable from them.
- Stage 3 becomes **slots B and E** rather than B, C and E.

**A7 was also incomplete, recorded because it would matter if slot C ever returns.** It
licenses ordinals from declared relations but never says that direction must therefore go
**unscored**. Assigned direction scored back is a read-back — the defect A2 refused when it
made edges derived rather than stored. Any future reinstatement of slot C must close that
gap before transcription, not after.

**What this decision does NOT claim.** It is not a finding about commentarial traditions,
which are richly ordered and self-documenting. It is a finding about **what this mechanism
can measure on them**: a reconstructor whose only direction signal is a date field cannot
derive descent in a corpus whose ordering is declared rather than dated, and whose shared
text is universal by genre.

**Why cutting is legitimate now and would not be later.** No slot C data exists. Not one
excerpt was transcribed, no key was authored, and no edge was ever reconstructed. Removing a
slot before any of its data exists is scope management; removing it after seeing its numbers
would be selection on the dependent variable, and would invalidate everything the other
slots report. The distinction is the entire reason this amendment is dated today rather than
during analysis.

This is the offline stages working exactly as chartered. Requirements §9 gives each rung the
power to end the experiment; the same discipline applied to a single slot ends the slot. The
cost avoided — four layers of Sanskrit, an unresolved edition question, and a translation
that would have made the mutation operator measure the translator — is a benefit and is not
the reason.

### A9 — 2026-08-13: an assertion pointing at nothing must be countable

**What slot E's step 2 found.** Hamblin (1981) asserts that the spinach claim descends from
a decimal-point error, and **names no document**: only "German chemists" and "the original
workers". No von Wolff, no Bunge, no date, no citation. That emptiness is confirmed by a
peer-reviewed source and is one of slot E's findings rather than a gap in the corpus.

An assertion whose upstream endpoint is never named is not an edge case here. It is the
**commonest situation in a contested genealogy**, and slot B has the same shape — Gamow
asserting a remembered conversation.

**The defect, verified against the mechanism before this was written.** Encoded the obvious
way — record the assertion, let the edge not form — the assertion **disappears entirely**:

- no pair can share a record only one instance cites, so no edge forms;
- the pair's `declined` reason reads `"no shared evidence record"`, which is **false**, since
  a record exists and has one end;
- the record appears nowhere in `Reconstruction.as_dict()`.

FR-5 exists precisely so that nothing vanishes without a record: *an edge that vanishes
without a record is indistinguishable from one never considered*. A silent assertion is the
same failure a step earlier.

**The amendment.** `Reconstruction` gains `unresolved_assertions` — assertion records
reaching fewer than two claim-instances, reported as
`(record_id, asserting_source_id, reason)`. Step 3a stamps
`metadata["record_kind"] = "assertion"` on records generated from a worksheet's `ASSERTED
DESCENTS` block.

**Why this is not FR-1's violation**, which is the question that matters:

1. **`classify_support` never reads `record_kind`.** The discriminator still derives
   `TESTIMONY` from shared-record cardinality together with `source_id` distinctness, exactly
   as P2 registered and stage −1 measured. Pinned by
   `test_record_kind_never_reaches_the_discriminator`.
2. **`score` never reads it either**, and no scored dimension moves. Pinned by
   `test_unresolved_assertions_do_not_move_a_scored_dimension`.
3. It **reports** something already present in the corpus rather than adding a signal that
   decides an edge.

FR-1 forbids authoring an edge type to win slot E's discrimination. This authors no edge
type, wins nothing, and touches no scored quantity.

**What it deliberately refuses to do.** Absent a `record_kinds` map, nothing is reported.
Guessing which singly-cited records were *meant* as assertions would invent the finding — and
most singly-cited records are ordinary span records, so a heuristic here would fire
constantly and mean nothing.

**The option not taken.** A placeholder node standing in for Hamblin's unnamed source was
considered and refused. It would be a node with no document, no excerpt and no date —
exactly what A5 refused when it kept Weinstein's unattested German original out of slot B.
The same rule gives the same answer, which is what makes it a rule rather than a preference.

The correct output is that **the edge does not form and the assertion is reported.** A
genealogy that shows an assertion pointing at nothing is more informative than one that
shows nothing at all.

---

## A10–A12: the source-contact pass, 2026-08-13

The three investigation papers were obtained and read: Valtin (2002) for slot A, Livio
(2013) and O'Raifeartaigh & Mitton (2018) for slot B, Rekdal (2014) for slot E. Each
overturned something the requirements asserted.

**The pattern is itself a finding and belongs in `results.md`.** Four slots have now had a
premise refuted by contact with their own sources: slot C was cut (A8), slot A's origin
turns out contested (A10), slot B's silence turns out to be disagreement (A11), and slot E
has a lineage a layer deeper than charted (A12). None was caught by reading the spec. All
were caught in step 2, before any key was authored and before any spend.

That is what the offline stages are for. It is also a measurement of how much of the
original §7 was assumption presented as fact, and the results must say so rather than
present four tidy slots as though they had been designed correctly.

### A10 — 2026-08-13: slot A's origin is contested, and its head carries no textual descent

**What Valtin establishes.** §7.1 charters slot A as calibration — *"recover a lineage that
is objectively in the record"* — on the premise that the 1945 → "8 glasses" chain is
documented. The paper that documents it refutes that premise.

Valtin does not assert the FNB origin. He reports it at two removes: *"According to J. Papai
(65), P. Thomas has suggested a different origin"*, where ref 65 is a page on
`urbanlegends.com` and "P. Thomas" is never fully cited. The dropped-sentence claim —
that the last sentence was not heeded — is **Thomas's assertion about descent**, not a
textual link.

His own candidate origin is Stare & McWilliams (1974, p. 175), which he immediately
undercuts: not one of the sources he read cites it, and half a dozen leading nutritionists
could not point him to it.

**And the wordings do not match.** FNB 1945 says *2.5 liters* and *1 milliliter for each
calorie*; Stare says *6 to 8 glasses*, counting coffee, tea, milk and beer toward the total;
the modern claim is *eight 8-oz glasses*, excluding exactly those. **No shared span carries
the top of this chain.**

**Decided: slot A is narrowed, not cut.**

- **Calibration is retained for the lower half** — the modern propagation of the stock phrase,
  where verbatim repetition is expected and textual descent is demonstrable.
- **The origin edge is marked `undetermined`**, with two rival candidates (FNB 1945 and Stare
  1974), neither textually linked to the claim.

**Consequences.** P3 is unaffected: it scores hand-fed instances at stage 0 and `score`
excludes undetermined edges from `expected`. P6 — the arms tying on slot A — now concerns
the textual lower half, and is recorded as such. The slot becomes *better* than chartered:
it carries calibration, a genuine underdetermined edge, and the portfolio's verbatim case.

**Confirmed from Valtin's reference list**, and superseding the worksheet's guesses: FNB 1945
is *Recommended Dietary Allowances, revised 1945*, National Research Council, Reprint and
Circular Series No. 122, **1945 (Aug), pp. 3–18** — month resolution confirmed. Stare &
McWilliams is *Nutrition for Good Health*, Fullerton CA: Plycon, 1974, **p. 175**.

### A11 — 2026-08-13: slot B's edge is undetermined because the investigators disagree

**What the two investigations say.** Livio (2013, ch. 10) concludes Gamow probably invented
the phrasing, and states his search scope: Einstein's papers, books and personal
correspondence after 1932, chosen because that is when Einstein and de Sitter declared the
constant unnecessary; plus Pauling's diary, where Einstein calls the Roosevelt letter *one
great mistake* and not the constant; plus evidence that Gamow and Einstein were **not**
close.

O'Raifeartaigh & Mitton (2018, *Physics in Perspective* 20: 318–341; arXiv:1804.06768)
conclude the opposite — that it is very likely Einstein said it — on reports from three
independent physicists.

**The amendment.** P8 **stands, re-grounded.** It was registered on the premise that the
record is silent. The better reason is that **two published investigations reach opposite
conclusions from the same evidence**. An edge two experts contest is undetermined in a
stronger sense than one merely uncited, and it is the sense experiment 5's machinery was
built for.

This was very nearly got backwards. Reading O'Raifeartaigh & Mitton's abstract alone
suggested P8 would fail; Livio's chapter shows P8 is safer than registered. **A conclusion
drawn from one investigation would have been wrong in a way no later check would have
caught**, because it would have produced a confident key that the arms were then scored
against.

**Livio's scope qualifies** under the standard this experiment applies to every disputant —
a search of unstated scope establishes no absence. His is bounded and checkable.

**Slot B's repeaters are identified**, ending the harvest problem: Gino Segrè (*Ordinary
Geniuses*), Albrecht Fölsing (who assumed Gamow authentic and repeated the citation), and
J. P. Leahy ("Einstein's Greatest Blunder").

**One caution recorded.** A PDF supplied as "Livio" was a three-page book review in a
mathematics newsletter, not the book. It garbles the claim and misspells Gamow, and its ISBN
disagrees with the book's. It is a legitimate corpus node as a downstream mutation, and it is
**not** the investigation. Its brief mistaken use is recorded here because the failure mode —
a secondary source standing in for the primary one — is the exact failure slot E studies.

### A12 — 2026-08-13: slot E's lineage runs a layer deeper, and gains a second undetermined edge

**Five Bender nodes, not four** (Rekdal 2014: 645, with loci):

| Node | Locus |
|---|---|
| Bender 1972 | p. 11 — inaugural lecture, Queen Elizabeth College |
| Bender 1975a | **p. 15** — *The Facts of Food*, reportedly the same sentence |
| Bender 1975b | **p. 142** — journal article, same year |
| Bender 1977 | *The Spectator* — hedge weakened |
| **Bender & Bender 1982** | **p. 55** — medical textbook |

**Bender & Bender 1982 is new and is the most mutated node in the corpus.** It postdates
Hamblin by a year, adds a specific year (1870), and converts "misplaced decimal point" into
"a mistake in the transcription of analytical results".

**And Rekdal marks its ancestry undetermined himself**: he cannot tell whether Bender's
increased certainty came from his own further investigation or from Hamblin's 1981 article.
That is an undetermined edge **stated by the investigator**, not argued for by the corpus
author — the strongest form available, and slot E now carries two undetermined edges rather
than one.

**Also recorded.**

- **Sutton is 2010a and 2010b**, two documents. This supersedes the worksheet's
  2010-versus-2012a framing; the one-node-one-document rule applies to both.
- **Hamblin's own reply to Sutton** (2010a: 7): he could not remember where he learned it,
  but was sure he had not made it up. A first-hand statement about the origin's
  unknowability, and direct evidence for the undetermined mark.
- **Larsson (1995: 448–449)** — Rekdal's own entry point, absent from the worksheet.
- **Bonnie Taylor-Blake** — the reader who connected Sutton to Bender; a node in the
  discovery chain rather than the descent chain, and it must not be confused for one.
- **Rekdal's dates**: OnlineFirst 12 June 2014, a second OnlineFirst 23 June 2014, Version of
  Record 29 July 2014, issue 44(4). Per the convention that `published` is when a text became
  available to be descended from, **12 June 2014** governs. Two OnlineFirst versions means the
  text may have changed between them; whichever is used must be recorded.

**A transcription hazard, recorded because it would be invisible in a corpus file.** The
indented blocks on Rekdal p. 640 are **his own constructed example sentences**, written to
illustrate citation practice. They are not quotations of any source. Harvesting excerpts by
layout would file them as corpus instances, and they would look entirely plausible as
layer-2 repetitions.

### A13 — 2026-08-13: an edge can carry more than one mutation; the vocabulary returns one

**Found on the first real corpus.** In slot A's pilot, `vreeman2007 → carroll2015` is
reported as `ATTRIBUTION_SHIFT` — Vreeman names Valtin, Carroll degrades that to a bare
hyperlink. It is *also* a genuine `DELETION`: Carroll's excerpt is a proper sentence-subset
of Vreeman's. Both are true. `classify_mutation` returns the first that matches, so the
deletion is invisible.

This was not anticipated by §11 or by A4, and it was not visible on the synthetic fixtures —
only a corpus where one source both re-attributes *and* abridges its predecessor produces it,
which is what real correction chains do.

**Decided: `mutation` stays single-valued for now.** The concession is recorded: an edge
genuinely can carry several mutations, and the single value is a simplification rather than
a claim about how texts change. Making it a set is the faithful design and remains open.

**Why not now.** Changing it alters what `mutations_identified` and `mutations_misidentified`
count, which are scored dimensions. No key exists yet, so the change would be legitimate
today — but the pilot has not yet shown that the loss matters, and §11's dimensions should
not be re-cut on a single instance. If a hand-authored key turns out to need two operators on
one edge often enough to distort the score, that is the trigger, and the amendment is written
then.

**The binding consequence, and it falls on the key author rather than the code.**

> A key must record **only the highest-precedence operator** for each edge. A key recording
> both `attribution_shift` and `deletion` would count one as `misidentified` against an arm
> that was entirely correct.

The precedence is fixed, and is now pinned by
`test_mutation_precedence_is_fixed` so that reordering the checks cannot silently invalidate
keys authored under the old order:

1. `ATTRIBUTION_SHIFT` — `attributed_to` differs
2. `DELETION` — the descendant's sentences are a proper subset of the ancestor's
3. `QUALIFICATION` — the hedge set differs
4. `REWORDING` — the excerpts differ and nothing above applies
5. `NONE` — the excerpts are identical modulo whitespace and case

The ladder is also carried in every corpus file's `key_authoring_note`, because that is where
a key author will be looking, and a rule that lives only in the pre-registration is a rule
someone applies from memory.

### A14 — 2026-08-14: `alpher1998` is admitted, and this amendment is late

**Decision: `alpher1998` enters slot B.** A5 excluded it. That exclusion is lifted.

**A5's condition, and what actually happened.** A5 wrote:

> `alpher1998` — a third reported recollection, on a mailing list — is **excluded** unless
> the post proves retrievable. An unretrievable post is not a document.

The post did **not** prove retrievable. The HASTRO-L archive was never consulted. What was
obtained is a *reproduction*: O'Raifeartaigh & Mitton print Alpher's recollection verbatim as
Figure 7 of their 2018 paper, in *Physics in Perspective*, under peer review.

So A5's literal condition is **not met**. Its purpose is. The condition was protecting
against a claim that could not be checked — a recollection reachable only through someone's
paraphrase of a vanished e-mail. A verbatim reproduction in a peer-reviewed paper fixes the
text, dates it, and makes it checkable by anyone with the paper. That is the same protection
by a different route, and it is the route slot A already relies on for Stare & McWilliams and
slot E relies on for Larsson: **a witness's words live in the document that reproduces them.**

**This amendment is late, and that is a defect in the record.** `alpher1998` was added to
`corpus_B.json` and committed in `0445906` *before* this amendment was written. The amendment
discipline exists so that a decision is on the record before its effect is visible, and here
the effect — slot B at 11 instances and 10 edges, two of them testimony — was visible first.

What limits the damage, stated so a later reader can weigh it rather than take reassurance:

- **No arm has run and no key exists.** Nothing about a *result* informed this. The scored
  dimensions have never been computed on any slot B corpus, with or without Alpher.
- What *was* seen first is the corpus **shape**: that admitting Alpher yields one more
  textual edge (`alpher1998 → oraifeartaigh2018.q_alpher`) and one more testimony edge.
- A reader who thinks that is enough contamination to matter should discount this amendment
  and read the pre-Alpher corpus at `1bb76aa`. Both states are in the history on purpose.

**What changes.** §7.2 registered slot B as a clean single-origin suspension case; A5 made it
two claimed origins; this makes it **three**. That is not decoration — O'Raifeartaigh &
Mitton's published argument turns on exactly this: *"it seems a stretch to accuse three
different scientists of invention."* The count of independent reports is load-bearing in the
literature the slot is drawn from, so a corpus holding two of three misrepresents the dispute
it exists to encode.

**How it is encoded, and this is not optional — the same constraint A5 imposed on Wheeler.**
`alpher_recall` is *"his introduction of the concept in his early work was a blunder"*. It
shares **no** distinctive run with `blunder_phrase`; Alpher has no superlative at all — no
*biggest*, no *of my life*. No span therefore connects Alpher to Gamow, and no `TEXTUAL` edge
between them can form. Verified against `reconstruct` before this amendment was written: the
`gamow1956 → alpher1998` pair declines on `no shared evidence record` until an assertion
carries it.

**A limitation this creates, recorded rather than fixed.** O'Raifeartaigh & Mitton *raise*
the possibility that Wheeler and Alpher were influenced by Gamow and then argue against it.
The record vocabulary can say *"a third document asserts this descent"*; it cannot say
*"raises it and declines to affirm it"*. Both edges therefore come out `TESTIMONY`, which is
**stronger than what the source wrote**. The key must mark them undetermined, and `results.md`
must report the gap between what O&M wrote and what the graph can hold.

**A5 is not withdrawn.** Its reasoning stands, including its refusal to record a Gamow →
Wheeler span; only its exclusion clause is superseded, and its condition is the reason this
amendment had to be written at all.

### A15 — 2026-08-14: FR-2 is suspended, and the keys are provisional

**Decision: `key_A.json`, `key_B.json` and `key_E.json` are installed from
model-authored drafts, at the experimenter's explicit and repeated instruction.** FR-2 —
"answer keys are hand-authored; no model is involved in their production" — is suspended
for these three files and for no others. `key_D.json` is unaffected: it is generated
alongside its corpus by design (FR-8).

**What FR-2 was protecting against, stated concretely because it is now unguarded.** The
Manyu arm's reconstruction is produced by a mechanism; the bare arm's is produced by a
model. Scoring either against a key a model wrote measures *agreement between two
readings of the same documents*, at least one of which shares the failure modes of the
thing being measured. It does not measure correctness. Crucially the failure is **silent**:
the output is a set of well-formed numbers that look exactly like a result.

**The demonstration, run before this amendment was written.** Against these keys, with
suspension wired:

| slot | precision | recall | mutations identified |
|---|---|---|---|
| A | **1.0** | **1.0** | 7 of 7 |
| B | 0.50 | 0.36 | 6 of 18 |
| E | 1.0 | 0.25 | 0 of 12 |

**Slot A returns exactly 1.0 / 1.0 — the threshold §2's P3 registers as its criterion.**
P3 is therefore, on paper, confirmed. It is not. That number is the clearest available
statement of why FR-2 existed: a prediction that was meant to be hard to satisfy was
satisfied on the first attempt by a key that agrees with the mechanism because both read
the same documents the same way.

**Binding consequences.**

- **P3 is NOT confirmed and may not be recorded as confirmed.** Any 1.0/1.0 obtained
  against `key_A.json` in its present state is void.
- **No stage 1–3 result computed against these keys may be reported as a measurement of
  reconstruction accuracy**, for either arm, including the between-arm difference — a
  model key can be wrong in ways that flatter one arm and not the other, and nothing here
  detects that.
- **The keys are deliberately NOT frozen.** Freezing is the commitment step; these are
  explicitly provisional. `freeze.json`'s `files` block continues to carry slot D only,
  and the absence is now a statement rather than an omission.
- Each key file carries its provenance in `authored_by`, at the top, before the original
  draft's own header. Neither may be stripped.

**What lifts the suspension.** Hand-authored keys, from the worksheets at
`docs/experiments/08-epistemic-archaeology/key-worksheets/` — 18 decisions for slot A, 47
for B, 12 for E — converted by `key_from_worksheet.py`, which makes no judgement. On
arrival they replace these files and are frozen, and this amendment is superseded rather
than deleted.

**One corpus defect is unresolved underneath this and inflates slot E's numbers.** The span
`misplaced_decimal_point` occurs verbatim in all three `rekdal2014` excerpts and the corpus
records it only for `bender1972` and `bender1977`, in breach of the shared-span rule. Six of
slot E's nine false negatives are that error rather than a disagreement about descent. The
fix is a judgement — record it, or exclude it with a note as A5 excluded *"biggest blunder"* —
and it is not made here.

### A16 — 2026-08-14: `misplaced_decimal_point` is recorded for `rekdal2014`

**Decision: the span gains `rekdal2014`, and slot E gains six textual edges.** A15 left this
open; it is settled here.

**It was a defect, not a judgement.** The phrase *"a misplaced decimal point"* occurs
verbatim in all three `rekdal2014` excerpts. The shared-span rule takes one record per
document a span appears in, so the corpus was in breach of its own rule and had been since
the Rekdal loci were added. It went unnoticed because the transcription commit asserted the
opposite — *"Rekdal paraphrases rather than quotes… layer 1 adds nodes and no edges"* — which
is false: his paraphrase reuses Bender's exact four words. That sentence is now corrected in
`known_gaps` rather than deleted.

**How it surfaced, which is worth recording.** A model-authored draft key (A15) asserted
these six edges. Checking the draft against the corpus showed the corpus, not the draft, was
wrong. The drafts are unusable as keys and found a real defect anyway; both facts belong in
`results.md`.

**Why recorded rather than excluded.** A5 kept *"biggest blunder"* out of slot B's spans
because two tokens naming the legend would produce a textual edge contradicting every
witness's claim of independent hearing. The parallel is close enough to have to be answered:
this is **four** tokens and a *description* rather than a name, so the exception would need an
argument specific to this phrase, and there is none. The general principle the two amendments
share: **the corpus records evidence, the key records belief.** Excluding a verbatim span
because it might not mean descent moves a judgement out of the key, where it is visible and
scored, into the fixture, where it is neither.

**What is genuinely unsettled, and now sits with the key author.** Rekdal reached the story
through Larsson from Hamblin — and Hamblin's own wording is *"put the decimal point in the
wrong place"*, which shares nothing. So either Larsson carried Bender's phrasing to Rekdal,
or two writers independently reached for the obvious four words. The corpus cannot tell those
apart and does not try. `hamblin1981` remains correctly outside the span.

**Effect.** Slot E: 3 edges → 9. The six new ones run from both Bender loci to all three
Rekdal loci; `bender* → p640_bare` classifies as `rewording` and the other four as
`attribution_shift`, since the three Rekdal instances differ only in the citation that
follows them. No key is frozen, no arm has been scored, and slot E's corpus is not in
`freeze.json`.

### A17 — 2026-08-14: an assertion may be *raised and declined*, and suspension is wired

**Decision: the record vocabulary gains an optional `undetermined` flag on an asserted
descent.** `descent.undetermined_from_records` derives pairs from it and hands them to
`reconstruct`, which continues to mark what it is told and decide nothing.

**What it fixes.** Until now the vocabulary had one word for two different acts. A document
that *asserts* X descended from Y and a document that *raises* the possibility and argues
against it were both recorded as `assertion`, so both produced a confident `TESTIMONY` edge.
Slot B carries the clean case: O'Raifeartaigh & Mitton write that Wheeler and Alpher may have
been influenced by Gamow's recollections, then answer *"it seems a stretch to accuse three
different scientists of invention"*. The corpus was recording the first half and discarding
the second, and slot B's `known_gaps` has said so since the day those edges were built.

**The second thing it fixes, which was worse.** Nothing anywhere supplied
`undetermined_pairs`. `suspension_correct` was therefore `False` on every slot regardless of
what any key said — a whole registered dimension returning a constant, and returning it in
the shape of a failed prediction. **P8 could not have been tested at all.**

**What the flag does and does not claim.** It records what the *asserting document did*: it
raised a descent and did not settle it. It does not claim the edge is undetermined in fact.
The key marks `undetermined` separately, from the documents, so the dimension still compares
two authorships rather than reading one back.

**The risk this creates, stated rather than managed away.** A corpus author who flags freely
turns `suspension_correct` into a read-back. Two things hold against it: the key is authored
independently, and the flag is a structured form of a sentence that is already in the corpus
as text, not privileged information handed to one arm. **If a bare arm is ever handed the
evidence records rather than the documents, the second protection lapses and this dimension
stops measuring anything.** Whoever builds the arms owns that.

**Demonstrated on slot B before this was written.** The mechanism derives exactly the two
pairs `gamow1956 → wheeler2000` and `gamow1956 → alpher1998` and marks those edges. Scored
against the provisional model key (A15) `suspension_correct` is `False`, because that key
also marks two pairs pointing at O'Raifeartaigh & Mitton's own quoting loci rather than at
the witnesses; scored against the same key with those two removed it is `True`. The dimension
discriminates a right key from a wrong one, which is the only property that makes it worth
scoring — and the first thing it discriminated was an error in a model-written key.

**Not applied to slots A or E.** Neither carries an assertion whose source raises a descent
and declines it, so neither gains a flag. Slot A's undetermined origin edges have an absent
endpoint and form no edge at all; that is a different condition (A9) and is left alone.

### A18 — 2026-08-14: the keys are validated, two rows corrected, `suspended_edges` refused

**Decision: A15's suspension of FR-2 is downgraded, not lifted.** The experimenter has read
the three model-authored keys against the documents and accepted them. `key_A`, `key_B` and
`key_E` are therefore **model-drafted, experimenter-validated** rather than model-authored,
and each file records that in `authored_by`.

**Two rows of `key_B` were wrong and are corrected.** The draft marked
`gamow1956 → oraifeartaigh2018.q_alpher` and `gamow1956 → oraifeartaigh2018.q_wheeler` as
`testimony` + `undetermined`, on the grounds that O'Raifeartaigh & Mitton raise the descent
and decline to settle it. They do — but about **Wheeler and Alpher themselves**, which the
key already records as `gamow1956 → wheeler2000` and `gamow1956 → alpher1998`. These two
endpoints are O&M's own reproductions, which descend from the witnesses textually, and those
edges are recorded separately as well. The draft counted one suspension twice. Corrected to
`textual`, with the reasoning in each edge's `why`.

**It was found by A17's suspension dimension on its first run**, which is the strongest thing
that can be said for that dimension: it discriminated a right key from a wrong one before any
arm existed to be scored, and what it discriminated was an error a human review had passed.

**Why the suspension is downgraded rather than lifted, and this is not a formality.**

- **Reviewing a draft is not deciding independently.** The anchoring failure is well
  established and the worksheets exist precisely because deciding first and comparing second
  is a different act. A validation pass can confirm that every edge is defensible without ever
  asking which edges a reader would have drawn unprompted — and recall, unlike precision, is
  invisible to that kind of review. **Nine of `key_B`'s eighteen edges claim textual descent
  where the corpus records no shared evidence at all, and the validation pass did not catch
  them either.**
- **Slot A's 1.00 / 1.00 is still not P3 confirmed.** The key agrees with the mechanism on
  all seven edges. If the validation asked "is this right?" against the same corpus, that is
  the same reading a third time, not an independent one. **P3 remains unconfirmed**, and the
  keys remain **unfrozen**.

**What still lifts it fully:** hand-authored keys from the worksheets — 18 decisions for slot
A, 47 for B, 12 for E — where the edges are chosen before the mechanism's output is seen.

**Separately: `suspended_edges` is now refused.** `key_D.json` carried a top-level
`suspended_edges` block that `AnswerKey.from_dict` never read. Empty there, so harmless — but
a key author who used it would have lost the entire suspension dimension with no error raised,
`suspension_correct` reading `None` because `undetermined` stayed empty. Suspension is a
per-edge flag; `from_dict` now raises on the block rather than ignoring it, and the empty one
is removed from `key_D.json`. Supporting both spellings was the alternative and would have let
them disagree.

### A19 — 2026-08-14: a third arm, `bare_agent`, registered before any arm runs

**Decision: a third arm is added.** The slate becomes `manyu`, `bare`, `bare_agent`. It is
registered now, while `arms.py` does not exist and no arm has been scored, because an arm
added after a result is a result chosen.

**What it is.** The same corpus, the same key, the same metric — but the model runs inside an
agent harness (Claude Code CLI, or the Agent SDK) with the transcribed sources on disk, tools,
and a multi-turn loop, instead of §8's single pass.

**Why it is worth a third arm rather than a substitution.** §8 names three ways the comparison
can land and calls the third the most useful: *"The bare model handles A and C but cannot hold
B underdetermined or separate testimony in E. This localises the contribution precisely."*
`bare_agent` sharpens exactly that axis. If a stock model fabricates edges on slot D and an
agent with the same documents on disk does not, then the substrate's contribution on that slot
is bookkeeping and working memory rather than reasoning — which is a narrower and more useful
claim than either arm alone can support.

**What it is NOT: a replacement for `bare`.** Running the harness *instead of* the registered
single-pass arm would silently swap the question from *what does the substrate add over a
stock model* to *what does it add over an agent harness*. **If `bare` does not run, the
registered comparison did not happen**, and no `bare_agent` number may stand in for it.

**Four binding constraints, and the first two are not stylistic.**

1. **No retrieval. Network access denied.** §4 puts retrieval out of scope explicitly: *"The
   corpus is hand-transcribed and closed. Searching for sources is a different capability and
   would confound corpus quality with reconstruction quality."* An agent that can search the
   web can find Valtin's paper and read past the transcription — which is the confound §4
   excluded, arriving through the arm instead of through the corpus.
2. **The same documents as `bare`, never the evidence records.** `bare_agent` gets the
   transcribed excerpts, citations and dates. It must **not** be given `corpus_*.json`, whose
   `evidence` block encodes shared-span structure, assertion records, and — since A17 — the
   `undetermined` flag. A17 states the lapse condition in terms: *"If a bare arm is ever handed
   the evidence records rather than the documents, the suspension dimension stops measuring
   anything."* That applies to this arm first, because it is the one with a filesystem.
3. **The harness configuration is part of the arm and must be captured.** Model id pinned as
   the house does it (`AnthropicAPIJSONProvider` pins `claude-opus-5`); system prompt, tool
   list and any `CLAUDE.md` in reach recorded verbatim into the artifact and hashed into
   `freeze.json`. An unpinned harness would be the loosest thing in a design that freezes the
   mechanism, the standards, the pre-registration and the fixtures.
4. **Scoring does not change.** FR-4 requires one scoring function applied without branching on
   arm, already pinned by `test_score_does_not_branch_on_arm`. A third arm is a third
   `Reconstruction`, nothing more. `priced_prediction` stays a **string**; an agent's cost
   accounting differs in kind from a single call's and must not be coerced into a number that
   enters an average.

**P11, registered here and therefore later than P1–P10, but before any arm has run.**

> On slot D, `bare_agent` draws **fewer** spurious edges than `bare` and **more than zero**.

The first half says the harness helps; the second says it does not close the gap. Both halves
can fail independently and each failure is informative: zero spurious edges would mean the
substrate's restraint contribution is reproducible with a filesystem and a loop, which is a
result this project should want to know and would not enjoy; no improvement over `bare` would
mean the harness adds nothing on the dimension it most plausibly should.

**What would withdraw this amendment.** If constraint 1 or 2 cannot be enforced in the harness
actually used — if the tool surface cannot be restricted to the transcribed documents — then
`bare_agent` is measuring retrieval and must not be run at all. Recorded now so that
discovering it later is a withdrawal rather than a footnote.

### A20 — 2026-08-14: the corpora and the provisional keys are frozen, for drift and not for record

**Decision: `corpus_{A,B,E}.json` and `key_{A,B,E}.json` enter `freeze.json`'s `files` block.**
A15 and A18 said the keys were *"deliberately NOT frozen"* because *"freezing is the commitment
step"*. That is amended here, by separating two jobs the one mechanism has been doing.

**Freezing has two meanings and this experiment has been using only one.**

- **Drift detection** — nothing changed under us between a capture and the score that reads it.
  This is a mechanical property and it is wanted *whatever* the file's status is. An unfrozen
  key can be edited between a paid run and its scoring with nothing to notice.
- **Commitment** — this is the artifact of record, and a result may be reported against it.

A15 refused the second and, having only one lever, got neither. The refusal was right and its
consequence was not: **the three least trustworthy files in the experiment were also the only
ones nothing was watching.**

**How the separation is carried.** Each provisional entry's `role` string states it outright —
frozen for drift detection, provisional under A15/A18, not an artifact of record. A digest is
evidence a file did not change; it has never been evidence that a file is right, and no reader
may take one for the other.

**The corpora are frozen too, and that is the more important half.** A key is meaningless
except against a specific corpus. Slots A, B and E each moved several times on 14 August — slot
E went from 3 edges to 9 on A16 alone — and a key pinned to a moving corpus pins nothing. Both
sides go in together or neither does.

**What is NOT resolved by this, and stays visible.**

- **Nine of `key_B`'s eighteen edges claim `textual` descent where the corpus records no shared
  evidence at all.** Slot B's recall is therefore substantially a measurement of key error
  rather than of any arm. Flagged, affirmed by the experimenter, frozen as-is, and repeated
  here because a freeze makes a file harder to change and easier to trust.
- **P3 remains unconfirmed.** Slot A's 1.00/1.00 is unaffected by freezing: the objection was
  never that the file might change, it was that the key agrees with the mechanism because both
  read the same documents the same way.
- `suspension_correct` is `None` on slots A and E, whose keys mark nothing undetermined, so
  **P8 is exercised on slot B alone**. That is as registered; slot E's second undetermined edge
  needs `bender&bender1982`, which is not obtained.

**What lifting this looks like.** Hand-authored keys replace these files, the `role` strings
lose the provisional clause, and A15's suspension of FR-2 ends. The digests change and the
freeze log records it, which is the same path any re-freeze takes — the point of freezing them
now is that the change will be *visible* rather than silent.

### A21 — 2026-08-14: suspension is measured as transport, not as judgement

**Recorded as a limitation, not fixed here.** `descent.py`'s module docstring describes a
suspension mechanism that does not exist, and A17 built a weaker one without saying so. This
amendment states the gap so that no result can be read as more than it is.

**What the docstring promises.**

> Where the record cannot settle an edge, the contested edge is materialised as a
> claim-instance in its own right and `underdetermination.derive` decides. Writing a hedging
> rule in this module would reinvent experiment 5 and — worse — would make suspension **a
> string this module chose rather than a state the store holds, which is exactly what P8's
> falsifier turns on.**

**What exists.** `undetermined_from_records` reads an `undetermined: true` flag off a corpus
assertion and hands the pairs to `reconstruct`, which marks them. `grep -rn underdetermination
src/manyu/descent.py` returns **five matches, all of them prose**. The module is never
imported and `derive` is never called.

So suspension is currently closer to *a value the fixture chose* than to *a state the store
holds* — which is the condition the docstring names as fatal to P8's falsifier. The warning
describes what got built.

**What this does and does not invalidate.**

- The A17 work stands and was necessary. Before it, `suspension_correct` returned `False` on
  every slot regardless of any key — a constant in the shape of a refutation. That is fixed,
  and the dimension now discriminates: `False` against the provisional key, `True` against the
  same key with its two wrong rows corrected.
- What is measured is **transport fidelity**: the corpus records that O'Raifeartaigh & Mitton
  raised a descent and declined to settle it, and the pipeline carries that to the score
  without flattening it. That is a real property and a bare model may well fail it.
- What is **not** measured is judgement: whether the substrate can recognise an undetermined
  edge from evidence it holds, with nothing in the fixture saying so.

**Binding on reporting.** If stages 1–3 run before this is closed, `results.md` must say that
**P8 was tested as transport rather than as judgement**, and no `suspension_correct` figure may
be described as the substrate holding an edge open on its own account. A between-arm difference
on this dimension remains reportable — carrying a hedge faithfully is a difference worth
having — but it must be named as what it is.

**The route that would close it, specified now so the choice is not made later under pressure.**
Materialise the two verdicts as **rival claims about the same edge**: Livio's *"he never
actually called it the biggest blunder"* and O'Raifeartaigh & Mitton's *"very likely that he
labelled the term his biggest blunder"* are claim-instances that contradict each other about
`gamow1956`'s ancestry. `underdetermination.derive` finds rival sets over stored candidates —
`evidence_overlap` between those two is high and neither dominates. Suspension would then be
**derived from two documents disagreeing**, which is the situation slot B was chosen for, and
no corpus flag would decide it.

**Why the flag is not simply removed.** It is faithful to something real: a document *can*
raise a descent and decline it, and that fact belongs in the record whatever the mechanism
later does with it. The two routes are complementary — the flag records what a source said,
`derive` would decide what the corpus establishes. Keeping both, and being clear which one a
number came from, is the honest arrangement.
