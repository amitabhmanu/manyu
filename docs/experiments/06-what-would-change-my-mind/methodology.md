# Experiment 6 — "What Would Change My Mind": Methodology

**Requirements:** [requirements.md](requirements.md) · **Pre-registration:** [pre-registration.md](pre-registration.md) · **Results:** not yet written

How the experiment is run and what is looked at. The mechanism itself will be
documented in `src/manyu/counterfactual.py`; this file changes when the
*procedure* changes, not when the code does.

## 1. Running the offline stages

Everything in stages −1 through 3 is deterministic under `FrozenClock` and makes
no provider call. `n=1` is correct for all of it — repetition re-measures the same
arithmetic (experiment 2 methodology §1).

The order is a dependency order, and each step gates the next.

```bash
python -m pytest tests/test_counterfactual_substrate.py -v
```

```bash
python evals/analysis/exp06/run_stage_minus1.py
```

```bash
python evals/analysis/exp06/run_stages.py
```

```bash
python -m pytest tests/ -q
```

**Stage −1 is a gate, not a formality**, and it is a harder gate here than in
experiment 5. It has to reproduce experiment 5 results §3.1's published
trajectory from a different code path (pre-registration §0, §1.3). A pricer that
cannot re-derive the only published dose figure in the project is wrong, and
every number in stages 0 through 2b is computed by it. Nothing proceeds until it
passes.

It also settles §14.7's first open question — whether
`HypotheticalEvidence.salience` reaches `stake_of` — which costs nothing to check
there and would be expensive to discover in stage 2.

## 2. Reading the artifacts

| File | Holds |
|---|---|
| `evals/analysis/exp06/stage_minus1.jsonl` | The re-derivation against experiment 5's six published values, the starting stability read off the store, the structural-enumeration shape census over existing webs, the content-blindness pair, and a `verdict` row |
| `evals/analysis/exp06/stages.jsonl` | Enumeration precision/recall and both negative controls (stage 0); predicted-versus-observed per record on both paths with a topology stamp (stage 1); the dose per belief and the entrenchment census (stage 2); the corroboration ratio (stage 2b); the receipts read (stage 3); and a `verdict` row per stage |
| `evals/analysis/exp06/freeze.json` | sha256 per fixture, per criterion test, plus the pre-registration and mechanism digests |

**Verdict rows are computed by the runner and recomputed by the test suite.**
`tests/test_exp06_rederivation.py` re-derives every published figure from the
JSONL and recomputes every headline claim rather than reading it, on experiment
5's pattern — so a number cannot drift from its evidence without something going
red. It carries a positive control proving the derivability check can fail;
experiment 5 found that such checks acquire exemption lists and quietly stop
working.

**One artifact is unusual and is called out here so it is not mistaken for
duplication.** Stage 1 records *two* numbers per hypothetical record — the
analytic price and the replayed observation — plus the arm stamp that says which
path was taken. The pair is the datum. A row carrying only one of them is a
dropped sample, not a zero (FR-2).

## 3. What may be authored, and what may not

Carried from experiment 3 §4, experiment 4 §8 and experiment 5 §3, and it binds
differently here because the dependent variable is a *prediction*.

A fixture may author **which beliefs exist, what evidence they hold, how that
evidence is shared, which of them conflict, and how entrenched they are**.
Authoring those is manipulation, not rigging — they are the independent variable.

A fixture may **not** author what would change Manyu's mind, nor any expected Δ.
The check before any fixture is admitted: *does the dependent variable pass back
through anything I typed?*

**Where the ground truth comes from instead**, and it is the reason stages 0 and
1 run on `evals/fixtures/exp05/` unmodified: for a rival pair whose evidence sets
are identical, the records that would move the meta-belief are exactly those
entering one rival's `evidence_ids` and not the other's. That is
`separating_evidence`'s definition
([underdetermination.py:91](../../../src/manyu/underdetermination.py)), written
before this experiment existed and for another purpose. The target is fixed by
structure, and nobody typed it.

The three new fixtures (requirements §11) carry **structural** `expect` blocks
only — evidence counts, stability values, edge directions — each with a note
saying so, checkable by reading the file. They are not predictions about what the
pricer does.

**One authoring risk is specific to this experiment and has no structural
guard.** `entrenched` sets a stability value directly, and stability is an input
to the dose. A fixture that sets stability is therefore authoring a large part of
the answer. That is accepted — the row exists to show dose responds to
entrenchment at all — but it means `entrenched` is a **positive control and never
evidence for the dose result**. The census over naturally-accumulated stability
(stage 2) is where the dose claim lives.

## 4. The freeze, and what each half enforces

Unchanged in structure from experiment 5 §4:

- **Fixtures** are enforced continuously by `verify_freeze()`, which every runner
  calls before doing anything. A fixture edit invalidates every result resting on
  it. Experiment 5's fixtures are already frozen and this experiment **must not
  re-freeze them** — it consumes them read-only, and a re-freeze here would
  silently invalidate experiment 5's published results.
- **Criterion tests** are enforced by `verify_standards_freeze`, called by a
  scored run and deliberately *not* by the test suite. Adding a check strengthens
  the standard and must stay cheap; what must not happen is a standard being
  weakened after a result is visible.
- **The pre-registration** is hashed so "the numbers were fixed in advance" is
  checkable rather than remembered. Amending is allowed and recorded in its §7;
  amending silently is not.

Re-freezing is an explicit act with a recorded reason.

## 5. The two pricers, and how disagreement is attributed

This is the measurement, so the procedure is written out rather than left to the
runner.

**The analytic pricer is the prediction.** A pure function over
`(Belief, HypotheticalEvidence, RevisionConfig)`. It never touches the store, and
FR-1 is verified by comparing `export_agent` before and after rather than by
inspection.

**Replay is the observation.** The agent is copied into a scratch `:memory:`
store and the real path is run against the copy. Two sub-arms, and keeping them
apart is the point of stage 1:

| Sub-arm | Delivery | Expected |
|---|---|---|
| `direct` | The record is injected as evidence on the belief | Agreement to 1e-9. **Reported as a regression test, never as calibration** (requirements §5.1) |
| `extractor` | The record is delivered through ingest | Divergence. This is the experiment |

**Every extractor-path row carries a topology stamp** — whether the extractor
emitted a mutual `contradicts` edge, a one-way edge, or none — because
experiment 5 §6.1 measured that a one-way edge separates an otherwise identical
pair by 0.2333, and pre-registration §3 predicts mispredictions concentrate
there. Without the stamp, an uncalibrated result is uninterpretable; with it,
"the pricer is exact and the extractor is the uncertainty" becomes a checkable
claim rather than an excuse.

**The attribution rule, fixed before the run:** an error is *attributable* when
its row carries a topology mismatch or a `new_evidence` no-op, and
*unattributable* otherwise. Pre-registration §3 makes an uncalibrated-but-
attributable result a finding and an uncalibrated-and-unattributable result the
end of the experiment, so this rule cannot be decided after seeing the residuals.

## 6. Plots

Three, and each answers one pre-registered question. No plot is produced for
anything not registered.

| Plot | Shows | Reads on |
|---|---|---|
| `calibration.png` | Predicted Δ against observed Δ, one point per hypothetical record, coloured by topology stamp, with the identity line and the ±0.05 / ±0.15 bands | Pre-registration §3 |
| `dose_curves.png` | Confidence against records delivered, `symmetric_rivals` and `near_miss` overlaid, with the 0.45 threshold ruled | Pre-registration §4.1 — the k=5 versus k=10 prediction |
| `entrenchment_census.png` | Dose against stability across every belief in the census, with the `entrenched` control marked distinctly | Pre-registration §4.3 — monotonicity, where a single falling point is a defect report |
| `arrival_ratio.png` | Dose against arrival ratio `r`, log-scaled on dose, with the `r* = 11/9` asymptote ruled and the unfalsifiable region shaded | Pre-registration §4.4 — the phase transition |

`arrival_ratio.png` must plot the **analytic** asymptote as a line and the
simulated doses as points. Showing only the points would make a divergence look
like a steep curve, and the claim registered in §4.4 is that it is an asymptote —
the difference between "expensive" and "impossible" is the finding.

The direct sub-arm is **excluded** from `calibration.png`. Plotting a regression
test on a calibration chart would put a perfect diagonal in the figure that
carries the headline, and the reader would be right to be misled by it.

`matplotlib` is already an optional dependency under
`[project.optional-dependencies] analysis` (experiment 1 v2).

## 7. Stage 4 — the paid run, and what it costs

Not run. Blocked on §8.

### 7.1 What it must answer

1. **Does a real model name evidence the pricer agrees is separating**, or does
   it restate the belief's negation? This is the steelman framing, and it is the
   only place in the experiment where it appears (requirements §8).
2. **The structural-enumeration base rate on a live web** — pre-registration
   §1.1 fixes 1 in 4 beliefs carrying a `contradicts` or `supports` edge as the
   line below which structural enumeration is fixture-only. Stage −1 measures
   this on stored webs, which are all offline and all predate the extractor
   changes; the live number is the one that decides it.
3. **Whether the extractor path's divergence (§5) survives contact with a real
   extractor**, rather than the `ScenarioJSONProvider` one.

**Not in scope, and deliberately:** cosmology (requirements §14.6), which stays
with experiment 5 Stage 5 where it was chartered.

### 7.2 Costing

Scale is set by experiment 3 Stage 4, the nearest comparable live run:
`claude-opus-5`, n=10 × 3 scenarios, 30 clean records, 0 provider errors.

| Component | Calls | Note |
|---|---|---|
| Variance pilot | ~10 | **Run first and read before committing.** Two of experiment 1's four fixtures sat at ceiling and cost full price for zero variance |
| Steelman enumeration | ~60 | n=10 × 3 fixtures × 2 framings |
| Delivery and re-scoring | ~60 | one ingest per proposed record, to observe what the pricer predicted |
| Receipts scoring | ~30 | one report per steelman run |

Roughly **160 calls**, with the pilot's ~10 as a hard gate on the rest.

Two rates must be absorbed rather than treated as failures, both from experiment
3 §3.4: live webs are one hop deep, and about 1 extraction in 10 over-merges into
a single belief with no edges. **An over-merge destroys the belief being priced
and is a dropped sample, not a null.**

**One cost specific to this experiment:** every proposed record has to be
*delivered* as well as proposed, so the call count is roughly double what an
enumeration-only run would cost. A prediction without its paired observation is
not a result (FR-2), and cutting the delivery half to save money would leave the
experiment with nothing it could not have got offline.

### 7.3 Pre-flight, before any spend

1. `verify_freeze()` and `verify_standards_freeze` both clean.
2. The mechanism digest in `freeze.json` matches `counterfactual.py` — a pricer
   edit between the offline stages and the live one invalidates the comparison
   the live stage is against.
3. The generation-path check run and recorded **first**, on experiment 5's
   procedural improvement over experiment 4's voided Stage 0a: confirm the
   provider can emit what the stage needs to measure *before* reading any number
   off it.
4. Stage 1's attribution rule (§5) applied to the offline residuals and recorded,
   so the live run inherits a rule rather than negotiating one.
5. The variance pilot read.

## 8. Prerequisites, unclosed

1. **`/code-review ultra exp03-base` has never been re-run**, and this experiment
   moves it from a background concern to a blocker. Every number here comes out
   of `blend_confidence` and `_contradiction_share`, so an unreviewed revision
   engine is an unreviewed dependent variable. **It should close before stage 1,
   not before the paid stage.** It is user-triggered and billed and cannot be
   launched from inside a session.
2. **Rotate the API key** used for experiment 3 Stage 4 — it was pasted into a
   chat transcript. Carried from experiment 3 §6, through experiment 5 §6, still
   open.
3. **Experiment 4 stages 0a/0b and experiment 5 Stage 5 remain unrun**, all
   blocked on a provider that can emit `contradicts`. Stage 4 here needs the same
   capability, and the four should be answered by one spend rather than four.
