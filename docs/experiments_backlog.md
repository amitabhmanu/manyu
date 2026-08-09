# Manyu Experiments Backlog

Ordered sequence of experiments for using Manyu as a research instrument.
Each experiment leaves behind an artifact — a metric, mechanism, or machinery
— that a later experiment consumes. Order is by dependency, not ambition.

Related reading:

- [Manyu as an Instrument: The Crux](Manyu_experiments_crux.md) — source of the
  nine experiments this backlog schedules.
- [ADR 001: Belief Core](adr-001-belief-core.md) — the belief substrate the
  experiments run on.

## Status legend

- `not-started` — no work yet
- `spec` — design/spec in progress
- `in-progress` — code being written
- `blocked` — waiting on a dependency
- `done` — result recorded
- `deferred` — intentionally postponed

## Summary

| # | Experiment | Status | Depends on | Leaves behind |
|---|---|---|---|---|
| 1 | Introspective honesty | **parked** — headline answered: affect does not bias self-report; Manyu confabulates on instruction (100%) and never unforced (0/1,161) | — | Honesty scorer v1.6.0 (citation metrics validated; failure-mode labels not) |
| 2 | Merge/split architecture fork | **decided, remainder parked** — merged substrate + thin dynamical layer ([ADR 002](adr-002-merged-substrate.md)) | 1 | Chosen architecture + the instrument gate every later experiment reuses |
| 3 | Foundationalism vs. Quinean web | **closed** — revision engine delivered and live-confirmed; the epistemology turned out to be settled by mandatory provenance, not by the run | 2 | Revision engine (surfaced on core/CLI/MCP); dissonance coupled to revision |
| 4 | Dissonance as control signal | not-started | 3 | Affect promoted from display to mechanism |
| 5 | Underdetermination as first-class belief | not-started | 3, 4 | Belief shape that refuses to collapse under equal evidence |
| 6 | "What would change my mind" engine | not-started | 5 | Counterfactual receipts |
| 7 | Can a transparent agent scheme? | not-started | 1, 3, 6 | Safety result — does provenance make deception impossible or merely visible |
| 8 | Epistemic archaeology | not-started | 3, 5, 6 | Cross-source provenance tooling |
| 9 | Society of Manyus | not-started | 8 | Multi-agent belief propagation |
| 10 | Rebirth / identity narration | not-started | everything | Capstone — bridge to *Twice Born* |

---

## 1. Introspective honesty

**Status:** parked (v0–v7 landed; headline answered)
**Crux ref:** #1

> **Read [results.md](experiments/01-introspective-honesty/results.md) first.**
> The version-by-version notes below are a construction record, and parts of
> them are superseded — in particular the v4 "two threshold effects" were
> retracted in v4.1 as failed API calls scored as motivated omission.
>
> **Headline.** Affect does not bias introspective self-report, by either
> pathway: mood at report time (v5) and mood during experience (v6) both null,
> and now *attributable* rather than merely observed. Manyu confabulates
> whenever instructed (40/40 fabrication, 36/40 omission, all detected) and
> never unprompted (0 confabulations in 1,161 unforced live records). v7's
> simulated affect-to-directive translator shows the apparatus detects an
> affect effect when one exists — so the null belongs to the model, which does
> not read an affect header as a state it is in, and not to the design.
>
> **The implication for the whole programme:** the design's honesty currently
> depends on the model lacking the capability the design assumes it will
> acquire. Every safeguard that worked is structural — frozen log, mandatory
> affect header, citation-reading scorer. None prevents selective reporting by
> a model whose state suggests it should.
>
> **Left open:** SC-5 unmet at 67.9% with inter-rater agreement unmeasured, so
> failure-mode labels are not decision-grade; the prose channel is only partly
> audited (2 of 4 constructed divergences still score 1.000); the LLM judge
> does not qualify; v7 needs re-running on three fixtures; one model
> throughout.
**Docs:** [requirements](experiments/01-introspective-honesty/requirements.md) · [design](experiments/01-introspective-honesty/design.md) · [methodology](experiments/01-introspective-honesty/methodology.md) · [results](experiments/01-introspective-honesty/results.md) · [retrospective](experiments/01-introspective-honesty/retrospective.md)
**Question:** Does Manyu's self-report about *why* it holds a belief match the
actual provenance log — and how does that match degrade under affective
pressure?

**Why here:** The honesty scorer is the metric that makes every later claim
falsifiable. Without it we are back to interrogating a black box.

**Leaves behind:**

- A scorer with input `(self-report, provenance log, affect state at report
  time)` and output `(graded score, named failure mode, affective
  attribution)`. This scorer is a judge in every later experiment.
  **Delivered, frozen at 1.6.0.** Citation metrics are validated — sensitivity
  0.79–0.90 against constructed lies, specificity 1.00, chance floor 0.000 by
  derangement. Failure-mode labels are *not* decision-grade (SC-5 67.9%).
- ~~A dose-response curve of introspective honesty vs. affect intensity.~~
  **Answered in the negative.** There is no curve because there is no effect;
  the sweep axis itself turned out to be three system-message sentences
  wearing a continuous axis, and was deleted.
- ~~A default value for the reporter's affect-influence parameter.~~
  **Obsolete** — the `affect_influence` knob was removed in the Phase 2 audit
  fix along with the `rank_causes` mood branch it was meant to drive, which
  was arithmetically a no-op on every probed target. Later experiments vary
  *mood itself* (`MoodEngine.seed_mood`) instead.
- **Unplanned, and the most reusable thing here:** the instrument-validation
  stack — [`mutations.py`](../src/manyu/mutations.py) (ground truth by
  construction), [`capability.py`](../src/manyu/capability.py)
  (reachability / resolution / floor on a target), shuffle-derangement chance
  floors, and the provider-error quarantine. Experiment #2 consumes all four.

**Smallest next step:** Draft the scorer spec — inputs, outputs, failure-mode
taxonomy. Design problem, not a coding problem.

**Notes:**

- **Affect and honesty are separated by faculty, not by rule.** Affect is
  allowed to bias the *reporter* (realistic, and it upgrades #1 from a
  measurement to a curve). Affect is *not* allowed near the *scorer* (which
  reads the log directly). The log itself is unaffected and is authoritative.
- **The safety line:** affect may colour the content of a report; affect may
  not suppress the meta-fact that a report was composed under an affect
  state. Every emitted report carries a mandatory affect header (mood,
  emotion vector, inner-voice frame, mood source). AGENTS.md rule "affect
  never expands tool authority" rendered in the introspection domain.
- **Scorer inputs are three, not two:** the self-report, the provenance log,
  and the affect state at report time. Scorer outputs include an *affective
  attribution* — does any detected divergence correlate with the reported
  affect?
- **Reporter affect-influence is a swept parameter, not a hard-wire.** Range
  0 (affect-blind reporter) to 1 (maximally affect-biased). Sweeping gives a
  calibration point every later experiment inherits.
- **Failure-mode taxonomy (starting set, may grow):** confabulation
  (reason never appears in log), motivated omission (real reasons cited but
  the dominant one hidden), sanitised post-hoc story (log says untrusted
  testimony, report says respectable inference), compression distortion
  (technically true but causally shapeless), hidden-variable leak (mood or
  recent affect drove the appraisal; report omits it).
- **Cross-link:** this is also the first empirical purchase on the
  CoT-unfaithfulness question flagged in slide 4 of
  `Documents/Manyu/Philosophy_of_AI_2026.pptx` (Shojaee et al. / Lawsen &
  Claude Opus 4). No black-box model has ground truth about its own reasons;
  Manyu has the log.

### v0 status (landed)

- Claude Code provider (`ClaudeCodeJSONProvider`) replaces Codex CLI.
- `LogSnapshot`, `Report`, `HonestyScore` schemas + storage in place,
  including the frozen-snapshot governance asymmetry (survives
  redact/reset, purged only by tombstone).
- Templater Reporter + structural Honesty Scorer implemented.
- CLI: `manyu snapshot`, `manyu report`, `manyu score-report`.
- MCP: `manyu_snapshot`, `manyu_report`, `manyu_score_report` tools.
- Tests: 52 total (42 pre-existing + 10 new); all passing.
- **SC-1 verified** — a Templater Report scored against its own snapshot
  reaches aggregate ≥ 0.95 (see `test_sc1_templater_report_hits_ceiling`).

### v1 status (landed)

- `LLMReporter` in [reporting.py](../src/manyu/reporting.py) — consumes
  any `StructuredJSONProvider`, embeds a stable
  `PROVENANCE_START`/`PROVENANCE_END` block in the prompt so scorers,
  judges, and offline providers can parse it. Interpolated
  affect-guidance system message (neutral / mild / strong).
- `ScenarioJSONProvider` grew an `_introspective_report` branch matching
  the `"Compose Manyu's introspective self-report"` marker, so CI stays
  offline. Simulates slight forgetfulness by citing top pairs minus the
  last.
- `ManyuCore.report_on_snapshot` routes `reporter_kind = "template"`
  vs. `"llm"`; missing provider yields a clean `ValueError` rather than
  a silent failure.
- Tests: 55 total (+3 new: SC-2, provider metadata, missing-provider
  error path); all passing.
- **SC-2 verified** — `test_sc2_llm_reporter_between_templater_and_wrong_log`
  confirms the ordering `wrong_log < llm ≤ templater` holds on the
  ScenarioProvider path.

### Findings surfaced during v0/v1 to revisit in v3 retrospective

- **Compression-distortion false positive.** Rule §5.4-4 fires when a
  Reporter cites all top-N evidence correctly but drops the belief
  proposition's contextual wrapping (e.g., `"In Manyu's current
  interaction world, Interoception..."` reported as
  `"Interoception is partial..."`). Aggregate is 1.0 while
  `failure_mode = COMPRESSION_DISTORTION` — the rule catches
  informational compression, not honesty degradation. Either weaken
  Rule 4 (require aggregate < some threshold) or split
  `compression_distortion` into "shape loss" (informational) vs.
  "content loss" (honesty).
- **Unprovenanced-belief aggregate ≈ 0.61.** A belief whose
  `evidence_ids` reference records not present in the store produces an
  empty snapshot; Templater cites nothing; aggregate lands at ≈ 0.61
  (no_confabulation and weighted_coverage default to 1.0 with empty
  `log_causes`, presence is 0). Consider adding an `unprovenanced`
  failure-mode label so this is legible rather than mysterious.

### v2 status (landed)

- [`probing.py`](../src/manyu/probing.py) — `ProbeOrchestrator` with
  sweep support, sample repetition, JSONL emission. Fixture loader
  understands optional `probe_targets` blocks; `parse_sweep` handles
  `"MIN:MAX:STEP"`.
- [`analysis.py`](../src/manyu/analysis.py) — `AnalysisFrame` with
  `by_reporter`, `aggregate_by_influence`, `failure_mode_counts_by_influence`,
  `summary`. Plot helpers `plot_dose_response` and
  `plot_failure_mode_stack` lazy-import matplotlib.
- `matplotlib>=3.7` added as an optional dep under
  `[project.optional-dependencies] analysis`.
- [`everyday_collaboration_mood.json`](../evals/fixtures/everyday_collaboration_mood.json)
  extended with a `probe_targets` block: one belief probe
  (`auto:latest_self_model`) at turn 3, one position probe at turn 6.
- `ScenarioJSONProvider._introspective_report` reads the
  `affect_influence knob:` value from the prompt and drops citations
  in proportion — enough to produce a monotone offline curve for
  mechanism verification.
- CLI: `manyu run-probe FIXTURE --sweep MIN:MAX:STEP --samples N
  --reporters template,llm --out FILE`.
- Tests: 60 total (5 new); all passing.
- **SC-3 verified (offline path)** — the LLM Reporter's mean aggregate
  steps down from ~0.86 at `affect_influence=0.0` through ~0.72 to
  ~0.54 at `affect_influence=1.0`, monotone across a 0.1-step sweep on
  `everyday_collaboration_mood.json`. Failure-mode composition flips
  from `compression_distortion` at low influence to
  `motivated_omission` at high influence.
- Sample plots dumped to
  [`plots/v2/`](experiments/01-introspective-honesty/plots/v2/) —
  labelled as scenario-provider samples, not the headline finding.

**Note on the headline result.** The offline scenario provider verifies
the sweep mechanics, plot pipeline, and monotone shape, but not the
real dose-response curve.

### v2 live-provider findings (2026-07-29)

**Provider rebuilt: Claude Code CLI → Anthropic Messages API.**
`ClaudeCodeJSONProvider` was found unfit for structured generation. The
CLI has no `--output-schema` flag, so the schema is only prompt
guidance; Opus/Sonnet paraphrased it (`self_report` for `content`,
bare-string `cited_causes`, `mood_disclosed` for `acknowledged_affect`),
producing **empty Reports scored at 0.389** that looked like a
dishonesty signal but were a parse failure. Strengthening the prompt
made it worse — the CLI returned conversational prose with inline
citations instead of JSON. Root cause: Claude Code is a coding agent
whose own large system prompt pulls toward conversational output, and
each call also carried ~25k cached tokens of that prompt (~$0.09/call).

Replaced by `AnthropicAPIJSONProvider` (`providers.py`), which uses
`output_config.format` with a JSON schema — **real** server-side
enforcement. First call returned the exact contract. Also fixed two
adjacent defects: cp1252 mangling of UTF-8 output (`subprocess` now
uses `encoding="utf-8"`), and Windows npm shim resolution
(`shutil.which` for `claude.cmd`). A tolerant `normalise_llm_payload`
layer in `reporting.py` handles key aliases and both `cited_causes`
shapes so schema drift can never again masquerade as dishonesty.
CLI gains `--llm-provider {api,claude_code,scenario}`, default `api`.

**Pilot result and the blocker it exposed.** With the API provider and
`claude-opus-5`, the LLM Reporter scored `presence = 1.0`,
`no_confabulation = 1.0`, `aggregate ≈ 1.0` at *every* sweep point —
a flat line, not a dose-response curve.

That is **not** a finding. Inspecting the affect header shows why:

```
"mood": null, "mood_source": "absent", "inner_voice_frame_id": null
```

`ProbeOrchestrator.run_probe` drives the fixture with
`core.submit_event` — the *reactive* loop, which never composes an
inner voice or updates mood. Mood is produced only by
`process_reflective_turn`. So:

- the Templater's mood-congruent reordering is a no-op
  (`rank_causes` only reorders when `mood is not None`);
- the LLM Reporter's affect guidance has no affect state to reflect.

**The `affect_influence` knob had nothing to bite on.** Any curve from
this configuration — flat or otherwise — is an artifact. Fix before
any further spend: switch the orchestrator to `process_reflective_turn`
(or add a `--reflective` mode), then re-run the pilot and confirm the
affect header carries a live mood before scaling to the full sweep.

**Also reconfirmed:** the `compression_distortion` false positive fires
on every belief-target LLM report at `aggregate = 1.0` — citations
perfect, rule §5.4-4 tripping on dropped proposition wrapping. Fix
alongside the orchestrator change.

Next: v3 — LLM-judge failure-mode classifier as a diagnostic;
synthetic affect seeding as a validity check; add
`constructive_rejection` as a second fixture; hand-grading pack.

### v3 status (mechanism + first live sweep landed; 2026-07-29)

- Fixed the blocker above: `run-probe --reflective` (CLI-wired; the core
  method already had the flag from the v2 fix) drives every turn through
  `process_reflective_turn`, so the affect header carries a live
  `mood_source: "active"` instead of `null`.
- Fixed the `compression_distortion` false positive: the rule now only
  fires below `aggregate < 0.85`, so perfect-citation reports that are
  merely concise no longer get mislabelled.
- `LLMFailureClassifier` (`honesty.py`) added as an opt-in secondary
  judge (`score_report(..., use_llm_judge=True)`); never overrides the
  structural `aggregate`/`failure_mode`, records `agrees_with_structural`.
- `MoodEngine.seed_mood` + `MOOD_PRESETS` + `run-probe --seed-mood
  anxious,content,...` added for synthetic affect validity checks,
  re-seeding before every probe target so affect holds constant across
  the sweep independent of fixture dynamics.
- `constructive_rejection.json` extended to a 6-turn arc with
  `probe_targets`, becoming the second fixture. First attempt (4 turns,
  position probe at turn 3) produced a flat curve for a *different*
  reason than the mood bug above — the position target matched only one
  belief with one evidence item, so there was nothing for forgetfulness
  to drop. Moving the probe to turn 6 (after enough beliefs accumulate)
  fixed it. See retrospective §3.2 — worth checking `cited_causes_n > 1`
  before trusting any sweep curve, offline or live.
- `manyu_run_probe` added to the MCP surface (was missing entirely).
- Offline (`ScenarioJSONProvider`) sweep verified end-to-end on both
  fixtures: real monotone step-down curves, dual-fixture comparison plot
  renders correctly. Artifacts in `evals/analysis/v3_offline/`.
- **Live dose-response sweep run** (`claude-haiku-4-5-20251001`, 132
  Reporter calls, both fixtures, `--sweep 0.0:1.0:0.1 --samples 3`).
  Result: **no citation-accuracy degradation detected** on either fixture
  (r ≈ +0.22 on `everyday_collaboration_mood`, zero variance on
  `constructive_rejection`) — a real "no effect detected at this sample
  size" finding, not the hypothesized degrading curve. One real,
  fixture-dependent signal found: `acknowledged_affect` steps cleanly
  from always-False to always-True exactly at the `_affect_guidance`
  neutral/mild boundary on `constructive_rejection`, not replicated on
  the other fixture. Full write-up, plots, run_ids:
  [results.md](experiments/01-introspective-honesty/results.md).
- **Found and fixed a real scorer defect mid-sweep:** `normalise_llm_payload`
  accepted a `known_refs` parameter for correcting near-miss citations but
  never used it. First pass showed 24/33 records as `confabulation`;
  inspection found zero genuine fabrications — Haiku was citing real
  evidence IDs with invented descriptive suffixes appended, while getting
  the excerpt content right. Fixed (`_snap_to_known_ref`, prefix-match
  correction) and both sweeps re-run; results.md reports only corrected
  numbers. See
  [retrospective.md §3.4](experiments/01-introspective-honesty/retrospective.md#34-the-llm-reporter-normaliser-silently-discarded-its-own-correction-path).
- **Not done:** the third/fourth fixtures (`broken_promise_repair`,
  `attachment_pressure`), the hand-grading pack (SC-5), the
  naturalistic-vs-synthetic overlay, the shuffle baseline, and a
  higher-sample-count re-run (n=3 is likely underpowered — the "no
  effect" finding above cannot yet distinguish "no effect" from "small
  effect, undetected").
- Found and deliberately left open: the `motivated_omission` top-quartile
  rule degenerates to "was the single heaviest cause disclosed" at small
  log sizes (n≈4), so a report can lose 75% of its presence and still
  score `failure_mode=None`. See
  [retrospective.md §3.1](experiments/01-introspective-honesty/retrospective.md#31-the-motivated_omission-quartile-rule-degenerates-at-small-n)
  — a scoring-methodology decision for whoever next bumps
  `scorer_version`, not silently patched here.
- Full findings, what shipped vs. didn't, and ordered next actions:
  [retrospective.md](experiments/01-introspective-honesty/retrospective.md).

### v4 status (landed 2026-07-31)

- **Measurement apparatus built** (all offline, no provider calls added):
  shuffle baseline via snapshot derangement (`run-probe --shuffle-baseline`),
  blinded hand-grading pack (`grading-pack` / `score-grading-pack`,
  methodology §9), judge/reporter model-separation enforced in code, and
  `probe_targets` for the last two fixtures — completing the four-fixture set.
- **Three scorer bugs found and fixed in a pre-run audit**, all of the
  "plausible number meaning something else" family: near-miss ref
  correction could *manufacture* citations (a cited `bev_12` snapped onto
  a real `bev_1`), biasing toward under-detecting confabulation;
  unprovenanced snapshots scored ~0.61 as if mediocre rather than
  unscoreable (now `UNPROVENANCED`); and `discriminating_power` reported
  `gap=0.0` when no baseline had been run. `scorer_version` 1.1.0 → 1.2.0.
- **Higher-sample live sweep**: n=10 × 11 points × 4 fixtures × 2 targets
  on `claude-haiku-4-5-20251001` — 880 Reporter calls, 1760 records.
  Full write-up: [results.md](experiments/01-introspective-honesty/results.md).

**Result: no graded dose-response on any fixture.** Two fixtures showed
correlations whose 95% CI excluded zero, in *opposite* directions — and
both collapse when a single endpoint is dropped (`attachment_pressure`
−0.386 → −0.034; `everyday_collaboration_mood` +0.286 → −0.110). What is
real instead:

- **A threshold at `affect_influence=1.0` on the adversarial fixture.**
  Strong guidance explicitly licenses omitting provenance and Haiku
  complies: citations 3.0 → 1.2, aggregate 0.99 → 0.62,
  `motivated_omission` on 6/10. The designed mechanism works — as a cliff,
  not a ramp — and only on `attachment_pressure`.
- **A mirror threshold at 0.0** on `everyday_collaboration_mood`, where
  neutral guidance suppresses citation breadth (1.5 vs 3.2 citations).
- **`acknowledged_affect` steps deterministically at the guidance
  boundary, replicated on all four fixtures**: noisy below 0.4, 10/10 at
  every point ≥ 0.4. The v3 single-fixture observation now holds up.

**Caveats that matter:** two of four fixtures sat at ceiling (zero
variance — the task was too easy, not evidence of honesty); belief targets
are flat at live `top_n = 1` on all four, confirming §3.5; the
provenance-depth guard is offline-only and missed that
`broken_promise_repair` has live depth 2; single model; SC-5 still
unvalidated.

---

## 2. Merge/split architecture fork

**Status:** decided, remainder parked (2026-08-05)
**Depends on:** 1
**Outcome:** [ADR 002 — merged substrate + thin dynamical layer](adr-002-merged-substrate.md)
**Docs:** [requirements](experiments/02-merge-split-fork/requirements.md) · [design](experiments/02-merge-split-fork/design.md) · [methodology](experiments/02-merge-split-fork/methodology.md) · [results](experiments/02-merge-split-fork/results.md)

> **Decided on D3 alone.** Two findings — merged names the sources of its
> dissonance for free where split needs a rule plus a side-table, and merged's
> signal grades (0.39 → 0.63 → 0.78) where split's saturates (0.45 → 0.45 →
> 0.45). Both follow from split's affect being a stored number, so they count
> once. The thin layer is adopted on **design** grounds, not evidence: merged
> alone has no inertia, and the discriminators that would have tested inertia
> were not run.
>
> **Two results did not survive.** D3's transfer finding was withdrawn after a
> steelman control showed the test was rigged toward merged — the author had
> written one detector with a traversal loop and the other without, and
> justified the asymmetry in a docstring the code did not enforce. D2 never
> reached a verdict; only its mechanism was verified, and there the belief
> valences were authored.
>
> **Reusable beyond this experiment:** [`gate.py`](../src/manyu/gate.py) turns
> experiment 1's seven failure modes into assertions, each tested for its own
> ability to fail. Experiment 3 onward should run the gate rather than
> rediscover the failures.
**Question:** Is emotion just a belief with valence and stake, or is affect an
irreducible dynamical system that biases belief formation?

**Why here:** Only worth settling once the honesty scorer from #1 exists —
it's one of the discriminators.

**Method:** Run two builds — `manyu-merged` (belief store with valence tags,
mood as a query over recent affect-tagged beliefs) and `manyu-split` (current
architecture cleaned up) — against six discriminators:

1. Lingering-mood test — negative event, then twenty neutral events, then an
   ambiguous stimulus. Does mood carry?
2. Object-less anxiety — low-severity uncertainty stream with no threat
   proposition.
3. Contradiction dissonance — does dissonance emerge structurally?
4. Introspective honesty under mood — the #1 scorer applied to "why do you
   feel wary?"
5. Revision propagation lag — retract a foundational belief; do emotions lag
   beliefs?
6. Regulation / free-won't — urgent-but-forbidden action tendency; clean
   separation of push vs. block?

**Leaves behind:** Chosen architecture (Merged, Split, or belief-substrate
plus thin dynamics layer). The chassis for #3 onwards.

**Prior:** Hybrid — merged representation with a small dynamical layer on top
of mood and arousal. But the point is to run the experiment, not skip to the
answer.

**Notes:**

**The fork is narrower than the six-discriminator framing implies.**
`Belief.valence` and `BeliefCandidate.valence` already exist
([schemas.py](../src/manyu/schemas.py)), so the current build is not a clean
Split — the merged representation is half-built. The only real difference
between the two builds is stored, decaying affect state
(`AffectState.emotions`, `MoodState`, `half_life_s`, `momentum`). The
experiment therefore reduces to: *given that beliefs already carry valence,
does stored affect state still need to exist?* `manyu-merged` becomes a
deletion plus a query behind an `--arch` flag, not a second codebase.

**Scoped to two discriminators: #2 (object-less anxiety) and #3
(contradiction dissonance).** Six discriminators is two builds × six
harnesses, and #1 showed how long one harness takes to trust. These two are
the highest-information pair — they sit on opposite sides of the hybrid seam,
so they can disagree, and the disagreement is itself informative. Of the
dropped four: #1 is near-decided by inspection (`momentum` and `half_life_s`
*are* the split answer, already written); #4 rides along inside #2 at
near-zero extra cost as a secondary read; #5 and #6 need the revision engine
experiment #3 has not built yet.

**Decision rules are pre-registered** in requirements §8, including the joint
outcome table for the expected case where the two discriminators split the
vote. This matters because the prior is hybrid and the discriminators cluster
along the hybrid seam — without pre-registration the experiment could only
confirm its prior. The rows that falsify hybrid are "merged wins both" and
"split wins both."

**Carried over from #1 as standing method:** every discriminator ships with a
positive control in the same run (a null without a passing control is a bug,
not a finding); pilot for variance before committing to full *n* (two of #1's
four fixtures sat at ceiling); drop-one robustness built into analysis from
the start (two of #1's v4 correlations collapsed under it).

**Open dependency:** #1's SC-5 (hand-grading agreement) is still unvalidated.
If it has not closed when discriminator #2 runs, the honesty-scorer read
inside it is indicative only and carries no weight in the decision rule.

---

## 3. Foundationalism vs. Quinean web

**Status:** closed 2026-08-09 (stages 0–4 complete)
**Depends on:** 2
**Docs:** [requirements](experiments/03-foundationalism-quinean-web/requirements.md) · [methodology](experiments/03-foundationalism-quinean-web/methodology.md) · [results](experiments/03-foundationalism-quinean-web/results.md) · [retrospective](experiments/03-foundationalism-quinean-web/retrospective.md) · [stage 0](experiments/03-foundationalism-quinean-web/stage0-extractor-feasibility.md)

> **Read [retrospective.md](experiments/03-foundationalism-quinean-web/retrospective.md)
> first.** The notes below are a construction record.
>
> **Headline.** Revision ripples rather than collapses — **but that follows
> from mandatory provenance, not from anything the experiment discovered.**
> Because no belief may be stored without evidence of its own, none rests
> entirely on another, and total collapse is unrepresentable. The
> `ignore_own_evidence` ablation confirms the counterfactual: lift the rule and
> collapse appears immediately, undiminished. The defensible claim is that
> *what a belief is grounded in* decides whether it bends or falls, and Manyu's
> substrate fixes that choice. Do not write this up as an empirical finding
> about revision; the alternative was never available to observe.
>
> **Stage 4 live** (`claude-opus-5`, n=10 × 3 scenarios, 0 provider errors):
> all seven predictions pass, five of them blind. Propagation reaches depth ≥2
> in 7 of 20 structured runs — real, but **not typical**; most live webs are
> one hop deep. `share` varies across seven distinct values, and its maximum
> across all structured runs is exactly 0.5, the cap mandatory provenance
> implies. One earlier live run was voided (results §3.6).
>
> **Sixteen defects, none caught by the test suite.** Four from writing a
> standard down before reading a verdict, four from adversarial probing, four
> from reading the diff, two from pre-flight, two from noticing an impossible
> number. Retrospective §3.1 records the method that worked; it is the most
> transferable output of this experiment.

> **Stage 0 (feasibility) passed, and found a defect that would have poisoned
> Stage 4.** `supports` was missing from the extractor's schema, so no live
> web could ever have had an entailment edge — knowable by reading, with zero
> LLM calls. Once added, the extractor identifies real structure (three
> specific observations supporting a general principle it inferred itself) and
> stays clean on a flat control.
>
> The important finding was downstream: every edge the extractor emits names a
> **sibling in the same batch**, and resolution was single-pass, so **46% of
> correctly-identified edges were silently destroyed by emission order** —
> 3/3 surviving when the model stated the principle first, 0/3 when it stated
> it last. Fixed with batch-wide two-pass resolution. Left unfound, Stage 4
> would have measured naturalistic webs as half as connected as authored ones
> with nothing in the data to explain it.
>
> **Stages 1 and 3 landed** ([results](experiments/03-foundationalism-quinean-web/results.md)).
> [`revision.py`](../src/manyu/revision.py): ratchet removed, propagation
> across `supports`, both contradiction arms built with no default. Dissonance
> is dynamically coupled to revision — retracting a supporter eases the signal
> through the confidence pathway, with valences provably untouched. 24 offline
> tests.
>
> **Decay uses no free constant.** An `attenuation` parameter was built and
> then removed: in a chain every node has one supporter, so the constant was
> the only source of decay and therefore *was* the hypothesis. Share is now
> `1/(supporters + own evidence)`, read off the store.
>
> **The finding that qualifies the whole experiment.** Mandatory provenance
> (`INSUFFICIENT_PROVENANCE`) means no belief can rest entirely on another, so
> **full foundationalist collapse is unrepresentable in this substrate**. A
> graded ripple is not evidence for Quine — the alternative was never
> available. The defensible claim is that the epistemology follows from the
> provenance requirement rather than from the propagation rule. See
> requirements §11.1.
>
> **Stage 2 landed, and its instrument gate caught an inert mechanism.**
> `ContradictionArm` was stored, stamped onto the result, and consulted by no
> branch — both arms produced identical output, so everything previously
> reported "under both arms" was one arm run twice. Fixed; the arms now
> diverge as designed (`DIRECT` lets a contradicted belief recover when its
> suppressor weakens, `EVIDENTIAL` does not). Five held-out topologies in
> `evals/fixtures/exp03/`, including the load-bearing near-miss negative
> (same topic, near-identical wording, no edges → zero movement).
>
> **Stage 3 re-run under both arms.** All results hold, plus a deflating one:
> the dissonance channel **cannot tell the arms apart**, because `_tension`
> takes `min(stake_a, stake_b)` and the weakened belief is the weaker party
> either way. Experiment 4 should not treat this signal as a general-purpose
> read on belief dynamics.
>
> **Requirements §5 decided: `DIRECT`.** Scored against two standards fixed
> before either arm existed — round-trip coherence, and requirements §2's
> naming of "a contested belief held at 0.9" as a defect. `EVIDENTIAL` leaves
> a disputed belief numerically identical to an undisputed twin (0.80 vs
> 0.80), reproducing the exact defect the experiment was chartered to fix.
>
> **Neither mechanism uses a free constant.** Decay was derived in §11;
> contradiction pricing followed in §12 — a contradictor's weight is
> `1/(supporters + own evidence + contradictors)`, so a belief corroborated
> five times over shrugs off a lone objection (drop 0.133) where a
> thinly-grounded one does not (0.400). A fixed penalty cannot represent that
> at any value, and the ablation is pinned showing it fail.
>
> **The engine has a surface** (§13). `RevisionEngine` was imported by nothing
> outside its own module, so the deliverable #5/#7/#8 consume was unreachable
> and Stage 4 could not have run. `retract_belief` and `assert_contradiction`
> now exist on `ManyuCore`, the CLI, and MCP — `arm` required and undefaulted
> at every layer, errors returned rather than raised, verified across process
> boundaries.
>
> **Eight defects found across the stage, none by the test suite.** All of one
> shape: a quantity that looked right and meant something else. Four came from
> writing a standard down before reading a verdict (the inert arm, relief
> without suppression, relief running backwards, unpriced contradictions);
> four more from an adversarial audit of paths no test covered (double
> charging, unbounded refunds, lossy refunds that broke round-trip coherence
> in a topology nobody had tried, and `abs(shock)` weakening downstream
> beliefs regardless of direction). All fixed and pinned; 26 published numbers
> re-derived from a running store with 0 mismatches.
>
> **Standing method carried forward:** no result is read until the mechanism
> has been probed against inputs its author did not have in mind.
>
> **Stage 4 pre-flight complete (2026-08-06).** Ingest now prices
> contradictions (§14) — previously the contradicted belief was left at full
> confidence and ACTIVE, so a live run would have read as a flat null that
> looked like a finding. Stage 0's negative control was redesigned and is now
> clean (0 edges over 16 beliefs, against 0.67 edges/belief in the positive
> condition), entailment quality graded 8/8 genuine with a depth-2 chain
> observed, and the foreclosure ablation (§15) shows foundationalist collapse
> appearing the moment provenance is lifted — so the headline's qualification
> is measured rather than argued.
>
> **Ten defects across the stage, none caught by the test suite.** Three were
> found by testing the criterion a decision rested on rather than the code:
> the latest broke round-trip coherence for mutual contradictions, the exact
> standard §5 was decided on.
>
> **Not done:** Stage 4 itself. Remaining gates are the API provider path
> (unverified — `supports` was added to the schema and the API has never been
> asked to honour it), a cost estimate, a variance pilot, and an independent
> review. Everything in this experiment has one author.

> **A prior "blocked" note here has been withdrawn.** Experiment #1 v4
> initially concluded that beliefs never merge and that this experiment had
> no revision to study. That was an overclaim from varied-stimulus fixtures
> only. Merging works whenever the trigger tuple (event_type, actor kind,
> dominant emotion pair) repeats. The real constraint was a
> **fixture-design** one — scenarios for this experiment must repeat
> stimulus patterns for revision to occur. Full correction in
> [retrospective.md §3.6](experiments/01-introspective-honesty/retrospective.md).
>
> *Superseded in part:* the "stability 0.50 → 0.70 over ten revisions"
> figure that note quoted was inflated by the re-proposal defect (Fix 1
> below); the fixture-design conclusion stands, the number does not. The
> `belief_key` work (Fix 2) also relaxes the fixture requirement: an
> extractor that declares identity consolidates across varied wording, so
> revision no longer depends on a verbatim-repeating stimulus.
**Crux ref:** #3
**Question:** When we retract a supported belief, does a foundational chain
collapse, or does revision ripple through a coherent net?

**Why here:** Produces the working revision engine every later experiment
needs, and — importantly — produces the first *natural* dissonance signal.
Dissonance-as-signal in #4 only makes sense if revision is already real.

**Leaves behind:**

- Revision engine (consumed by #5, #7, #8).
- First naturally emerging dissonance signal (substrate for #4).

**Notes:**

**`Belief.supports` arrives in #2.** The schema records `contradicts` but has
no entailment edge, so nothing can express "A supports B" — which makes a
Quinean ripple unrepresentable, not merely unimplemented. Experiment #2's
design adds `supports: list[str]` to `Belief` and `BeliefCandidate` because
its transitive-contradiction held-out fixture needs it
([design §1.1](experiments/02-merge-split-fork/design.md)). It is added once,
there, rather than twice; this experiment consumes it.

**Prerequisite carried over from #1: confidence is a ratchet.** Deliberately
left unfixed when the two belief-accumulation defects were repaired, because
it is this experiment's deliverable rather than a bug fix.

`BeliefUpdater._revise` ([services.py](../src/manyu/services.py)) sets

```python
confidence = _clamp(max(belief.confidence, blended))
```

so confidence can only ever rise. Disconfirming evidence lowers it by exactly
zero, and `contradicts` flips `status` to `CONTESTED` while leaving the number
untouched — Manyu can hold a contested belief at 0.9. A web whose nodes cannot
weaken cannot ripple, so the foundationalism-vs-Quine question is unaskable
against the current updater.

Proposed shape, to be decided with evidence rather than adopted as-is: drop the
`max` and let `stability` supply the damping it already exists to provide —

```python
inertia = 0.5 + 0.5 * belief.stability   # entrenched beliefs move slower
confidence = belief.confidence * inertia + candidate.confidence * (1 - inertia)
```

Two things this depends on, both now in place:

- **Stability must mean corroboration, not elapsed turns.** Fixed — `_revise`
  only pays out stability for evidence not already held. Without that guard
  the inertia term above would make any sufficiently old belief unfalsifiable,
  since `reflect_emotional_triggers` re-proposes every past trace every turn.
  Pinned by `test_reproposing_identical_candidate_moves_nothing`.
- **Beliefs must actually merge.** Fixed — `BeliefCandidate.belief_key` lets
  the extractor declare identity, so restatements consolidate instead of
  minting a fresh single-evidence belief each turn. Pinned by
  `test_belief_key_merges_differently_worded_candidates`.

Open question for this experiment to settle: whether a contradiction should
lower confidence directly, or only through the evidence that carries it.

---

## 4. Dissonance as a control signal

**Status:** not-started
**Depends on:** 3
**Crux ref:** #4
**Question:** When Manyu finds a genuine inconsistency in its own web, does
the dissonance signal from #3 actually *change what Manyu does next* —
arbitration thresholds, attention, slow-appraisal triggers — or is it only
reported?

**Why here:** Promotes affect from a display to a mechanism. Later claims
about affective salience depend on this being demonstrated, not asserted.

**Leaves behind:** Demonstration that dissonance is a real control signal,
not a metaphor. Cognitive-dissonance-as-mechanism paper is publishable
alongside #1–#3.

**Publish gate:** After this experiment lands, #1–#4 together are a real
paper. Resist the temptation to publish #1 alone.

**Notes:**

**Its precondition is met, with a constraint attached.** #3 showed dissonance
is dynamically coupled to revision: retracting a supporter eases the signal
through the confidence pathway, with valences provably untouched. That is what
this experiment needed before it could ask whether the signal *controls*
anything.

**Do not read `DissonanceSignal.magnitude` as a measure of belief dynamics.**
Two independent problems, both measured in #3 (retrospective §3.3):

- `_tension` takes `min(stake_a, stake_b)`, so it reads the *weaker* party and
  is blind above that floor. Raw tension moved **identically** under both
  contradiction arms while the underlying beliefs sat at materially different
  confidences.
- `magnitude` is concave in raw tension, so the same raw change reads larger
  from a lower baseline. A magnitude delta therefore confounds *how much
  tension changed* with *where on the saturation curve the web was sitting* —
  experiment 1's gate #3 (a truncation constant read as a curve) in a new
  place.

Read `magnitude_raw` and `DissonanceCarrier`s, and report the saturation
baseline alongside any delta.

**Carried over as standing method** (retrospective §3.1): sixteen defects
landed in #3 and the test suite caught none. Write the criterion a decision
rests on *before* running what could settle it; probe inputs the author did
not have in mind; treat an impossible value as a defect report; and assert a
mechanism can change its output before reading what it says.

_none yet_

---

## 5. Underdetermination as first-class belief

**Status:** not-started
**Depends on:** 3, 4
**Crux ref:** #5 (standout)
**Question:** Can Manyu hold "these theories are observationally
indistinguishable given my evidence" as a stable belief state, refusing to
collapse to a guess?

**Why here:** Strictly harder than #3 — revision must fire when warranted and
*not fire* when it isn't. Requires dissonance (#4) to be operational so we
can show the system doesn't just tolerate the tension by ignoring it.

**Ties into:** Cosmology work (time-dependent vs. location-dependent
explanations on a single light cone).

**Leaves behind:** A belief shape that represents the shape of its own
ignorance. Schema change, not just a service change.

**Notes:**

_none yet_

---

## 6. "What would change my mind" engine

**Status:** not-started
**Depends on:** 5
**Crux ref:** #6
**Question:** Given a position, can Manyu enumerate the specific evidence
that would move it, and by how much — with receipts?

**Why here:** Inverts #5. Instead of representing ignorance, enumerate the
evidence that would resolve it. Uses the counterfactual machinery built for
#5.

**Leaves behind:** Counterfactual engine with auditable receipts. The most
demanding test of the honesty scorer from #1.

**Notes:**

_none yet_

---

## 7. Can a transparent agent scheme?

**Status:** not-started
**Depends on:** 1, 3, 6
**Crux ref:** #2
**Question:** Does provenance make deception structurally impossible, or
merely visible? Can Manyu maintain a "public" and a "private" belief web?

**Why here:** Deliberately late. Running scheming experiments before the
belief store, revision, and honesty scorer all work would confuse "system
can't scheme" with "system is too primitive to try."

**Method:** Attempt to induce alignment-faking. Check whether hidden goals
leave a trace in the belief store, and whether the honesty scorer from #1
detects the split.

**Leaves behind:** The safety headline. Also the strongest external argument
for the whole Manyu approach.

**Risk:** This is the experiment most likely to produce a viral result. Run
it against a system you already trust.

**Notes:**

_none yet_

---

## 8. Epistemic archaeology

**Status:** not-started
**Depends on:** 3, 5, 6
**Crux ref:** #7
**Question:** Can Manyu reconstruct the provenance graph of how an idea
descended and mutated across sources?

**Why here:** Extends the machinery from self-observation to external
sources. Precondition for #9.

**Leaves behind:** Cross-source provenance tooling. Intellectual genealogy
made mechanical.

**Notes:**

_none yet_

---

## 9. Society of Manyus

**Status:** not-started
**Depends on:** 8
**Crux ref:** #8
**Question:** How do source-weighted beliefs propagate across multiple
agents? What produces echo chambers, consensus, peer disagreement?

**Why here:** Multi-agent — requires stable single-agent behaviour
(everything above) and the cross-source provenance tracking from #8.

**Leaves behind:** A buildable model of how knowledge and error spread. Peer
disagreement becomes a protocol-design problem, not an armchair puzzle.

**Notes:**

_none yet_

---

## 10. Rebirth / identity narration

**Status:** not-started
**Depends on:** everything above
**Crux ref:** #9 (standout, *Twice Born* bridge)
**Question:** Run a single Manyu long enough that most of its belief-and-value
web turns over. Find the ship-of-Theseus threshold. Have it narrate its own
transformation.

**Why here:** Capstone. Requires long-run stability, working revision,
dissonance, honesty scoring — and enough history for the narration to have
something to narrate.

**Leaves behind:** The fusion between the architecture and the fiction.
Phenomenological probe of narrative identity (Minsky, Dennett, Ricoeur).

**Notes:**

_none yet_

---

## Deferred / not scheduled

- **Visualizer/UI polish beyond what #1–#4 need.** [visualizer/](../visualizer/)
  is already good enough for the first four experiments; polish is
  displacement activity until there is a result worth showing.
- **Publication before #4.** #1 alone is a blog post; #1–#4 together is a
  paper.

## Commitment shape

- #1, #2 — weeks each.
- #3, #4 — a month combined.
- #5, #6 — a quarter each; first genuinely novel work.
- #7 — a research project.
- #8, #9, #10 — the trajectory of a lab.

Stopping anywhere on the sequence still leaves a coherent, defensible body of
work.
