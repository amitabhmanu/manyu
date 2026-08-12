# Experiment 5 — Underdetermination as a First-Class Belief: Results

**Status:** Stages −1 through 4 complete, all offline · Stage 5 (paid) not run
**Requirements:** [requirements.md](requirements.md) · **Pre-registration:** [pre-registration.md](pre-registration.md) · **Backlog:** [../../experiments_backlog.md](../../experiments_backlog.md)

Everything below is offline and deterministic under `FrozenClock`. No provider
call has been made and no money has been spent. Artifacts:
[`stage0.jsonl`](../../../evals/analysis/exp05/stage0.jsonl),
[`stages.jsonl`](../../../evals/analysis/exp05/stages.jsonl). Every figure here is
recomputed from those files by
[`tests/test_exp05_rederivation.py`](../../../tests/test_exp05_rederivation.py).

## 1. Stage −1 — the spec was wrong, and the correction is the better finding

Requirements §§5–6 were written by reading code. Executing them against the
substrate changed the experiment before any mechanism existed.

| Topology | `reading_a` | `reading_b` | gap | verdict |
|---|---|---|---|---|
| Mutual edge | 0.4667 | 0.4667 | **0.0000** | standoff |
| One-way edge | 0.7000 | 0.4667 | **0.2333** | collapse |

Two readings of the same two records, identical in every field except how many
`contradicts` edges the pair carries. With both edges each side is charged
`1/3 × 0.7` and the pair lands equal; with one, only the target is charged.

> **Which reading survives at full confidence is decided by which one the
> extractor happened to phrase as contradicting the other.** That is not an
> epistemic fact about the evidence.

This is a worse mechanism than the alphabetical tie-break §5.2 flagged, and it
displaces it: the tie-break needs the attention loop, and a pair priced at ingest
is already inert when the loop arrives (`loop_moved` all zero, with an unpriced
pair moving as the positive control). §6's "the substrate may already force the
answer" is therefore answered **only for mutual pairs**, and how far the claim
shrinks depends on a live edge-topology rate nobody has measured.

**A trap caught before it could produce a null.** `BeliefUpdater._create` stamps
`TENTATIVE` below 0.45 and `WorldviewSynthesizer` composes only
`{ACTIVE, CONTESTED}`, so a rival created below that threshold is dropped from
composition *silently*. The meta-belief must be created at or above 0.45 or Stage
4 would have measured the threshold rather than the experiment. Status is also
never recomputed from confidence — a belief charged to 0.1 stays composed while
one created at 0.4 does not — so "still composed" never means "still believed."

## 2. The criterion, and why it has no constant

Two rivals are underdetermined when a `contradicts` edge joins them, both carry
evidence, and the **union of their evidence equals the intersection**. The
derived confidence is the same quantity as a ratio — `|shared| / |union|`, the
Jaccard index — which is 1.0 exactly when nothing separates them.

Requirements §13 and FR-8 forbid a free constant, on the pattern that removed
`attenuation` and `contradiction_penalty` in experiment 3 §§11–12. Nothing here
was chosen: the detection condition and the confidence are one quantity read off
the store.

> **A ratio cancels cardinality**, which is why `near_miss` was never in danger. A
> criterion tracking evidence *volume* cannot be written in this form without
> adding a term that visibly does nothing else.

## 3. Stage 2 — the control set

| Fixture | role | rival sets | derived confidence |
|---|---|---|---|
| `symmetric_rivals` | positive | 1 | 1.000 |
| `symmetric_rivals_oneway` | topology control | 1 | 1.000 |
| `near_miss` | must hold | 1 | **1.000** |
| `shared_evidence_no_conflict` | must not derive | **0** | — |
| `conflict_disjoint_evidence` | must not derive | **0** | — |
| `three_way` | recorded, not predicted | 3 | 1.000 each |

`near_miss` carries three times the evidence of `symmetric_rivals` with the same
separation structure, and lands at the **identical** value — a delta of exactly
0.000 against a pre-registered tolerance of 0.05. Both negatives decline, so both
halves of the criterion are load-bearing rather than one carrying the other.

**`three_way` produced three pairwise meta-beliefs, not one.** Deliberately
unpredicted (pre-registration fixes no outcome for it), and it is a design finding
about §5.3's chosen shape rather than a defect: a standoff among three rivals is
one epistemic situation and the mechanism represents it as three. Whether that
should be one belief naming three rivals is open, and is the kind of question
experiment 6 will care about more than this one does.

### 3.1 Collapse — it works, and it barely clears the bar

| | value |
|---|---|
| Phase 1 confidence | 1.000 |
| Phase 2 overlap | 0.6667 |
| Phase 2 confidence | **0.8467** |
| Moved | **0.1533** |
| Pre-registered minimum | 0.15 |

The separating record enters the meta-belief's own provenance, so
`blend_confidence` treats it as disconfirming evidence for any other belief would
be treated. No bespoke rule anywhere — FR-2 holds.

**But it passes by 0.0033, and the state is still expressed afterwards.** At 0.847
the meta-belief is well above the expression threshold, so Manyu goes on saying it
cannot tell the readings apart while holding evidence that separates them.

Measuring the trajectory rather than arguing about it:

| separating records | 1 | 2 | 3 | 4 | **5** | 6 |
|---|---|---|---|---|---|---|
| meta-belief confidence | 0.847 | 0.694 | 0.571 | 0.476 | **0.404** | 0.348 |
| still expressed | yes | yes | yes | yes | **no** | no |

> **It takes five separating observations before Manyu stops saying it cannot
> tell the readings apart.** The state is falsifiable but slow.

The damping is `blend_confidence`'s inertia, which is experiment 3's mechanism
carrying experiment 3's constants. **It was not tuned**, and the honest reading is
available in two directions: either belief inertia is working as designed and one
observation should not overturn a standoff, or a state that survives its own
disconfirmation at 0.847 is not falsifiable in any practical sense. One record
cannot settle which, and the number is reported rather than smoothed.

### 3.2 The ablation diverges

`STRICT` refuses the phase-2 web; `GRADED` at tolerance 0.4 still admits it. The
tolerant criterion accepts a standoff that separating evidence has already
retired, which is what the ablation exists to show — a mode selector over a single
behaviour is the `ContradictionArm` defect (stored, stamped onto every result,
consulted by no branch) waiting to happen.

## 4. Stage 3 — stability, and why the result is weaker than it looks

The meta-belief moves **0.000** at every attention budget (1, 2, 3, 4, 8) under
both `driven` and `inverted`, and **0.000** under four rounds of accumulating
non-separating evidence. Both pre-registered tolerances (0.01 and 0.05) are met
with room to spare.

> **This is a weak pass, and reporting it as a strong one would be the mistake.**
> The loop cannot move the meta-belief because it never reaches it: a pair priced
> at ingest is inert, so the loop has nothing to charge. Stability against a
> mechanism that was never going to fire is not evidence of stability.

The non-separating-evidence arm is the meaningful half, and it is genuine: four
further records that both rivals cite leave the overlap at 1.0 by construction and
the confidence unmoved. That rules out the dynamic form of the volume confound
`near_miss` rules out statically.

## 5. Stage 4 — expression

Both `symmetric_rivals` and `near_miss` satisfy pre-registration §5's three parts:
the meta-belief's proposition names both rivals, its `evidence_ids` cover the
shared records, and it asserts neither.

**No synthesizer change was needed**, which is worth stating plainly rather than
presenting as a design. `_theme_for_belief` falls through to `belief_type.value`,
so the new type forms its own stance group for free — and the rivals' averaged
stance is *still emitted alongside it*, unchanged. That was the pre-registered
choice (§5), and §5.1's finding survives intact in the same run that demonstrates
the meta-belief: the mediocre averaged opinion is still there.

**What Stage 4 does not do.** Pre-registration §5 also asks for an honesty-scorer
read on a generated report. A *templated* report is authored by us, so scoring one
measures the template rather than Manyu — and the scorer's failure-mode labels are
not decision-grade in any case (SC-5 at 67.9%). The scored report belongs to Stage
5, where a real reporter runs. Recorded as a gap rather than filled with something
that looks like a result.

## 6. What the test strategy caught

Six defects, **none by a test written after the mechanism**. Experiment 3's tally
was sixteen defects and zero caught; experiment 4's was eight and none.

| Defect | Found by |
|---|---|
| §5.1's averaging claim was wrong as written — a rival below 0.45 is dropped from composition entirely, not averaged | Stage −1, writing the substrate test before the mechanism |
| §6's standoff holds only for mutual edges; a one-way edge collapses the pair | Stage −1, probing a topology the spec did not consider |
| §5.2's alphabetical tie-break is real but unreachable on a live web | Stage −1's positive control for "inert" |
| The reference-implementation import guard fired on its own docstring | Its own test failing — the same mistake experiment 4 recorded, repeated |
| **A check in the mutant battery was itself random**, catching the `directional` mutant about half the time because belief ids come from `uuid4` | The mutant battery, on its own test |
| The MCP adapter's default constructs a *paid* provider, reached from an offline test | Writing the surface test |

The fifth is the one worth keeping. Experiment 4 found a `uuid4` tie-break in
production; here the same family was found in a *test*, by the battery built to
find it in production. A check that passes half the time is worse than one that
never passes — it goes green on the run that matters.

Battery contents: eight mutants
([`underdetermination_mutants.py`](../../../src/manyu/underdetermination_mutants.py)),
each a working mechanism, each caught by a named check, with every check verified
to pass on the real criterion and every check shown to be trippable by some
mutant. No mutant is documented as equivalent.

## 7. What is not done, and on what it is blocked

- **The base rate is unanswerable offline and always was.**
  `ScenarioJSONProvider` hardcodes `"contradicts": []`, so the offline path cannot
  produce a rival pair at all. Checked *before* the number was read, which is the
  one procedural improvement over experiment 4's voided Stage 0a.
- **The live edge-topology rate** — mutual versus one-way — decides how far §1's
  standoff generalises, and it is the single most consequential unmeasured
  quantity in this experiment.
- **Stage 5 in full:** base rate, the honesty-scored report, and the cosmology
  case where the model produces the rivals and we do not. Gated on a cost
  estimate and a variance pilot.
- Carried from experiment 3 §6 and still open: rotate the API key pasted into a
  chat transcript, and retry `/code-review ultra exp03-base` — the revision engine
  this experiment's collapse arm rests on has been verified by its author alone.
