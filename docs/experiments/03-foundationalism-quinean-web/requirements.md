# Experiment 3 — Foundationalism vs. the Quinean Web: Requirements

**Status:** spec (Stage 0 complete, Stage 1 in progress)
**Backlog entry:** [../../experiments_backlog.md](../../experiments_backlog.md)
**Related:** [crux #3](../../Manyu_experiments_crux.md) · [experiment 2](../02-merge-split-fork/requirements.md) · [ADR-002 merged substrate](../../adr-002-merged-substrate.md)
**Stage 0 record:** [stage0-extractor-feasibility.md](stage0-extractor-feasibility.md)

## 1. Purpose

When Manyu retracts a belief that other beliefs rest on, does the structure
above it **collapse** (foundationalism) or **flex** (Quine)?

The dispute is sixty years old and has never been settled empirically, because
you cannot see inside a mind to watch revision propagate. Manyu's beliefs
carry provenance, confidence, and — since experiment 2 — entailment edges. The
propagation is therefore observable.

**Deliverable:** a working revision engine, plus the first dissonance signal
that arises from a real contradiction rather than an authored one. Experiments
4, 5, 7 and 8 all consume it.

## 2. The question is currently unaskable

`BeliefUpdater._revise` sets

```python
confidence = _clamp(max(belief.confidence, blended))
```

**Confidence can only rise.** Disconfirming evidence moves it by exactly zero.
`contradicts` flips `status` to `CONTESTED` and leaves the number untouched,
so Manyu can hold a contested belief at 0.9.

A web whose nodes cannot weaken cannot ripple. Until the ratchet goes, both
hypotheses predict the same thing (nothing moves), so the experiment cannot
discriminate. Removing it is Stage 1's first job.

Second gap: `supports` edges are recorded and **carry nothing**. `update`
accumulates them, `dissonance.py` walks them, but no confidence change has
ever crossed one.

## 3. Scope

### In scope

- Removing the ratchet; confidence responds to disconfirming evidence.
- **Propagation across `supports`** — the mechanism under test.
- Two arms of the open design question (§5), both run offline.
- Chain vs. net topologies, with negatives.
- The natural dissonance read via experiment 2's `dissonance.py`.

### Out of scope (deferred)

- Any change to how beliefs are *extracted* beyond Stage 0's fix.
- Belief deletion. Retraction here means confidence collapse, not removal —
  provenance must survive, which is the point of the substrate.
- The honesty read on revision self-reports (Stage 4; needs a provider).
- Multi-agent propagation (experiment 9).

## 4. Staging — LLM only at the end

The hypothesis concerns propagation dynamics, which are arithmetic and graph
traversal. The model's only role is producing the graph. So the experiment is
mostly free to run, and the expensive stage confirms rather than discovers.

| Stage | LLM | n | Establishes |
|---|---|---|---|
| 0 — feasibility | ~15 CLI calls | — | **Done.** Webs have `supports` structure; 46% edge loss found and fixed |
| 1 — engine | none | 1 | Ratchet removed; propagation implemented; both arms behind a flag |
| 2 — discrimination | none | 1 | Chain vs. net, held-out topologies, negatives |
| 3 — natural dissonance | none | 1 | Retraction produces an unstaged dissonance signal |
| 4 — live confirmation | yes | 10 | Naturalistic webs ripple as characterised; honesty read |

Stages 1–3 are deterministic under `FrozenClock`, so `n=1` is correct —
repetition re-measures the same arithmetic ([experiment 2 methodology
§1](../02-merge-split-fork/methodology.md)).

**What may be authored, and what may not.** Topology and starting confidences
are the independent variable; authoring them is manipulation, not rigging. The
dependent variable — the confidence trajectory after retraction — is computed
by the update rule and must never pass back through anything typed into a
fixture. Experiment 2's D2 failed this test (merged's measured channel read
authored valences) and its Stage 3 results were labelled plumbing. The check
before any fixture is admitted: *does the DV pass back through anything I
typed?*

## 5. The open design question (both arms built, neither assumed)

> Should a contradiction lower confidence **directly**, or only through the
> **evidence** that carries it?

This is the foundationalism/Quine fork rendered in code, so it is decided with
evidence, not chosen.

- **Arm `direct`** — a `contradicts` edge applies a confidence penalty of its
  own, scaled by the contradicting belief's confidence.
- **Arm `evidential`** — `contradicts` changes status only. Confidence moves
  when the *evidence* under a belief is undermined, and propagates from there.

Both run against identical fixtures. Neither is the default; the flag has no
default value and the harness refuses a run that does not name an arm.

### 5.1 Decided: `DIRECT` (2026-08-06)

Scored against two standards neither arm was allowed to set.

**Standard 1 — round-trip coherence.** Assert a contradiction, then retract
the contradictor; the web must return to where it started. Not a preference:
a system whose final state depends on events it has since undone is
incoherent, and it means retracting a false accusation never restores the
accused belief. **Both arms pass**, but only after the defect in §5.2 was
fixed. Verified at partial retraction too, so the two formulas are not merely
coinciding at one endpoint.

**Standard 2 — representability.** §2 named "Manyu can hold a contested
belief at 0.9" as a *defect*, before either arm existed. So: after a
well-evidenced contradiction, can any consumer reading `confidence`
distinguish a disputed belief from an identical undisputed one?

- `DIRECT` — yes. The disputed belief sits below its twin.
- `EVIDENTIAL` — **no.** Both sit at exactly 0.8; the dispute exists only as a
  status flag. And because `stake_of` multiplies by confidence, a belief
  facing five evidence records against it carries the same stake as one facing
  none, so the dispute cannot reach any affect consumer either.

`EVIDENTIAL` reproduces the exact defect this experiment was chartered to fix.
**`DIRECT` is adopted.** `EVIDENTIAL` is retained as a labelled arm, since
Stage 2's chain and net results are identical under both and the ablation
shows those results do not depend on the choice.

**What this does not settle.** `DIRECT` is adopted because `EVIDENTIAL` fails
a pre-existing standard, not because a contradiction penalty was shown to be
the *right* magnitude. ~~`contradiction_penalty = 0.3` is unjustified by
anything measured.~~ **Resolved in §12 — the constant was removed.**

### 5.2 The defect this decision surfaced

`DIRECT` had relief without suppression. `contradiction_penalty` appeared
only in the relief path, so retracting a contradictor *credited* a belief for
a cost it had never paid: a target seeded at 0.8, contradicted and then
un-contradicted, finished at **0.92**. Confidence manufactured from nothing.

Two things were wrong beneath it:

1. **No suppression existed.** `BeliefUpdater` records a `contradicts` edge
   and sets `CONTESTED` without touching confidence, and that is the path
   every extractor-produced and fixture-seeded contradiction takes. Added
   `RevisionEngine.assert_contradiction`, and a guard so relief may only undo
   a suppression that was actually applied — an unpriced contradiction is now
   inert and audited rather than silently generative.
2. **Relief ran in both directions.** Suppression is directional (`Q`
   contradicts `P` charges `P`), but relief treated conflict as symmetric, so
   weakening the *suppressed* belief paid its suppressor. Now mirrored
   exactly.

Both were found by writing the round-trip standard down before reading any
verdict.

## 6. Functional requirements

**FR-1 — Confidence is bidirectional.** `_revise` blends toward the candidate
rather than ratcheting. Entrenchment damps movement but never blocks it: the
inertia coefficient is capped strictly below 1.0, so no belief is
unfalsifiable at any stability.

**FR-2 — Propagation crosses `supports`.** A confidence change on X propagates
to every belief X supports, attenuated per hop, to a pinned maximum depth.
Direction: `A.supports == [B]` means A lends support to B, so weakening A
weakens B.

**FR-3 — Propagation is recorded.** Every propagated change writes a
`BeliefRevision` naming the originating belief and the hop count. A ripple
nobody can audit is not a result.

**FR-4 — Cycles terminate.** The graph is not guaranteed acyclic. Traversal
visits each belief at most once per retraction.

**FR-5 — Shape is measurable.** The harness reports, per retraction: which
beliefs moved, by how much, at what depth, and in what order — the footprint
that distinguishes a collapse from a ripple.

**FR-6 — Arms are selectable and neither is default.** See §5.

**FR-7 — Support is fractional.** A belief with three supporters loses less
when one is retracted than a belief with one supporter loses when its sole
supporter goes. This is the core discriminator: a chain and a net differ
precisely in how much of a node's grounding any single edge carries.

## 7. Pre-registered predictions

Recorded **before `revision.py` exists**, 2026-08-06.

| Topology | Foundationalist prediction | Quinean prediction | What we expect |
|---|---|---|---|
| Deep chain (A→B→C→D) | Retracting A drives B, C, D to near-zero; depth barely attenuates | Each hop attenuates; D moves little | **Quinean** — attenuation is in the rule |
| Dense net (3 supporters per node) | Retracting one supporter still collapses | Node absorbs it; moves ~⅓ of the chain case | **Quinean** |
| Net vs chain, same retraction | No difference | Net moves strictly less | **Net moves less** |
| Isolated belief, no path | No movement | No movement | **No movement** (negative) |
| Near-miss: related wording, no edge | No movement | No movement | **No movement** (negative) |

**The honest risk:** these predictions are partly predictions about our own
hand, since we write the propagation rule. FR-7 is where that bites hardest —
fractional support is what makes the net differ from the chain, and we chose
it. The constraint is that the rule must be the most natural thing to write
for *a graph of weighted evidential support*, not the thing that makes the net
win. If that argument comes to feel strained, this is where to say so, and the
result stops being about epistemology and starts being about our arithmetic.

**What would falsify the Quinean reading:** a rule with fractional support and
per-hop attenuation that nevertheless collapses the net as hard as the chain,
because a single retraction cascades through enough of the web to reach every
node by some path. That is a real possibility in a densely connected store and
it is the outcome worth watching for.

## 8. Success criteria

- **SC-1** — Confidence falls under disconfirming evidence. Pinned by test.
- **SC-2** — A retraction at the root of a chain moves a depth-3 dependent by
  a non-zero but strictly smaller amount than a depth-1 dependent.
- **SC-3** — Same retraction magnitude moves a net node strictly less than a
  chain node (FR-7).
- **SC-4** — Both negatives (§7) show exactly zero movement. A propagation
  mechanism that fires on unconnected beliefs is keying on similarity.
- **SC-5** — A retraction produces a non-zero `dissonance.py` signal on a web
  nobody authored a valence into.
- **SC-6** — Every propagated change is reconstructible from the revision
  trail alone.

## 9. Carried-over method

From experiments 1 and 2, as standing practice:

- Every discriminator ships a positive control in the same run. A null without
  a passing control is a bug, not a finding.
- Drop-one robustness runs inside analysis, not after it. Two of experiment
  1's v4 correlations collapsed under it.
- Constants are pinned before the run that consumes them; changing one after
  voids that arm.
- Run experiment 2's [`gate.py`](../../../src/manyu/gate.py) rather than
  rediscovering its seven failure modes.
- **New, from Stage 0:** before trusting any structural measurement, check
  that the structure survives the write path. Stage 0's 46% edge loss was
  invisible in the extractor output and invisible in the store — it appeared
  only when the two were compared.

## 10. Open questions for the design phase

1. Should propagation be depth-limited or magnitude-limited (stop below
   epsilon)? Magnitude-limited is more principled; depth is easier to reason
   about. Possibly both.
2. Does a `contradicts` edge propagate at all, or only `supports`?
3. Should `status` transitions (ACTIVE → CONTESTED → …) be driven by
   confidence thresholds, or stay independent as today?
4. Stage 0 §4.3: the flat negative control is licensed by the extractor prompt
   to produce the generalisation it is controlling for. Redesign before Stage
   2 negatives carry weight.
5. ~~Whether attenuation should be capped below 0.5.~~ **Resolved — the
   constant was removed instead.** See §11.

## 11. Decision: decay is derived, not chosen (2026-08-06)

The first Stage 1 build had a free `attenuation` constant at 0.6. It was
removed, and the reason is not tuning.

**In a chain every node has exactly one supporter, so `support_share` is 1.0
and the constant is the only thing producing decay.** At 1.0 a chain
transmits a retraction undiminished to depth 3 — foundationalist collapse.
Below 1.0 it grades. In the topology where the two hypotheses most sharply
disagree, the constant *is* the hypothesis, and a graded result would have
been the constant reported back.

`DecayMode.PROVENANCE` replaces it. A belief is grounded by its own evidence
*and* its supporters, both already in the store, so retracting one supporter
removes `1/(supporters + evidence)` of the grounding. SC-2 and SC-3 both hold
with no constant consulted — pinned by
`test_decay_needs_no_constant_under_provenance_mode`, which runs the same
fixture at attenuation 0.1, 0.6 and 1.0 and asserts identical deltas.
`DecayMode.FIXED` survives as a labelled ablation.

Conservation now falls out rather than being pinned: a chain sums to 0.70
against a 0.8 retraction, where the old constant gave 0.94.

### 11.1 The finding this exposed, and it is larger than the constant

**Mandatory provenance forecloses foundationalism by construction.**

`BeliefUpdater._rejection_reason` refuses any candidate with empty
`evidence_ids` (`INSUFFICIENT_PROVENANCE`). Every belief therefore holds at
least one evidence record of its own, so under the provenance rule
`support_share` can never exceed `1/(1+1)` and **no belief can ever collapse
entirely when a supporter is retracted.** A purely derivative belief — the
foundationalist's load-bearing case — is not merely absent from our fixtures;
it is unrepresentable in this substrate.

This materially qualifies §7's predictions. A graded ripple is not, on its
own, evidence for Quine over foundationalism, because the architecture cannot
produce the alternative. The honest form of the result is narrower:

> Given a substrate that requires every belief to carry independent
> provenance, revision necessarily ripples rather than collapses. The
> epistemology follows from the provenance requirement, not from the
> propagation rule.

That is a real result and arguably a more interesting one, but it must not be
written up as though the experiment discovered a graded ripple empirically.
Pinned by `test_mandatory_provenance_forecloses_full_collapse`, so that if the
provenance rule is ever relaxed, this conclusion is known to depend on it.

**Follow-up for Stage 2:** run an arm with the provenance requirement lifted,
so the foundationalist limb becomes representable and the comparison is
between two reachable outcomes rather than one.

## 12. Decision: contradiction pricing is derived too (2026-08-06)

§5 adopted `DIRECT` while its strength was a constant — `contradiction_penalty
= 0.3`, unjustified by anything measured. That left a free parameter at the
centre of a decision, which is exactly what §11 removed from decay.

`ContradictionPricing.PROVENANCE` replaces it. A contradictor is one more
voice in the target's epistemic field, competing with the grounds the target
already holds:

```
share = 1 / (supporters + own evidence + contradictors)
```

scaled at the call site by the contradictor's own confidence, so a tentative
objection lands more softly than a confident one. Every term is read off the
store. `ContradictionPricing.FIXED` survives as a labelled ablation.

### 12.1 The property that justifies it

`resistance_to_a_lone_objection` holds two beliefs facing the identical
objection, differing only in evidence count:

| target | grounding | share | drop |
|---|---|---|---|
| thin | 1 evidence | 1/2 | 0.400 |
| thick | 5 evidence | 1/6 | 0.133 |

**A fixed penalty cannot represent this at any value**, because a constant
cannot see the target's grounding — pinned by
`test_the_fixed_ablation_cannot_tell_them_apart`, which shows the ablation
moving both identically. Corroboration is resistance, not immunity: the
well-grounded belief still moves.

All contradictors sit in the denominator, so a second objection dilutes the
first rather than stacking. Otherwise *n* objections would drive any belief to
zero regardless of grounding, which is a majority vote rather than an
epistemology.

### 12.2 What changed, and what did not

The §5 verdict is unaffected: `EVIDENTIAL` still leaves a disputed belief
numerically identical to its undisputed twin, which is what disqualified it.
Levels moved — the disputed belief now lands at 0.35 rather than 0.53 — and
§3.1's finding survives intact, including the identical **Δ 0.220** raw
tension drop under both arms that makes the masking argument.

Round-trip coherence still holds, and its test now asserts the *proportion*
refunded rather than a computed number, so the invariant survives any future
change to how the penalty is priced.

## 13. Decision: the engine gets a surface (2026-08-06)

`RevisionEngine` was imported by nothing outside its own module. No `retract`
or `assert_contradiction` in `ManyuCore`, the CLI, or the MCP tools — so the
deliverable experiments #5, #7 and #8 are meant to consume could only be
driven from this experiment's own tests, and Stage 4 could not have run at
all. Experiment 1 hit the same thing when `manyu_run_probe` turned out to be
missing from the MCP surface entirely.

Added: `ManyuCore.retract_belief` / `assert_contradiction`, `manyu
retract-belief` / `assert-contradiction`, and `manyu_retract_belief` /
`manyu_assert_contradiction`.

Three properties the surface enforces:

- **`arm` is required and has no default** at every layer, including
  `choices=` on the CLI. A silent default would settle §5 by whichever branch
  a caller happened not to think about.
- **Errors are returned, not raised.** Unknown belief, missing argument, and
  an upward `to_confidence` all come back as `{"status": "error"}`.
- **The full per-step footprint is serialised** (FR-5), because a collapse and
  a ripple are told apart by which beliefs moved and at what remove, not by a
  total. `total_movement` is included but is not conserved under the `fixed`
  decay ablation and must not be read as a headline.

Pinned by `test_cli_revision_commands_drive_the_engine`, which prices a
contradiction in one CLI invocation and asserts the *next process* sees the
suppressed value — otherwise the CLI would only be pretending to expose the
engine.

## 14. Ingest prices contradictions (2026-08-06)

**The Stage 4 blocker, and it would have invalidated the run silently.**

`BeliefUpdater` recorded a declared `contradicts` edge and marked the
*declaring* belief CONTESTED. The belief actually being contradicted was left
untouched in every channel:

```
deploy-bad   conf=0.8  status=contested  contradicts=1
deploy-ok    conf=0.8  status=active     contradicts=0
```

So a live web carried no trace that anything was disputed — not confidence,
not status, not the graph. Under the adopted `direct` arm a Stage 4 run would
have read as a flat null **that looked like a finding**. This is experiment
1's v2 failure exactly (mood `null`, the knob with nothing to bite on, a flat
line that survived a full pilot).

`ManyuCore.update_beliefs` now routes every newly declared contradiction
through `RevisionEngine.assert_contradiction`, so ingest and the explicit
surface share one pricing path and one ledger. Idempotent, so re-running a
batch cannot compound the penalty. `ManyuCore(contradiction_arm=...)` selects
the arm, defaulting to §5.1's decision, so the `EVIDENTIAL` ablation runs
through the same pipeline.

Fixtures are unaffected: `fork.seed_beliefs` writes edges straight to the
store, deliberately bypassing the updater so experiment 2 can vary `status`
and `contradicts` independently.

## 15. The foreclosure ablation (2026-08-06)

§11.1 established that mandatory provenance makes foundationalist collapse
unrepresentable, which qualifies the headline: a graded ripple is not evidence
for Quine when the alternative cannot occur. That left the central claim
resting on an untested counterfactual — *if* collapse were representable, the
engine would produce it.

`RevisionConfig.ignore_own_evidence` lifts the requirement **for propagation
arithmetic only**; the write path still refuses a belief without provenance.
Same engine, same fixture, same retraction:

| regime | depth 1 | depth 2 | depth 3 | shape |
|---|---|---|---|---|
| grounded (default) | 0.4 | 0.2 | 0.1 | attenuates — Quinean |
| provenance lifted | 0.8 | 0.8 | 0.8 | undiminished — foundationalist |

The counterfactual holds: collapse appears the moment beliefs stop carrying
independent grounding. That licenses the narrow claim — **the ripple follows
from the provenance requirement, not from the propagation rule** — because had
the rule been doing the work, lifting provenance would not have changed the
shape.

Partial grounding sits between the two, so the architecture represents the
space *between* the classical positions rather than picking one.
