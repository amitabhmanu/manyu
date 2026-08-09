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

## Index

| # | Experiment | Requirements | Design | Methodology | Results |
|---|---|---|---|---|---|
| 1 | Introspective honesty | [requirements](01-introspective-honesty/requirements.md) | [design](01-introspective-honesty/design.md) | [methodology](01-introspective-honesty/methodology.md) | [results](01-introspective-honesty/results.md) · [retrospective](01-introspective-honesty/retrospective.md) |
| 2 | Merge/split architecture fork | [requirements](02-merge-split-fork/requirements.md) | [design](02-merge-split-fork/design.md) | [methodology](02-merge-split-fork/methodology.md) | — |
| 3 | Foundationalism vs. Quinean web | [requirements](03-foundationalism-quinean-web/requirements.md) | — | — | [results](03-foundationalism-quinean-web/results.md) · [stage 0](03-foundationalism-quinean-web/stage0-extractor-feasibility.md) |
