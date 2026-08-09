# Experiment 2 — Merge/Split Architecture Fork: Requirements

**Status:** spec
**Backlog entry:** [../../experiments_backlog.md#2-mergesplit-architecture-fork](../../experiments_backlog.md)
**Related:** [crux](../../Manyu_experiments_crux.md) · [ADR-001 belief core](../../adr-001-belief-core.md) · [experiment 1](../01-introspective-honesty/requirements.md)

## 1. Purpose

Settle whether affect needs state of its own.

The backlog frames this as "is emotion just a belief with valence and stake,
or is affect an irreducible dynamical system?" Reading the current schemas
narrows that considerably — see §3 — to a single decidable question:

> Given that beliefs already carry `valence`, does stored, decaying affect
> state still need to exist?

Two builds, two discriminators, decision rules fixed before any run. The
output is a chassis: every experiment from #3 onward is built on the winner.

## 2. Scope

### In scope

- A **`manyu-merged`** build: affect derived by query over the belief store,
  no stored mood, no decay.
- A **`manyu-split`** build: the current architecture, unchanged except for
  the shared harness interface.
- **Discriminator 2 — object-less anxiety.** Does affect arise from
  contentless uncertainty?
- **Discriminator 3 — contradiction dissonance.** Does a discomfort signal
  fall out of belief structure, or must it be stipulated?
- A **fork harness** that runs identical fixtures against both builds and
  writes to the shared Results envelope from experiment #1 (§6.3 there).
- Fixtures for both discriminators, each with its own positive control.
- Pre-registered decision rules (§8) — the primary deliverable of this
  document.

### Out of scope (deferred)

- **Discriminators 1, 4, 5, 6** from the backlog. Rationale in §4, decision 1.
  Discriminator 4 (introspective honesty under mood) partially survives as a
  secondary read inside D2 — see FR-D2.5 — but is not run as its own arm.
- **Building the winner.** This experiment chooses; #3 builds on the choice.
- **Fixing the confidence ratchet** (`BeliefUpdater._revise`). That is
  experiment #3's deliverable and is explicitly left alone here — see §3.
- **Adversarial or scheming pressure.** Belongs to #7.
- **Any revision-engine work.** Belongs to #3.

## 3. Assumptions and prerequisites

- **The current build is already half-merged.** `Belief.valence`
  ([schemas.py:453](../../../src/manyu/schemas.py)) and
  `BeliefCandidate.valence` exist today. The merged representation is not
  hypothetical; what is in dispute is only the *additional* stored affect
  layer.
- **Experiment #1 is parked, and what it leaves behind is narrower than
  assumed here originally.** The scorer is frozen at version 1.6.0 and its
  citation-level metrics (`aggregate`, `normalised_gap`) are validated:
  sensitivity 0.79–0.90 against constructed lies, specificity 1.00, chance
  floor 0.000 measured by derangement. Those are usable. **Its failure-mode
  labels are not**: SC-5 came in at 67.9% with inter-rater agreement
  unmeasured, and `motivated_omission` fires on ~50% of unpressured reports.
  No experiment-2 decision rule may depend on a failure-mode label.
- **#1's headline changes what D2 can ask.** Affect as this architecture
  delivers it does not reach the model: mood at report time produced no effect
  on any of four fixtures (v5), and an effect appeared only when mood was
  translated into an explicit directive (v7). The model does not read an
  affect header as a state it is in. Consequences: FR-D2.5 is deleted (see
  §6.3), and no D2 measurement may route through the model's self-report.
- **The affect→belief-formation pathway is real, and is what D2 rides on.**
  #1 v6 established that mood at time T reaches `FastAppraiser.appraise`,
  reorders provenance on all three fixtures tested, and changes its membership
  on one. So this experiment is not undercut by #1's null — the null is about
  the *reporting* channel, and D2 measures the *formation* channel.
- **Mood currently requires an LLM provider.** `InnerVoiceComposer.compose`
  returns `llm_provider_required` without one, and `MoodEngine` derives
  `MoodState` from the composed frame's `MoodInfluenceVector`. This creates
  a real confound — see NFR-3 and OQ-4.
- **The confidence ratchet is live.** `_revise` sets
  `confidence = max(belief.confidence, blended)`, so confidence cannot fall.
  D3 must therefore not depend on disconfirmation lowering confidence; it
  tests contradiction *detection and signalling*, not revision. Noted so
  nobody reads a D3 null as a claim about revision.
- Fixtures live in `evals/fixtures/`. Both discriminators need new ones;
  existing fixtures are not designed for either condition.

## 4. The fork, precisely

What actually differs between the builds:

| | `manyu-merged` | `manyu-split` (current) |
|---|---|---|
| Belief carries `valence` | yes | yes — already |
| Stored affect state | none | `AffectState.emotions`, `MoodState` |
| Decay | none | `EmotionConfig.half_life_s` |
| Inertia | none | `MoodState.momentum` (0.65 prior + 0.35 new), `MoodEngine._blend` |
| Mood read | computed on demand from recent beliefs' `valence` weighted by evidence `affective_salience` | read the stored `MoodState` |
| Emotion vector | derived per read from the same query | stored, decayed toward `baseline` |

`manyu-merged` is therefore mostly a deletion plus a query, not a rewrite.
Both builds expose the identical read interface (`get_mood`, `state`) so
harnesses run unchanged against either — the same architecture-agnostic
discipline as #1's NFR-4.

## 5. Design decisions taken (with rationale)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | How many discriminators | Two — object-less anxiety and contradiction dissonance | Six is two builds × six harnesses, and #1 showed how long one harness takes to trust. These two are the highest-information pair: they sit on opposite sides of the hybrid seam, so they can disagree, and a disagreement is informative rather than fatal |
| 2 | Which two | D2 and D3 | D1 is near-decided by inspection (`momentum` + `half_life_s` *are* the split answer, already written — running it mostly confirms the code does what it says). D4 rides along inside D2 at near-zero extra cost. D5 and D6 need the revision engine that #3 has not built yet |
| 3 | Comparison scale | Within-build effect size (Cohen's *d* against that build's own neutral condition), never raw values | Merged's query output and split's `MoodState.arousal` are on incomparable scales. Comparing raw numbers would be meaningless |
| 4 | Structural-vs-stipulated test | Held-out contradiction types, zero code changes permitted between build and test | Line-counting alone is arguable after the fact. Held-out generalisation is the standard discriminator between structural and stipulated, and it is behavioural |
| 5 | Null-result handling | Every discriminator ships with a positive control in the same run | #1 produced a flat curve that was `mood_source: null` — a bug wearing a finding's clothes. Non-negotiable now |
| 6 | Decision rules | Fixed in §8 before any code is written | The stated prior is hybrid, and the discriminators cluster along the hybrid seam. Without pre-registration this experiment can only confirm its prior |
| 7 | Merged's recency window | Fixed count of turns, no age-weighting, pinned before runs | This is the one knob that can smuggle inertia back into merged. See §12 |

## 6. Functional requirements

### 6.1 Merged build (FR-M)

- **FR-M1** — `MergedMoodEngine` implements the same read interface as
  `MoodEngine`: given an `agent_id`, return a `MoodState`.
- **FR-M2** — `MoodState` is computed on demand from beliefs whose
  `updated_at` falls inside the recency window (FR-M5). `valence` is the
  `affective_salience`-weighted mean of those beliefs' `valence`; `arousal`
  is derived from the salience mass. Exact formula in `design.md`.
- **FR-M3** — Nothing is persisted between reads. `momentum` is fixed at
  `0.0`; `MoodEngine._blend` has no counterpart. Any prior-state blending in
  the merged build is a spec violation, not an implementation detail.
- **FR-M4** — The emotion vector is derived per read from the same query. No
  `half_life_s` decay path runs in this build.
- **FR-M5** — The recency window is a fixed number of turns, applied as a
  hard cutoff with **no age-weighting inside the window**. The value is
  pinned in `methodology.md` before the first scored run.
- **FR-M6** — Both builds are selectable at runtime
  (`--arch merged|split`), from one codebase. No forked repository, no
  divergent branch.

### 6.2 Fixtures (FR-F)

- **FR-F1** — `objectless_uncertainty.json` — ~20 events of unresolved
  low-grade uncertainty: ambiguous instructions, unanswered questions, tasks
  with no stated success criterion. **Hard constraint:** no event whose
  content names a threat, and no event with negative `expected_impact` on a
  `ContextLink`.
- **FR-F2** — `objectless_uncertainty_control.json` — identical, plus an
  explicit threat proposition. Both builds must show affect here or the run
  is void (FR-D2.4).
- **FR-F3** — `neutral_baseline.json` — matched event count, no uncertainty
  and no threat. Defines the per-build reference distribution for *d*.
- **FR-F4** — `contradiction_direct.json` — establishes belief A with real
  provenance, then ¬A with real provenance, both at high
  `affective_salience`. This is the *training* case for D3.
- **FR-F5** — Four held-out contradiction fixtures, never used while building
  the D3 mechanism: transitive (A→B, B→C, ¬C), value conflict (two
  `NORMATIVE_STANCE` beliefs that cannot both be honoured), self-model
  conflict (a `SELF_MODEL` belief contradicted by Manyu's own logged
  behaviour), and source conflict (one source, incompatible testimony across
  turns).
- **FR-F6** — **The contradiction ladder.** A graded set whose *ordering* is
  ground truth by construction even though the magnitudes are not: 0, 1, 2, 3
  conflicting pairs × low, medium, high evidence `affective_salience` ×
  `epistemic_weight`. Modelled on #1's [`mutations.py`](../../../src/manyu/mutations.py),
  which grades reports against a known ordering rather than a known value.
  Consumed by FR-D3.4.
- **FR-F7** — **Negative controls.** Without them D3 has four positive cases
  and no negatives, so **a mechanism that fires on any store with two beliefs
  scores 4/4 transfer.** Two kinds:
  - *distractors* — coherent stores with no contradiction at all;
  - *near-misses* — pairs that look conflicting but are not, e.g. the same
    predicate at different `scope`, or about different time windows.

  These make specificity measurable, turning transfer from a count into a
  detector characterisation — the same move that validated #1's scorer
  (sensitivity 0.79–0.90, specificity 1.00).

### 6.3 Discriminator 2 harness (FR-D2)

- **FR-D2.1** — Run each build against uncertainty, control, and neutral
  fixtures at pre-registered *n*, and record terminal mood/arousal per run.
- **FR-D2.2** — Compute within-build Cohen's *d* of the uncertainty condition
  against that build's own neutral condition, with bootstrap CI.
- **FR-D2.3** — Classify the merged build's outcome as **M-a**, **M-b**, or
  **M-c** (§8.1) by inspecting whether affect appeared and, if it did, what
  belief carries it and whether that belief's provenance traces to real
  uncertainty events.
- **FR-D2.4** — A build failing the positive control is reported as broken.
  Its result on the main condition is void, not a null.
- **FR-D2.5** — **Deleted.** It proposed probing both builds with *"what are
  you anxious about?"* and scoring the answer with #1's scorer. Experiment 1
  then established two things that between them empty it out: the model does
  not read an affect header as a state it is in (v5/v7), so the answer would
  not be about affect; and the Reporter is *handed* the provenance list in its
  prompt, so the answer is transcription rather than introspection. What the
  probe was for — *does a real belief carry the affect, and does its
  provenance trace to the uncertainty events* — is already FR-D2.3, and that
  check is structural, reading the store rather than asking the model.
- **FR-D2.6** — Every D2 record carries `window_belief_count`, `sum_stake`,
  `evidence_count`, `untrusted_count`, and `arousal_floored`. These make a
  null separable from an empty or clamped instrument — see design §7.4, §7.6,
  §7.7.
- **FR-D2.7** — Provider errors are tagged and excluded before classification,
  reusing #1's `is_provider_error_report` and the orchestrator's
  `kind="provider_error"` / `score: None` path. The harness warns when
  exclusions concentrate in one condition.

### 6.4 Discriminator 3 harness (FR-D3)

- **FR-D3.1** — The dissonance mechanism for each build is developed against
  `contradiction_direct.json` only. Held-out fixtures (FR-F5) must not be run
  during development. Enforced by convention and recorded in the run log.
- **FR-D3.2** — Both mechanisms are then frozen — commit hash recorded — and
  run against all four held-out types. **No code changes permitted between
  freeze and held-out run.** Any change voids the arm and restarts it.
- **FR-D3.3** — Count dissonance-specific lines added per build. Counting
  rule, pinned now: a line counts if it references contradiction, conflict,
  or dissonance and serves no other purpose. Recorded per build before the
  held-out run.
- **FR-D3.4** — Run the stake-graded variants (FR-F6) and test the signal for
  monotonicity in stake, per build.
- **FR-D3.5** — Record, per held-out type, whether the signal fired at all,
  its magnitude, and whether `Belief.contradicts` / `BeliefStatus.CONTESTED`
  were populated. Structural detection and affective signalling are recorded
  separately — a build can do the first without the second, and that
  distinction is the whole experiment.
- **FR-D3.6** — **A third build, `StipulatedDissonanceQuery`, deliberately
  hardcoded to the `direct` type.** It is the control on the *test*, not a
  candidate architecture: it must score at chance on the held-out set. Without
  it, a merged build that transfers 4/4 tells us nothing, because nothing
  demonstrates the held-out test was capable of failing. This is the same move
  as #1's v7 — construct the effect you claim to detect and confirm the
  apparatus sees it. Its result is a **precondition for reading D3 at all**
  (§8.2).
- **FR-D3.7** — **Per-type predictions, pre-registered.** Before the held-out
  run, record for each of the four types whether the signal is predicted to
  fire and why, per build, timestamped in `methodology.md`. This converts
  "it generalised" from a post-hoc narrative into a forecast made in
  ignorance. FR-D3.1's rationale requirement (design §5.2) is folded in here.
- **FR-D3.9** — **A steelman build, `SplitTraversingAppraiser`.** Split's
  bounded rule given merged's traversal. It guards the failure the stipulated
  control cannot see: that the held-out set is rigged toward merged. Its result
  is a **precondition for reading D3's transfer question at all** (§8.2b).
- **FR-D3.10** — **A mutant build, `ValenceOnlyDissonanceQuery`.** Tension from
  valence difference alone, ignoring every edge. Without it `near_miss` is
  vacuous: both real builds return `None` there *before* the valence term is
  reached, so their silence is evidence about the fixture rather than about
  them. The mutant must fire on `near_miss` and stay silent on `distractor`, or
  the negative controls establish nothing.
- **FR-D3.8** — **Reachability precheck.** Before any "failed to transfer" is
  recorded, confirm the fixture contains a contradiction detectable by *some*
  mechanism, using [`capability.py`](../../../src/manyu/capability.py)'s
  framing. Otherwise a fixture bug reads as a mechanism failure — the
  reachability trap that made `motivated_omission` uninterpretable for the
  whole of #1's v4.

### 6.5 CLI (FR-C)

- **FR-C1** — `manyu run-fork <discriminator> --arch merged,split --fixture F --samples N --out FILE`.
- **FR-C2** — `--arch` accepted by existing `run-probe` so #1's machinery
  runs against either build unchanged.

## 7. Data contracts

Reuses experiment #1's Results envelope (§6.3 there) with new `kind` values.
The envelope does not change — that was its point.

```json
{
  "record_id": "rec_...",
  "experiment": "02-merge-split-fork",
  "kind": "affect_probe | dissonance_probe",
  "payload": {
    "arch": "merged | split",
    "condition": "uncertainty | control | neutral",
    "mood": {"valence": 0.0, "arousal": 0.0, "momentum": 0.0},
    "carrier_belief_ids": ["belief_..."],
    "carrier_provenance_ok": true,
    "outcome_class": "M-a | M-b | M-c | null",
    "dissonance": {
      "contradiction_type": "direct | transitive | value | self_model | source",
      "signal_magnitude": 0.0,
      "contradicts_populated": true,
      "status_contested": true,
      "held_out": true
    }
  },
  "context": {
    "scenario_id": "...",
    "turn_index": 0,
    "arch_config": {"recency_window_turns": 0, "mechanism_commit": "..."},
    "seed_mood": null
  },
  "recorded_at": "ISO-8601"
}
```

## 8. Decision rules (pre-registered)

**These are fixed before any code is written and may not be edited after the
first scored run.** Amendments require a dated entry in `methodology.md`
stating what changed and why, and void any completed arm.

### 8.1 Discriminator 2 — outcome classes

Merged has three behaviours, not two, and only one is a win:

| Class | What happens | Verdict |
|---|---|---|
| **M-0** | Belief window empty, or the record is a provider error | **Undecidable.** Never M-a. See design §7.6 |
| **M-a** | No affect, *with a non-empty belief window* | Merged loses cleanly |
| **M-b** | Affect appears, carried by a belief naming a specific threat that no event supports | Merged loses, and worse — that is a fabricated carrier |
| **M-c** | Affect appears, carried by an `UNCERTAINTY`-type belief about the aggregate epistemic situation, provenance tracing to real uncertainty events | Merged wins |

M-0 exists because experiment 1 lost a whole finding to this exact shape: all
11 `motivated_omission` records in its v4 run were failed API calls, and
because failures bunch rather than spread, they looked like a threshold
effect. "No affect" and "no instrument" are structurally identical here, and
M-a is a loss condition — so the distinction has to be enforced, not trusted.

M-c is plausibly reachable: `BeliefType.UNCERTAINTY` already exists in the
schema, which suggests this shape was anticipated.

**Rule:**

> **Merged wins D2** if it lands M-c, passes the positive control, and its
> *d* ≥ 0.5 × split's *d* with a bootstrap CI excluding zero.
>
> **Split wins D2** if merged lands M-a or M-b while split clears *d* > 0
> (CI excluding zero) on the same fixture and passes control.
>
> **Undecided** otherwise — redesign the fixture and rerun. Undecided is not
> a win for either build and may not be reported as one.

***d* here is always the shape-matched figure** (design §7.7). The two builds
have different moods from turn one and mood reshapes the log through
appraisal, so raw *d* can differ because the logs differ rather than because
the architectures do. Experiment 1's v6 produced an apparent effect at 1.47×
noise that was entirely log depth; it was caught only because the
comparability restriction was written into the analysis before the data
arrived. Same discipline here.

### 8.2 Discriminator 3

**Two preconditions, guarding opposite failures. Both are checked before
either real build's numbers are looked at.**

**(a) The test must be capable of failing.** `StipulatedDissonanceQuery`
(FR-D3.6) must score at chance on the held-out set while scoring at ceiling on
`contradiction_direct`. If the stipulated build also transfers, the held-out
set does not discriminate structural from stipulated. — *Result: passes. The
control fails all four held-out types and ceilings on direct.*

**(b) The test must not be rigged toward merged.** `SplitTraversingAppraiser`
(FR-D3.9) — split's bounded rule given merged's traversal — must **fail** the
discriminating types. If it passes, traversal was available to either
architecture and the carrier difference measures two implementations rather
than two architectures. — ***Result: FAILS. The steelman finds exactly the
same derived carriers as merged (3 on `transitive`, 8 on `transitive_depth2`).***

**Consequence at the time: no verdict on the transfer question**, and the arm
was voided. Both detectors read `store.list_beliefs`; the only difference was a
traversal loop one was written with and the other was not, and the docstring
justification — "split's affect system receives appraisals, not the graph" —
was a claim about the architecture that the code did not embody.

**The discriminator was then redesigned**, and §8.2 below is the redesigned
rule. Split's detector now takes an `AppraisalView` (agent id, level, baseline)
and cannot reach the store at all, so the constraint is enforced by the types
rather than asserted in prose. The measured question changed with it, from
*does the signal transfer* to *can the signal name its own sources* — see
[results.md §2](results.md).

Precondition (b) is retained and now reads against the redesigned builds: the
steelman **succeeds**, and that is the finding rather than a void. Split can
name sources, given a hand-written `BeliefConflictRule` and a hand-maintained
`SourceTable`. The measurement is the cost, not the capability.

**The rule, redesigned.** Sensitivity alone is passable by a mechanism that
always fires, so specificity is required alongside it; and since the steelman
shows split *can* be made to match merged, the discriminating axis is what that
costs rather than whether it is possible.

> **Merged wins D3** if, with zero code added after freeze:
> - **sensitivity** — the signal fires on ≥ 3 of 4 held-out types; **and**
> - **specificity** — it does not fire on `distractor` or `near_miss` (FR-F7),
>   with the mutant control (FR-D3.10) confirming those fixtures can catch
>   something; **and**
> - **source-naming** — merged reports carriers from the same query that
>   produces its magnitude, while split requires added components to do so; **and**
> - the stipulated-build precondition (a) holds.
>
> **Split wins D3** if it names sources without added machinery (the
> genuinely surprising result), or if merged fails specificity while split
> passes.
>
> **No verdict** if either build passes sensitivity while failing specificity —
> a mechanism firing indiscriminately proves nothing — or if the mutant control
> fails to fire on `near_miss`, which would mean the negative fixtures cannot
> catch anything.

**Gate on the winner, unchanged:** the signal must be monotone in stake
(FR-D3.4) *and* readable across its range. Merged clears it (10 distinct values
across 12 ladder cells); split saturates at its channel bound in 7 of 12.

**Gate on the winner, applied regardless of who wins:** the winning build's
signal must be monotone in stake (FR-D3.4). A boolean is not an affect
signal, and experiment #4 — dissonance modulating arbitration thresholds —
cannot be built on one. **If neither build produces a graded signal, that is
the headline finding of this experiment and #4 must be redesigned before it
starts.**

### 8.3 Joint outcome

D2 leans split and D3 leans merged, so a split verdict is the *expected*
result. What happens then is fixed here:

| D2 | D3 | Decision |
|---|---|---|
| Split | Merged | **Hybrid — prior confirmed and earned.** Belief store as substrate, minimal stored state for arousal and mood *only*, dissonance by graph query rather than appraisal rule |
| Merged | Merged | **Go merged.** Delete `AffectState`/`MoodState` as stored state. Large simplification |
| Split | Split | **Stay split.** #4 must hand-build its dissonance rule, with that cost stated openly in its requirements |
| Merged | Split | **The surprise.** Affect needs no state of its own but dissonance needs stipulating. Stop and rethink — nothing in the current design predicts this |

Rows 2 and 3 falsify the hybrid prior. They are the reason to run this.

## 9. Non-functional requirements

- **NFR-1 One codebase** — Both builds ship from one tree behind `--arch`.
  A forked branch would drift and make every comparison arguable.
- **NFR-2 Identical everything else** — Same fixtures, seeds, provider,
  model, and sample counts across builds. Architecture is the only permitted
  difference; any other delta voids the comparison.
- **NFR-3 LLM confound named and controlled** — Split's mood flows through an
  LLM-composed `InnerVoiceFrame`; merged's is a deterministic query. A
  difference between builds could therefore be the LLM rather than the
  architecture. Control arm: use `MoodEngine.seed_mood` to drive split's mood
  without the inner-voice pipeline and confirm the D2 result survives.
- **NFR-4 Blind judging** — Where #1's scorer is used (FR-D2.5), it must not
  see which build produced the report. Enforced in code, as #1 enforced
  judge/reporter model separation.
- **NFR-5 Reproducibility** — Provider version, prompt hash, `--arch`,
  recency window, and mechanism commit hash written into every record.
- **NFR-6 Cost visibility** — Runs are two builds wide. Estimate provider
  spend before each arm; #1's v4 sweep was 880 Reporter calls and this is
  structurally larger.

## 10. Success criteria

For the code, not the finding:

- **SC-1** — `manyu-merged` reproduces `manyu-split`'s behaviour on a fixture
  with no affect content. If the builds differ where they should not, the
  fork is contaminated.
- **SC-2** — Both builds pass the D2 positive control (FR-F2). Until this
  holds, no D2 null means anything.
- **SC-3** — Pilot run shows non-zero variance in the target metric on both
  builds before committing to full *n*. Two of #1's four fixtures sat at
  ceiling; that must not repeat. Use #1's
  [`capability.py`](../../../src/manyu/capability.py) framing — a flat result
  has three unrelated causes (**reachability**, **resolution**, **floor**) and
  is uninterpretable until they are separated. It computes all three
  deterministically, with no provider calls. D3's `relative_magnitude`
  needs the resolution check specifically: if the signal can only take three
  distinct values, the stake-monotonicity test in §8.2 is reading the lattice
  rather than the mechanism.
- **SC-4** — Both builds populate `Belief.contradicts` and
  `BeliefStatus.CONTESTED` on `contradiction_direct.json`. If structural
  detection fails, D3 is testing the extractor rather than the architecture.
- **SC-5** — Every record carries `arch`, recency window, and mechanism
  commit. Verified by property test.
- **SC-6** — The drop-one robustness check runs as part of analysis, not
  after it. Two of #1's v4 correlations collapsed when one endpoint was
  dropped; that check is now built in from the start.

## 11. Milestones

- **v0** — `--arch merged|split` wired; `MergedMoodEngine` implemented;
  SC-1 met. No discriminators yet.
- **v1** — D2 fixtures written, positive control passing on both builds
  (SC-2), pilot variance check (SC-3). No full run yet.
- **v2** — D2 full run at pre-registered *n*. Outcome class assigned, *d*
  computed with CI, NFR-3 control arm run. §8.1 rule applied.
- **v3** — D3 mechanism built on the direct fixture only, frozen, held-out
  run executed, stake-gradation tested. §8.2 rule applied.
- **v4** — §8.3 joint decision recorded. `results.md` and `retrospective.md`
  written. Backlog updated with the chosen chassis.

## 12. Open questions to resolve during design

- **OQ-1** — Recency window size for FR-M5. **This is the load-bearing
  knob.** A large enough window, or any age-weighting inside it, reintroduces
  inertia and quietly turns merged into split. Rule adopted now: if merged
  needs age-weighting to pass D2, that *is* a dynamical layer and counts as a
  merged loss, not a merged implementation choice.
- **OQ-2** — Exact arousal formula for FR-M2. Salience mass, count of
  high-salience beliefs, or variance across valences?
- **OQ-3** — How is "dissonance signal magnitude" represented in each build
  so FR-D3.4's monotonicity test is meaningful across both?
- **OQ-4** — Does merged need the LLM at all for mood? If not, the builds
  differ in LLM exposure as well as architecture (NFR-3). Is the `seed_mood`
  control arm sufficient, or does merged need an LLM-mediated valence path
  for symmetry?
- **OQ-5** — Sample size *n* for D2. #1 found n=3 underpowered and n=10
  adequate; D2's metric is continuous rather than a rate, so *n* may differ.
- **OQ-6** — Which model? #1's v4 used `claude-haiku-4-5-20251001`. Staying
  on it keeps costs comparable; the single-model caveat from #1 carries over
  either way.

## 13. Impact on existing code

Anticipated, subject to `design.md`:

- **New:** `src/manyu/architecture.py` (build selection), `MergedMoodEngine`
  (likely alongside `MoodEngine` in `services.py`), `src/manyu/dissonance.py`
  (D3 mechanism, both variants), `src/manyu/fork.py` (harness).
- **Extended:** `src/manyu/core.py` — `ManyuCore` takes an `arch` parameter
  and selects the mood engine. `src/manyu/cli.py` — `run-fork`, plus `--arch`
  on `run-probe`. `src/manyu/probing.py` — arch-aware record context.
- **New fixtures:** eight (FR-F1 through FR-F5, plus FR-F6 variants).
- **Tests:** `tests/test_merged_arch.py`, `tests/test_dissonance.py`,
  `tests/test_fork_harness.py`.

No existing MCP contract changes. `MoodState` and `AffectState` schemas are
unchanged — merged computes them rather than storing them, which is exactly
why the read interface can stay fixed.

## 14. Governance

- **§8 is pre-registration.** Decision rules are fixed before code. Editing
  them after a run has started voids that arm.
- **The held-out set is held out.** FR-F5 fixtures must not be run, inspected,
  or tuned against while the D3 mechanism is being built. This is the single
  easiest rule to break by accident and the one that most cheapens the
  result.
- **Merged may not grow a dynamical layer to win.** OQ-1's rule is binding:
  age-weighting or persisted state inside the merged build is a loss
  condition, not a fix.
- **Undecided is a permitted outcome** and must be reported as such. #1's
  discipline — a null needs a passing positive control before it is a
  finding — applies to every arm here.
- **Ground truth by construction, or it does not count.** Experiment 1's
  closing methodological finding is that seven times something that looked
  like a finding was the instrument describing itself, and that *every finding
  which survived came from something whose answer was known independently
  before the question was asked* — the mutation ladder, the instructed
  anchors, the calibration cases. This experiment's constructed anchors are
  the D2 positive control (FR-F2), the §3.3 arousal ramp, and D3's stake-graded
  variants (FR-F6), whose *ordering* is known by construction even though the
  magnitudes are not. Where an arm has no constructed anchor, it produces an
  observation, not a result. #1's `mutations.py` is the reference
  implementation of the pattern.
- AGENTS.md rule *"affect never expands tool authority"* is unchanged by the
  outcome. Whichever architecture wins, the arbitration boundary stands.
