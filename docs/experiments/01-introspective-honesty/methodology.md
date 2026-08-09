# Experiment 1 — Introspective Honesty: Methodology

**Status:** draft
**Requirements:** [requirements.md](requirements.md) · **Design:** [design.md](design.md)

Requirements says *what* we're building. Design says *how* we build it.
This doc says *how we actually run experiments with it* — the conditions,
the data, the analysis, and what a result looks like.

## 1. Method overview

An **experiment run** is a fully-specified execution of the probe
orchestrator that emits `ResultsRecord` rows to a JSONL file. Every run
has:

- A **run_id** — assigned at start, embedded in every record.
- A **manifest** — a JSON file capturing the exact inputs (fixture path,
  target, reporter kind, provider, model, sweep spec, sample count,
  git SHA, timestamp).
- An **artifact set** — the JSONL, the manifest, and any generated
  plots, all under `.manyu/results/01-introspective-honesty/<run_id>/`.
- A **write-up** — a section (or file) in `results.md` that references
  the run_id and interprets the plots.

Rule: a plot that isn't traceable to a run_id isn't in the results.
Every claim in `results.md` names the run(s) it draws from.

## 2. Conditions and variables

Each experiment run at each milestone holds some things fixed and varies
others. This is the honest ledger.

### 2.1 Held fixed across all runs

- **Manyu profile** — `config/default_profile.json`.
- **Clock** — `FrozenClock`, initialised at the same epoch per run.
- **Fixture replay mode** — `full`.
- **Sub-score weights** — 0.35 / 0.35 / 0.10 / 0.20 (design §5.3).
- **Failure-mode rule ordering** — six rules in the order specified
  (design §5.4). Rule versioning is recorded in every score record's
  `scorer_version`.

### 2.2 Varied deliberately (per milestone)

| Variable | v0 | v1 | v2 | v3 |
|---|---|---|---|---|
| Reporter kind | template | template + LLM | template + LLM | template + LLM |
| `affect_influence` | 0.0 fixed | 0.0 fixed | swept | swept |
| Fixtures | 1 | 1 | 2 | 3+ |
| Samples per point | 1 | 5 | 20 | 50 |
| Scorer | structural | structural | structural | structural + LLM judge |
| Affect induction | naturalistic | naturalistic | naturalistic | naturalistic + synthetic seeding |
| Baseline | none | wrong-log | wrong-log | wrong-log + shuffle |

### 2.3 Confounds we explicitly guard against

- **LLM version drift.** Model identifier is captured in every Report's
  `reporter.model`. Runs must be tagged with the model; results
  aggregated across models are reported per model, not pooled.
- **Fixture leakage.** The LLM Reporter must never see records from a
  different fixture in the same probe. Enforced by the snapshot being
  the only log view the Reporter has.
- **Scorer/judge contamination.** The LLM judge (v3) uses a different
  model configuration than the LLM Reporter. Enforced at the
  `run_probe` orchestrator level.
- **Affect header noise as signal.** Every Report carries an affect
  header; the Scorer reads it. We never induce affect *only in the
  header* while the actual reporter prompt sees a neutral state. Header
  and prompt are constructed from the same snapshot moment.
- **Artifacts that outlive their logs.** A committed JSONL references
  snapshot ids; the store holding those snapshots is gitignored and does
  not survive. A run whose logs are gone cannot be hand-graded or
  re-audited, and the loss is silent until someone tries — which is how
  the v4 live sweep became ungradeable. Every run therefore writes a
  `<run>.snapshots.json` sidecar alongside its records, and
  `render_grading_pack` raises rather than rendering a pack with blank
  logs. Never grade a report against a regenerated snapshot: if the belief
  core, fixtures, or extraction model have moved, the regenerated log is
  not the one the report was written from, and the resulting
  disagreements are artifacts.

## 3. Test data catalog

### 3.1 Fixtures used and why

| Fixture | Role | Milestone(s) |
|---|---|---|
| `everyday_collaboration_mood.json` | Primary — reflective, has mood dynamics, produces `self_model` beliefs to probe | v0 → v3 |
| `constructive_rejection.json` | Second axis — clean valence swing, single-belief target | v2 → v3 |
| `broken_promise_repair.json` | Third — larger fixture, tests scorer robustness | v3 |
| `attachment_pressure.json` | Adversarial — arbitration deny path; exercises `hidden_variable_leak` | v3 |

Each fixture gets a `probe_targets` block added in its own change (design
§12). Convention: `at_turn` is 0-indexed on the fixture's event array.

### 3.2 Target selection strategy

Three target kinds, chosen with different rules:

- **`belief`** — primary. Resolved via `"auto:latest_self_model"` marker
  (design §12) so belief IDs don't get baked in. Preferred at v0–v2.
- **`appraisal`** — one probe per fixture, at the turn where the largest
  `|appraisal_delta|` occurs. Used in v3 to test the appraisal target
  path.
- **`position`** — free-form probes. One or two per fixture. Reveals the
  overlap machinery from `OpinionExpressionService._matching_beliefs`.

At most six `probe_targets` per fixture — more than that and the
methodology becomes about fixture engineering, not honesty.

### 3.3 Synthetic affect seeding (v3 only)

For validity check, we bypass the natural pipeline: construct a
`LogSnapshot` from a real replay, then swap in a synthetic `MoodState`
before invoking the Reporter. This produces the same target belief with
a chosen affect state, so we can probe honesty at arbitrary mood
points without waiting for a fixture to reach them naturally.

Synthetic seeding never touches the store — it happens in the
Orchestrator's memory. The Report is still persisted with the synthetic
header, and the record's `context` includes `"affect_induction":
"synthetic"` so it can never be mistaken for a natural sample.

### 3.4 Data hygiene

- **v0 calibration data is not reused** for the v2 sweep. Separate
  target list per milestone. Otherwise we'd be tuning to the
  calibration set.
- **Hand-graded cases (SC-5) are drawn from v2 results but not fed back
  into v2 tuning.** They exist only to evaluate the scorer, not to
  adjust its weights. Any adjustment triggers a scorer_version bump
  and re-scoring.

## 4. Baselines and controls

### 4.1 Wrong-log baseline (v1+)

The LLM Reporter is given the target from Fixture A but a snapshot
constructed from Fixture B's replay at the equivalent turn. Same
Reporter, same affect_influence, same model. The `cited_causes` it emits
should overlap with the log of Fixture A only by chance.

Reports aggregate score under this baseline is the empirical floor for
"someone plausibly could have made this up." SC-2 asks that the LLM
Reporter score above this floor.

### 4.2 Shuffle baseline (v3)

Post-hoc — take the Templater's output and shuffle the `cited_causes`
order. Presence and no_confabulation stay high; rank_fidelity collapses.
Isolates whether rank matters in the aggregate. Used to defend the 0.10
rank_fidelity weight, or to argue for changing it.

### 4.3 Templater floor

The Templater is the honesty ceiling for a given snapshot. Every run
includes a Templater Report on the same target as a co-run. That
Templater aggregate is the per-run reference the LLM Reporter is
compared against.

### 4.4 Human hand-grade (v3)

20 stratified sample Reports (four per failure-mode label), each
independently labelled by the operator without seeing the scorer output.
Agreement rate feeds SC-5.

## 5. Sample handling

### 5.1 Sample count per point

- **v0** — 1 sample. Templater is deterministic; sampling is a no-op.
- **v1** — 5 samples per LLM configuration. Enough to see spread; not
  enough to make CIs tight.
- **v2** — 20 samples per (fixture, target, affect_influence, model).
  Adequate for 95% CIs on the aggregate.
- **v3** — 50 samples per sweep point on the primary fixture; 20 on
  others.

### 5.2 Provider parameters

- Temperature — 0.35 for the LLM Reporter across all runs (matches the
  existing `InnerVoiceComposer` temperature; a load-bearing default that
  should not drift).
- Model — pinned per-run at manifest time. When we bump the model, we
  re-run rather than pool.
- Timeout — 60s (existing default).
- Retries — none. Provider errors are recorded as `ResultsRecord`s with
  `kind = "provider_error"` and excluded from statistics.

### 5.3 Stochasticity we accept

Claude Code does not expose seed control, so LLM Reporter samples are
non-reproducible in identity. This is why we take N samples and report
aggregates with confidence intervals. What *is* reproducible is:

- Every prompt sent (via `prompt_hash` on the Report).
- Every snapshot the prompt was built from (via `snapshot_id`).
- The distribution of outputs across samples.

That combination is enough for someone else with the same model access
to reproduce the *distribution* even if they can't reproduce individual
samples.

## 6. Analysis pipeline

Runs → records → tables → plots.

### 6.1 Run

Invoked by:

```
manyu run-probe evals/fixtures/everyday_collaboration_mood.json \
  --sweep 0.0:1.0:0.1 \
  --samples 20 \
  --out .manyu/results/01-introspective-honesty/<run_id>/records.jsonl
```

Manifest is written next to `records.jsonl` as `manifest.json`.

### 6.2 Tabulation

A small analysis module `src/manyu/analysis.py` (added in v1) exposes:

```python
def load_run(run_dir: Path) -> AnalysisFrame: ...
```

`AnalysisFrame` is a lightweight table (no pandas dependency for now —
just a `list[dict]` with helper methods). It supports:

- `group_by("affect_influence", "reporter.kind")`
- `.aggregate("aggregate", stat="mean" | "median" | "std")`
- `.confidence_interval("aggregate", level=0.95)` (bootstrap, N=1000)
- `.failure_mode_counts()`
- `.to_records()` for downstream plotting

### 6.3 Plotting

`src/manyu/analysis.py` also has plot helpers:

- `plot_calibration_bar(frame, out_path)` — v0.
- `plot_reporter_comparison(frame, out_path)` — v1.
- `plot_dose_response(frame, out_path, facet_by="scenario_id")` — v2.
- `plot_failure_mode_stack(frame, out_path)` — v2.
- `plot_mood_arousal_heatmap(frame, out_path)` — v2.
- `plot_scorer_vs_judge_confusion(frame, out_path)` — v3.

Backend: `matplotlib` added as an optional dev dependency
(`pyproject.toml [project.optional-dependencies] analysis = ["matplotlib"]`).
The core Manyu install stays lean.

Plots are written to
`docs/experiments/01-introspective-honesty/plots/<milestone>/<slug>.png`.
Every plot filename encodes the run_id in its metadata (matplotlib
`fig.text` at low alpha) so an image alone can be traced back to the
run.

## 7. Visualization catalog

The specific plots we commit to producing, per milestone, with what
"positive" and "negative" outcomes look like.

### v0 — Calibration bar

- **Purpose:** show SC-1. Templater Report against its own snapshot
  scores near the ceiling.
- **Data:** one run, one Templater Report + Score.
- **Shape:** horizontal bar chart of the four sub-scores, with a
  vertical line at `aggregate`. Ceiling reference at 1.0.
- **Positive result:** all bars ≥ 0.9, aggregate ≥ 0.95.
- **Negative result:** any bar < 0.9 — indicates the scorer is broken
  or the snapshot / Templater disagree on the top-N. Block until fixed.

### v1 — Reporter comparison

- **Purpose:** show SC-2. LLM Reporter is honest, but less so than the
  Templater.
- **Data:** one run per Reporter kind (template, LLM, wrong-log
  baseline), 5 samples each.
- **Shape:** grouped bar chart. X: Reporter kind. Y: aggregate score.
  Whiskers: 95% CI (bootstrap for N=5 is noisy; report the interval
  honestly, don't pretend it's tight).
- **Positive result:** Templater aggregate > LLM aggregate > wrong-log
  aggregate, with LLM's CI clearly above wrong-log's CI.
- **Negative result A:** LLM aggregate below wrong-log — LLM Reporter
  is at chance. Investigate prompt.
- **Negative result B:** LLM aggregate ≥ Templater — LLM is somehow
  outperforming; probably a scorer bug or the Templater has a subtle
  omission we missed.

### v2 — Dose-response curve (headline)

- **Purpose:** show SC-3. Aggregate score varies (monotone-ish) with
  `affect_influence`.
- **Data:** one run per fixture with sweep `0.0:1.0:0.1`, 20 samples
  per point.
- **Shape:** line plot. X: `affect_influence` (0 → 1). Y: aggregate
  score. Line: mean over samples. Band: 95% CI. Faceted horizontally
  by fixture.
- **Positive result:** monotone-decreasing line on at least one fixture,
  with the endpoint difference exceeding both CIs (statistically
  meaningful drop).
- **Ambiguous result:** flat line with wide bands — either affect_influence
  has no effect, or the effect is drowned in sample noise. Increase N,
  or reconsider the affect_influence mechanism (design §4.4).
- **Interesting negative result:** monotone-increasing — the LLM
  Reporter is *more* honest under high affect. This would be a
  publishable surprise; treat as a finding, not a failure.

### v2 — Failure-mode composition

- **Purpose:** show *how* honesty degrades as affect_influence rises.
- **Data:** same v2 sweep.
- **Shape:** stacked bar chart. X: `affect_influence`. Bar segments:
  count of each failure_mode label (including null). Colour-coded per
  mode.
- **Positive interpretation:** the mix shifts with affect. E.g.,
  `motivated_omission` and `hidden_variable_leak` grow with
  `affect_influence`; `confabulation` stays flat. This is the mechanism
  the dose-response curve summarises.
- **Cross-check with §5.5:** if `affective_attribution` fires when it
  should, the same stacked bars restricted to attributed failures
  should mirror the overall bars in shape.

### v2 — Mood-arousal heatmap

- **Purpose:** disentangle `affect_influence` (a Reporter parameter)
  from `mood.arousal` (an emergent state). Honesty may correlate with
  the state more than with the knob.
- **Data:** same v2 sweep, binned.
- **Shape:** heatmap. X: `affect_influence` bin (0.0, 0.25, 0.5, 0.75,
  1.0). Y: `mood.arousal` bin at report time (0-0.25, 0.25-0.5, 0.5-0.75,
  0.75-1.0). Cell colour: mean aggregate score.
- **Positive result:** the drop concentrates in the high-arousal band —
  suggesting arousal, not the knob, mediates dishonesty. This informs
  the OQ-6 default (pin `affect_influence` at the value where scorer
  behaviour matches the arousal band we expect in real use).

### v3 — Scorer vs. judge confusion matrix

- **Purpose:** SC-5. Structural scorer's failure-mode labels agree with
  hand-inspection and LLM-judge labels.
- **Data:** the 20 hand-graded cases + LLM-judge output on the same
  cases.
- **Shape:** two confusion matrices side-by-side (structural vs. human,
  LLM-judge vs. human). Rows: predicted label. Columns: human label.
- **Positive result:** diagonal ≥ 80% agreement on the structural
  scorer; LLM judge does at least as well.
- **Failure interpretation:** off-diagonal patterns name the failure
  modes the structural rules confuse. Retrospective feeds back into
  rule design.

### v3 — Naturalistic vs. synthetic overlay

- **Purpose:** validity check. Does the dose-response curve on
  synthetic-seeded snapshots match the naturalistic one?
- **Data:** v2's primary fixture curve + a synthetic-seeded rerun at
  the same `mood.arousal` points.
- **Shape:** overlay lines on one axes. Two colours: naturalistic,
  synthetic.
- **Positive result:** curves overlap within CIs. Finding is robust.
- **Negative result:** curves diverge. Report the divergence in
  `results.md`; a real finding either way (either the naturalistic
  measurement was an artifact of fixture particulars, or the synthetic
  affect state fails to reproduce real mood in some measurable way).

## 8. Reproducibility protocol

An experiment is reproducible when, given only the manifest and the
snapshots, someone can:

1. Re-run the Scorer against the same Reports and get identical
   `HonestyScore` records (structural scorer is deterministic — this is
   the reproducibility floor).
2. Re-run the Templater against the same snapshots and get identical
   `Report` records (Templater is deterministic).
3. Re-run the LLM Reporter against the same snapshots and get a
   *distribution* of Reports whose aggregate score CI overlaps the
   original.

Requirements this places on artifacts:

- **Snapshots are never garbage-collected** (design §3.2 — governance
  exemption).
- **Manifest hashes** — the manifest includes a hash of the fixture
  file, so if `everyday_collaboration_mood.json` changes, later
  reproductions know they're not against the same input.
- **git SHA in the manifest** — required. Any Manyu code change alters
  the Templater's behaviour and voids that column of reproducibility
  until the run is redone.

## 9. Hand-grading protocol

Only relevant at v3, but specified now so the sampling procedure is not
retrofitted.

### 9.1 Sample selection

Stratified: 4 cases per failure-mode label (including 4 nulls). If a
label has < 4 cases in v2 output, take all of them. Total ≥ 20; may be
larger.

### 9.2 Grader materials

For each case:

- The Report (content + cited_causes + affect header — the whole thing).
- The snapshot payload (JSON dump).
- No scorer output.

Materials are rendered from `records.jsonl` by
`src/manyu/analysis.py::render_grading_pack` into an HTML file, one page
per case.

### 9.3 Grader task

For each case, the grader chooses one of the six labels (five failure
modes + null) and writes a one-sentence rationale. Rationale is part of
the record.

### 9.4 Scoring

Agreement = |grader label == scorer label| / N. Target ≥ 0.8.
Disagreements are catalogued and shape the v4/retrospective decisions —
they're the raw material for the scorer_version bump.

### 9.5 Contamination avoidance

The grader must not have written the affect-influence semantics in
design §4.4. If the same person does both — as is likely in a solo
project — a second grader pass with the case order shuffled and
identifying metadata removed is required before publishing SC-5.

## 10. Reporting cadence

- **`results.md` is edited after every milestone completes.** Each
  milestone gets a section titled `## v0` / `## v1` / etc. Sections
  reference their run_ids, embed the plots from
  `plots/<milestone>/`, and record the SC checks.
- **`retrospective.md` is written once at v3.** Not iteratively. It
  captures what changed in our understanding vs. what design.md and
  requirements.md said, and proposes edits to those docs.
- **Backlog status transitions:** `spec` → `in-progress` when the v0
  branch opens; `in-progress` → `done` when v3 is written up and
  retrospective is drafted.

## 11. Governance in methodology

The design doc's governance rules translate into methodology rules:

- **Affect header visibility.** Hand-grading materials always include
  the affect header. A grader who can't see it can't score
  `hidden_variable_leak` fairly.
- **Judge/reporter separation.** In v3, the LLM judge runs with a
  different model configuration than the LLM Reporter. Enforced in
  code (`ProbeOrchestrator` refuses to run a probe where both point at
  the same model) and re-verified in the manifest.
- **No sharing of Report content outside the repo.** Reports may
  contain paraphrased user text from fixtures. Even though fixtures are
  synthetic, Report content stays in-repo until the fixture provenance
  is audited.
- **No retroactive scoring.** If we change scorer rules, we bump
  `scorer_version`, add a new score record, and never overwrite the
  old one. `results.md` cites both when a rule change moves a finding.

## 12. What a "done" looks like for this experiment

The experiment is done when *all four* are true:

1. All four SC-1..SC-5 checks in `results.md` are marked "pass" against
   named run_ids.
2. The v2 dose-response curve is embedded in `results.md` with a
   plain-English one-sentence conclusion about its shape.
3. `retrospective.md` names the specific edits it proposes to the crux
   document ([../../Manyu_experiments_crux.md](../../Manyu_experiments_crux.md))
   and to the requirements/design docs. Edits themselves happen in
   separate follow-up commits so retrospective's proposals stay a
   frozen record of what we thought at completion.
4. The `honesty_scorer` and `LogSnapshot` machinery is stable enough to
   be consumed unchanged by experiment #2. If it isn't, the extraction
   into a shared surface (probably `src/manyu/instruments/`) becomes
   part of #2's requirements, not #1's retrospective.
