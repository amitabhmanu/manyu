# Experiment 2 — Merge/Split Architecture Fork: Results

**Status:** D3 complete (offline). D2 mechanism verified (offline); D2 verdict
not run — it needs the one provider call in this experiment.
**Requirements:** [requirements.md](requirements.md) · **Design:** [design.md](design.md) · **Methodology:** [methodology.md](methodology.md)

Every number on this page comes from a deterministic offline run. **No provider
was called at any point in D3**, so nothing here has a sampling error, a model
version, or a cost.

## D3 — one architectural finding, one withdrawn one

| Question | Answer |
|---|---|
| Can each build say *what* its dissonance is about? | **Merged yes, split no** — and for a reason in the types, not the implementation. See §2 |
| What does it cost split to match merged? | A hand-written traversal rule **and** a hand-maintained side-table. See §2.3 |
| Do the negative controls hold? | **Yes**, and they are non-vacuous — see §3 |
| Is the signal graded enough for experiment #4? | **Merged yes, split no.** See §4 |

> **This section was rewritten after a redesign.** The first D3 build measured
> whether each detector's signal *transferred* to held-out contradiction types.
> A steelman control showed that result was an artifact — both detectors read
> `store.list_beliefs`, and the only difference between them was a traversal
> loop the author gave one and not the other. That arm is void; the superseded
> freeze hash is recorded in `evals/analysis/exp02/freeze.json`. §2 is the
> redesigned discriminator, and §5 keeps the account of what went wrong,
> because the failure is more instructive than the finding.

## 1. What was run

Three fixtures groups, seven files, hashed before any mechanism code existed
(`evals/analysis/exp02/freeze.json`):

- **development** — `direct` (the only fixture the mechanisms were built against)
- **held-out** — `transitive`, `transitive_depth2` (discriminating);
  `value_conflict`, `source_conflict` (sanity — see methodology §3.2)
- **negative** — `distractor`, `near_miss`

Five detectors: two candidate architectures (`merged`, `split`) and three
controls (`stipulated`, `split_traversing`, `valence_only`).

## 2. Can the signal say what it is about?

### 2.1 The redesigned question

The original framing — does the mechanism *transfer* to unseen contradiction
shapes — turned out to be unanswerable with these two builds, because transfer
is a property of whichever loop the implementer wrote. The redesign asks
something the architectures decide instead.

`AffectState.emotions` is a `dict[str, float]`. **A scalar has no pointers back
into the graph.** Merged's mood is already a query over the belief store, so it
recomputes carriers on demand and nothing has to be remembered. Split's affect
is an accumulated number; to say what the number is *about*, something must
have written the sources down separately.

That asymmetry is not a choice. It is enforced in the types:
`SplitDissonanceAppraiser.detect` takes an `AppraisalView` — an agent id, a
level and a baseline — and never receives the store
(`test_split_detector_cannot_reach_the_store`).

### 2.2 Result

| Fixture | merged | split | split + table (adjacent rule) | split + table (traversing rule) |
|---|---|---|---|---|
| `direct` | 1 carrier | **0** | 1 | 1 |
| `transitive` | 4 (3 derived) | **0** | 1 (0 derived) | 4 (3 derived) |
| `transitive_depth2` | 9 (8 derived) | **0** | 1 (0 derived) | 9 (8 derived) |
| `value_conflict` | 1 | **0** | 1 | 1 |
| `source_conflict` | 1 | **0** | 1 | 1 |
| `distractor` | none | none | none | none |
| `near_miss` | none | none | none | none |

Split registers the tension on every positive fixture — magnitude 0.45 — and
names nobody on any of them.

### 2.3 What it costs split to catch up

Split *can* match merged. The steelman does, exactly. It needs two things the
architecture does not provide:

1. **A `BeliefConflictRule`** — a hand-written bridge, because the affect layer
   cannot reach the graph. This is the stipulation, now a named injectable
   object so its cost is countable (FR-D3.3).
2. **A `SourceTable`** — a side-store holding the belief ids the scalar cannot,
   maintained alongside the affect state.

And the table's coverage is bounded by its rule's: with the natural
`AdjacentConflictRule` it names the stated pair and stays blind to all eight
derived ones on `transitive_depth2`. Reaching merged's coverage requires
`TraversingConflictRule`, which is `MergedDissonanceQuery` called from inside
split.

**So the finding is a cost, not a capability.** Naming the sources of a
dissonance signal is free for merged and takes two purpose-built components for
split — one of which is a copy of merged's query.

**How to falsify it:** write a split build that names sources without a
side-table. If the affect layer can be made to carry belief references without
becoming a query over beliefs, this finding is wrong.

## 3. Specificity holds, and the negatives are real

| Fixture | merged | split | stipulated | **valence_only** |
|---|---|---|---|---|
| `distractor` | none | none | none | **none** |
| `near_miss` | none | none | none | **fires, 0.986, 9 carriers** |

Both real builds are silent on both negatives. On its own that establishes
little: they return `None` on `near_miss` *before* the valence term is reached,
because there are no `contradicts` edges and they bail at `_leaf_conflicts`.
Their silence was evidence about the fixture, not about them.

The mutant closes it. `ValenceOnlyDissonanceQuery` is the mechanism `near_miss`
was designed to catch — merged's `(1 + |Δv|)/2` term is a weighting on pairs
that already conflict, and an implementation mistaking it for a *detector*
would fire on every line of that fixture while still scoring 4/4 on held-out.
It fires at 0.986 while merged stays silent, and is correctly silent on
`distractor`. So the trap works and merged genuinely resists it.

## 4. Gradedness: the one architectural result

The contradiction ladder — 0/1/2/3 conflicting pairs × low/medium/high stake,
ordering known by construction.

| stake | pairs | merged | split |
|---|---|---|---|
| low | 1 / 2 / 3 | 0.104 / 0.197 / 0.281 | 0.215 / 0.380 / **0.450** |
| medium | 1 / 2 / 3 | 0.226 / 0.402 / 0.537 | 0.435 / **0.450** / **0.450** |
| high | 1 / 2 / 3 | 0.393 / 0.631 / 0.776 | **0.450** / **0.450** / **0.450** |

Both builds are monotone in both axes. They are not equally *readable*:

- **merged** — 10 distinct values across 12 cells, range 0.000–0.776,
  unsaturated at the top rung.
- **split** — 5 distinct values, pinned at **0.450** in 7 of 12 cells.

0.450 is `baseline (0.05) + max_delta_per_event (0.40)`. Split's affect channels
are bounded per event — that bounding is what makes them stable — and a
dissonance signal routed through one inherits the bound and flattens above it.

**This does not depend on the constant chosen.** Every channel in
`config/default_profile.json` caps between 0.25 and 0.35; the 0.40 used here is
already more generous than any of them. A single high-stake conflicting pair
produces ~0.75 of raw tension, so split saturates at one pair under *any*
profile-consistent bound.

**Consequence for experiment #4**, which modulates arbitration thresholds with
this signal: a signal that is flat across most of its range cannot do that.
Merged clears the §8.2 gradedness gate; split does not.

This one *is* architectural. It follows from where the signal is stored rather
than from how either detector was written — which is exactly the property the
transfer question turned out to lack.

## 5. The arm that was voided, and why it is kept here

The first D3 build measured transfer to held-out contradiction types. Merged
scored 2/2 on the discriminating types and split 0/2 — matching the
pre-registered prediction exactly, which is what made it convincing.

It was an artifact. `SplitTraversingAppraiser` — split's rule handed merged's
traversal — found identical derived carriers, so the difference lived in the
implementations rather than the architectures. The docstring justifying the
asymmetry ("split's affect system receives appraisals, not the graph") stated a
constraint **the code did not enforce**: that build took the store and merely
declined to walk `supports`.

Three things are worth carrying forward:

- **The pre-registered prediction was no protection.** It came true because the
  same person wrote the prediction and the mechanism it described. Registering a
  forecast guards against reading the result afterwards; it does nothing about
  building the thing that produces it.
- **The stipulated control passed and would not have caught this.** It guards
  the risk that the test *cannot fail*. The opposite risk — that the test is
  rigged toward the favoured build — needed its own control, and that control is
  what turned the finding over.
- **The fix was to move the constraint into the type system.** "Split cannot see
  the graph" stopped being a claim in prose and became `detect(view:
  AppraisalView)`. Claims that live only in docstrings are not constraints.

This is experiment 1's failure mode #1 — an instrument built to produce the
result its criterion asked for — recurring in the machinery built to prevent
experiment 1's failure modes.

## 6. What this costs the joint outcome

Requirements §8.3 reads D2 and D3 together. D3 supplies two inputs, both
favouring merged: source-naming cost (§2) and gradedness (§4). Both are about
what split's *stored scalar* can hold, which makes them one finding seen twice
rather than two independent votes — worth weighting accordingly when the joint
table is read.

---

# D2 — mechanism stage (offline)

**None of this section is a D2 result.** Belief valences are authored, so
merged's numbers are our authorship (design §6.1). What is established is that
the apparatus works, so the single paid run in Stage 4 is spent on the question
rather than on debugging. Artifact:
[`d2_mechanism.jsonl`](../../../evals/analysis/exp02/d2_mechanism.jsonl).

## 8. The conditions separate on both builds

20 events per condition, clock advancing 60s between them so `fear`'s 900s
half-life genuinely opposes accumulation.

| build | channel | neutral | uncertainty | control |
|---|---|---|---|---|
| merged | negative valence | **0.000** | **0.309** | **0.692** |
| split | `AffectState.fear` | 0.080 | 0.561 | 0.935 |

`control > uncertainty > neutral` on both. Gate #4 (the axis is real) and gate
#7 (conditions comparable) both pass. Split's neutral sits exactly at its
configured baseline — `goal_progress` never touches the fear channel.

The two builds are on different channels because those are the affect each
architecture *has* offline: without a provider `process_reflective_turn` never
composes an inner voice, so split has no `MoodState` at all. Nothing is
compared across builds; the analysis is within-build against each build's own
neutral (methodology §4.3).

## 9. Split's route to object-less affect, confirmed

The uncertainty event carries **no goal link and no claims** — nothing that
could name a threat — and still produces `fear 0.036`, because `FastAppraiser`
groups `TOOL_RESULT` with `GOAL_OBSTRUCTION` and defaults `negative = 0.45`
when `goal_impact >= 0`.

So split's D2 arm rests on an accident of the rule table. Used as-is and pinned
by `test_tool_result_yields_fear_without_negative_goal_impact`, whose docstring
states that changing it invalidates the D2 result rather than merely breaking a
test (design §6.2).

## 10. Two corrections the diagnostics caught

Both were found by gates rather than by inspection, and both would have
produced a confident wrong number.

**The neutral condition was not comparable.** It originally used
`social_feedback` from the user, which produces no fear — but swung
`untrusted_count` from 0 to 45, so the conditions differed in log shape as well
as in treatment and gate #7 refused the comparison. This is v6's trap exactly.
Fixed by sourcing all three conditions from the same verified tool.

**Arousal was the wrong channel for merged.** Measured on arousal, merged spans
0.678 → 0.738 across *all three* conditions — a range of 0.06. Merged's arousal
is `1 − exp(−Σstake/τ)`, and neither stake nor τ depends on valence: it measures
how much is on the agent's mind, not how bad any of it is. That is the standard
circumplex separation and correct, but it means **a store of pleasant beliefs
is as aroused as one of dreadful ones.** D2's merged channel is therefore
negative valence. Pinned by `test_merged_arousal_does_not_separate_the_conditions`.

A third thing was nearly a false alarm: gate #7 initially refused all three
conditions because `evidence_count` differed (51/54/58). It was checking a key
the metric does not depend on — merged reads the belief *window*, which is
identical across conditions (21 beliefs, 8 in window, 7 authored carriers).
Shape keys are now declared per build in `D2_SHAPE_KEYS`, with the rule that a
key is admissible only if the measured channel is a function of it. Choosing
keys after seeing which ones pass would be gate #1.

## 11. What Stage 4 still has to answer

Everything above holds the belief valences fixed, which is the one thing D2's
real question is about. The verdict run replaces authored candidates with the
live `BeliefExtractor` and asks whether a carrier arises **unprompted** — M-0 /
M-a / M-b / M-c per requirements §8.1. Preconditions are now all green:
instrument gate, ramp on both builds, `FastAppraiser` coverage, and
shape-comparable conditions.

---

## 12. Caveats

- **The `BeliefConflictRule` boundary is still a modelling choice.** Putting the
  store behind the rule and the scalar in front of it is the honest reading of
  how `FastAppraiser` and `AffectState` are built, but nothing in the codebase
  *forces* that line — `FastAppraiser` itself holds a store reference it never
  uses. A reader who thinks split's affect layer should have belief access will
  reject §2, and the argument they need to make is about the boundary, not
  about the numbers.
- **Split's saturation inherits a chosen bound.** What makes it stronger than
  the withdrawn transfer claim is that it holds across the whole range of
  existing channel bounds (0.25–0.35) rather than at one value.
- **`value_conflict` and `source_conflict` are sanity checks, not
  generalisation tests** — `direct` with different metadata, which both
  mechanisms ignore by design (methodology §3.2). They are reported for
  completeness and carry no weight.
- **Split's signal does not decay here.** `EMOTIONS` is a closed vocabulary
  enforced in four validators, so routing dissonance through a real
  `AffectState` channel would have meant invalidating the default profile and
  handing merged a channel it never writes. D3 asks nothing temporal, so
  nothing measured depends on it — but a temporal experiment would have to pay
  that cost. See `dissonance.py`'s `SplitDissonanceAppraiser` docstring.
- **`self_model` was dropped** from the held-out set during fixture authoring:
  in this schema a `contradicts` edge always runs belief↔belief, so it is
  `direct` with a different `belief_type`. Replaced by `transitive_depth2`.
