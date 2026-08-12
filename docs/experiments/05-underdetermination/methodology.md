# Experiment 5 — Underdetermination as a First-Class Belief: Methodology

**Requirements:** [requirements.md](requirements.md) · **Pre-registration:** [pre-registration.md](pre-registration.md) · **Results:** [results.md](results.md)

How the experiment is run and what is looked at. The mechanism itself is
documented in [`underdetermination.py`](../../../src/manyu/underdetermination.py);
this file changes when the *procedure* changes, not when the code does.

## 1. Running the offline stages

Everything below is deterministic under `FrozenClock` and makes no provider call.
`n=1` is correct for all of it — repetition re-measures the same arithmetic
(experiment 2 methodology §1).

The order is a dependency order, and each step gates the next.

```bash
python -m pytest tests/test_underdetermination_substrate.py -v
```

```bash
python evals/analysis/exp05/run_stage0.py
```

```bash
python evals/analysis/exp05/run_stages.py
```

```bash
python -m pytest tests/ -q
```

**Stage −1 is a gate, not a formality.** It executes the requirements document
against the substrate, and three of its claims were quoted in the backlog as
findings before they were run. If one fails, the document is wrong and correcting
it is the stage's output. Nothing proceeds until it passes.

## 2. Reading the artifacts

| File | Holds |
|---|---|
| [`stage0.jsonl`](../../../evals/analysis/exp05/stage0.jsonl) | Both edge topologies × both seeding paths, plus the synthesizer's output and a `verdict` row |
| [`stages.jsonl`](../../../evals/analysis/exp05/stages.jsonl) | The control set, the collapse arm and its trajectory, the ablation, the budget sweep, the evidence sweep, expression, and a `verdict` row |
| [`freeze.json`](../../../evals/analysis/exp05/freeze.json) | sha256 per fixture, per criterion test, plus the pre-registration and mechanism digests |

**Verdict rows are computed by the runner and recomputed by the test suite.**
[`tests/test_exp05_rederivation.py`](../../../tests/test_exp05_rederivation.py)
re-derives every published figure from the JSONL and recomputes every headline
claim rather than reading it, so a number cannot drift from its evidence without
something going red. It also carries a positive control proving the derivability
check can fail — the check has a large exemption list, which is the shape that
quietly stops working.

## 3. What may be authored, and what may not

Carried from experiment 3 §4 and experiment 4 §8, and it is the hardest
constraint here.

A fixture may author **which beliefs exist, what evidence they hold, how that
evidence is shared, and which of them conflict**. Authoring those is manipulation,
not rigging — they are the independent variable.

A fixture may **not** author that a pair is underdetermined. That is enforced
structurally rather than by discipline: `Belief.rivals` does not exist on
`BeliefCandidate` and `underdetermination` is not offered in the extractor schema,
so there is no field to write it in. `ManyuModel` sets `extra="forbid"`, so an
attempt is a validation error rather than a silently dropped key.

The check before any fixture is admitted: *does the dependent variable pass back
through anything I typed?*

Fixture `expect` blocks therefore carry **structural** properties only — evidence
counts, overlap sizes, edge directions — each with a note saying so. They are
checkable by reading the file, and they are not predictions about what the
criterion does.

## 4. The freeze, and what each half enforces

- **Fixtures** are enforced continuously by `verify_freeze()`, which every runner
  calls before doing anything. A fixture edit invalidates every result resting on
  it. They were authored before `underdetermination.py` existed.
- **Criterion tests** are enforced by `verify_standards_freeze`, called by a
  scored run and deliberately *not* by the test suite. Adding a check strengthens
  the standard and must stay cheap; what must not happen is a standard being
  *weakened* after a result is visible, and that risk lives at the scored run.
- **The pre-registration** is hashed so "the numbers were fixed in advance" is
  checkable rather than remembered. Amending is allowed and is recorded in its §8;
  amending silently is not.

Re-freezing is an explicit act with a recorded reason.

## 5. Stage 5 — the paid run, and what it costs

Not run. Blocked on the prerequisites in §6.

### 5.1 What it must answer

1. **The base rate.** How often does a naturalistic reflective run produce two
   beliefs that share evidence *and* carry a `contradicts` edge? Below 1 in 20
   turns the claim is fixture-only (pre-registration §1). This is unanswerable
   offline — `ScenarioJSONProvider` hardcodes `"contradicts": []` — and the check
   for that runs before the number is read, which is the one procedural
   improvement over experiment 4's voided Stage 0a.
2. **The edge-topology rate.** Of the rival pairs found, what fraction carry a
   *mutual* edge? This is the most consequential unmeasured quantity in the
   experiment: results §1 showed the substrate holds a standoff only for mutual
   pairs, so if mutual pairs are rarer than 1 in 4, the standoff is a laboratory
   artifact and the headline must say so.
3. **Experiment 4's Stage 0a/0b**, blocked since 2026-08-10 on the same missing
   capability. Answered by the same spend rather than a second one.
4. **The cosmology case**, where the model produces the rivals and we do not —
   the only condition under which detection is not a read-back of a fixture we
   wrote.
5. **The honesty-scored report** deferred from Stage 4. A templated report is
   authored by us, so scoring one measures the template; this needs a real
   reporter. Citation metrics only — SC-5 at 67.9% is not decision-grade.

### 5.2 Costing

Scale is set by experiment 3 Stage 4, which is the nearest comparable live run:
`claude-opus-5`, n=10 × 3 scenarios, 30 clean records, 0 provider errors.

| Component | Calls | Note |
|---|---|---|
| Variance pilot | ~10 | **Run first and read before committing.** Two of experiment 1's four fixtures sat at ceiling and cost full price for zero variance |
| Base rate + edge topology | ~120 | n=10 × 4 experiment-1 fixtures × ~3 extraction points |
| Cosmology condition | ~30 | n=10 × 3 framings |
| Reporter + honesty scoring | ~30 | one report per cosmology run |

Roughly **190 calls**, with the pilot's ~10 as a hard gate on the rest. Two rates
must be absorbed rather than treated as failures, both from experiment 3 §3.4:
live webs are one hop deep, and about 1 extraction in 10 over-merges into a single
belief with no edges — **an over-merge destroys a rival pair outright and is a
dropped sample, not a null.**

Model choice is open. Experiment 1's sweeps ran on `claude-haiku-4-5-20251001` and
experiment 3's Stage 4 on `claude-opus-5`; a specificity result established on one
provider is provisional until re-run on the provider carrying the finding
(experiment 3 §3.2), so the pilot should settle which.

### 5.3 Pre-flight, before any spend

1. `verify_freeze()` and `verify_standards_freeze` both clean.
2. The mechanism digest in `freeze.json` matches `underdetermination.py` — a
   criterion edit between the offline stages and the live one invalidates the
   comparison the live stage is against.
3. Derivation wired into `process_reflective_turn`, which is deliberately *not*
   done for stages 0–4 so they stay deterministic.
4. The generation-path check run and recorded **first**.
5. The variance pilot read.

## 6. Prerequisites, unclosed and not this experiment's work

1. **Rotate the API key** used for experiment 3 Stage 4 — it was pasted into a
   chat transcript.
2. **Retry `/code-review ultra exp03-base`.** The cloud review failed and was never
   re-run, so every fix in the revision engine this experiment's collapse arm
   rests on has been verified by its author alone.
