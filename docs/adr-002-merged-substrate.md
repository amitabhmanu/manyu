# ADR 002 — Merged belief substrate with a thin dynamical layer

**Status:** accepted (2026-08-05)
**Supersedes:** the split mood path in [ADR 001](adr-001-belief-core.md)
**Evidence:** [experiment 2 results](experiments/02-merge-split-fork/results.md) — D3 complete, D2 mechanism stage only

## Decision

Manyu's affect is **derived from the belief store on demand**. What it feels, and
what it feels it *about*, are recomputed at read time from belief valence,
evidence salience, and the graph's `contradicts` / `supports` edges.

A **thin dynamical layer** sits on top, holding a blended valence and arousal so
mood carries between turns. It stores no belief references and no discrete
emotions.

## The loop

```
event → fast appraisal (biased by current mood)
      → belief evidence → belief store
belief store --query--> valence · arousal · carriers      (never stored)
belief store --query--> dissonance magnitude · carriers   (never stored)
      → thin layer: blend(prior, now) → mood (2 floats + momentum)
      → biases the next appraisal
      → inner voice narrates mood *and* carriers
```

**The largest structural consequence:** the inner voice moves from *upstream* of
mood to *downstream* of it. Mood used to be whatever `InnerVoiceComposer`'s
influence vector said it was — prompt-shaped, and carrying no belief references.
It is now a fact about the belief store, and the LLM consumes it.

## Constraints on the layer

1. **No per-event hard cap on magnitude.** Split's dissonance signal flattened
   because its channel bounds each event's delta — 0.45 at one conflict, 0.45 at
   three. Saturation may only come from a constant chosen to leave range across
   the operating region.
2. **Valence and arousal stay separate.** Arousal is intensity and is blind to
   valence; collapsing them reproduces the channel that failed to separate calm
   from threatened.
3. **No belief references in stored state.** This is what keeps the substrate
   authoritative, and it is the easiest line to cross for a plausible reason.

## What this rests on

Two D3 findings, both offline and deterministic. They are consequences of one
property — **split's affect is a stored number** — so they count once, not twice.

| Finding | Merged | Split |
|---|---|---|
| Naming what the dissonance is about | free, from the same query | needs a hand-written rule *and* a side-table |
| Grading it (1 → 2 → 3 conflicts) | 0.39 → 0.63 → 0.78 | 0.45 → 0.45 → 0.45 |

## What this does *not* rest on

- **The transfer finding is withdrawn.** The first D3 build showed merged
  generalising to unseen conflict shapes and split not; a steelman control proved
  that was an artifact of the author writing one detector with a traversal loop
  and the other without.
- **D2 never returned a verdict.** Only the mechanism was verified, and there the
  belief valences were authored by us.
- **The dynamics half of the prior is untested.** Lingering mood and revision lag
  were not among the two discriminators run. **The layer is adopted on design
  grounds, not on evidence** — merged alone demonstrably has no inertia, and
  inertia is what split was keeping.

**Counterweight, recorded so it is not lost:** merged's arousal moved 0.06 total
across calm, uncertain and threatening conditions. Merged needs two numbers where
split's single fear channel did both jobs.

## Parked

Available, not abandoned — fixtures, gates and pre-registered rules are in the
repository.

- **D2 verdict** — the one paid run. Every precondition is green.
- **A structurally-constrained transfer test** — needs a conflict-detection route
  that does not pass through a hand-written rule.
- **The four unrun discriminators** — lingering mood and revision lag would test
  this decision's dynamics half and set the momentum coefficient with evidence;
  regulation ("free won't") remains the one with safety consequences.
- **Discrete emotion channels** — the eight-channel `AffectState` is retained
  unchanged and untested. Whether those should also become queries is a coherent
  extension that neither discriminator examined. Retaining them is the
  conservative option, not the reasoned one.
