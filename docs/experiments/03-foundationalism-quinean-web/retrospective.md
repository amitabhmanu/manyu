# Experiment 3 — Foundationalism vs. the Quinean Web: Retrospective

**Status:** closed 2026-08-09
**Requirements:** [requirements.md](requirements.md) · **Methodology:** [methodology.md](methodology.md) · **Results:** [results.md](results.md) · **Stage 0:** [stage0-extractor-feasibility.md](stage0-extractor-feasibility.md)
**Backlog:** [../../experiments_backlog.md](../../experiments_backlog.md)

Written once at the close, as the record of where expectation and outcome
parted. Proposed edits to the crux and to downstream experiments are named
here; the edits themselves land separately.

## 1. The headline, and why it is not the one we set out for

The question was whether retracting a supported belief collapses a
foundational chain or ripples through a coherent net. **In Manyu it ripples —
but that follows from a design decision made long before this experiment, not
from anything the experiment discovered.**

`BeliefUpdater._rejection_reason` refuses any candidate without evidence of
its own. So no belief rests *entirely* on another, `support_share` can never
exceed `1/(1+1)`, and total collapse is unrepresentable. The
`ignore_own_evidence` ablation confirms the counterfactual: lift that rule and
collapse appears immediately, undiminished down a chain, from the same engine
on the same fixture.

The defensible claim is therefore sharper than picking a side:

> Whether a belief collapses or sags is settled by how it is grounded. A
> belief holding evidence of its own bends; one resting purely on another
> falls with it. Manyu's substrate guarantees the first case.

**This is a better result than "Quine wins."** It converts an unfalsifiable
dispute into a structural property you can read off a store. But it must not
be written up as an empirical discovery about revision — the alternative was
never available to observe, and §11.1 says so.

**Proposed crux edit:** #3 currently reads "settle a 60-year epistemology
dispute by observing which architecture behaves sensibly under stress." That
overstates what any single architecture can settle. Suggested replacement:
*determine what property of a belief decides whether revision collapses or
propagates, and show the substrate that fixes it.*

## 2. What shipped

- **[`revision.py`](../../../src/manyu/revision.py)** — the revision engine.
  Bidirectional confidence (the ratchet is gone), propagation across
  `supports`, both contradiction arms, three labelled ablations
  (`DecayMode.FIXED`, `ContradictionPricing.FIXED`, `ignore_own_evidence`).
- **No free constants in either mechanism.** Decay and contradiction strength
  are both `1/(supporters + own evidence [+ contradictors])`, read off the
  store. Constant-based versions were built first and demoted to ablations,
  each pinned by a test showing the ablation *fail*.
- **Requirements §5 decided: `DIRECT`.** Contradictions cost confidence.
  `EVIDENTIAL` left a disputed belief numerically identical to an undisputed
  twin — the exact defect §2 named before either arm existed.
- **A surface** — `ManyuCore.retract_belief` / `assert_contradiction`, CLI, and
  MCP. The engine was previously importable from nothing outside its own
  module.
- **Ingest prices contradictions**, so a live web carries a trace of dispute.
- **Stage 4 live confirmation**: all seven predictions pass, five of them
  blind.
- **56 offline tests** across five files, plus fixtures in `evals/fixtures/exp03/`.

## 3. Findings that revise the plan

### 3.1 The test suite caught none of sixteen defects

This is the most transferable thing here, and it deserves to outlive the
experiment.

| How it was found | Count |
|---|---|
| Writing a standard down *before* reading a verdict | 4 |
| Adversarial probing of paths no test covered | 4 |
| Stage 4 pre-flight on live-shaped inputs | 2 |
| Reading the diff | 4 |
| Noticing an impossible number in output | 2 |
| **The test suite** | **0** |

The cause is structural, not carelessness: each test was written minutes after
the mechanism it covers, by the same author, sharing its assumptions. Such a
test agrees with the code *precisely where the code is wrong*.

Every defect was the same shape — **a quantity that looked right and meant
something else.** The family experiment 1's audit kept surfacing.

**Standing method for experiments 4 onward:**

1. Write the criterion a decision rests on before running anything that could
   settle it. Three defects surfaced this way, including one that broke the
   very standard §5 was decided on.
2. Probe inputs the author did not have in mind. Self-reference, mutual
   relations, repeated application, zero-valued operands.
3. Treat an impossible value as a defect report. `share = 1.0` cannot occur
   under mandatory provenance; chasing that rather than reporting seven
   passing predictions is the only reason a foundationalist result was not
   published as a Quinean one.
4. Assert that a mechanism *can* change its output before reading what it
   says. `ContradictionArm` was stored, stamped onto results, and consulted by
   no branch — everything reported "under both arms" was one arm run twice.

### 3.2 Offline validation does not transfer across providers

Stage 0's negative control was clean on the Claude Code CLI — 0 edges over 16
beliefs — and **failed immediately on the API**, which is markedly more
generative (7 beliefs where the CLI gave 4). It found a real entailment the
fixture had accidentally supplied.

Worse, the replacement fixture *also* produced edges. A generative extractor
abstracts from anything; **edge presence is not a specific signal at any
sample size.** What does discriminate is *shared* structure — which is also
what the propagation claim depends on.

**For later experiments:** a specificity result established on one provider is
provisional until re-run on the provider that will carry the finding. Budget a
pilot for it.

### 3.3 The dissonance channel is confounded by saturation

Retracting a supporter eases dissonance, so the signal is coupled to revision
— experiment 4's precondition holds. But the coupling is not clean:

- `_tension` takes `min(stake_a, stake_b)`, so it reads the *weaker* party and
  is blind to changes above that floor. Raw tension moved identically under
  both contradiction arms.
- `magnitude` is concave in raw tension, so the same raw change reads larger
  from a lower baseline.

**A magnitude delta therefore confounds "how much tension changed" with "where
on the saturation curve the web was sitting."** Experiment 4 must not treat it
as a general-purpose read on belief dynamics — that is experiment 1's gate #3,
a truncation constant read as a curve, in a new place.

### 3.4 Live webs are shallower than the fixtures assumed

Depth-2 propagation occurred in 7 of 20 structured runs. It happens; it is not
typical. Experiments 5, 7 and 8 build on this engine and should expect
one-hop webs as the common case, with deeper structure as something to elicit
rather than assume.

Also measured: about 1 extraction in 10 over-merges into a single belief with
no edges. Any *n* must absorb that.

### 3.5 Two schema-level gaps closed in passing

`supports` was absent from the extractor schema entirely — the field existed
and was unreachable, so no live web could ever have had an entailment edge.
And edges are emitted as `belief_key`s, since the extractor sees only evidence
and cannot know a belief id. Both were found by reading, before any call.

Related: **46% of correctly-identified edges were being destroyed** by
single-pass resolution, because every edge the extractor emits names a sibling
in the same batch. Fixed; 118 emitted / 0 unresolved at Stage 4 scale.

## 4. What this leaves for the experiments downstream

- **#4 (dissonance as control signal)** — precondition met, with §3.3's
  warning attached. Read carriers and raw tension, not saturated magnitude.
- **#5, #7, #8** — the revision engine they consume now exists *and is
  reachable*, which it was not until the surface landed.
- **Anything reasoning about belief structure** inherits §1: mandatory
  provenance is doing epistemological work, and `ignore_own_evidence` is the
  switch that makes the alternative representable.

## 5. What "done" would require from here

- **An independent review.** The cloud review failed and was never re-run.
  Every fix in this experiment was verified by its author, and the one review
  that did happen — my own, of my own diff — still found four defects in code
  already audited twice.
- **A second model or provider**, given §3.2.
- **Blinding.** Stage 2's fixtures were written after the engine existed. Only
  `negative_near_miss` and the arm comparison were genuinely held out.
- **P3′ and P5′ re-run blind.** Both were set with pilot numbers visible and
  are confirmatory only.

## 6. Concrete next actions, ordered

1. Retry `/code-review ultra exp03-base`; work through whatever it finds.
2. **Rotate the API key** used for Stage 4 — it was pasted into a chat
   transcript.
3. Apply the §1 crux edit.
4. Open experiment #4 against §3.3's constraint, not against `magnitude`.
