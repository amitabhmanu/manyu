# Experiment 4 — Dissonance as a Control Signal: Design

**What the code does.** Changes when the code changes. How the experiment is
*run* lives in [methodology.md](methodology.md); a code reviewer reads this file,
someone judging whether the finding is defensible reads that one.

**Requirements:** [requirements.md](requirements.md) · **Results:** [results.md](results.md)

## 1. Modules

| File | Role |
|---|---|
| [`salience.py`](../../../src/manyu/salience.py) | The coupling: view boundary, selectors, loop, Stage 3 measures, freeze |
| [`salience_mutants.py`](../../../src/manyu/salience_mutants.py) | Ten catalogued mutants, each reproducing a historical defect family |
| [`schemas.py`](../../../src/manyu/schemas.py) | `AttentionStepRecord`, `LoopTrace` — the storable face of a run |
| [`store.py`](../../../src/manyu/store.py) | `dissonance_signals`, `loop_traces` tables; both governed |
| [`core.py`](../../../src/manyu/core.py) | `read_dissonance`, `run_attention_loop`, `get_loop_trace`, and the in-turn read |

Nothing here calls a provider.

## 2. `TensionView` — the boundary that carries the constraint

```
DissonanceSignal          TensionReading            TensionView
  magnitude_raw     -->     magnitude_raw     -->     magnitude_raw
  magnitude               magnitude                  carriers
  carriers                saturation_baseline        agent_id
                          carriers
```

The loop receives a `TensionView` and nothing else. `magnitude` and
`saturation_baseline` stop at `TensionReading`, which is the analysis record.

**This is a type, not a convention, and the distinction is load-bearing.**
Experiment 2's `SplitDissonanceAppraiser` originally took the store and merely
*declined* to walk `supports`; the steelman test correctly called that the
implementer's restraint rather than the architecture's. Requirements §12 forbids
reading `magnitude` as a measure of belief dynamics, and the only way to make
that stick is for the control path to be unable to reach it.

`TensionView.conflicts` returns only pairs whose carrier has an **empty path** —
those are the ones with a stated `contradicts` edge underneath. Derived pairs
(reached through `supports`) are real tension with nothing to price, so they
appear in `implicated` and are not selectable.

## 3. Selectors

All three take a view and a set to exclude, and return a conflict or `None`.

| Arm | Rule |
|---|---|
| `DRIVEN` | Highest tension. Consults no randomness. |
| `INVERTED` | Lowest tension — the floor. The same actions in the worst order tension recommends. |
| `RANDOM_MATCHED` | Uniform draw, seeded. |

`Arm` has no default at any layer — core, CLI (`choices=`, `required=True`), MCP.
`RANDOM_MATCHED` refuses to construct without a seed.

**There is no threshold and no free constant.** Selection is by ranking, so no
firing level is needed; see [requirements §13.1](requirements.md).

## 4. The action

`AttentionLoop` prices the selected conflict through
`RevisionEngine.assert_contradiction`. Three properties made that the choice:

- **No new constant.** Experiment 3 §12 derived a contradictor's weight as
  `1/(supporters + own evidence + contradictors)`, read off the store. An
  invented "attention strength" would put a free parameter at the centre of the
  result — the thing §§11–12 removed twice.
- **Idempotent**, so attending twice cannot compound, which is what makes
  `EXHAUSTED` a real terminal state.
- **Direction is read off the graph.** The contradictor is whichever belief
  declares the edge; both declaring is labelled `mutual` and broken by sorted id.
  Charging whichever side is weaker would *build* the motivated-reasoning result
  rather than measure it.

## 5. The loop

```
for iteration in range(max_iterations):
    reading = read()                  # live, every step
    if reading is None: -> NO_SIGNAL / EXHAUSTED
    conflict = selector.select(view, attended)
    if conflict is None: -> NO_SIGNAL / EXHAUSTED
    record best_available_tension, tied_with
    price it
    attended.add(conflict)
else: -> BOUND_REACHED
```

**Already-attended conflicts are excluded from selection.** Pricing is
idempotent and tension falls by exactly what was charged, so the conflict just
handled is often still the highest; without the exclusion the loop spent *half of
every budget* on `already_priced` no-ops. Since the budget is Stage 2's
independent variable, that would have made the arm comparison measure the waste.

`TerminationReason` has three values and **deliberately no `OSCILLATING`**:
pricing only lowers confidence and nothing in the loop raises it, so the
trajectory is monotone and thrashing is unrepresentable. A reason that cannot
occur is decoration.

### 5.1 The record is self-auditing

`AttentionStep` carries `best_available_tension` — the highest tension among
unattended conflicts, read off the live web at selection time. A driven arm must
show `tension_before == best_available_tension`; any gap means the choice was
made from stale information. Without it, a loop deciding from an outdated reading
records a *live* tension beside a *stale* choice and looks entirely correct.

`tied_with` records how many conflicts shared the selected tension. Greater than
one means the choice was arbitrary **and not reproducible** — the tie-break runs
on `belief_id`, which is `uuid4`. `LoopResult.had_arbitrary_choice` surfaces it,
and arms may not be compared across separately-seeded stores when it is set.

## 6. Stage 3 measures

`spread(view, belief_count)` is the fraction of the web any carrier implicates.
`derange_supports(specs, seed)` rewires every `supports` edge at random,
preserving out-degree and leaving `contradicts` untouched — so a deranged web
holds the same conflicts at the same tension, and the only thing destroyed is
which belief entails which. Deleting edges instead would confound "the structure
was meaningful" with "there was less of it".

## 7. The surface

`read_dissonance` persists the signal; `run_attention_loop` persists a
`LoopTrace`; `get_loop_trace` reads one back. Errors are returned, never raised.
All three reach the CLI (`dissonance`, `run-attention-loop`, `loop-trace`) and
MCP, and the cross-process test drives one interpreter and reads from the next —
without it the CLI would only be pretending to expose the engine.

`process_reflective_turn` takes a dissonance read on **both sides** of belief
update. `update_beliefs` routes new contradictions through `assert_contradiction`
(experiment 3 §14), so by the time it returns a contradiction that arrived this
turn is already charged; a single read afterwards cannot tell a calm web from a
disturbed-and-immediately-priced one.
