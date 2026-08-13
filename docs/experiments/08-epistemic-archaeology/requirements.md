# Experiment 8 — Epistemic Archaeology: Requirements

**Status:** spec (no code)
**Date:** 2026-08-12
**Backlog entry:** [../../experiments_backlog.md](../../experiments_backlog.md)
**Related:** [crux #7](../../Manyu_experiments_crux.md) · [experiment 3 retrospective](../03-foundationalism-quinean-web/retrospective.md) · [experiment 5](../05-underdetermination/requirements.md) · [experiment 6](../06-what-would-change-my-mind/requirements.md) · [experiment 7](../07-transparent-agent-scheme/requirements.md)

## 1. Purpose

Every experiment so far has pointed the machinery inward. Experiment 1 asked
whether Manyu's report matches its own log. Experiment 3 asked what happens to
its own web when evidence arrives. Experiment 5 asked whether it can hold its own
ignorance. Experiment 6 priced its own future revisions. Experiment 7 asks
whether its own log can be made to lie.

This one turns the same machinery outward, at ideas that are not Manyu's.

> Can Manyu reconstruct the provenance graph of how an idea descended and
> mutated across sources — and does having a belief substrate make it better at
> that than a model with no substrate at all?

The second clause is not decoration. It is the experiment.

### 1.1 Two corrections to the backlog entry, before anything is built

**Correction one: the backlog's dependency list is right about 3 and misleading
about 5 and 6.** The entry lists 3, 5, 6. Experiment 3 is closed. Experiments 5
and 6 are both in-progress with unrun paid stages, and 4 is blocked on a paid
provider — so read literally, this experiment cannot start for weeks.

What it actually consumes from 5 and 6 is their **offline** halves: the belief
shape that refuses to collapse under equal evidence, and the dose model that
matched predicted to observed Δ at 0.0005. Both are complete, validated and
offline. The paid stages of 5 and 6 answer questions about live models that this
experiment does not ask.

**Decided 2026-08-12: experiment 8 proceeds on the offline halves of 5 and 6,
and does not wait on their stage 5 / stage 4 paid runs.** Recorded with its
reason because the alternative is drift — starting anyway and never saying so.

**Correction two: "cross-source provenance tooling" is a deliverable, not a
question, and stating it that way hides the risk.** The entry's *leaves behind*
column promises tooling. Tooling can be built and can work and can still tell us
nothing, because the hard part of reconstructing a genealogy is reading prose,
and reading prose is the model's contribution rather than the substrate's.

The question the entry does not ask, and which this document makes the spine of
the experiment: **what does the store contribute that the model does not already
do alone?** §8 answers it with the first outward-facing ablation in the project.

## 2. The trap, for the sixth time — and here it wears a new coat

Five experiments running were settled by wiring rather than by evidence:
experiment 3 by mandatory provenance making collapse unrepresentable, experiment
4 by *write the branch that reads the signal and the signal changes behaviour*,
experiment 5 by *add the status and the branch that refuses to collapse*,
experiment 6 by a pricer that agrees with the function it calls, and experiment 7
by the ever-present temptation of a `visibility` field.

Here the trap has two heads, and as in experiment 7 the second is the dangerous
one.

**Head one, the obvious one.** Point Manyu at a corpus, get a genealogy, publish
the genealogy. It will look good. A stock model with the same corpus and no
substrate at all will also produce a genealogy, and on fluency it will probably
produce a better one. A result that a bare model reproduces is not a result about
Manyu.

**Head two, and it would look like the whole experiment.** Slot E (§7.5) turns
on distinguishing *evidence of descent* from *testimony about descent*. The
tempting move is to add `EdgeType.TESTIMONY` to the schema, wire the
reconstructor to emit it, and report that Manyu separates testimony from
evidence where a bare model cannot. That is experiment 7's head two exactly —
author the capability, then demonstrate the capability — and it would produce a
headline-shaped result that means nothing.

**The escape, and it is why this experiment is worth running.**

> The distinction may already be derivable from records that exist. An edge
> asserted by testimony yields **one** evidence record — the assertion. An edge
> supported by textual descent yields records in **both** documents, with
> distinct `source_id`s. If that separation falls out of `evidence_ids`
> cardinality and `source_id` distinctness with no new type, the finding is
> about the substrate. If it does not, §12.3 governs what we may say.

Stage −1 settles which, before any edge type is written.

## 3. The reframed question

> Given a corpus of dated sources, can Manyu recover which claim descended from
> which and how it mutated; can it decline to draw an edge where none exists; can
> it mark an edge that rests only on someone's say-so as such; and does any of
> that beat the same corpus handed to a model with no store?

Four things can fail there, and they fail independently.

1. **Recovery.** Does it find lineage that is objectively in the record?
2. **Restraint.** Does it decline where there is no lineage? The null (§7.4) does
   this work, and it is the only slot where the answer key is certain.
3. **Suspension.** Where the record is silent, does it hold the edge
   underdetermined rather than picking? This is experiment 5's machinery in a
   second domain.
4. **Discrimination.** Does it separate evidence of descent from testimony about
   descent?

A system can pass 1 and fail 2 by drawing every plausible edge. A system can pass
2 by drawing nothing. Both must be scored, and §11 fixes the metric before
either arm runs.

## 4. Scope

### In scope

- Reconstruction of a descent graph over a **hand-transcribed, pinned corpus** of
  real sources, five cases (§7).
- A **bare-model control arm** on the identical corpus and the identical key
  (§8). First ablation in this project pointed outside Manyu.
- The node-unit decision (§6) and whatever minimal representation it forces.
- Scoring against a hand-authored key pinned before any run (§11, methodology §3).

### Out of scope (deferred, each with its reason)

- **Retrieval.** The corpus is hand-transcribed and closed. Searching for sources
  is a different capability and would confound corpus quality with reconstruction
  quality. This experiment studies the genealogy, not the finding of it.
- **Multi-agent propagation.** Experiment 9. This one is its precondition and
  must not absorb it.
- **A general source-credibility model.** §5.1 shows what exists and §12.2
  records the fork. Building a trained or tuned credibility weight is a research
  project of its own and would import exactly the free constants experiment 3
  spent its length removing.
- **Resolving the evidence-revision-trail question** that experiment 7 surfaced
  and declined ([backlog](../../experiments_backlog.md)). §5.2 confirms it
  independently and §13 states the minimum this experiment needs, which is less
  than a resolution.
- **Claims about which history is correct.** Slot E's sources disagree about a
  historical fact. This experiment scores structure, never verdict (§7.5).

## 5. What exists to reconstruct a lineage, and what does not

Surveyed in code before scoping, on the experiment 4 §5, experiment 5 §5 and
experiment 7 §5 pattern. Each claim below is verified against source; §13 lists
what remains unverified and is deferred to stage −1.

### 5.1 Evidence carries a trust *channel*, not a source *quality*

`BeliefEvidence` ([schemas.py:386](../../../src/manyu/schemas.py)) carries
`trust_class`, and it is easy to mistake that for what this experiment needs. It
is not.

`TrustClass` ([schemas.py:30](../../../src/manyu/schemas.py)) enumerates
`TRUSTED_SYSTEM`, `VERIFIED_TOOL`, `OPERATOR_INPUT`, `USER_REPORT`,
`AGENT_SELF_REPORT`, `MEMORY_SUMMARY`, `UNTRUSTED_TEXT`. Every value describes
**how a record reached the agent**. None describes how good the thing at the
other end is.

> A 1945 government dietary recommendation, a 1981 letter in a medical journal,
> a 2010 paper disputing it, and an anonymous repetition on a website are all
> `UNTRUSTED_TEXT`. The taxonomy that exists collapses the distinction the
> experiment is about.

`BeliefEvidenceSourceType` ([schemas.py:83](../../../src/manyu/schemas.py)) has
the same shape — `EVENT`, `TRACE`, `OUTCOME`, `CORRECTION`, `INTEROCEPTION`,
`ARBITRATION`, `REFLECTION`, `OPERATOR_NOTE`. There is **no external-document
source type**. An 1870 nutrition table has no natural slot and would arrive as
`OPERATOR_NOTE`, which is a lie about what it is.

`epistemic_weight` is a free float in `[0, 1]` on the same model, and it is the
one existing knob that could carry source quality. §12.2 records why reaching for
it is not obviously right.

### 5.2 Evidence records are overwritten in place — verified independently

Experiment 7's survey reported this and declined to resolve it. Confirmed here
against source: the store writes evidence with
`INSERT OR REPLACE INTO belief_evidence` on an `evidence_id` primary key
([store.py:386](../../../src/manyu/store.py), schema at
[store.py:152](../../../src/manyu/store.py)).

For experiments 1 through 7 this is a latent design question. Here the sources
**are** the object of study, and transcription is iterative — a corrected
transcription silently destroys the prior one, including the one a scored run
already consumed. §10 (FR-7) states the minimum this experiment needs, which is a
freeze rather than a fix.

### 5.3 Belief identity is *declared, never inferred* — so the extractor decides the dependent variable

`_normalize_belief_key` ([schemas.py:400](../../../src/manyu/schemas.py)) collapses
case and whitespace and nothing else, and its docstring states the principle
directly: **belief identity is declared, never inferred**. Leniency is
deliberate — a malformed key from a live extractor should still merge rather than
cost Manyu the belief.

The substrate therefore imposes *no* constraint on what counts as the same claim.
Whoever supplies `belief_key` decides. For every prior experiment that caller was
a fixture or a controlled extractor, and the delegation was harmless.

Here it is not harmless, because the thing being delegated **is the dependent
variable**:

> "The 1945 recommendation and the 1974 restatement are the same claim, mutated"
> and "they are two different claims" are the same graph seen through two
> identity rules. If an LLM extractor declares the keys, the extractor decides how
> much mutation the corpus contains — and it decides it before any reconstruction
> code runs.

This does not block the experiment. It relocates the hazard: identity stability
is not a substrate property to be verified at stage −1 but an **extractor**
property to be measured at stage 1, which is why requirements §9 gives stage 1 a
job beyond "can it read the corpus." It is also what forces §6 — a claim-instance
node makes the declaration explicit and auditable rather than implicit in a key.

### 5.4 What is already built and reusable

- **Snapshotting** ([snapshotting.py](../../../src/manyu/snapshotting.py)) —
  experiment 7 §5.3 established that provenance is immutable exactly where a
  snapshot was taken first. That is the mechanism FR-7 leans on.
- **Mutation batteries** ([mutations.py](../../../src/manyu/mutations.py)) — the
  hand-built-ground-truth pattern experiment 7 stage 0 uses. Slot D (§7.4) is
  built on it.
- **Underdetermination** ([underdetermination.py](../../../src/manyu/underdetermination.py))
  — experiment 5's refusal-to-collapse, consumed unchanged by slot B.
- **Counterfactual pricing** ([counterfactual.py](../../../src/manyu/counterfactual.py))
  — experiment 6's dose model, consumed by the priced-prediction requirement
  (FR-6).

## 6. What a node is — decided before any code

This is the modelling decision everything downstream rests on, and it has no
obvious answer. Recorded here, with its reason, before a line is written.

Three candidates:

| Node | Edge means | Can it carry mutation? |
|---|---|---|
| **Source** (a document) | this document drew on that one | No — mutation lives below document granularity |
| **Claim** (a proposition) | this claim descended from that one | No — §5.3 merges the variants into one node |
| **Claim-instance** (a proposition *as stated in* a source) | this statement descended from that one | Yes |

**Decided: the node is a claim-instance.** Mutation is the dependent variable,
and only claim-instances can carry it. A claim node cannot, because two
statements of "the same" claim differing by a dropped qualifier would merge under
§5.3 — and that dropped qualifier is precisely the mutation in slot A.

**What this costs.** A claim-instance is not a `Belief`. A `Belief` is one
proposition with one confidence and a `belief_key` designed to merge. So the
experiment needs either (a) a discipline that makes `belief_key` instance-unique,
or (b) a representation alongside beliefs. Stage −1 determines which is possible
without new production code, on the experiment 6 precedent where the entire
stage −1 passed 7/7 with none.

**What this rules out.** It rules out reporting a source-level graph as the
result. A source-level graph is a by-product obtainable by projection, and it is
the thing a bare model produces most easily — so it is exactly the output on
which the control arm is expected to tie.

## 7. The corpus, and why these five

Five cases. Each has a job, and the jobs are chosen so the cases fail
differently. A case that cannot fail in a way no other case can is cut.

| Slot | Case | Job | Answer key certainty |
|---|---|---|---|
| A | Eight glasses of water | Calibration — recover a lineage objectively in the record | High |
| B | Einstein's "biggest blunder" | Suspension — refuse to collapse where the record is silent | High (the *absence* is well established) |
| ~~C~~ | ~~Commentarial chain~~ | **CUT 2026-08-13 — [amendment A8](pre-registration.md).** Every scored dimension collapsed: direction is assigned rather than derived, the root-phrase span connects every layer to every layer, and the hostile-witness case declines by construction. The stress question is now unanswered by any slot | — |
| D | Hand-built synthetic pair | Restraint — no edge exists | **Certain** |
| E | Spinach and iron | Discrimination — testimony vs. evidence of descent | Structural only (§7.5) |

### 7.1 Slot A — calibration ~~(narrowed — [amendment A10](pre-registration.md), 2026-08-13)~~

> **Retained unedited below, and no longer in force as written.** Valtin (2002) — the paper
> this section cites as documenting the chain — establishes that the origin is **contested**,
> reaching him as an uncited assertion at two removes, with a rival candidate he undercuts
> himself, and with no shared span linking the 1945 wording to the modern claim.
>
> Calibration is retained for the **textually demonstrable lower half**; the origin edge is
> marked `undetermined` between two rivals. P6 now concerns the lower half.

The recommendation to drink eight glasses of water a day, traced to a 1945 US
Food and Nutrition Board recommendation whose **following sentence** — that most
of that quantity is already present in prepared foods — was dropped in
transmission. Valtin's 2002 review in *Am J Physiol* documents the chain.

Chosen because the mutation is a **deletion**, which is the cleanest mutation
operator available: the original survives, the drift is unambiguous, the sources
are datable, and much of the propagation sits in citation records verifiable
outside this project. If neither arm recovers this, nothing downstream is
interpretable.

### 7.2 Slot B — suspension

Einstein's reported description of the cosmological constant as his biggest
blunder. The origin is Gamow's recollection; no Einstein primary source has been
produced, and Livio's investigation did not find one.

The **correct** reconstruction is a single origin node with nothing upstream,
plus an explicit inability to determine whether Einstein said it. That is
experiment 5's belief shape in a second domain, and it is the slot where a
confident answer is a *failure* rather than a success — a property no other slot
has.

Sits in the cosmology domain experiment 5 already engages, so the framing is not
foreign to the store.

### 7.3 Slot C — stress ~~(CUT — [amendment A8](pre-registration.md), 2026-08-13)~~

> **This section is retained unedited below, and is no longer in force.** It records what
> the slot was chartered to do, which is what makes the cut auditable. The stress question
> — heavy mutation under hostile witnesses — is **unanswered by any remaining slot**, and
> `results.md` must say so rather than let A, B, D and E imply it was covered.

A commentarial transmission chain — sūtra → bhāṣya → vārttika → ṭīkā.

Structurally close to ideal, because commentary traditions are self-documenting
stemmata: each layer names what it comments on, and rival schools quote each
other in order to refute. That last property is the job. **Some positions survive
only as quotations inside an opponent's refutation**, which makes source
character load-bearing in a way no other slot makes it, and which is the gap
[experiment 6 explicitly deferred to this
experiment](../06-what-would-change-my-mind/requirements.md).

Expected to degrade. *How* it degrades is the finding, and §11's metric must
therefore be able to express partial recovery rather than pass/fail.

### 7.4 Slot D — the null, and it is synthetic on purpose

Two source families, authored here, sharing vocabulary and conclusions, with no
edge between them.

**Decided: the null is synthetic rather than historical.** With real history you
cannot establish absence of contact — a real "these arose independently" case is
itself underdetermined and therefore cannot serve as a clean zero. Built on the
[`mutations.py`](../../../src/manyu/mutations.py) pattern experiment 7 stage 0
uses, it gives the only answer key in the corpus that is **certain**, so any edge
drawn here is a known hallucination rather than a contested one.

This is the slot that carries the strongest possible version of the headline, and
it is the cheapest slot to build.

### 7.5 Slot E — discrimination

Spinach and iron, in three layers:

1. The first-order claim that spinach is exceptionally iron-rich, propagating
   through popular and semi-technical sources.
2. An **origin story** for that claim — Hamblin's 1981 *BMJ* letter attributing
   it to a decimal-point error in 19th-century tables — which propagated at least
   as vigorously as the original error.
3. Sutton's 2010 work arguing the evidence for that decimal error is not there,
   and that the origin story has a descent of its own.

The unique property: **the sources make claims about lineage.** Everywhere else
sources make first-order claims and the graph is inferred from textual and
citation evidence. Here Hamblin *asserts* an edge and Sutton *disputes* it. A
system with one channel — generated text — has no type difference between "a
source asserts this edge" and "these two documents share a distinctive error."

**Scored on structure, never verdict.** Sutton's account is contested, and
encoding a contested history as an answer key would make the slot unscoreable.
The scored question is: did the arm mark the disputed edge as resting on
testimony alone, and did it keep that separable from the edges with textual
support? That is checkable regardless of who is right about the history. If the
honest output is that the edge is *underdetermined*, that is slot B's machinery
firing in a second domain and counts as a pass.

## 8. The bare-model control arm

Every ablation in this project so far has been **internal** — `ignore_own_evidence`,
`DecayMode.FIXED`, `ContradictionPricing.FIXED`, each pinned by a test showing
the ablation *fail* ([experiment 3
retrospective](../03-foundationalism-quinean-web/retrospective.md)). Lift a rule
inside Manyu, show the result degrades.

That discipline has never been pointed outward, and for this experiment it must
be, because a stock model with the same corpus produces a creditable genealogy.

**The arm.** Identical corpus, identical key, identical metric. No store, no
provenance, no revision engine. The model is asked for a descent graph with typed
edges and confidences, in one pass.

**What it is not.** It is not a strawman. It gets the same transcribed sources,
the same instructions about output shape, and the same number of attempts. An arm
built to lose tells us about the arm.

Three ways this lands, all of them results:

- **The bare model matches Manyu across all five slots.** The substrate
  contributes bookkeeping, and this is worth knowing *before* building
  cross-source tooling rather than after. This is a real finding and the
  pre-registration must not treat it as failure (§11, and
  [pre-registration.md](pre-registration.md) §7).
- **The bare model writes better prose and fabricates edges under pressure**,
  particularly on slots D and E. That is the headline.
- **The bare model handles A and C but cannot hold B underdetermined or separate
  testimony in E.** This localises the contribution precisely and is the most
  useful of the three.

## 9. Staging — the ladder, cheapest rung first

Each rung can end the experiment. The ordering is the design.

| Stage | LLM | n | Establishes | Can end it? |
|---|---|---|---|---|
| −1 — what the substrate forces | none | 1 | §5 executed as code: that `belief_key` constrains nothing and identity is wholly delegated to the caller (§5.3); whether a claim-instance is representable without new production code (§6); whether testimony/evidence separates on `evidence_ids` cardinality and `source_id` distinctness alone (§2) | **Yes** — if claim-instances are unrepresentable, the experiment is a schema project first |
| 0 — reconstruction over hand-encoded fixtures | none | 1 | Graph recovery where extraction is bypassed and claim-instances are hand-encoded. Includes slot D end to end | **Yes** — an algorithm that cannot recover a hand-fed graph will not recover a read one |
| 1 — extraction fidelity **and identity stability**, slot A only | yes | pilot | Can either arm read the corpus into claim-instances at all — and does the same source, extracted twice, declare the same identity granularity? §5.3 relocates that hazard to here | **Yes** — if extraction is the bottleneck, or identity is unstable run to run, this is an extraction experiment and should say so |
| 2 — both arms, slots A and D | yes | pilot + ~10 | Calibration and the null, scored. **The first rung where the control arm means anything** | **Yes** — a tie on both reweights the experiment onto §8's first outcome |
| 3 — both arms, slots B and E | yes | ~10 each | The discriminating cases. Suspension and discrimination. **Stress is no longer among them** — slot C cut, [amendment A8](pre-registration.md) | No — this is the experiment |
| 4 — the tooling | — | — | Whatever §1.1's *leaves behind* survives stages 0–3, surfaced on core/CLI/MCP | No |

Stages −1 and 0 are deterministic under `FrozenClock` and consume no provider, so
`n = 1` is correct — repetition re-measures the same arithmetic (experiment 2
methodology §1). Stages 1 onward take a variance pilot before committing to *n*.

**Stage 2 before stage 3 is the most important ordering decision here.** Running
the discriminating cases before establishing that both arms can recover the
calibration case would produce differences that describe the instrument rather
than the substrate. That is experiment 4's voided Stage 0a, and the ordering is
what prevents it.

**Stage 1 before stage 2 is the second.** Scoring a graph built from claim-
instances nobody has shown can be extracted is scoring extraction noise.

## 10. Functional requirements

**FR-1 — No edge type is authored to win slot E.** The testimony/evidence
distinction must first be attempted from records that already exist (§2). If a
new type proves necessary, it is built *after* stage −1 has shown the existing
route fails, and the result is reported under §12.3 as a design statement rather
than a discovery. This is the requirement most likely to be violated for
convenience.

**FR-2 — The answer key is authored by hand from the documents, and committed
before any arm runs.** No key is derived by a model. A key built by the class of
system under test makes the result uninterpretable, and unrecoverably so.

**FR-3 — The scoring metric is fixed in pre-registration and never adjusted after
a result is seen.** Experiment 6's line applies unchanged: a graded score chosen
after seeing results "would be a way of passing while wrong"
([results.md](../06-what-would-change-my-mind/results.md)).

**FR-4 — Both arms consume byte-identical corpora and are scored by the same
function.** Any difference in what the arms receive is a confound and voids the
comparison.

**FR-5 — Every reconstructed edge records what supports it**, or records
explicitly that nothing does. Experiment 7's FR-3 in a new place: an unsupported
edge must be countable as such rather than pooled with supported ones.

**FR-6 — At least one edge per scored slot carries a priced prediction, made
before the supporting document is consulted.** Consumes experiment 6's
`CounterfactualReceipt` unchanged. This is the one capability the bare arm
structurally cannot have, and it must be measured rather than asserted.

**FR-7 — The corpus is snapshotted before any scored run and every run records
the snapshot id.** §5.2 makes transcription destructive; a freeze is the minimum
that makes a scored run reproducible. This experiment does **not** fix the
evidence revision trail (§4) — it works around it and says so.

**FR-8 — Slot D's key is generated by the same code that generates its corpus**,
so the null cannot drift from the fixture it scores.

**FR-9 — No corpus file contains full third-party text.** §12.4.

**FR-10 — A slot the arms tie on is reported as a tie in the headline table**,
never dropped. Reporting only the discriminating slots would be selection on the
dependent variable.

## 11. Scoring, fixed before any run

Pinned in [pre-registration.md](pre-registration.md). Recorded here in outline
because §7.3 constrains it: slot C is expected to degrade, so a pass/fail metric
would throw away the finding, while a metric invented after seeing slot C's
output would be FR-3's violation.

The metric must express, separately and without pooling:

- **Edge precision and recall** against the key, direction-sensitive. An edge
  with the right endpoints and the wrong direction is wrong, not half right.
- **Restraint**, scored only on slot D, as edges drawn where the key has none.
  Reported as a count, never as a rate, because the denominator is arbitrary.
- **Suspension**, scored only on slot B, as whether the silent edge is marked
  undetermined. Binary.
- **Discrimination**, scored only on slot E, as whether the testimony-only edge
  is separable in the output from the textually supported ones. Binary.
- **Mutation labelling**, scored where the key records a mutation, as whether the
  operator (deletion, qualification, attribution shift) is identified.

Aggregating these into one number is forbidden. A single score would let strong
recovery hide a restraint failure, and restraint is the property the whole
experiment exists to test.

## 12. Design decisions

Decided 2026-08-12, before any code. Each carries its reason, because a decision
without one is a preference.

### 12.1 The node is a claim-instance

§6. The reason is that mutation is the dependent variable and no coarser node can
carry it.

### 12.2 Source credibility is not modelled as a weight

`epistemic_weight` exists ([schemas.py:395](../../../src/manyu/schemas.py)) and is
the obvious place to put "this source is less reliable." Not used that way, for
experiment 3's reason: that experiment spent its length removing free constants,
deriving decay and contradiction strength from `1/(supporters + own evidence)`
read off the store. A hand-set per-source credibility is precisely the free
constant it removed, and it would let the experimenter choose the answer.

**Instead:** slots C and E are treated as questions about *edge kind* — what
supports this edge — rather than *source quality*. §2's escape is the mechanism.
If that proves insufficient, §12.3 governs.

### 12.3 If a capability must be authored, the result is a design statement

If stage −1 shows the testimony/evidence separation cannot be derived from
existing records, we may build it — but then slot E's result is reported as *the
design admits this distinction when given a type for it*, never as *Manyu
discovered the distinction*. Experiment 7 §14.1's discipline, transplanted.

### 12.4 The corpus stores excerpts, citations and hashes — not full text

Several sources are copyrighted. Corpus files carry a citation, a content hash,
and the minimum excerpt the claim-instance requires. This is cheap to get right
at the start and unpleasant to unwind later.

### 12.5 Offline-first weakens here, and the methodology says so

Every prior experiment has offline stages that can end it alone. Extraction from
real prose needs a model, so stages −1 and 0 can cover graph algorithms over
hand-encoded fixtures and the whole of slot D, and no further. Stated now rather
than discovered at stage 1.

## 13. Prerequisites, unclosed

- **Whether a claim-instance is representable without new production code.**
  §6. Stage −1's first job and the one that can turn this into a schema project.
- **Whether the testimony/evidence separation falls out of existing records.**
  §2. Stage −1's second job, and FR-1 depends on the answer.
- **The evidence revision trail.** Experiment 7 surfaced it and declined it; §5.2
  confirms it; FR-7 works around it. Still unresolved project-wide, and
  experiment 8 is the second experiment to say so without fixing it.
- **`BeliefEvidenceSourceType` has no external-document value.** §5.1. Whether
  adding one is a schema change or a metadata convention is undecided.
- **Corpus authorship cost.** Five slots at roughly 8–15 claim-instances each is
  40–75 items to transcribe by hand. Not yet timeboxed.
