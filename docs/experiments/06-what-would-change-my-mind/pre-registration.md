# Experiment 6 — Pre-registration (stages −1 through 2)

**Written:** 2026-08-11
**State at writing:** No mechanism exists. `src/manyu/counterfactual.py` has not
been created, no pricer has been written, no enumeration rule has been fixed, and
no new fixture has been authored. Stage −1 has not been run.
**Requirements:** [requirements.md](requirements.md) §10 · **Methodology:** [methodology.md](methodology.md) · **Covers:** stages −1,
0, 1, 2 and 2b. Stages 3 and 4 are registered when reached and before they run.

Why this file exists: choosing a threshold after seeing the distribution is
experiment 1's failure mode #1 — the mock whose own comment said its output was
tuned to sit just below the ceiling — and `assert_constants_pinned` exists to
catch it. Experiments 3 §7, 4 §10 and 5 all carried this discipline.

**Changing any number below after the run it governs voids that arm.** Amending
is allowed; amending silently is not. Every amendment is appended to §7 with a
date and a reason.

---

## 0. Not a prediction — a re-derivation performed by hand

Experiment 5 results §3.1 publishes the only dose figure in the project: the
underdetermination meta-belief on `symmetric_rivals` under accumulating
separating evidence.

| separating records | 1 | 2 | 3 | 4 | **5** | 6 |
|---|---|---|---|---|---|---|
| published confidence | 0.847 | 0.694 | 0.571 | 0.476 | **0.404** | 0.348 |

That trajectory is reproduced here by hand from the substrate's own constants,
**before any pricer exists**, to fix the model the rest of this file predicts
from. Each step is `blend_confidence`: `x' = x·i + c·(1 − i)`, where
`i = 0.5 + 0.4·stability` ([revision.py:174](../../../src/manyu/revision.py)),
`stability` rises 0.05 per revision carrying new evidence
([services.py:871](../../../src/manyu/services.py)), and `c` is the meta-belief's
recomputed confidence — the Jaccard overlap `|shared| / |union|`, which falls as
separating records accumulate.

| k | overlap `c` | stability | `i` | predicted | published |
|---|---|---|---|---|---|
| 1 | 2/3 = 0.6667 | 0.10 | 0.54 | 0.8467 | 0.847 |
| 2 | 2/4 = 0.5000 | 0.15 | 0.56 | 0.6942 | 0.694 |
| 3 | 2/5 = 0.4000 | 0.20 | 0.58 | 0.5706 | 0.571 |
| 4 | 2/6 = 0.3333 | 0.25 | 0.60 | 0.4757 | 0.476 |
| 5 | 2/7 = 0.2857 | 0.30 | 0.62 | 0.4035 | 0.404 |
| 6 | 2/8 = 0.2500 | 0.35 | 0.64 | 0.3482 | 0.348 |

Six of six, maximum absolute error 0.0005. The model is the substrate's
arithmetic and nothing else — no term was added to make it fit.

`|shared| = 2` was **read off**
[`symmetric_rivals.json`](../../../evals/fixtures/exp05/symmetric_rivals.json)
(`obs_redshift`, `obs_isotropy` on both rivals), not inferred from the published
overlap.

**One quantity here was inferred rather than read: the starting stability of
0.10.** It was solved for from the k=1 step, not observed in the store. Stage −1
must read it off `symmetric_rivals` directly. If it is not 0.10, this table is
wrong, every number in §4 below is wrong, and that is a defect report about the
model rather than a reason to refit — refitting after the fact is precisely what
this file exists to prevent.

## 1. Stage −1 — what the substrate forces

### 1.1 Enumeration triviality (requirements §6, risk one)

**Prediction: enumeration is *not* trivially complete, but only just.** The
degenerate rule ("any disconfirming record you do not already hold") applies to
every belief; a *structural* enumeration applies only to beliefs carrying rivals
or supporters.

**The number fixed in advance:** if fewer than **1 in 4** beliefs across the
existing webs in `evals/` carry either a `contradicts` edge or a `supports` edge,
structural enumeration is a **fixture-only** capability and the headline says so.

Recorded because experiment 4's Stage 0a produced a base rate of zero that read
exactly like a finding and described the instrument instead, and experiment 5
§13's strictness risk is the same shape. This number is what stops the reading
being negotiated afterwards.

### 1.2 Price is content-blind (requirements §6, risk two)

**Prediction: two hypothetical records with identical confidence and identical
edges are priced identically, to 0.000, however differently their prose bears on
the proposition.**

This is a prediction that the mechanism has a limit, not that it works, and it is
expected to pass. It is registered because if it *fails* — if two records with
the same confidence price differently — something is reading content that
`blend_confidence` cannot see, and that is a defect, not a feature.

Consequence accepted in advance: "specific evidence" in the crux's framing means
specific in its *edges*, not in what it says. The results must state this in the
headline rather than in a caveat.

### 1.3 The re-derivation

**Prediction: the pricer reproduces §0's six values to within 0.001 absolute**,
and reads a starting stability of exactly 0.10 off `symmetric_rivals`.

A pricer that cannot re-derive the only published dose figure in the project, by
a different code path from the one that produced it, is wrong. This is the gate
on everything downstream.

## 2. Stage 0 — enumeration against structural ground truth

Ground truth is `separating_evidence`'s definition — a record entering exactly
one rival's `evidence_ids` — written before this experiment existed and for
another purpose (requirements §7).

**Prediction: exact set agreement on `symmetric_rivals`.** Precision 1.00 and
recall 1.00 against the structural target, not a threshold-graded score. A
graded score here would be a way of passing while wrong.

**Negative controls, both required in the same run:**

- `irrelevant_evidence`: priced at **≤ 0.01** absolute movement, and observed at
  **≤ 0.01** when delivered. Both halves, because a prediction of zero that is
  never checked against a delivery is the `MergedDissonanceQuery` shape.
- `already_held`: priced at **exactly 0.000**, matching the `new_evidence` guard
  ([services.py:851](../../../src/manyu/services.py)). Not "approximately" — the
  substrate returns the belief untouched, so any nonzero price is a defect
  (FR-9).

**The stage ends the experiment** if the enumerator cannot beat the degenerate
rule on any fixture — an enumerator that returns "everything" has precision equal
to the base rate and is not an enumerator.

## 3. Stage 1 — calibration

**The direct path is a regression test and is reported as one.** Predicted equals
observed to within **1e-9**, because both call `blend_confidence` with the same
arguments (requirements §5.1). Reporting this agreement as calibration would be
the mock-tuned-to-its-own-criterion failure in a new costume, and it is
pre-committed here as bookkeeping so it cannot be promoted later.

**The extractor path is the experiment.** Predicted Δ versus observed Δ, where
the hypothetical record is delivered through ingest rather than injected.

**Prediction: the extractor path diverges, and the divergence is dominated by
edge topology rather than by the pricing arithmetic.** Specifically, mispredicted
cases are expected to concentrate in records where the extractor emitted a
one-way `contradicts` edge where the pricer assumed a mutual one, or emitted no
edge at all.

**The number fixed in advance:** the pricer is **calibrated** if the median
absolute error on the extractor path is **≤ 0.05**, and **uncalibrated** if it
exceeds **0.15**. Between the two it is reported as neither rather than rounded
into one — experiment 1's v4 correlations collapsed under drop-one precisely
because a marginal reading was reported as an effect.

**An uncalibrated result does not end the experiment if the errors are
attributable.** If every large error carries a recorded topology mismatch
(FR-7's arm stamp), the finding is "the pricer is exact and the extractor is the
uncertainty", which is a stronger claim than calibration. If the errors are
*unattributable*, stage 1 ends it.

## 4. Stage 2 — dose, and the headline prediction

### 4.1 The prediction that inverts experiment 5's headline

Experiment 5 results §2 established that its criterion cannot see evidence
volume, because a ratio cancels cardinality: `near_miss` carries three times the
evidence of `symmetric_rivals` and lands at the **identical** confidence, a delta
of exactly 0.000.

**Prediction: the dose does not cancel cardinality, and `near_miss` is roughly
twice as hard to move.**

The marginal record changes the overlap by `|shared|/(|shared| + k)`, which is a
function of `|shared|` — so volume, invisible to detection, dominates the dose.
Computed from §0's model, with the shared counts **read off the fixtures** rather
than inferred: `symmetric_rivals` carries 2 records on both rivals, `near_miss`
carries the same 2 plus `obs_magnitude_scatter`, `obs_calibration`,
`obs_survey_depth` and `obs_dust`, for 6.

| k | `symmetric_rivals` | `near_miss` |
|---|---|---|
| 1 | 0.847 | 0.934 |
| 2 | 0.694 | 0.853 |
| 3 | 0.571 | 0.775 |
| 4 | 0.476 | 0.705 |
| **5** | **0.404** ← crosses | 0.644 |
| 6 | 0.348 | 0.592 |
| 8 | — | 0.510 |
| **10** | — | **0.448** ← crosses |

**Registered:** `symmetric_rivals` crosses the 0.45 expression threshold at
**k = 5**; `near_miss` crosses at **k = 10**, and in no case earlier than
**k = 8**. The direction — `near_miss` strictly larger — is the load-bearing part
and is registered separately from the exact integers, because it survives a wrong
starting stability where the integers do not (§0).

> If this holds, experiment 5's headline and this one are two halves of one
> statement: **the evidence you have does not tell you which reading is right,
> and the more of it you have, the more it takes to find out.**

### 4.2 The threshold, and what it does and does not mean

**Fixed here: "changed my mind" is confidence falling below 0.45.** That is
`BeliefUpdater._create`'s `TENTATIVE` line and therefore the line at which
`WorldviewSynthesizer` stops composing a belief created below it (experiment 5
§5.1).

**And it is registered together with its own limitation**, so the limitation
cannot be discovered as a caveat later: status is never recomputed from
confidence, so a belief that falls below 0.45 having been *created* above it goes
on being composed. The dose therefore measures **when the number crosses**, not
when Manyu stops saying it. Any claim of the second kind requires the synthesizer
read, and stage 2 does not take one.

### 4.3 The entrenchment census

**Prediction: dose rises monotonically with stability**, across every belief in
the census, with no exceptions. A single belief whose dose falls as stability
rises is an impossible value and is treated as a defect report, not as variance
(requirements §15).

**The `entrenched` fixture is the positive control** in the same run: the same
proposition and the same disconfirmer at high versus low stability must give a
strictly larger dose at high. A census without it would be a distribution with
nothing establishing that the mechanism can move.

## 4.4 Stage 2b — dose under corroboration, and a phase transition

Requirements §14.5 added this arm so that "a dose computed against a static
belief is an underestimate by an unmeasured amount" becomes a number rather than
a caveat. Working the arithmetic out in advance turned it into the sharpest
prediction in this file.

For the underdetermination meta-belief the candidate confidence *is* the Jaccard
overlap. A **separating** record enters one rival's evidence and raises the union
alone; a **shared** record enters both and raises numerator and denominator
together. So with `r` separating records arriving per shared record, the overlap
converges to

> `c → 1/(1 + r)`

and since `blend_confidence` converges to its candidate, the meta-belief's
confidence converges there too. **Whether the state is falsifiable at all is
therefore decided by the arrival ratio**, against the 0.45 threshold registered
in §4.2:

> `r* = (1 − t)/t = 0.55/0.45 = 11/9 ≈ 1.222`

**Registered predictions:**

1. **At `r = 1` — one confirming record per disconfirming record — the dose is
   infinite.** Confidence converges to exactly 0.500 and never crosses 0.45. This
   is an analytic limit, not a run that got tired: `1/(1+1) = 0.5 > 0.45`.
2. **The critical ratio is `11/9`**, and it is a function of the registered
   threshold and nothing else. No free constant enters (FR-8).
3. **The dose diverges as `r` approaches `r*` from above**, on these values,
   against pure separating evidence (`r = ∞`) at k = 5:

| `r` | 1.0 | 1.2 | **1.222** | 1.25 | 1.3 | 1.5 | 2.0 | 3.0 | ∞ |
|---|---|---|---|---|---|---|---|---|---|
| asymptote | 0.500 | 0.455 | **0.450** | 0.444 | 0.435 | 0.400 | 0.333 | 0.250 | 0 |
| records to cross | never | never | **never** | 223 | 88 | 38 | 18 | 11 | 5 |

**Scope, stated before the run so it cannot be quietly widened.** This holds for
the underdetermination meta-belief, where the candidate confidence is computed
from the store. For an *ordinary* belief the candidate confidence is carried by
the record, so the limit is a weighted mean of the arriving confidences and the
transition is at a different place. Stage 2b measures the meta-belief case; the
ordinary case is recorded as unmeasured rather than assumed to follow.

**Why this matters more than the ratio it was chartered to produce.** Experiment
5 results §3.1 left two readings open — belief inertia working as designed, or a
state surviving its own disconfirmation at 0.847 being unfalsifiable in practice
— and said one record could not settle which. This does settle it, in a
qualified form: **below `r*` the state is unfalsifiable in principle and not
merely slow**, and the ratio at which real evidence arrives is not something the
substrate controls.

If prediction 1 fails — if the state crosses at `r = 1` — the convergence
argument is wrong, and that is a defect report about §0's model rather than a
finding about corroboration.

## 5. What would make this experiment uninteresting

Recorded in advance so it cannot be argued away later. Any of these means the
result is reported as small rather than inflated:

- **The pricer only ever agrees with itself** — §3's direct path passes, the
  extractor path is never run or is unattributably noisy, and nothing was
  predicted that could have been wrong.
- **Structural enumeration is fixture-only** (§1.1 below 1 in 4), so "what would
  change my mind" reduces to the degenerate rule for most real beliefs.
- **The dose is uniformly enormous.** Every belief needs tens of records, the
  engine emits honest lists of things that would work in principle and never do,
  and the finding is about `blend_confidence`'s inertia rather than about
  counterfactual reasoning. **This is requirements §3.1 and it is a legitimate
  outcome** — but it is a result about the substrate, and it must be reported at
  that altitude and not dressed as a capability.
- **The enumeration is stored and read by nothing** — `MergedDissonanceQuery`
  before experiment 4 §6, `RevisionEngine` before experiment 3 §13.

## 6. Fixed constants

| Constant | Value | Where it binds |
|---|---|---|
| Structural-enumeration base rate | 1 in 4 beliefs | Stage −1 |
| Re-derivation tolerance | 0.001 absolute | Stage −1 |
| Starting stability (to be *verified*, not assumed) | 0.10 | Stage −1, §0 |
| Enumeration precision / recall | 1.00 / 1.00 | Stage 0 |
| Irrelevant-evidence tolerance | 0.01, predicted **and** observed | Stage 0 |
| Already-held price | exactly 0.000 | Stage 0 |
| Direct-path agreement | 1e-6 (amended from 1e-9, §7 A1) | Stage 1 |
| Calibrated / uncalibrated bands | ≤ 0.05 / ≥ 0.15 median absolute error | Stage 1 |
| Expression threshold | 0.45 | Stage 2 |
| `symmetric_rivals` dose | k = 5 | Stage 2 |
| `near_miss` dose | k = 10, and never earlier than 8 | Stage 2 |
| Critical arrival ratio | `r* = 11/9 ≈ 1.222` | Stage 2b |
| Dose at `r = 1` | infinite (converges to 0.500) | Stage 2b |

**The dose formula itself contains no constant** and none is registered for it —
it is read off current confidence, current stability, and the candidate's
confidence (requirements §5.2, FR-8). `inertia_base`, `inertia_span` and the
+0.05 stability step are experiment 3's constants, inherited and **not re-tuned
here**; if the dose result is unflattering, that is the finding (§5).

## 7. Amendments

### A1 — 2026-08-11: direct-path agreement 1e-9 → 1e-6

**What changed.** §3 registered the direct path as agreeing "to within **1e-9**".
That tolerance is amended to **1e-6**.

**Why.** It was unreachable by construction, and would have been at any value
below ~5e-7. `BeliefUpdater._revise` stores `round(confidence, 6)`
([services.py:880](../../../src/manyu/services.py)), so an observation read back
from the store is quantised to six decimal places while the analytic prediction
is not. The maximum possible disagreement from rounding alone is 5e-7, and the
observed errors across all twelve stage-1 rows fall between 0.0 and 4.8e-7 —
entirely inside that band, with no residual.

**What it does not change.** The claim §3 makes is unaffected: the direct path
agrees by construction and is reported as a regression test, never as
calibration. This amendment corrects a number that described the arithmetic
rather than the substrate, and it makes the check *stricter* in the only sense
that matters — 1e-6 is now a bound the store can actually violate, where 1e-9
could only ever have failed.

**Registered before the amended check was read as a result**, and the
pre-amendment numbers are preserved in
[`stages.jsonl`](../../../evals/analysis/exp06/stages.jsonl) as `abs_error` on
every row, so the correction is auditable rather than asserted.
