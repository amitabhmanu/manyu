# Experiment 3 — Results

**Stages complete:** 0 (feasibility), 1 (engine), 2 (discrimination),
3 (dissonance coupling, re-run under both arms)
**All offline.** No provider is constructed in any Stage 1–3 test; `n=1` under
`FrozenClock`, per requirements §4.

## 1. Headline

**Revision ripples rather than collapses — but the architecture could not have
produced the alternative, and that is the actual finding.**

Retracting a supported belief propagates outward with graded attenuation, and
the dissonance signal eases as it does. Neither behaviour needed a tuning
constant: both fall out of provenance the store already holds.

The qualification is load-bearing and is stated first deliberately. Manyu's
belief core refuses any candidate without evidence of its own
(`INSUFFICIENT_PROVENANCE`), so every belief has independent grounding, no
belief can rest *entirely* on another, and full foundationalist collapse is
unrepresentable. A graded ripple is therefore not evidence for Quine over
foundationalism — the alternative was never available. Details in
requirements §11.1.

The defensible claim:

> Given a substrate that requires every belief to carry independent
> provenance, revision necessarily ripples rather than collapses. The
> epistemology follows from the provenance requirement, not from the
> propagation rule.

## 2. Stage 1 — the engine

[`revision.py`](../../../src/manyu/revision.py), 18 offline tests.

### 2.1 The ratchet is gone

`_revise` took `max(belief.confidence, blended)`. Disconfirming evidence moved
a belief by exactly zero, so both hypotheses predicted "nothing moves" and the
experiment could not discriminate. Confidence now blends bidirectionally,
damped by stability with inertia capped strictly below 1.0.

**Removing it broke no test.** 430 passed before and after — the entire
disconfirming direction was uncovered. That gap is now SC-1.

The backlog's proposed `inertia = 0.5 + 0.5 * stability` was not adopted: it
reaches 1.0 at full stability, reintroducing the ratchet under another name at
precisely the belief the experiment cares most about.

### 2.2 Propagation

| | depth 1 | depth 2 | depth 3 | total |
|---|---|---|---|---|
| Chain, 0.8 retraction | 0.400 | 0.200 | 0.100 | 0.700 |

Non-zero at depth 3 (the ripple reaches) and strictly decreasing (it decays) —
SC-2. Aggregate stays below the shock without anything being pinned to make it
so.

### 2.3 Decay is derived, not chosen

The first build had `attenuation = 0.6`. It was removed because **in a chain
every node has one supporter, so the constant was the only source of decay** —
which makes it the hypothesis rather than a parameter (requirements §11).

Under `DecayMode.PROVENANCE`, share is `1/(supporters + own evidence)`. Both
success criteria hold with the constant never consulted:

- **SC-2** chain: 0.4 / 0.2 / 0.1, identical at attenuation 0.1, 0.6 and 1.0.
- **SC-3** net absorbs what chain transmits: a target with three supporters
  moves 0.200; the same target with one moves 0.400.
- Own evidence shields: a belief corroborated five times moves less than one
  corroborated once, from the same retraction.

`DecayMode.FIXED` remains as a labelled ablation, so Stage 2 can show the
result does not depend on a free parameter by running the arm that has one.

## 2.4 Stage 2 — discrimination on held-out fixtures

13 tests over five JSON topologies in `evals/fixtures/exp03/`, every
discriminating and negative case run under **both** contradiction arms.

### The instrument gate caught the thing it exists to catch

`ContradictionArm` was **inert**. The engine stored the arm, stamped it onto
`PropagationResult`, and consulted it in no branch — `DIRECT` and
`EVIDENTIAL` produced byte-identical output. Only the enum and the
no-default constructor existed, and the constructor made it worse by implying
a choice was being made. This is experiment 1's `affect_influence` and
experiment 2's gate #5 over again.

It was found by `test_gate_the_arms_are_not_the_same_mechanism`, written
before the arm comparison was read. The first implementation *also* failed
that gate: relief only consulted the retraction target's own `contradicts`,
so nothing fired whenever the contradiction sat on a belief reached by
propagation — which is the common case. Two no-ops, one gate.

**Anything reported previously about "both arms" was about one arm run
twice.**

### Results

| Fixture | Result |
|---|---|
| `chain_deep` | SC-2 holds on held-out structure: 0.400 / 0.200 / 0.100, aggregate 0.700 < 0.8 |
| `net_dense` vs `chain_shallow` | SC-3 holds: matched fixtures differing only in supporter count |
| `negative_near_miss` | **Zero movement.** Same topic, near-identical wording, matching valence, no edges |
| `contradiction_pair` | The arms diverge — see below |
| all | The arms agree exactly wherever no contradiction exists |

`negative_near_miss` is the load-bearing one. A rule keying on similarity,
shared topic, or valence proximity rather than on the declared graph passes
every positive above and fails here.

### The arm comparison — requirements §5

- **`DIRECT`:** a contradiction is priced. Weakening the contradictor refunds
  exactly the fraction of the penalty it no longer justifies.
- **`EVIDENTIAL`:** a contradiction is bookkeeping. Nothing was charged, so
  nothing is refunded.

Relief is one hop and **directional**, mirroring suppression exactly: support
is transitive, "the enemy of my enemy" is not a relation worth asserting.

**Decided: `DIRECT`** — see §2.5.

### 2.5 Deciding requirements §5, and the defect it surfaced

Scored against two standards neither arm was allowed to set.

**Round-trip coherence.** Assert a contradiction, retract the contradictor,
and the web must return to where it started — otherwise retracting a false
accusation never restores the accused belief. Both arms pass now; `DIRECT`
did not before the fix below. Verified at partial retraction too.

**Representability.** Requirements §2 named "a contested belief held at 0.9"
as a defect before either arm existed. After a well-evidenced contradiction:

| | disputed belief | identical undisputed twin |
|---|---|---|
| `DIRECT` | 0.35 | 0.80 |
| `EVIDENTIAL` | **0.80** | 0.80 |

`EVIDENTIAL` reproduces the exact defect the experiment was chartered to fix.
Because `stake_of` multiplies by confidence, the dispute cannot reach any
affect consumer either. **`DIRECT` adopted.**

**The defect this surfaced.** `DIRECT` had relief without suppression:
`contradiction_penalty` appeared only in the relief path, so retracting a
contradictor credited a belief for a cost it never paid. Measured: a target
seeded at 0.8, contradicted and un-contradicted, finished at **0.92**.
Confidence from nothing. And relief ran symmetrically while suppression was
directional, so weakening a *suppressed* belief paid its suppressor.

Both were found by writing the round-trip standard down before reading any
verdict — and both had been reported here as working behaviour beforehand.

**Adopted on a failure, not a success.** `DIRECT` wins because `EVIDENTIAL`
fails a pre-existing standard, not because any particular penalty was shown
correct. The constant that carried it has since been removed — see §2.6.

### 2.6 Contradiction pricing is derived too (requirements §12)

§5 was decided while `DIRECT`'s strength was a constant. That constant is now
gone: a contradictor's weight is `1/(supporters + own evidence +
contradictors)`, scaled by its own confidence. The property that justifies it,
on two beliefs facing the identical objection:

| target | grounding | share | drop |
|---|---|---|---|
| thin | 1 evidence | 1/2 | 0.400 |
| thick | 5 evidence | 1/6 | 0.133 |

**A fixed penalty cannot represent this at any value** — the ablation moves
both identically, which is pinned as a test rather than asserted. All
contradictors sit in the denominator, so a second objection dilutes the first
instead of stacking; otherwise enough objections would flatten any belief
regardless of grounding, which is a vote rather than an epistemology.

The §5 verdict is unchanged. Levels moved (the disputed belief now lands at
0.35, not 0.53) and §3.1's identical **Δ 0.220** raw drop survives intact.

### 2.7 The engine now has a surface (requirements §13)

`RevisionEngine` was imported by nothing outside its own module — no `retract`
in `ManyuCore`, the CLI, or the MCP tools. The deliverable experiments #5, #7
and #8 are meant to consume could only be driven from this experiment's own
tests, and **Stage 4 could not have run at all.**

`retract_belief` and `assert_contradiction` now exist at all three layers,
with `arm` required and undefaulted everywhere, errors returned rather than
raised, and the full per-step footprint serialised. Verified across process
boundaries: a contradiction priced in one CLI invocation is visible to the
next.

### What this is not

The engine existed before these fixtures were written, so this is not
experiment 2's blinding (fixtures first, hash, build against dev only,
freeze, run held-out). Genuinely held out: `negative_near_miss` and the whole
arm comparison, neither exercised by any earlier test. The chain and net
results are re-confirmations on cleaner structure, not independent evidence.

## 3. Stage 3 — dissonance is coupled to revision

6 offline tests. `stake_of` is `mean(evidence salience) * confidence`, and
confidence is what the engine moves — so a retraction reaches the dissonance
signal through a pathway nobody authored.

- A contested web registers dissonance (positive control).
- **Retracting a supporter reduces it**, and does not zero it: the
  contradiction is still there, so easing is not resolving.
- Retracting an unrelated belief leaves it unchanged (negative control) —
  without this, any mechanism recomputing a global number would pass.
- A depth-2 retraction moves the signal less than a depth-1 one, so
  attenuation survives the hand-off to the affect layer.
- **Valences are byte-identical before and after.**

That last check is the one that keeps this from repeating experiment 2's D2
failure, where the measured channel read authored valences and the numbers
were downgraded to plumbing. Here `_tension` still reads authored valence, but
every assertion is on a *change* across a retraction, and valence provably
does not move.

**Claimed narrowly:** the contradiction is still an authored `contradicts`
edge and the valences are still authored. This is not "dissonance arose
spontaneously". It is that dissonance is dynamically coupled to revision —
the property experiment 4 needs before it can ask whether the signal
*controls* anything.

### 3.1 Re-run under both arms — saturation, not mechanism

Stage 3 originally ran only `EVIDENTIAL`, which at the time was the only
behaviour that existed. Every test now runs under both arms and every result
holds.

Measured on the contested web, retracting the supporter:

| arm | raw tension | saturated magnitude |
|---|---|---|
| `EVIDENTIAL` | 0.440 → 0.220 (**Δ 0.220**) | 0.254 → 0.136 (Δ 0.118) |
| `DIRECT` | 0.293 → 0.073 (**Δ 0.220**) | 0.178 → 0.048 (Δ 0.130) |

**The mechanism is masked.** The propagation delta depends on the shock and
the support share, never on the contested belief's starting confidence, and
`min(stake_a, stake_b)` reads that belief either way. So the raw tension drop
is *identical* under both arms even though one has charged for the dispute
and the other has not.

**Saturation un-masks it, for a reason unrelated to the mechanism.**
`magnitude` is concave in raw tension, so the same raw drop taken from
`DIRECT`'s lower baseline sits on a steeper part of the curve and reads as a
larger observable change.

**The warning for experiment 4:** a magnitude delta confounds *how much
tension changed* with *where on the saturation curve the web was sitting*.
Read as a measure of belief dynamics it will attribute to the mechanism what
is actually curve position — experiment 1's gate #3, a truncation constant
read as a curve, in a new place.

*An earlier version of this section claimed the two arms were
indistinguishable through this channel. That was an artifact: the fixture
priced its contradiction under a hardcoded arm, so `DIRECT` was never
suppressing.*

## 3.2 Adversarial audit (2026-08-06)

Four defects had been found by writing standards down, and none by the test
suite — so the suite was treated as unreliable and the engine probed directly
against paths no test covered. **Four more turned up, in code the suite passed
green on.**

| Defect | Observed | Fix |
|---|---|---|
| Asserting a contradiction twice charged twice | 0.80 → 0.56 → **0.32** | Idempotent via the revision-trail ledger |
| Refunds were unbounded | A contradictor that weakened, recovered, weakened again refunded twice: a belief charged 0.24 finished at **0.92**, above its pre-contradiction 0.80 | Refund priced against the balance |
| Refunds were also *lossy* | When the `seen` guard skipped a weakening, that portion was lost for good — a fully retracted contradictor left its target permanently suppressed | Price against the contradictor's **current** confidence, not per-increment |
| `_propagate` used `abs(shock)` | Every change weakened downstream *regardless of direction*: raising a supporter 0.4 → 0.9 pushed its target 0.80 → **0.55** | Signed propagation; `retract` rejects an upward move |

The third is the one that matters most, because **round-trip coherence is the
standard §5 was decided on**. A topology where it silently failed would have
undercut the decision itself, and no test covered it.

Clean on re-audit: cycles terminate, a diamond charges its shared node once,
the arms agree exactly on pure-support topologies, a missing belief raises
rather than passing silently, and a ceiling belief round-trips. The
`services.py` write path passed all eleven probes (duplicate-key collapse,
self-edges, type-guarded keys, rejection, ordering, batch idempotency,
bidirectional blend end-to-end).

Every number published in this file and in requirements was then re-derived
from a running store: **26 checks, 0 mismatches.**

### What the pattern says

All eight defects are the same shape — *a quantity that looked right and meant
something else*. It is the family experiment 1's audit kept turning up, and
the tests did not catch a single one, because each test was written by the
same person who had just written the mechanism and shared its assumptions.
What did work: writing an independent standard down first (round-trip
coherence, gate #5), and probing adversarially for paths no test covers.

**Standing method for Stage 4:** no result is read until the mechanism has
been probed against inputs its author did not have in mind.

## 3.3 Stage 4 pre-flight (2026-08-06)

The earlier audit probed hand-built fixtures. This one probes the paths a
**live** run exercises: extractor-shaped candidate batches, ingest pricing,
and both arms through the real surface. **Two more defects**, both in code the
suite passed green on, and both found only because mutual contradiction was
tried at all.

| Defect | Observed | Fix |
|---|---|---|
| Mutual contradictions priced sequentially | A→B charged first weakened B, so B→A landed softer: the pair settled at **0.6 / 0.4**, with the split decided by extractor emission order | Batch priced against a snapshot taken before any charge |
| A refund could undo an explicit retraction | Retracting both halves left a belief driven to 0.0 sitting back at **0.4**, and the end state differed by order (`x=0.0,y=0.4` vs `y=0.2,x=0.0`) | Relief withheld from a target retracted since the assertion |

The second **broke round-trip coherence — the standard §5 was decided on** —
in a topology nobody had run. That is now the third time a defect has been
found by testing the criterion the decision rests on, rather than by the
tests written alongside the mechanism.

Clean on the remaining seven probes: dangling contradictions survive ingest,
ingest and explicit assertion do not stack, the public round trip restores its
target, a depth-2 chain propagates end to end, both arms are drivable through
live ingest, the foreclosure ablation is off by default, repeated retraction
keeps confidence in range, and an empty batch is a clean no-op.

## 4. What is not established

- **No blinding.** The engine predated the Stage 2 fixtures (§2.4). Only
  `negative_near_miss` and the arm comparison are genuinely held out.
- **No independent review.** Ten defects across this stage, none caught by the
  test suite, and every fix verified by the person who wrote it. The numbers
  check out; they check out against an engine with one author.
- **Entailment grades are not blind** (Stage 0 §6.1). Every edge is dumped
  with both propositions so the judgement is re-checkable, but it was the
  author's.
- **One entailed run in four produced no structure at all**, collapsing three
  observations into a single belief. Stage 4's *n* must be large enough that a
  null run reads as a null run.
- **The API provider path is still unverified.** Stage 0 confirmed the
  extractor on the CLI only; `supports` was added to the schema and the API
  has never been asked to honour it.
- **The foundationalist limb is unreachable** (§1). Until an arm runs with the
  provenance requirement lifted, the comparison has one available outcome.
- **No live web has been revised.** Stage 4 is untouched, and the Stage 0
  caveats stand: one provider, and a negative control the extractor prompt
  licenses to produce the thing it controls for.
- **Entailment quality was never graded.** Stage 0's edges were structurally
  plausible and correctly directed, but nobody scored whether each is a
  genuine entailment.
