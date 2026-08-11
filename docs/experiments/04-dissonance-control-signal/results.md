# Experiment 4 — Dissonance as a Control Signal: Results

**Status:** Stage 0.5 complete · Stage 0a **void** · Stages 2–4 have offline results on authored webs
**Requirements:** [requirements.md](requirements.md) · **Backlog:** [../../experiments_backlog.md](../../experiments_backlog.md)

Everything below is offline and deterministic under `FrozenClock`. No provider
call has been made and no money has been spent.

## 1. Stage 0.5 — what the substrate forces

Established by reading the code and pinned in
[`tests/test_salience_substrate.py`](../../../tests/test_salience_substrate.py),
before `salience.py` contained any mechanism.

- **`contradicts` edges are only ever added.** `BeliefUpdater.update` unions
  them, `_revise` does not touch the field, `RevisionEngine.assert_contradiction`
  also only unions. Nothing anywhere removes one.
- **A conflict can therefore never be retired**, and `magnitude_raw` sums
  `min(stake_a, stake_b)` over a set that never shrinks. Tension falls *only* by
  weakening a party.
- **The `min` rule leaves no choice of side.** Weakening the higher-staked belief
  moves the signal by exactly zero.
- **Stake is blind to grounding.** `stake_of` averages evidence salience rather
  than summing it, so one evidence record and five produce identical stake.

> **"Tension fell" is never evidence that anything was resolved.** The one thing
> that survives is the carrier set: a conflict is still *named* when its tension
> reads zero, which is what makes capitulation distinguishable from resolution at
> all.

This is experiment 3 §11.1 in a new place — the architecture, not the run,
settles the question — and it is why the primary dependent variable is *which
side got weakened*, not whether the web converged.

## 2. Stage 0a — base rate: **VOID**

| | |
|---|---|
| Naturalistic turns | 35, across all four experiment-1 fixtures |
| Turns producing a signal | **0** |
| Authored positive control | fires 3/3 |
| **Verdict** | **VOID — not a finding** |

A base rate of zero with a passing control reads exactly like a result. It is
not one.

`ScenarioJSONProvider._belief_candidates` hardcodes `"contradicts": []`
([providers.py:438](../../../src/manyu/providers.py)), so the offline extraction
path **cannot represent a contradiction at all**. The zero describes the
instrument, not the webs.

**The authored control did not catch this and could not have** — it exercises the
*detector*, while the defect is in the *generation* path. A positive control has
to sit on the path that could be broken. `run_stage0.py` now runs
`generation_path_can_contradict` before reading anything, and marks the base rate
void when the path cannot fire.

**Consequence: Stage 0a is not answerable offline**, and Stage 0b inherits that —
a disagreement set over turns where dissonance never fires is empty for a reason
that has nothing to do with distinctness. The plan's "offline, can kill it
cheaply" framing was wrong on this point.

For the record, the incumbent channels escalate on **91.4%** of naturalistic
turns (32/35), which is worth carrying into 0b whenever it becomes answerable: a
near-saturated incumbent rate makes it hard for any new signal to add a distinct
branch.

## 3. Stage 2 (offline, authored webs) — the signal's value is scarcity

Raw tension remaining on `multi_conflict_web` after *N* acts of attention, lower
being better. Random is 20 seeds. Run by
[`run_stages.py`](../../../evals/analysis/exp04/run_stages.py).

| budget | driven | inverted | random mean [min, max] |
|---|---|---|---|
| 1 | **0.836** | 1.144 | 0.991 [0.836, 1.144] |
| 2 | **0.671** | 0.979 | 0.824 [0.671, 0.979] |
| 3 | 0.605 | 0.605 | 0.605 |
| 4 | 0.605 | 0.605 | 0.605 |

Driven beats random beats inverted while attention is scarce. **At a budget
covering every conflict all three are identical**, because the actions are
idempotent and their total is order-independent. The pattern replicates on
`hub_web` and `adversarial_multi`, converging in each case at exactly the
conflict count.

> **The signal's value is entirely a function of scarcity.** With enough
> attention to reach everything, dissonance-as-control does nothing at all.

This makes the **attention budget the real independent variable** for Stage 2,
not the arm. The requirements treat the bound as a fixed parameter; it is swept
here and should stay swept.

### 3.1 Driven is not optimal, and `hub_web` shows it

On `multi_conflict_web` the random draw is exactly bracketed by the other two
arms. **On `hub_web` it is not:** at budget 2 the driven arm leaves 0.9579 while
the best random ordering leaves 0.9114.

The cause is structural. `assert_contradiction` charges
`share × contradictor.confidence`, so how much a conflict yields depends on the
*contradictor's* confidence — while selection ranks by tension, which is
`min(stake_a, stake_b)` weighted by valence distance. On a web whose conflicts
share a party those two come apart, and picking the highest-tension conflict is
not the same as picking the one that will move the most.

> **"Attend to the most tense conflict" is a heuristic, not an optimum.** It is
> the best *available* ordering only when conflicts are disjoint.

This is why `test_random_is_bracketed_by_driven_and_inverted` is scoped to
`multi_conflict_web` alone; asserting it generally would have pinned something
false.

**`always` was specified and dropped.** In a loop that acts on one conflict per
step and never declines, "escalate regardless of tension" cannot differ from
"pick one without consulting tension" — which is `random_matched`. Running both
would have reported one arm twice, the exact defect experiment 2 found when
`ContradictionArm` was stored, stamped onto every result, and consulted by no
branch. `inverted` replaces it and brackets the driven arm from below.

## 4. Stage 3 — the signal is **not** more specific than chance

The targeting question as the requirements posed it — "do the carriers name the
beliefs acted on?" — is settled by wiring: the loop selects a conflict *from* the
carrier set, so the overlap is 100% by construction. Experiment 3 §1 in a new
place, and not asked.

What can fail is whether the signal points at a *part* of the web. `spread` is
the fraction of beliefs any carrier implicates; the null is a **degree-preserving
derangement of the `supports` edges**, which leaves every conflict and every
tension untouched and destroys only which belief entails which. 50 derangements
per web.

| web | beliefs | spread | null mean [min, max] | p | verdict |
|---|---|---|---|---|---|
| `distractor_web` | 10 | 0.400 | 0.476 [0.200, 0.800] | 0.48 | **indistinguishable from chance** |
| `depth_carrier_web` | 4 | 1.000 | 0.950 | 1.00 | unmeasurable at ceiling |
| `hub_web` | 4 | 1.000 | 1.000 | 1.00 | unmeasurable at ceiling |

> **On the only web where the measurement is possible, the carrier set is no
> more specific than random rewiring.** Real spread sits at the 48th percentile
> of the null.

Two things this does and does not say. It does **not** say the traversal is
wrong — the carriers do name beliefs genuinely connected to the conflict, which
experiment 2's D3 established. It says the *set* it names is no smaller than
connectivity alone would predict, so "the signal points at where the trouble is"
is not supported: on this web it points at whatever the graph happens to reach.

It also flags a fixture-design problem worth carrying forward. Two of three webs
sit at `spread = 1.0` — experiment 1's failure mode #3, a metric pinned at the
end of its range reporting its own constant. Any future Stage 3 needs webs
substantially larger than their conflict neighbourhoods, and
`distractor_web` was authored for exactly that reason.

**Caveat:** *n* = 1 measurable web. This is a direction to take seriously, not a
settled result.

## 5. Stage 4 (offline, authored webs) — what resists motivated reasoning

`adversarial_grounding` and `aligned_grounding` are identical in every field
except which side holds five evidence records.

| | tension | magnitude | carriers | belief weakened | its grounding | moved |
|---|---|---|---|---|---|---|
| `adversarial_grounding` | 0.3080 | 0.1856 | 1 | `well_grounded` | 5 records | **0.117** |
| `aligned_grounding` | 0.3080 | 0.1856 | 1 | `thinly_held` | 1 record | **0.350** |

**The dissonance channel cannot tell the two webs apart** — byte-identical raw
tension, magnitude and carrier count. So the loop makes the same decision on
both, with nothing in its input to distinguish a case where weakening the forced
target is right from one where it is wrong.

What differs is the consequence: the well-grounded belief moves **three times
less**. Experiment 3 §12's provenance-based contradiction pricing —
`1/(supporters + own evidence + contradictors)` — is what pushes back, through a
channel the control signal never sees.

> Requirements §11 asked what would resist if the loop did *not* discard the
> better-grounded belief. The answer is mandatory provenance again, the same
> property that decided experiment 3.

**That result is on a single conflict**, which cannot discriminate any ordering.
The selection blindness from §1 only bites where the loop has a *choice*, which
is what `adversarial_multi` was authored to provide.

### 5.1 On a multi-conflict web, attention goes to the best-corroborated beliefs

`adversarial_multi` holds three conflicts whose targets carry 5, 3 and 1 evidence
records, with grounding **anti-correlated** with tension — the most tense dispute
has the best-evidenced target. Well-grounded targets hit, per budget:

| budget | driven | inverted | random mean |
|---|---|---|---|
| 1 | **1 / 1** | 0 / 1 | 0.90 |
| 2 | **2 / 2** | 1 / 2 | 1.35 |
| 3 | 2 / 3 | 2 / 3 | 2.00 |
| 4 | 2 / 3 | 2 / 3 | 2.00 |

> **Under scarce attention the tension-driven loop spends its entire budget on
> the best-corroborated beliefs**, and the inverted arm spends none of it there.
> Once the budget covers every conflict the arms are identical again — the bias
> lives entirely in what gets attended *first*.

The mechanism is the one §1 established: tension is `min(stake_a, stake_b)`,
stake is `mean(salience) × confidence`, and grounding appears nowhere in it. A
well-corroborated belief that is also confidently held is, for that reason alone,
the most attractive thing in the web to attack.

**The two halves of the picture pull against each other**, and neither is the
whole answer:

- Dissonance-driven attention **targets** well-grounded beliefs preferentially
  (this section).
- Provenance-based pricing means each hit **costs them less** (§5's minimal
  pair — 0.117 against 0.350).

Which dominates over a long run is not measured here and should not be guessed.
It is the sharpest open question this experiment has produced.

## 6. What the test strategy caught

Eight defects so far, **none by a conventional test-written-after-the-code**.
Experiment 3's tally was sixteen defects and zero caught, from the same author
writing tests minutes after the mechanism.

| Defect | Found by |
|---|---|
| Stage 0a's base rate was an instrument artifact | Checking the generation path before reading the number |
| The tie-break ran on `uuid4`, so it was random not deterministic | A property test over repeated stores |
| Half of every attention budget spent re-attending handled conflicts | Reading actual loop output |
| Two of three planned arms were the same mechanism | Building it |
| The minimal pair could not separate "reads the graph" from "charges the weaker side" | The mutant battery |
| No fixture could catch a loop deciding from a stale reading | The mutant battery |
| The reference-independence guard matched its own docstring | Its own test failing |
| The cross-process CLI helper invoked a module with no `__main__`, so three tests asserted nothing | Requiring output |

The mutant battery ([`tests/test_salience_mutants.py`](../../../tests/test_salience_mutants.py))
holds ten catalogued mutants, each reproducing a historical defect family, and
asserts every one is caught by a named check. Two are documented as uncatchable
with reasons: `saturated` cannot differ because the transform is monotone, and
`trajectory_never_rises` cannot be tripped because monotonicity is structural.

## 7. What is blocked, and on what

- **Stage 0a and 0b** need a provider that can emit `contradicts`. That is the
  live API path, which makes the base-rate question a *paid* one. Deciding
  whether to spend on it is the open question.
- **Stage 2 at scale** needs the attention-budget sweep (§3) and webs with more
  conflicts than the authored set has.
- **Stage 4** needs multi-conflict adversarial webs, since the current result
  rests on a single conflict.
- Carried from experiment 3 §6 and still open: rotate the API key pasted into a
  chat transcript, and retry `/code-review ultra exp03-base`.
