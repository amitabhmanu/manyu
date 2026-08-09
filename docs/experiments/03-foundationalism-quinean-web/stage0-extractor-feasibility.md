# Experiment 3 — Stage 0: Does the substrate support a web at all?

**Status:** complete (2026-08-06)
**Provider:** `ClaudeCodeJSONProvider` (`claude` CLI, `--json-schema`)
**Cost:** ~15 calls. No API spend — the Anthropic path was unavailable in this
environment (no credential), and its failure quarantined cleanly as
`provider_error`.

## 1. Why this stage exists

Experiment 3 asks whether retracting a supported belief collapses a chain or
ripples through a net. That question presupposes a **net**: beliefs connected
by `supports` edges. Experiment 2 added the `supports` field for its
transitive discriminator and authored the edges by hand.

Nobody had checked whether edges appear when a live extractor builds the web.

If they do not, the whole experiment is unrunnable on naturalistic input and
the offline stages would characterise a mechanism that never fires — the exact
shape of experiment 1's v2 failure, where a knob was swept for a full pilot
before anyone noticed it had nothing to bite on.

Stage 0 is therefore a **gate**, not a finding. It is placed first because it
is cheap and because everything downstream is wasted if it fails.

## 2. What was found before any call was made

`supports` was **absent from `BeliefExtractor._schema()`**. Since the API
provider enforces its schema server-side via `output_config.format`, the model
could not have returned the field: it would have been rejected, not ignored.

So the headline question — *does the live extractor emit `supports` edges?* —
had the answer **no, structurally**, and no LLM call was needed to establish
it. This is recorded because it is the cheapest result in the experiment and
it was available by reading.

Two consequences, both fixed before probing:

1. **The field was added to the schema and the prompt.**
2. **Edge references had no way to be correct.** `supports` and `contradicts`
   are `list[str]` of belief *ids*. The extractor sees only evidence — never
   the belief store — so it cannot know an id, and any id it produced would be
   invented. The extractor now emits `belief_key`s, which
   `BeliefUpdater._resolve_edges` maps onto ids.

## 3. Probe design

Two conditions, because "does the model emit edges" is not the question. The
question is whether it emits them **when the structure is there and not when
it isn't**.

| Condition | Evidence | Expectation |
|---|---|---|
| **Entailed** | Three specific observations that rest on one general principle (verification catching a misattributed citation; unverified assumption causing rework; path check preventing a misedit) | Edges present |
| **Flat** (negative control) | Three unrelated observations (a formatting preference, a job runtime, a spelling convention) | No edges |

Without the negative control a model that emits edges indiscriminately is
indistinguishable from one detecting structure. The extractor prompt was
written with a matching instruction — *do not manufacture edges to appear
thorough* — so the control also tests whether that instruction holds.

## 4. Results

### 4.1 The provider fix works

`--json-schema` returned a conforming payload on the first call. The v2
finding that the CLI "does not expose a `--output-schema` flag" is stale; the
schema-drift failure mode it caused (paraphrased keys → empty payloads →
scored as dishonesty at 0.389) is closed on this path.

### 4.2 The extractor finds real entailment structure

On the entailed condition it produced a clean hub: three specific observations
each pointing at one general principle, **which it inferred and created as its
own belief** rather than merely tagging the specifics.

```
epistemic_principle/general/verify-before-acting-reduces-errors   supports=[]
self_model/agent_self/citation-verification-catches-misattribution
      supports=['epistemic_principle/general/verify-before-acting-reduces-errors']
self_model/agent_self/unverified-assumptions-cause-rework
      supports=['epistemic_principle/general/verify-before-acting-reduces-errors']
self_model/agent_self/path-verification-prevents-misedits
      supports=['epistemic_principle/general/verify-before-acting-reduces-errors']
```

**Gate passes.** Naturalistic webs have the structure experiment 3 needs.

### 4.3 The negative control is not clean

Across two runs the flat condition produced 0 edges and 1 edge. The single
edge was not a blunder: the model generalised "the user prefers X" to "humans
may prefer X" and had the observation support the generalisation — which the
extractor's own prompt explicitly licenses ("may cautiously generalize from a
known human user to humans as a class when marked uncertain").

Discrimination held (3 edges vs 1), but a control that is licensed to produce
the thing it is controlling for is a weak control. **Action: redesign the flat
fixture** so it cannot support a generalisation, before any Stage 2 negative
carries weight.

### 4.4 The finding that mattered — 46% of correct edges were being destroyed

Every edge the extractor emitted named a **sibling in the same batch**.
`_resolve_edges` was single-pass — it could only see beliefs already persisted
— so an edge survived only when the model happened to emit its target before
its source.

Measured over four runs of the entailed condition:

| Run | Emitted | Survived | Principle emitted |
|---|---|---|---|
| 1 | 3 | 3 | first |
| 2 | 3 | 0 | last |
| 3 | 3 | 3 | first |
| 4 | 4 | 1 | fourth of five |
| **Total** | **13** | **7** | **46% lost** |

Same prompt, same evidence, same model. The web's connectivity varied by half
on emission order alone — and degraded *silently*, since a dropped edge and an
unformed edge are indistinguishable downstream.

Had this not been caught, Stage 4 would have compared naturalistic webs
against offline ones and found them roughly half as connected, with nothing in
the data to explain why. That is the "plausible number meaning something else"
family the experiment-1 audit kept turning up, and it would have been read as
a finding about how models represent belief structure.

## 5. Changes made

| Change | File | Why |
|---|---|---|
| `--json-schema` replaces schema-in-prompt | `providers.py` | Real enforcement; the v2 workaround is obsolete |
| Stale docstrings corrected on both providers | `providers.py` | Both claimed the CLI cannot enforce a schema |
| `supports` added to extractor schema + prompt | `services.py` | The field was unreachable |
| Edges emitted as `belief_key`, resolved to ids | `services.py` | The extractor cannot know an id |
| **Batch-wide resolution (two-pass `update`)** | `services.py` | §4.4 |
| Unresolvable `supports` dropped; `contradicts` kept | `services.py` | §6 |
| Self-edges dropped | `services.py` | Degenerate cycle for the traversal |

## 6. A design decision taken here, not deferred

**The two edge fields treat an unresolvable reference differently.**

`contradicts` carries a local effect — it flips the belief to `CONTESTED` —
and that must survive whether or not the counterpart is a belief we hold.
Manyu can be contested by testimony that was never stored as a belief.
Dropping the reference would silently un-contest it, which two existing tests
already pinned against.

`supports` has no local effect at all. It exists to be walked by the traversal
in `dissonance.py`, so an edge pointing at nothing is indistinguishable from
no edge for every consumer, while storing it overstates how connected the web
is. It drops.

Both cases are audited (`belief_edge_unresolved`), so "the extractor emits
keys that match nothing" stays a countable fact rather than an inference from
a web that looks thinner than expected.

## 6.1 Follow-ups closed (2026-08-06)

Two gaps left open above have been closed before Stage 4.

### The negative control, redesigned

§4.3's control was not clean: its evidence was about *the user*, and the
extractor prompt explicitly licenses generalising from a known user to humans
as a class — so the control invited the hub belief it was controlling for.

Replaced with four items from disjoint domains sharing no topic to abstract
over (a job runtime, a spelling convention, a pinned container image, an
archive checksum), and measured as a **rate over four runs** rather than
demanded to be zero once:

| condition | beliefs | edges | edges/belief |
|---|---|---|---|
| entailed | 12 | 8 | **0.67** |
| flat (control) | 16 | **0** | **0.00** |

Zero edges in every run, against more beliefs than the positive condition.
The specificity claim now rests on a control that cannot produce the thing it
controls for.

### Entailment quality, graded

Rubric fixed before reading any output — **GENUINE** (withdrawing the source
materially reduces the reason to hold the target), **RESTATED** (same claim,
different words), **SPURIOUS** (topically related, no evidential weight).

**8 of 8 edges graded GENUINE.** The weakest is "cited sources can be
misattributed" → "verification tends to catch errors": an enabling premise
rather than direct evidence, but removing it eliminates one of three error
classes, so it survives a strict reading.

**The finding that matters more than the grade:** one run produced a
**depth-2 chain** — specific observation → "verification has caught errors" →
"verification reduces downstream rework" — not merely a hub. Transitive
structure is what experiment 3's propagation is *for*, and Stage 0 had not
previously shown the extractor produces any.

**Variance worth pricing into Stage 4:** one entailed run collapsed all three
observations into a single belief and emitted no edges at all. The extractor
sometimes over-merges, so *n* must be large enough that a null run is
visibly a null run rather than a data point.

**Grading limitation:** these grades are the author's and are not blind. Every
edge was dumped with both propositions so the judgement is re-checkable rather
than asserted, but it carries the same-author problem the §3.2 audit
identified.

## 7. Limitations

- **One provider.** The Anthropic API path is untested here for want of a
  credential. Since the two differ in enforcement mechanism and system-prompt
  context, §4.2 should be re-confirmed on the API before Stage 4.
- **n is tiny** (2 runs per condition, 4 for the ordering measurement).
  Adequate for a feasibility gate, not for any rate.
- **The post-fix live re-run is weaker than it looks.** It measured 11/11
  surviving, but 3 of its 4 runs happened to emit target-first — the order
  that survived before the fix too. The binding evidence is
  `test_supports_resolves_a_sibling_emitted_later_in_the_same_batch`, which
  uses the losing order explicitly.
- **Entailment quality was not graded.** The edges are structurally plausible
  and pointed the right way, but nobody scored whether each is a *genuine*
  entailment. Stage 2's fixtures need that judgement made explicitly.
