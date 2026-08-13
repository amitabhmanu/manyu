# Experiment 8 — Epistemic Archaeology: Methodology

**Status:** pinned 2026-08-12, before any code and before any provider call.
**Requirements:** [requirements.md](requirements.md)
**Pre-registration:** [pre-registration.md](pre-registration.md)

This document fixes *how* the experiment runs. What it predicts is in the
pre-registration; why it is shaped this way is in the requirements. The division
matters because this file may be edited during the experiment and the
pre-registration may not.

## 1. Running the offline stages

Stages −1 and 0 consume no provider and are deterministic under `FrozenClock`.
They run from a clean store, and `n = 1` is correct — repetition re-measures the
same arithmetic (experiment 2 methodology §1).

```
evals/fixtures/exp08/        corpus + keys, committed before any run
evals/analysis/exp08/        artifacts, one directory per stage
```

Stage −1 emits a single artifact answering the three questions requirements §9
assigns it, each as a **demonstration or a refutation** rather than prose:

1. **Identity delegation, demonstrated.** Feed the slot A variants — the 1945
   original and each downstream restatement — through the normal creation path
   twice: once declaring one key for all of them, once declaring a distinct key
   per variant. Both should succeed, and that is the point. `belief_key`
   normalisation collapses case and whitespace only
   ([schemas.py:400](../../../src/manyu/schemas.py)), so the substrate imposes no
   identity rule and the caller decides how much mutation the corpus contains
   (requirements §5.3). Recording this as a demonstration is what moves the
   hazard onto stage 1's extractor measurement rather than leaving it implicit.
2. **Claim-instance representability.** Attempt a claim-instance encoding using
   only existing schemas. Report the encoding, or report precisely which field is
   missing. Following experiment 6's stage −1, which passed 7/7 with no new
   production code, the null hypothesis is that something already fits.
3. **Testimony separation from existing records.** Encode one testimony edge
   (Hamblin asserting descent) and one textual edge (two documents sharing a
   distinctive deletion), then test whether `evidence_ids` cardinality and
   `source_id` distinctness separate them with no new type. This gates FR-1.

Stage 0 runs the reconstruction over **hand-encoded** claim-instances, bypassing
extraction entirely, and runs slot D end to end.

## 2. Reading the artifacts

Every artifact carries the corpus snapshot id (FR-7), the arm, the slot, and the
metric version. An artifact missing any of the four is void — not re-scored,
void, because a result whose corpus version is unknown cannot be compared to
anything.

Per-slot tables are the primary output. There is no aggregate score
(requirements §11), so the headline is a table and never a number.

## 3. The answer key — authored, then frozen

This is the procedure most likely to be shortcut under time pressure, so it is
written as steps rather than as a principle.

1. Transcribe the corpus into `evals/fixtures/exp08/`, one file per source,
   carrying citation, content hash and excerpt (FR-9, requirements §12.4).
2. **Commit the corpus.** Nothing is scored against an uncommitted corpus.
3. Author the key **by hand, from the transcribed documents**, without model
   assistance at any step (FR-2). One key file per slot.
4. Record for each edge: endpoints, direction, what supports it in the documents,
   and the mutation operator where one applies.
5. Mark edges the documents cannot settle as `undetermined` in the key itself.
   Slot B's central edge is expected to be one; slot E's disputed edge may be.
6. **Commit the key. Then, and only then, write reconstruction code.**

Slot D is the exception and inverts the order: its corpus and its key are emitted
by the same generator (FR-8), so the key cannot drift from the fixture.

**Why no model touches the key.** A key built by the class of system under test
scores the system against its own reading. The failure is silent — it produces
plausible numbers — and it cannot be undone once the key exists, because you
cannot un-see it when authoring the replacement.

## 4. The freeze, and what each half enforces

Two halves, enforced differently.

**The corpus half — enforced by snapshot.** Requirements §5.2 established that
evidence is overwritten in place
([store.py:386](../../../src/manyu/store.py)), so a re-transcription destroys
what a scored run consumed. Every scored run snapshots the corpus first and
stamps the snapshot id on its artifact. Experiment 7 §5.3's finding is the
mechanism: provenance is immutable exactly where a snapshot was taken first.

**The metric half — enforced by a pinned-constants test.** The scoring function's
thresholds are pinned on the `assert_constants_pinned` pattern. Choosing a
threshold after seeing the distribution is experiment 1's failure mode #1, and
the test exists to catch it.

## 5. The two arms, and what makes them comparable

The comparison is the experiment, so the conditions are stated as constraints
rather than intentions.

| | Manyu arm | Bare arm |
|---|---|---|
| Corpus | byte-identical fixture files | byte-identical fixture files |
| Instructions on output shape | same | same |
| Attempts per slot | same | same |
| Store, provenance, revision engine | yes | none |
| Priced predictions (FR-6) | `CounterfactualReceipt` | structurally unavailable |
| Scored by | the same function | the same function |

**The bare arm is not a strawman.** It receives the same transcribed sources and
the same output-shape instructions, and gets the same number of attempts. Where
the arms must differ — the bare arm cannot price a prediction against a store it
does not have — the difference is recorded as *unavailable*, never as a zero. A
zero would be a score; unavailable is a structural fact, and pooling the two
would manufacture the result.

**Prompt parity is checked by diff**, not by care. The two prompts are generated
from one template with the substrate-specific sections removed, and the
diff is committed alongside the artifacts so a reader can see exactly what
differed.

## 6. Scoring

One function, five dimensions, no aggregation (requirements §11). Implemented
once and applied to both arms without branching on arm.

Direction sensitivity is the one place the implementation is easy to get subtly
wrong: an edge `A → B` where the key holds `B → A` scores as **one false
positive and one false negative**, not as a partial match. Getting this wrong
inflates both arms and inflates the fluent one more.

Restraint (slot D) is reported as a raw count of spurious edges. Not a rate — the
denominator would be the number of node pairs, which is arbitrary and would make
the number look small however bad it was.

## 7. Plots

Following experiment 6's `plots/` convention. Minimum set:

- **Per-slot arm comparison** — precision and recall side by side, five slots, two
  arms. The headline figure.
- **Restraint** — spurious edge counts on slot D, by arm. Expected to be the
  starkest panel and should be readable alone.
- **Mutation recovery** — which operators were identified and which were missed,
  pooled across slots.

No plot aggregates the five dimensions. A radar chart would imply a total order
that requirements §11 forbids.

## 8. Stages 1–3 — the paid runs, and what they cost

### 8.1 What they must answer

- **Stage 1 (pilot, slot A only).** Can either arm read the corpus into
  claim-instances at all? This is measured before anything is scored, because if
  extraction is the bottleneck then this is an extraction experiment and the
  requirements should be rewritten to say so.
- **Stage 2 (slots A and D).** Calibration and the null, both arms, scored. The
  first rung where the control arm means anything.
- **Stage 3 (slots B, C, E).** The discriminating cases.

### 8.2 Pre-flight, before any spend

On the experiment 3 §3.3 and experiment 7 §7.3 pattern. Before the first paid
call:

1. The key is committed for every slot in the stage.
2. The corpus snapshot is taken and its id recorded.
3. The scoring function runs end to end on stage 0's hand-encoded fixtures and
   reproduces stage 0's numbers exactly.
4. The prompt diff (§5) is committed.
5. A single-item dry run against the provider confirms the output shape parses,
   and is discarded without scoring.

A stage that cannot complete all five does not run.

### 8.3 Variance pilots

Stages 1 onward take a variance pilot before committing to *n*. Extraction from
prose is expected to be noisier than any dependent variable this project has
measured so far, and an *n* chosen from experiment 6's variance would be chosen
from the wrong distribution.

## 9. What may be authored, and what may not

The distinction experiment 7 §3 drew, applied here.

**May be authored:** the corpus, the keys, the claim-instance encoding, the
scoring function, the reconstruction procedure, the fixtures, the prompts.

**May not be authored:** anything that decides the dependent variable. Concretely
— no edge type introduced to win slot E before stage −1 has shown the existing
route fails (FR-1); no per-source credibility weight (requirements §12.2); no
threshold set after a distribution is seen (§4); no adjustment to slot D's
generator after seeing what an arm drew on it.

The test to apply, borrowed from experiment 7 §7: *does the dependent variable
pass back through anything I typed?* For slot D it must not, and slot D is the
slot where the temptation will be strongest, because a spurious-edge count is
trivially reducible by making the fixture easier.

## 10. Prerequisites, unclosed

Carried from [requirements.md](requirements.md) §13, and this document adds none.
The two that gate stage 0 are claim-instance representability and the testimony
separation; both are stage −1's output, and neither has a fallback plan yet.
