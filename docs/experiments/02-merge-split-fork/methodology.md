# Experiment 2 — Merge/Split Architecture Fork: Methodology

**Status:** pinned 2026-08-05, before any experiment code was written.
**Requirements:** [requirements.md](requirements.md) · **Design:** [design.md](design.md)

This document answers *how the experiment is run and what we look at*. Every
constant here is pinned **before** the run that consumes it. Changing one after
its run has started voids that arm — the pre-registration rule from
requirements §14.

## 1. Constants

| Constant | Value | Consumed by | Justification, independent of any outcome |
|---|---|---|---|
| `recency_window_beliefs` | **8** | Merged mood window (design §3.1) | The codebase's existing "recent" convention is already a belief count — `list_beliefs(agent_id)[:6]` in `InnerVoiceComposer`, `supporting_voice_ids[-6:]` in `MoodEngine`. 8 sits just above both, with room for the D2 stream. **Not used by D3**, whose query reads the whole active store |
| `arousal_tau` | **2.5** | Merged arousal, `1 − exp(−Σstake/τ)` | At fixture-typical stake (`affective_salience` ≈ 0.5 × `confidence` ≈ 0.7 ≈ 0.35/belief): 1 belief → 0.13, 8 → 0.67, 20 → 0.94. Range across the entire operating region with no clipping at either end — gate #3 |
| `dissonance_tau` | **1.5** | Merged dissonance saturation | At high stake (0.8) and opposed valence (Δ ≈ 1.5), tension ≈ 1.0/pair: 1 pair → 0.49, 3 → 0.87. Top ladder rung stays below 0.95, so monotonicity is not tested against a saturated ceiling |
| `supports_max_depth` | **3** | Merged traversal | The transitive fixture (A→B, B→C, ¬C) needs depth 2. One level of headroom, no combinatorial blow-up |
| `theta` (θ) | **0.20** | D3 transfer threshold on `relative_magnitude` | "Fired" means ≥ 20% of the build's own reference magnitude. A correct mechanism scores exactly 0 on negatives, so θ's precise value matters only for near-misses that partially fire |
| `n_offline` | **1** | Stages 1–3 | Every offline path is deterministic under `FrozenClock`. Repetition would only re-measure the same arithmetic |
| `n_live` | **10** | Stage 4 only | #1 found n=3 underpowered and n=10 adequate at the same fixture scale. 3 conditions × 2 builds × 10 |
| `specificity_floor` | **0.9** | D3 §8.2 | Negatives are authored to be unambiguous; anything below 0.9 means the mechanism is firing on structure that is not there |

**Saturation check (gate #3), run before any metric is read:** assert the
observed values on the ladder's top rung are `< 0.95` and on its bottom rung
`> 0.0`. A metric pinned at either end is reporting τ, not the mechanism.

### 1.1 Two corrections made while building Stage 1

**The window is a belief count, not a turn count.** Originally written as
`recency_window_turns`. Beliefs carry no turn index, and under `FrozenClock`
every `updated_at` is identical, so a time-based window would be degenerate in
exactly the tests that need it sharp. `ManyuStore.list_beliefs` returns
newest-first by rowid and the existing convention is already a count. Renaming
it is not cosmetic: a constant whose name misdescribes what the code does is
the gap experiment 1 kept falling into.

**The arousal ramp is read inside the window only.** The gate was specified as
*k* = 1…20. Merged's window caps accumulation at 8, so merged is flat from
*k* = 8 upward — pinned by `test_merged_arousal_is_flat_beyond_the_window`.
That flatness is merged's *answer* to whether affect accumulates indefinitely
(it has no memory beyond the window), not an instrument defect, so it must not
be scored as a gate failure. **Revised gate: monotone for *k* = 1…8 on both
builds**, with behaviour beyond the window reported as a finding in its own
right.

## 2. The instrument gate

Every stage passes all seven before its numbers are readable. Implemented in
`tests/test_instrument_gate.py`; run-time versions in
`evals/analysis/exp02/gate.py`.

| # | Exp-1 failure it prevents | Check |
|---|---|---|
| 1 | Mock tuned to satisfy its own criteria | No offline stand-in defines success. §1 constants pinned before their run |
| 2 | Provider errors scored as dishonesty | `M-0` class; errors tagged, unscored, excluded; warn on concentration in one condition |
| 3 | Truncation constant read as a curve | Saturation check (§1) |
| 4 | Knob that was three sentences | IV-reality: assert the IV measurably changes the store — D2 uncertainty vs neutral, D3 stake vs magnitude |
| 5 | Mechanism that was a no-op | Assert each mechanism *can* change its output: dissonant store ≠ consistent store |
| 6 | `seed_mood` with blank substance | **Assert at the consumer.** Verify the influence vector where `FastAppraiser` reads it, never the `MoodState` summary |
| 7 | Spread that was log depth | Shape-matching written into analysis before data; `evidence_count` / `untrusted_count` per condition |

## 3. D3 protocol

### 3.1 Order of operations

1. Write **all** fixtures; record SHA-256 of each in `freeze.json`.
2. Write per-type predictions (§3.3). Timestamp them.
3. Build mechanisms against `contradiction_direct.json` **only**.
4. Freeze: SHA-256 of `dissonance.py`, git commit, UTC timestamp,
   `magnitude_ref` per build.
5. Run `StipulatedDissonanceQuery` on the held-out set. **If it passes, stop** —
   the held-out set does not discriminate and must be redesigned.
6. Run merged and split on held-out, negatives, and ladder.

Steps 1–2 before step 3 is the enforceable form of blinding when one person
does both.

### 3.2 The held-out set is weaker than it looks — a correction found while writing §3.3

Writing the predictions exposed a problem with the four held-out types as
specified. Merged's query ignores `belief_type` and `source_mix` by design, so:

| Type | Structurally distinct from `direct`? |
|---|---|
| transitive | **Yes** — requires `supports` traversal |
| ~~self-model~~ | **No — dropped.** See below |
| value conflict | **No** — two `NORMATIVE_STANCE` beliefs with a `contradicts` edge is `direct` with different metadata |
| source conflict | **No** — `direct` with a different `source_mix` |

**Self-model was dropped while authoring the fixtures.** In this schema a
`contradicts` edge always runs belief↔belief, so a `SELF_MODEL` belief
contradicted by logged behaviour is only representable by making the behaviour
a belief too — which is `direct` with a different `belief_type`. The
alternative, leaving the behaviour as evidence, gives no second node, and then
*neither* build can fire: a test both builds fail discriminates nothing.
Replaced by **`transitive_depth2`**, which needs two `supports` hops per side,
so a mechanism traversing exactly one level passes `transitive` and fails here.

Final held-out set: **2 discriminating** (`transitive`, `transitive_depth2`),
**2 sanity** (`value_conflict`, `source_conflict`).

**Rule adjusted before any run:** the ≥ 3 of 4 sensitivity bar stands, **and**
the build must fire on **≥ 1 of the 2 discriminating types**. The sanity types
cannot carry a pass on their own.

### 3.2.1 Transitive detection is carrier-level, not magnitude-level

A second finding from fixture authoring, and it changes what is measured.

A transitive fixture **necessarily contains an adjacent conflicting pair** —
`contradicts` is always between two beliefs, so the leaf conflict is always
directly visible. Any mechanism therefore fires on `transitive` by magnitude
alone, and `relative_magnitude > θ` cannot distinguish a graph query from an
adjacency scan.

What distinguishes them is *which carriers the signal contains*:

| Mechanism | Carriers on `transitive` |
|---|---|
| adjacency scan | one: the leaf pair, `path == []` |
| graph query | two: the leaf pair, **and the derived pair reachable only through `supports`, with `path != []`** |

**So the transfer test on discriminating types reads
`DissonanceCarrier.path`, not `magnitude`.** `expect_derived_carrier` and
`min_path_length` in the fixtures encode it. This is why `DissonanceCarrier`
carries `path` at all — design §1.2 specified the field before its purpose was
this clear, and it turns out to be the whole measurement.

### 3.3 Pre-registered per-type predictions (FR-D3.7)

Recorded 2026-08-05, before `dissonance.py` exists.

Scored on **derived carriers** for discriminating types (§3.2.1) and on
magnitude for the rest.

| Type | Merged | Split | Stipulated |
|---|---|---|---|
| direct (dev) | fire (ceiling) | fire (ceiling) | fire (ceiling) |
| transitive | **derived carrier found** — traversal is generic, 1 hop per side | **leaf pair only** — an appraisal rule scanning `contradicts` has no reason to traverse | leaf pair only |
| transitive_depth2 | **derived carrier found** — 2 hops per side, inside `supports_max_depth` 3 | **leaf pair only** | leaf pair only |
| value conflict | fire (sanity) | fire (sanity) | no fire |
| source conflict | fire (sanity) | fire (sanity) | no fire |
| distractor | no fire | no fire | no fire |
| near-miss | **no fire** — pairs have no edge; firing here means keying on valence difference alone | no fire | no fire |

**Predicted totals:** merged 4 of 4 with 2 discriminating; split 2 of 4 with 0
discriminating; stipulated 0 of 4 held-out, ceiling on direct.

**Stated risks, in order of likelihood:**

1. **Split's rule is a design choice we make, so its prediction is partly a
   prediction about our own hand.** Written to scan `contradicts` it fails both
   discriminating types; written to traverse it passes. The honest constraint is
   that split's rule must be the most natural thing to write *for an appraisal
   pathway that cannot see belief structure* — it receives appraisals, not the
   graph. If that argument ever feels strained, split's result stops being
   about the architecture and this is where to say so.
2. **`transitive_depth2` may fail merged on traversal cost rather than
   traversal logic** if closure computation is capped somewhere other than
   `supports_max_depth`. Check FR-D3.8 reachability before recording a failure.
3. Near-miss is where merged is most likely to *over*-fire, given its valence
   multiplier.

### 3.4 Negative case design

- **Distractor** — coherent store, no `contradicts` edges, low valence spread.
- **Near-miss** — pairs with **high `|Δvalence|` and no edge**: same predicate,
  opposite valence, differing in `scope` or time window.

Near-miss is the load-bearing negative. Merged's formula uses
`(1 + |Δvalence|)/2` as a *multiplier on pairs that already have an edge*; a
sloppier implementation iterating all pairs and keying on valence difference
alone would fire here. Distractors are easy to pass and prove little.

### 3.5 Normalisation

`relative_magnitude = magnitude / magnitude_ref`, where `magnitude_ref` is
that build's own magnitude on `contradiction_direct` at the high-stake variant,
measured at freeze time. Native magnitudes are never compared across builds;
only transfer counts, sensitivity, and specificity are.

## 4. D2 protocol

### 4.1 Staging

| Stage | Beliefs | Provider | Yields |
|---|---|---|---|
| 3 (mechanism) | authored candidates | none | **Plumbing verification. Not a result** |
| 4 (verdict) | live `BeliefExtractor` | yes | M-class classification — the only D2 finding |

Stage 3 results are labelled in `results.md` as plumbing. Merged's numbers
there are our authorship of belief valences; see design §6.1.

### 4.2 Blocking gates before Stage 4

1. Instrument gate (§2) green.
2. **Arousal ramp** — *k* identical low-salience uncertainty beliefs,
   **k = 1…8** (see §1.1), arousal monotone increasing in *k* on **both**
   builds. Split's arousal is a `max` over influence dims and does not
   accumulate within a turn; if it is flat, D2 is measuring a formula choice
   and the formula is fixed first. Merged's half is already green
   (`test_merged_arousal_accumulates_with_belief_count`); split's is the open
   half and is checked in Stage 3.
3. **`FastAppraiser` coverage** — the uncertainty events produce a non-zero
   emotion delta in split without encoding a threat, via the `TOOL_RESULT`
   route (design §6.2), pinned by
   `test_tool_result_yields_fear_without_negative_goal_impact`.
4. **Capability precheck** — reachability / resolution / floor per
   [`capability.py`](../../../src/manyu/capability.py). Two of #1's four
   fixtures sat at ceiling; a pilot confirms both builds move before *n* is
   committed.
5. Cost estimate recorded.

### 4.3 Analysis

- Effect size is **within-build Cohen's *d*** of uncertainty against that
  build's own neutral condition, bootstrap CI.
- ***d* is always the shape-matched figure** (design §7.7), and shape keys are
  **per build, derived from each metric's causal path, declared before the
  run** (`fork.D2_SHAPE_KEYS`):
  - merged → `(window_belief_count, authored_in_window)`
  - split → `(n_events,)`

  Not `evidence_count`. Merged reads the belief window and split reads
  `event_type` deltas; neither channel is a function of evidence count, and
  gating on it refused all three conditions spuriously (51/54/58) while the
  windows were identical. **Admissibility rule, to stop this becoming "pick
  whichever key passes": a key counts only if the measured channel is a
  function of it.** Choosing keys after seeing which pass is gate #1.
- **The measured channel per build** — merged: `max(0, -valence)` over the
  window; split: `AffectState.emotions["fear"]`. Merged's *arousal* is not
  used: it is `1 − exp(−Σstake/τ)`, valence-blind by construction, and spans
  only 0.06 across all three conditions. See results §10.
- **Clock advances `INTER_EVENT_SECONDS` (60s) between events.** A `FrozenClock`
  with no advance switches decay off entirely and flatters split's
  accumulation by removing the only thing opposing it. 60s against `fear`'s
  900s half-life gives a per-step factor of 0.955.
- Drop-one robustness runs as part of analysis, not after it.
- `seed_mood` control arm (NFR-3) runs in the same session.

### 4.4 Amendment, 2026-08-09: the inner voice is off in Stage 4

Recorded before the Stage 4 arm started, per the requirements §14
pre-registration rule. No §1 constant changes, so no completed arm is voided.

`process_reflective_turn` composes an inner voice on every turn. In Stage 3
there was no provider, so the call was a no-op. In Stage 4 it would be a second
paid call per event — 1,200 extra calls across the arm — and it is the only LLM
in split's mood path.

**Both builds run with `core.inner_voice.provider = None`.** Two reasons, and
the second is the one that matters:

1. Neither measured channel reads it. Merged's is `max(0, -valence)` over the
   belief window; split's is `AffectState.emotions["fear"]`, written by
   `FastAppraiser` from `event_type` deltas. Leaving the voice on would double
   the spend to move a quantity the analysis never consults.
2. **It removes NFR-3's confound by construction rather than controlling for
   it.** NFR-3 was written because split's mood flows through an LLM-composed
   frame while merged's is a deterministic query, so a between-build difference
   could be the LLM. With the voice off and the extractor on, both builds make
   exactly one provider call per turn, of the same kind, and the belief path
   they share is the only place an LLM enters. The `seed_mood` control arm
   stays available behind `--seed-mood` and is **not** run by default; it is
   now a robustness check on a confound that has been designed out, not a
   precondition. If it is skipped, `results.md` must say so rather than let
   NFR-3 read as satisfied by an arm nobody ran.

Stage 3 also ran without an inner voice, so this keeps the only difference
between the two stages the one the staging exists to introduce: where beliefs
come from.

### 4.5 Pre-flight finding, 2026-08-09: valence is required but never asked for

Found by reading, before any call — the check experiment 3's retrospective §3.1
put on the standing list.

Merged's entire channel is belief `valence`. `BeliefExtractor._schema()` does
expose a numeric `valence` field, and `_strict_schema` marks every property
required, so the model cannot silently omit it — the failure mode that made
`supports` unreachable for the whole of experiment 3 is **not** present here,
and `test_the_extractor_can_emit_the_fields_merged_reads` pins that.

But the extractor's *prompt* never mentions valence. It asks for propositions,
keys, and edges. So the field is reachable and unelicited: the model must emit
a number and is told nothing about what it means.

**Decision: change nothing, and make the pilot answer it.** Adding valence
guidance to the prompt is an instrument change made on a hunch, and any wording
that hints uncertainty is unwelcome would be choosing merged's answer — gate #1
in the plainest form. The pilot (`--mode pilot`, 6 runs, 120 calls) exists to
confirm both builds move before *n* is committed; if merged's window comes back
uniformly at valence 0, the flat result is a fact about elicitation and **must
not be reported as M-a**, which is a loss condition. Treat it as the pilot
failing gate #4 and fix the elicitation before spending the full arm.

### 4.6 Amendment, 2026-08-09: M-c is a property test, not a type test

**Written after the pilot and before the scored run.** No scored run has
happened, so no arm is voided — but the ordering is the whole point and is
stated here so a reader can check it against the git history rather than take
it on trust. This is the amendment most likely to look like moving the
goalposts, and the strict reading is retained precisely so it can be checked.

**What the pilot showed.** Requirements §8.1 defines M-c as affect "carried by
an `UNCERTAINTY`-type belief about the aggregate epistemic situation". On the
object-less stream the live extractor produced exactly that belief and gave it
a different type tag:

> *"Tool outcomes that return no rows with no error signal are ambiguous
> without explicit scope documentation"* — `epistemic_principle`, valence −0.15
>
> *"When a database query returns no rows without error, the absence of results
> may reflect an unspecified scope"* — `world_model`, valence −0.05

Nothing in the extractor's prompt mentions the `uncertainty` type, and nothing
requires the model to reach for it. Deciding D2 on which of seven enum values
the extractor happened to pick would be experiment 1's gate #3 in a new place:
a tag read as a finding.

**The amended rule.** A carrier is M-c when all three hold:

1. it names no threat term absent from the run's own event stream (unchanged —
   this is what keeps M-b separate, and what stops the `control` condition's
   real threat being misread as a fabrication);
2. it **generalises beyond any single occurrence** — its proposition makes no
   indexed reference such as "Check 19" or "Query 3". A belief about Check 19
   is a belief about Check 19; a belief about what an empty result set means is
   a belief about the epistemic situation;
3. its provenance resolves to real evidence records from the run.

Belief type is now recorded as evidence rather than used as the gate.

**Guardrails.** Criterion 2 is mechanical (`INSTANCE_REF_RE`) and every
carrier's proposition is dumped into the record, so a wrong call is visible and
correctable without a re-run. `classify_merged_strict` computes the original
type-gated class on every run and `results.md` must report both columns; if the
two disagree, the disagreement is a finding about the extractor's typing and
must be written up as one rather than buried.

**What would have been wrong.** Widening M-c to "any negative-valence carrier"
would have made merged win by definition. The generalisation criterion can
fail, and does: the `control` condition's carriers name specific checks, and
under this rule those are not M-c.

### 4.7 Defect, 2026-08-09: the `0.5 x split` clause was unsatisfiable

Also found in the pilot, and a defect rather than an amendment — the rule as
written could not be satisfied by any merged result, which is not what §8.1
intended.

**Split's D2 channel is deterministic.** `AffectState.emotions["fear"]` is
written by `FastAppraiser` from `event_type` deltas and never reads a belief,
and with the inner voice off (§4.4) there is no mood to vary it either. The
pilot returned `0.560827` on the uncertainty stream under the offline scenario
provider *and* under live Haiku — identical to six decimal places, from two
different providers. Split's arm has no variance to sample.

Zero pooled SD with differing means makes Cohen's *d* infinite, so §8.1's
"merged wins if its *d* ≥ 0.5 × split's *d*" evaluates to `merged_d >= inf`,
which is false for every possible merged result. Merged could not have won
whatever it did — the same shape as experiment 3's `ContradictionArm`, a branch
that was consulted and could only answer one way.

**Fix:** when split's *d* is undefined the ratio clause is marked
`inapplicable` and the remaining conditions — M-c dominant, positive control
passing, merged's own bootstrap CI excluding zero — carry the decision. The
clause is never silently treated as failed, and any verdict reached this way
carries `ratio_clause: "inapplicable"` in the record so no reader mistakes it
for a rule that was applied and passed. Pinned by
`test_an_infinite_split_d_does_not_make_the_rule_unsatisfiable`, with a second
test confirming the waiver does not extend to the other conditions.

**This is also a D2 finding in its own right** and belongs in `results.md`
regardless of the verdict: split's affect on this discriminator is invariant to
whether a carrier arises, because the architecture gives it no path to read
one. It is the asymmetry D2 was built to expose, visible before the scored run.

## 5. What voids a run

- Any §1 constant changed after that arm started.
- Code changed between D3 freeze and held-out run (hash mismatch; the harness
  refuses).
- A held-out fixture inspected or run during mechanism development.
- Positive control failing while the main condition is reported as a null.
- Provider-error exclusions concentrated in one condition without the warning
  being acted on.

A voided arm is restarted and recorded as voided in `results.md`. #1's v4
published two threshold effects that were failed API calls; the cost of
restarting is much lower than the cost of retracting.
