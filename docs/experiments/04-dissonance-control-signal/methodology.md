# Experiment 4: Methodology

**Status:** pinned 2026-08-10, before any scored run and before any provider call.
**Requirements:** [requirements.md](requirements.md) · **Design:** [design.md](design.md) · **Results:** [results.md](results.md)

Every constant here is fixed *before* the run that consumes it. Changing one
afterwards voids that arm — the pre-registration rule carried from experiment 2
requirements §14 and experiment 3 methodology §1.

## 1. What is deterministic, and why *n* = 1 is right

Stages 0.5 and 2–4 consume no provider and run under `FrozenClock`. Where no
randomness is involved, repetition re-measures the same arithmetic and a larger
*n* buys nothing ([experiment 2 methodology §1](../02-merge-split-fork/methodology.md)).

Two places *are* stochastic and repeat:

| Source | Repeats | Why |
|---|---|---|
| `random_matched` arm | 20 seeds | The draw is the null; one draw is not a distribution |
| Stage 3 derangement | 50 seeds | Same |
| Id-sensitive mutant checks | 8 stores | Belief ids are `uuid4`, so a mutant ignoring tension is caught probabilistically (§6) |

## 2. Constants

| Constant | Value | Justification, independent of any outcome |
|---|---|---|
| `contradiction_arm` | `direct` | Experiment 3 requirements §5.1 decided it |
| `decay_mode` | `provenance` | Experiment 3 §11 — no free constant |
| `contradiction_pricing` | `provenance` | Experiment 3 §12 — no free constant |
| escalation threshold | **none** | Removed, not chosen. See §3 |
| `BUDGET_SWEEP` | 1, 2, 3, 4 | One past the conflict count of the widest web, so the convergence point falls *inside* the swept range rather than being assumed |
| `RANDOM_SEEDS` | 0–19 | Fixed before the run |
| `DERANGEMENT_SEEDS` | 0–49 | Fixed before the run |
| Stage 3 significance | p ≤ 0.05, one-sided | Conventional, and fixed before any spread was computed |

## 3. The threshold question is closed by removal

Requirements §13 treated the firing level as blocking. It is not, and no value
was chosen for it:

- **The loop needs none.** Selection is by *ranking* — take the most tense
  conflict — so there is no level at which anything fires.
- **Stage 0b needs none.** Its dissonance predicate is "the web contains a stated
  contradiction," which has no constant in it. If that already fails to separate
  from the incumbents, no threshold would rescue it.

This follows experiment 3 §§11–12, which removed `attenuation` and
`contradiction_penalty` rather than tuning them. **Removing a constant beats
choosing one well**, and there is no `FIXED` ablation here because there is no
constant to ablate.

## 4. What may be authored, and what may not

Carried from experiment 3 §4. Topology, starting confidences, salience, evidence
counts and which beliefs conflict are the **independent variable**; authoring
them is manipulation, not rigging. The dependent variables — which conflict the
loop selects, how much moved, which side paid, how much of the web is implicated
— must never pass back through anything typed into a fixture.

The check before any fixture is admitted: *does the DV pass back through anything
I typed?* Enforced by [`test_salience_criteria.py`](../../../tests/test_salience_criteria.py),
which computes each fixture's claimed structural properties from the store rather
than reading them out of the file's own `expect` block.

## 5. Fixtures are frozen, and re-freezing is an explicit act

Eleven webs in `evals/fixtures/exp04/`, hashed in
[`freeze.json`](../../../evals/analysis/exp04/freeze.json). `verify_fixture_freeze`
runs at the top of every runner and inside the suite; a drifted fixture voids the
arm resting on it.

`files` (the webs) is enforced continuously. `standards` (the criterion tests) is
enforced by `verify_standards_freeze`, which the **runner** calls before a scored
run and the suite does not — adding a criterion test strengthens the standard and
should not require a re-freeze, while weakening one after seeing a result is the
actual risk and lives at the scored run.

Two re-freezes so far, both recorded with reasons in the freeze file, both
**before any scored run existed**:

1. `counter_direction`, `hub_web` — added because the mutant battery found the
   original seven could not catch two mutants.
2. `distractor_web`, `adversarial_multi` — added because Stage 3 is unmeasurable
   on a web the signal already names entirely, and Stage 4 cannot discriminate an
   ordering on a single conflict.

Neither was authored in response to a result.

## 6. Instrument gates, run before any number is read

| Gate | Guards against |
|---|---|
| `generation_path_can_contradict` | A base rate of zero from a path that cannot fire — **this one fired**, and voided Stage 0a |
| `verify_fixture_freeze` | A held-out claim resting on an edited file |
| spread ceiling check | `spread = 1.0` reporting its own constant (experiment 1 failure mode #3) |
| mutant battery | A suite that cannot catch the defect families this project actually has |
| `_production_leaks` | A reference implementation that agrees with the code by calling it |
| `assert_above_chance` | An effect reported against its null's *mean* rather than its distribution |

### 6.1 Two planned gates that were not built

- **`assert_rate_matched`** — unnecessary. Every arm receives the same
  `max_iterations`, so rates are matched by construction rather than by
  assertion. A gate that can only ever pass is decoration.
- **`assert_reduction_is_not_capitulation`** — unbuildable as specified, and the
  reason is the finding. §1 established that in this substrate tension falls
  *only* by weakening a party, so reduction is **always** capitulation. The gate
  would fire on every run. What replaces it is the carrier channel: a conflict is
  still named when its tension reads zero, so capitulation is visible in the
  record rather than caught by an assertion.

**The gate that mattered most was the one on the *generation* path.** Stage 0a's
authored positive control passed 3/3 and could not have caught the defect,
because it exercises the detector while the fault was in generation. A positive
control has to sit on the path that can break.

## 7. Stage-by-stage procedure

**Stage 0** — [`run_stage0.py`](../../../evals/analysis/exp04/run_stage0.py).
Drives the four experiment-1 fixtures through `process_reflective_turn` with
`ScenarioJSONProvider`, recording per turn the dissonance read and every control
input `Arbiter` and `FastAppraiser` consult. Authored webs are the positive
control. **Currently void; requires a provider that can emit `contradicts`.**

**Stage 2** — [`run_stages.py`](../../../evals/analysis/exp04/run_stages.py).
Three arms × four budgets × three webs. Outcome: raw tension remaining. Reported
with the arms' convergence point, which must fall inside the swept range.

**Stage 3** — same runner. `spread` against 50 degree-preserving derangements per
web. A web at `spread = 1.0` is reported `unmeasurable_at_ceiling` and excluded
rather than counted.

**Stage 4** — same runner. On `adversarial_multi`, the count of well-grounded
targets attended per budget, driven vs inverted vs 20 random draws.

**Stage 5 (live)** — not scheduled. Conditional on Stage 0a, which is now a paid
question.

## 8. Reporting rules

- **Never `magnitude`.** Trajectories and deltas are `magnitude_raw`; the
  saturated channel is unreachable from the control path by type and absent from
  every run record, which
  [`test_exp04_rederivation.py`](../../../tests/test_exp04_rederivation.py)
  enforces on the artifacts.
- **Every published number is re-derived** from the stored JSONL by the same
  test file. Experiment 3 did this by hand for 26 figures; automating it means a
  number cannot drift from its evidence silently.
- **Verdicts are recomputed, not quoted.** Stage 3's p-based verdict in
  particular: comparing a real value to a null's *mean* said "more specific" at
  p = 0.48, which is squarely mid-distribution. The mean comparison is retained
  in the record and is explicitly not the verdict.
- **A null is reported with its control.** A null without a passing control is a
  bug, not a finding.

## 9. Carried-over standing method

From experiments 1–3, applied throughout rather than restated per stage: write
the criterion before running what could settle it; probe inputs the author did
not have in mind; treat an impossible value as a defect report; assert a
mechanism can change its output before reading what it says; ship a positive
control in the same run; run drop-one robustness inside analysis; pin constants
before the run that consumes them.
