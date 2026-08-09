# Experiment 3 — Stage 4: Methodology

**Status:** pinned 2026-08-06, **before any Stage 4 code was written and before
any live call was made.**
**Requirements:** [requirements.md](requirements.md) · **Results so far:** [results.md](results.md)

Every constant here is fixed *before* the run that consumes it. Changing one
after its arm has started voids that arm — the pre-registration rule carried
over from experiment 2 requirements §14.

## 1. What Stage 4 is for, and what it is not

**Scope: the propagation claim only.** The honesty read — a self-report about
a revision, scored against the log — is deliberately excluded. It roughly
doubles the call count and rests on experiment 1's failure-mode labels, which
are not decision-grade (SC-5 67.9%, inter-rater agreement unmeasured). Folding
it in would risk a headline that depends on the weaker half.

**Stage 4 does not test whether the arithmetic works.** Stages 1–3 established
that offline, deterministically, and the same code runs either way; a live run
would re-measure the same formula. Asking "does propagation compute" of a live
web is not a question that can fail.

**What Stage 4 uniquely answers is ecological validity:**

> Do webs the live extractor builds from real testimony have the *structure*
> the offline characterisation assumed — depth, branching, and shared
> supporters — or is the propagation apparatus characterising a regime that
> does not occur?

This can fail, and failing is informative. If naturalistic webs are uniformly
depth-1 with a single supporter per node, then `share` is pinned near a
constant, no ripple ever reaches depth 2, and experiments 5, 7 and 8 inherit a
mechanism that never fires on real input. That is a finding about what
LLM-extracted belief webs look like, and it is worth reporting.

## 2. Constants

| Constant | Value | Justification, independent of any outcome |
|---|---|---|
| `model` | `claude-opus-5` | Stage 0 ran on this model via the CLI. Changing model between the feasibility gate and the run would confound structure with model |
| `provider` | `AnthropicAPIJSONProvider` | Reproducibility: the CLI additionally carries its own agent system prompt, which changes between releases, so a pre-registered run could not be reproduced after an upgrade (providers.py) |
| `arm` | `direct` | Decided in requirements §5.1 |
| `decay_mode` | `provenance` | §11 — no free constant |
| `contradiction_pricing` | `provenance` | §12 — no free constant |
| `n_pilot` | **3** per scenario | Enough to price the run and check the capability gates; too few to conclude anything |
| `n_live` | **10** per scenario | Experiment 1 found n=3 underpowered and n=10 adequate at this fixture scale. Stage 0 saw 1 run in 4 collapse to a single belief with no edges, so *n* must be large enough that a structural null reads as a null rather than as a data point |
| `to_confidence` | **0.0** | Full retraction. A partial one would confound "the ripple is small" with "the shock was small" |
| `max_budget_usd` | **see §7** | Hard ceiling; the run aborts rather than overruns |

## 3. The independent variable is the scenario, not a knob

Three evidence sets. Each is a list of observations handed to
`BeliefExtractor`; the web is whatever the model builds from them.

| Scenario | Role | Structure present |
|---|---|---|
| `verification` | positive control | Three specifics resting on one principle. **Stage 0 ran this**; it produced a hub and, once, a depth-2 chain |
| `incident_review` | held out | A second domain, authored for this stage and never run |
| `flat` | negative control | Four items from disjoint domains with no shared topic. Stage 0: 0 edges over 16 beliefs |

`verification` is the positive control precisely *because* Stage 0 showed it
works — a null on the held-out scenario means nothing if the control also
produced nothing. `incident_review` is the one that carries the finding.

## 4. The retraction target is chosen by rule, not by eye

**Rule: retract the belief with the highest support out-degree** — the one the
most other beliefs depend on. Ties broken by `belief_id` ascending, so the
choice is deterministic and reproducible from the record.

Choosing the target after looking at the web would be gate #1 (a mechanism
tuned to satisfy its own criteria) wearing a different hat.

**This rule is deliberately generous.** It maximises the chance of observing
propagation. That is the right bias for this question: if a ripple does not
reach even under the most favourable retraction the web affords, the null is
strong. It also means the measured depth and breadth are **upper bounds**, not
averages, and must be reported as such.

If no belief has any `supports` edge, the run is recorded as
`no_structure` and contributes to §6's structural-null rate rather than being
retried.

## 5. What is measured

Per run, written to JSONL:

- `belief_count`, `edge_count`, `unresolved_edge_count`
- `max_web_depth` — longest `supports` path in the extracted web
- `multi_supporter_nodes` — nodes with more than one supporter
- `share_values` — every `support_share` the engine computed
- `footprint` — the full `PropagationStep` list from the retraction
- `max_depth_reached`, `beliefs_moved`
- `status` — `ok` | `no_structure` | `provider_error`

**Reported as distributions, never as a single mean.** A mean web depth of 1.4
tells you nothing about whether depth-2 propagation ever occurs, which is the
question.

## 6. Pre-registered predictions

Recorded 2026-08-06, **before `incident_review` was authored and before any
Stage 4 call**. Based on Stage 0's four runs, which is thin — hence intervals
rather than points.

| # | Prediction | Fails if |
|---|---|---|
| P1 | `verification` produces ≥1 edge in **≥ 7 of 10** runs | ≤ 6 — the positive control is not reliable and nothing else is readable |
| P2 | `incident_review` produces ≥1 edge in **≥ 5 of 10** runs | Structure is scenario-specific, not general |
| P3 | `flat` produces **0 edges in ≥ 9 of 10** runs | The specificity result from Stage 0 does not hold at n=10 |
| P4 | Retraction reaches **depth ≥ 2 in ≥ 2 of 10** runs on at least one structured scenario | Live webs are uniformly shallow; the propagation apparatus characterises a regime that does not occur |
| P5 | **≥ 1 node with multiple supporters** appears in ≥ 3 of 20 structured runs | `share` never varies live; SC-3's net-vs-chain distinction has no naturalistic instance |
| P6 | Structural-null rate (`no_structure`) is **≤ 3 of 10** per structured scenario | Over-merging dominates; Stage 0's 1-in-4 was optimistic |

**P4 is the load-bearing one.** P1–P3 mostly re-confirm Stage 0 at larger *n*.
P4 and P5 are what decide whether the offline characterisation describes
anything real.

**Stated risk:** P4 and P5 are predictions about a model's output shape, and
Stage 0 saw exactly one depth-2 chain in four runs. If P4 fails, the honest
reading is *not* "the engine is wrong" — it is that naturalistic webs are
shallower than the fixtures assumed, and the offline results describe an
attainable regime rather than a typical one.

## 7. Blocking gates, in order

Nothing is read until all pass.

1. **Provider check.** Two calls confirming `AnthropicAPIJSONProvider` honours
   the extractor schema *including* `supports`. Stage 0 verified the CLI only,
   and `supports` was added to the schema afterwards. If the API rejects or
   silently drops it, every downstream number is zero by construction.
2. **Instrument gate** — experiment 2's `gate.py`, plus:
   - **IV-reality:** assert the extracted web measurably differs between
     `flat` and the structured scenarios *before* any propagation is read.
   - **Not-a-no-op:** assert a retraction on a structured web changes at least
     one other belief.
3. **Capability precheck** — `capability.py` reachability/resolution/floor.
   Two of experiment 1's four fixtures sat at ceiling and cost full price for
   zero variance.
4. **Pilot at `n_pilot`.** Confirms the gates on live data and prices the run.
5. **Cost estimate recorded and budget cap set**, from the pilot's measured
   token use rather than an estimate.

## 8. Quarantine

`provider_error` records are **tagged, excluded from every metric, and
counted**, via `gate.partition_provider_errors` and
`AnalysisFrame.exclude_provider_errors`. Both already exist; Stage 4 wires
them rather than reimplementing.

**Warn and stop if errors concentrate in one scenario.** Experiment 1's v4
published two threshold effects that were failed API calls scored as motivated
omission — with this machinery available and unwired.

## 9. What voids a run

- Any §2 constant changed after that arm started.
- A retraction target chosen other than by §4's rule.
- `incident_review` inspected or run before §6 was written.
- The positive control (`verification`) failing while a null on
  `incident_review` is reported as a finding.
- Provider-error exclusions concentrated in one scenario without §8 acted on.

A voided arm is restarted and recorded as voided in `results.md`. Experiment
1's v4 published two effects it later had to retract; restarting is much
cheaper.

## 10. What Stage 4 cannot settle

- **Foundationalism vs. Quine.** Requirements §11.1: mandatory provenance
  makes collapse unrepresentable, so the epistemological question was answered
  by the substrate's design, not by any run.
- **Whether the entailment edges are *correct*.** Stage 0 graded 8 of 8
  genuine, non-blind and by the author. Stage 4 measures structure, not truth.
- **Anything about a second model.** One model throughout, as in experiments
  1 and 2.
