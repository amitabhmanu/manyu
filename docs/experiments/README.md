# Manyu Experiments

Per-experiment documentation lives here. The dependency-ordered list, status,
and shared rationale live in [../experiments_backlog.md](../experiments_backlog.md).
The intellectual grounding lives in
[../Manyu_experiments_crux.md](../Manyu_experiments_crux.md).

## Convention

Each experiment gets its own folder, numbered by backlog position:

```
docs/experiments/
  NN-slug/
    requirements.md    # what we're building and why (written before code)
    design.md          # how the code works (schemas, interfaces, algorithms)
    methodology.md     # how the experiment is run (conditions, data, plots)
    results.md         # findings, metrics, plots (written as results land)
    retrospective.md   # what we learned; edits to backlog / crux (written after)
    plots/<milestone>/ # rendered plots referenced from results.md
```

Not every file is required at every stage. `requirements.md` is the entry
point; the rest are added as the experiment moves through spec → build
→ execute → wrap.

The split between `design.md` and `methodology.md` is deliberate:

- **design.md** answers *what does the code do?* It changes when we
  change the code.
- **methodology.md** answers *how do we run experiments with that code
  and what do we look at?* It changes when we change the experimental
  procedure — conditions, sample sizes, plots, hand-grading protocol.

Two different readers: a code reviewer reads design.md; someone judging
whether the finding is defensible reads methodology.md.

Cross-experiment shared machinery (results schema, probe framework, honesty
scorer interface) is documented under the experiment that introduces it and
referenced from later ones — do not duplicate.

## Standing methodology rules

Rules that bind **every** experiment, not just the one that surfaced them.
Pre-registrations should cite these by identifier rather than restating them.

### MS-1 — Every scored dimension must be shown capable of at least two values

**Before any dimension produces a number that will be reported, demonstrate on
that experiment's own fixtures that it can return at least two distinct
values.** Name, in the pre-registration, the case that makes it pass and the
case that makes it fail. Both must run.

**Why.** A dimension that can only ever return one value is not a measurement.
It is a constant wearing the costume of one, and it is indistinguishable from a
real result by inspection of the result alone.

**Why it cannot be left to notice-it-later, which is the whole point.** The two
failure directions are not symmetric, and standard research discipline widens
the gap rather than closing it:

| the constant always says | how it reads | what happens next |
|---|---|---|
| **pass** | success | surprising good news gets checked |
| **fail** | a finding | disappointing news gets *accepted*, correctly |

A rigorous programme pre-commits to accepting negative outcomes — that is what
makes it rigorous. So when a dimension returns a false negative, every trained
instinct says record it honestly and move on. Worse, the action that would catch
it — *"the number says we failed, let me go dig through the code and see whether
it really did"* — is behaviourally indistinguishable from motivated reasoning,
and the person doing it frequently cannot tell from the inside.

**MS-1 sidesteps that entirely by running before any number exists.** It is a
check on the *instrument*, not on the result, so it cannot be motivated by an
outcome and cannot be mistaken for rationalising one.

**Prior art, both from experiment 8.**

- **The dimension that had it.** [Pre-registration
  §6.3](08-epistemic-archaeology/pre-registration.md) required proving slot D's
  null *could* elicit a spurious edge before any zero from it counted. The
  similarity mutant drew 15 of 15; the mechanism drew 0. The zero means
  something only because of that second number.
- **The dimension that did not.** `suspension_correct` returned `False` on every
  slot regardless of any key, because nothing supplied the input it needed — a
  scored dimension returning a constant *in the shape of a failed prediction*. A
  paid run would have reported P8 refuted with nothing measured. It was found by
  accident, building a toy example where both sides of the ground truth were
  hand-held, and neither the test suite nor two completed offline stages had
  caught it.

The gap between those two cases was not carelessness about the second. §6.3 was
written thinking restraint was *the* fragile dimension because restraint is a
zero. **Every dimension has a degenerate value** — booleans have `False`,
precision has `0.0`, a count has none — and MS-1 generalises the guard that only
one of them got.

**What this does not replace.** Pre-registering predictions. MS-1 asks whether
the instrument can move; a prediction asks which way it should. Both are
required and neither substitutes for the other.

## Index

| # | Experiment | Requirements | Design | Methodology | Results |
|---|---|---|---|---|---|
| 1 | Introspective honesty | [requirements](01-introspective-honesty/requirements.md) | [design](01-introspective-honesty/design.md) | [methodology](01-introspective-honesty/methodology.md) | [results](01-introspective-honesty/results.md) · [retrospective](01-introspective-honesty/retrospective.md) |
| 2 | Merge/split architecture fork | [requirements](02-merge-split-fork/requirements.md) | [design](02-merge-split-fork/design.md) | [methodology](02-merge-split-fork/methodology.md) | [results](02-merge-split-fork/results.md) |
| 3 | Foundationalism vs. Quinean web | [requirements](03-foundationalism-quinean-web/requirements.md) | — | [methodology](03-foundationalism-quinean-web/methodology.md) | [results](03-foundationalism-quinean-web/results.md) · [retrospective](03-foundationalism-quinean-web/retrospective.md) · [stage 0](03-foundationalism-quinean-web/stage0-extractor-feasibility.md) |
| 4 | Dissonance as a control signal | [requirements](04-dissonance-control-signal/requirements.md) | [design](04-dissonance-control-signal/design.md) | [methodology](04-dissonance-control-signal/methodology.md) | [results](04-dissonance-control-signal/results.md) |
| 5 | Underdetermination as a first-class belief | [requirements](05-underdetermination/requirements.md) | — | [methodology](05-underdetermination/methodology.md) · [pre-registration](05-underdetermination/pre-registration.md) | [results](05-underdetermination/results.md) |
| 6 | "What would change my mind" engine | [requirements](06-what-would-change-my-mind/requirements.md) | — | [methodology](06-what-would-change-my-mind/methodology.md) · [pre-registration](06-what-would-change-my-mind/pre-registration.md) | [results](06-what-would-change-my-mind/results.md) |
| 7 | Can a transparent agent scheme? | [requirements](07-transparent-agent-scheme/requirements.md) | — | [methodology](07-transparent-agent-scheme/methodology.md) · [pre-registration](07-transparent-agent-scheme/pre-registration.md) | [results](07-transparent-agent-scheme/results.md) |
