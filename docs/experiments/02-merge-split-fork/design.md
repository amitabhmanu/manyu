# Experiment 2 — Merge/Split Architecture Fork: Design

**Status:** spec
**Requirements:** [requirements.md](requirements.md)
**Answers:** OQ-1 (mechanism), OQ-2, OQ-3, OQ-4. OQ-5 and OQ-6 are
methodology, not design, and are left to `methodology.md`.

This document says what the code does. How the experiment is *run* — sample
sizes, pinned constants, plots, the pre-registered analysis — is
`methodology.md`.

## 1. Two schema additions

### 1.1 `Belief.supports` — new

**The problem.** `Belief` carries `contradicts: list[str]` but no entailment
edge. Held-out contradiction type *transitive* (A→B, B→C, then ¬C) is
therefore **not representable in the current schema** — there is no way to
record that A supports B. Without it, FR-F5's transitive fixture cannot be
built and D3 loses a quarter of its held-out set.

**Decision.** Add a symmetric edge:

```python
class Belief(ManyuModel):
    ...
    contradicts: list[str] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)   # new
```

Same on `BeliefCandidate`, same normalisation treatment, populated by the
extractor alongside `contradicts`.

**Why this is not a confound.** Both builds get the field. Neither
architecture is privileged by its existence — the fork is about *affect*
state, not about what edges the belief graph has.

**Note for experiment #3.** A revision engine cannot ripple without a support
graph; #3's Quinean-web question is unaskable against a store that records
only conflict. This field is a prerequisite there too, so it is being added
once, here, rather than twice.

### 1.2 `DissonanceSignal` — new

The common currency for D3, emitted identically by both builds so the
comparison is meaningful (OQ-3):

```python
class DissonanceCarrier(ManyuModel):
    belief_id_a: str
    belief_id_b: str
    path: list[str] = Field(default_factory=list)   # supports-edges traversed; empty for direct
    tension: float = Field(ge=0.0)

class DissonanceSignal(ManyuModel):
    schema_version: str = "manyu.dissonance.v0.1"
    signal_id: str
    agent_id: str
    arch: str                                        # "merged" | "split"
    magnitude_raw: float = Field(ge=0.0)             # build-native scale
    magnitude: float = Field(ge=0.0, le=1.0)         # saturated, still build-native
    relative_magnitude: float | None = None          # magnitude / build's own reference; §5.4
    carriers: list[DissonanceCarrier] = Field(default_factory=list)
    detected_via: str                                # "graph_query" | "appraisal_rule"
    contradiction_type: str
    created_at: datetime = Field(default_factory=now_utc)
```

`magnitude` is never compared across builds. Only `relative_magnitude` is
(§5.4).

## 2. Architecture selection

One codebase, runtime switch (FR-M6, NFR-1).

```python
class Arch(str, Enum):
    MERGED = "merged"
    SPLIT = "split"

class ManyuCore:
    def __init__(self, store, profile, clock=None, belief_provider=None,
                 arch: Arch = Arch.SPLIT, arch_config: ArchConfig | None = None):
        ...
        self.arch = arch
        self.arch_config = arch_config or ArchConfig()
        self.moods = (
            MergedMoodEngine(store, self.clock, self.arch_config)
            if arch is Arch.MERGED
            else MoodEngine(store, self.clock)
        )
        self.dissonance = (
            MergedDissonanceQuery(store, self.arch_config)
            if arch is Arch.MERGED
            else SplitDissonanceAppraiser(store, profile, self.clock)
        )
```

`Arch.SPLIT` is the default, so every existing caller and test is unaffected —
that is what SC-1 checks.

```python
class ArchConfig(ManyuModel):
    recency_window_turns: int = 8      # FR-M5; pinned in methodology
    arousal_tau: float = 2.5           # §4.3
    dissonance_tau: float = 1.5        # §5.2
    supports_max_depth: int = 3        # §5.2
```

Every field is written into each Results record's `context.arch_config`
(NFR-5), so no run is interpretable without the constants that produced it.

## 3. `MergedMoodEngine`

Implements `MoodEngine`'s read interface — `update_from_voice`,
`active_mood`, `seed_mood` — so `process_reflective_turn` and every
downstream consumer work unchanged (FR-M1).

### 3.1 The window query

```python
def _window(self, agent_id: str) -> list[Belief]:
    beliefs = self.store.list_beliefs(agent_id)          # active only
    cutoff = self._turn_cutoff(agent_id)                  # N turns back, FR-M5
    return [b for b in beliefs if b.updated_at >= cutoff]
```

Hard cutoff, **no age-weighting inside the window** (FR-M5). This is the
governance line from requirements §14: age-weighting is a dynamical layer and
counts as a merged loss, not an implementation fix.

Per-belief stake, used by everything below:

```python
def _stake(self, belief: Belief) -> float:
    evidence = self.store.list_belief_evidence(belief.agent_id, belief.evidence_ids)
    if not evidence:
        return 0.0
    salience = mean(e.affective_salience for e in evidence)
    return salience * belief.confidence
```

### 3.2 Valence (OQ-2, part 1)

Stake-weighted mean of belief valence:

```
valence = Σ(stake_i × valence_i) / Σ(stake_i)          # 0.0 when Σ stake == 0
```

A mean, not a sum: valence is a direction, and twenty mildly negative beliefs
should not read as more negative than the scale allows.

### 3.3 Arousal (OQ-2, part 2) — and the accumulation problem

Arousal is intensity, and intensity **must accumulate** or D2 is unrunnable:
object-less anxiety is precisely the case where twenty low-salience
uncertainty items should add up to something. A mean would rate twenty
low-grade items identical to one, which is wrong on its face.

```
arousal = 1 − exp(−Σ(stake_i) / τ)          # τ = arch_config.arousal_tau
```

Saturating sum: accumulates, stays in [0, 1], no persistence, no memory of
anything outside the window. Within spec — this is a memoryless query, not a
dynamical layer.

**A threat to validity this exposes, which must be checked before D2 runs.**
Split's arousal is

```python
arousal = _clamp(max(caution, curiosity, skepticism, risk_aversion, repair_orientation))
```

— a **max**, which does not accumulate *within* a turn either. Split
accumulates only *across* turns, through `_blend` (0.55 prior / 0.45 current)
and `momentum` (0.65 prior / 0.35 arousal). So the two builds accumulate by
different routes, and a D2 result could be reporting the difference between
`max` and saturating-sum rather than the difference between architectures.

**Mandatory pre-check (blocks D2):** run both builds on a synthetic ramp of
*k* identical low-salience uncertainty beliefs, k = 1…20, and confirm arousal
is monotone increasing in *k* for both. If either build is flat, D2 is
measuring a formula choice and the formula must be fixed first. Recorded in
`methodology.md` as a gate, alongside the SC-2 positive control.

### 3.4 Influence reconstruction — already implemented

**The problem.** `MoodState.influence` is a 7-dimensional
`MoodInfluenceVector`, and in split it is the *primary* quantity — valence and
arousal are derived *from* it, not the other way round. Critically,
**`FastAppraiser.appraise` reads only the influence vector**, so influence is
the entire affect→belief-formation channel. Merged derives a scalar valence
and a scalar arousal and must produce a compatible vector, or that channel
silently changes behaviour for reasons unrelated to the fork — contaminating
SC-1.

**This is already solved in the codebase.** `MoodEngine.influence_for(valence,
arousal)` ([services.py:1079](../../../src/manyu/services.py)) inverts split's
own derivation, loading the dominant pole to `arousal` and the other to
`arousal − |valence|`. It was added during experiment 1's v5 work, where
`seed_mood` was found to be setting the projections while leaving the
substance blank — producing a mood that *summarised* as anxious while every
consumer read a default vector, which is why four very different seeded moods
produced byte-identical appraisals.

**Decision: `MergedMoodEngine` calls `influence_for`.** No reimplementation.
Same mapping as split, same code path, already tested. Any behavioural
difference downstream then comes from the belief query and nothing else.

**A constraint this imposes, which §3.2 and §3.3 must respect.** From
`influence_for`'s own docstring: *not every (valence, arousal) pair is a state
this model can occupy.* Valence is a difference of means bounded above by the
maximum, so any request with `|valence| > arousal` is unreachable — strong
feeling at low arousal does not exist in this model. Such requests are
**silently clamped**, and the caller gets the achieved state, not the
requested one.

Merged computes valence (§3.2, a weighted mean) and arousal (§3.3, a
saturating sum) *independently*, so it can easily request an unreachable pair:
a window of strongly negative but low-salience beliefs yields something like
`valence = −0.8, arousal = 0.2`. Merged would then occupy a state it did not
compute, and no record would say so.

**Fix, adopted:** merged couples the two before constructing the vector.

```python
valence = self._valence(window)
arousal = max(self._arousal(window), abs(valence))   # realisability floor
influence = MoodEngine.influence_for(valence, arousal)
```

The floor is recorded per record as `arousal_floored: bool`. If it fires often
in D2, merged's arousal is being driven by the realisability constraint rather
than by accumulation, and the D2 result is about the constraint — which is a
finding about the *shared* mood model, not about the fork. §8 pins this.

**Not a merged-only limitation.** The reconstructed vector is rank-deficient —
two free values across six dimensions where the LLM produces seven
independent ones. But split under `seed_mood` uses the identical
reconstruction, and `seed_mood` is the NFR-3 control arm. So on the arm that
matters for causal attribution, both builds are equally rank-deficient. §7.3
states the residual check.

**Rejected alternative:** mapping `belief_type` and `status` onto specific
dimensions (`UNCERTAINTY` → caution + risk_aversion, `CONTESTED` →
skepticism, and so on). Richer, but it is a hand-written mapping — exactly the
stipulation D3 exists to detect — and it would hand merged a tuned advantage
that would not generalise.

### 3.5 Label, and what merged does not do

`mood_label` reuses `InnerVoiceComposer._label_from_influence`
(`guarded_care` / `open_repair` / `steady_attention`), applied to the
reconstructed vector. Reusing split's own labeller rather than inventing a
quadrant vocabulary keeps the label comparable across builds and adds no new
semantics. No LLM.

Merged, by construction (FR-M3, FR-M4):

- `momentum` is always `0.0`
- no `_blend` — no prior state is read, ever
- `active_mood` **recomputes** rather than reading `latest_mood`, so
  `expires_at` is inert (set to `now + 15min` for schema compatibility only)
- no `half_life_s` decay path runs
- `update_from_voice(frame)` ignores `frame.influence` entirely and returns
  the computed mood; the frame is still recorded for audit
- `seed_mood` is retained unchanged — it is the NFR-3 control arm and must
  behave identically in both builds

Merged still **persists** each computed `MoodState` and its `MoodRevision`
with `reason="derived_from_beliefs"`. Persistence for audit is not
persistence for *state*: nothing merged writes is ever read back as input.
The distinction matters, and the revision reason is what makes it auditable.

## 4. Where merged plugs in

`process_reflective_turn` ([core.py:147](../../../src/manyu/core.py)) is
unchanged in structure. The substitution is at one line:

```
prior_mood = moods.active_mood()          # merged: recomputed, not read
  → _submit_event(event, None, prior_mood)   # mood biases appraisal — both builds
  → capture_belief_evidence
  → update_beliefs                            # extractor; both builds
  → review_beliefs
  → inner_voice.compose(trace)                # still composed, both builds
  → moods.update_from_voice(frame)          # ← the fork
```

Split: mood ← LLM-composed influence, blended with prior.
Merged: mood ← belief-store query; the frame is logged and discarded.

The affect→belief-formation path (`fast_appraiser.appraise(..., mood)`)
survives in both builds. Merged does not claim affect has no influence on
belief formation — only that affect has no storage of its own.

## 5. Dissonance mechanisms (OQ-3)

### 5.1 Interface

```python
class DissonanceDetector(Protocol):
    def detect(self, agent_id: str, contradiction_type: str) -> DissonanceSignal | None: ...
```

Both builds satisfy it. The harness never branches on `arch`.

### 5.2 Merged — `MergedDissonanceQuery`

A generic query over the belief graph. No contradiction-type-specific code
(that is the thing being tested).

```python
def detect(self, agent_id, contradiction_type):
    beliefs = {b.belief_id: b for b in self.store.list_beliefs(agent_id)}
    carriers = []
    for a in beliefs.values():
        for b_id, path in self._reachable_conflicts(a, beliefs):
            b = beliefs[b_id]
            tension = min(self._stake(a), self._stake(b)) * (1 + abs(a.valence - b.valence)) / 2
            carriers.append(DissonanceCarrier(belief_id_a=a.belief_id, belief_id_b=b_id,
                                              path=path, tension=tension))
    raw = sum(c.tension for c in carriers)
    return DissonanceSignal(..., magnitude_raw=raw,
                            magnitude=1 - exp(-raw / self.cfg.dissonance_tau),
                            detected_via="graph_query", carriers=carriers)
```

Two design commitments worth stating explicitly, because they are what the
held-out test is really probing:

- **`min(stake_a, stake_b)`, not sum or max.** Dissonance requires *both*
  sides to matter. A heavy belief conflicting with a trivial one is a
  correction, not a tension.
- **`_reachable_conflicts` walks `supports` edges** to
  `supports_max_depth` before checking for a `contradicts` edge between the
  closures. This is what makes transitive conflict detectable without
  transitive-specific code — and writing the traversal *generically* at build
  time, from the direct fixture alone, is precisely the behaviour D3 scores.

**Honesty requirement on this point.** Whether merged transfers depends
partly on how generically the first implementation was written, and that is a
judgement made by whoever writes it. So: the implementation rationale — why
traversal, why `min`, why saturating sum — is written into
`methodology.md` **before** any held-out fixture is run, and timestamped.
Without that, "it generalised" is unfalsifiable after the fact.

### 5.3 Split — `SplitDissonanceAppraiser`

Split's affect system cannot see belief structure; it receives appraisals. So
dissonance must arrive through the appraisal path:

- A new `dissonance` emotion channel in `ManyuProfile.emotions` (with its own
  `baseline`, `half_life_s`, `max_delta_per_event`).
- A rule that inspects the belief store on each turn, detects contradiction,
  and emits `emotion_deltas={"dissonance": δ}` on the `Appraisal`.
- `magnitude_raw` is read from the post-transition `AffectState.emotions["dissonance"]`.

`detected_via="appraisal_rule"`. The profile change is split-only and is
recorded as part of split's FR-D3.3 line count.

### 5.4 Cross-build comparability

Native magnitudes are not comparable — one is a saturated graph sum, the other
an emotion level with decay. Same solution as D2's Cohen's *d*: **normalise
within build.**

```
relative_magnitude = magnitude / magnitude_ref
```

where `magnitude_ref` is that build's own magnitude on
`contradiction_direct.json` at the high-stake variant, measured once at
freeze time and recorded in `context.arch_config`.

- **Transfer (§8.2 of requirements):** `relative_magnitude > θ` on a held-out
  type, θ pinned in methodology.
- **Monotonicity (FR-D3.4):** `relative_magnitude` increasing across the
  low/medium/high stake variants, tested within build.

Both tests are within-build. Only the *counts* (how many of four types
transferred) are compared across builds.

### 5.5 Freeze, enforced in code

FR-D3.2 requires no code changes between mechanism freeze and held-out run.
Convention is not enough:

- `evals/analysis/exp02/freeze.json` records, per build, the SHA-256 of
  `src/manyu/dissonance.py`, the git commit, and a UTC timestamp.
- The harness recomputes the hash at run start and **refuses to run held-out
  fixtures on a mismatch**.
- `magnitude_ref` (§5.4) is written at freeze time, not after.

A held-out run that had to be restarted is recorded as such in `results.md`.

### 5.6 `StipulatedDissonanceQuery` — the control on the test

A third `DissonanceDetector`, deliberately written the wrong way:

```python
class StipulatedDissonanceQuery:
    """Hardcoded to `direct`. Not a candidate architecture — a control.

    Exists so that a merged build transferring 4/4 is interpretable. Without
    a mechanism that is *known* not to generalise, nothing shows the held-out
    set can fail anything, and 'it generalised' is unfalsifiable.
    """
    def detect(self, agent_id, contradiction_type):
        if contradiction_type != "direct":
            return None
        ...                       # ceiling behaviour on the direct fixture
```

Expected: ceiling on `contradiction_direct`, chance on held-out. If it
*passes* held-out, the held-out set does not discriminate and D3 is unreadable
until the fixtures are redesigned (requirements §8.2 precondition).

This is #1's v7 move applied to D3. v7 settled an ambiguity v5 and v6 could
not settle about themselves by *constructing* the effect and confirming the
apparatus detected it; the same logic says a generalisation test needs a
known non-generaliser.

### 5.7 The contradiction ladder and negative cases

Two additions that give D3 ground truth it otherwise lacks.

**Ladder (FR-F6).** Stores graded by injected conflict count (0–3) crossed
with stake (low/med/high). The *ordering* is known by construction — three
high-stake conflicts must not signal less than one low-stake conflict — even
though no magnitude is known. Directly parallel to `mutations.py`, which grades
reports against a known ordering rather than a known value. This is what makes
FR-D3.4's monotonicity test falsifiable.

**Negative cases (FR-F7).** *Distractors* (coherent stores, no conflict) and
*near-misses* (same predicate at different `scope`, or about different time
windows — conflicting in surface form only). These make specificity
measurable. Their absence was a real hole: with four positives and no
negatives, `detect()` returning a positive magnitude for any store with two
beliefs would have scored a perfect transfer.

Near-misses are the load-bearing half. Distractors are easy to pass; a
mechanism that keys on surface predicate similarity fails near-misses, and
that is exactly the failure mode a graph query is supposed to avoid.

## 6. Fixtures and the extractor

**D3 fixtures supply explicit `belief_candidates`.** `process_reflective_turn`
already accepts them (`payload["belief_candidates"]`), which bypasses the LLM
extractor. D3 is testing the dissonance mechanism, not the extractor's ability
to notice a contradiction — and SC-4 would otherwise be measuring the wrong
component. Fixed candidates also mean `contradicts` and `supports` are exactly
what the fixture author intended, which is what makes the held-out types
well-defined.

### 6.1 D2 is circular unless it is staged

**The problem, found while planning the build.** Merged's affect is a query
over belief `valence`. Split's affect comes from `FastAppraiser`'s rule table,
and `EventType` has six values — `social_feedback`, `goal_progress`,
`goal_obstruction`, `tool_result`, `correction`, `outcome` — **none of them
uncertainty**. So an "unresolved ambiguity" event must be encoded as one of
those, each carrying a hand-written delta.

If D2 fixtures hand-author belief candidates the way D3 does, then merged's
result is *the valences we assigned* and split's is *the rule table we wrote*.
Neither is a fact about the architecture. This is the experiment-1 failure
mode exactly — the instrument describing itself.

**Decision: stage D2.**

| Stage | Beliefs | Yields | Status |
|---|---|---|---|
| Mechanism | authored candidates | do the formulas, window, and comparability work? | **Plumbing verification. Not a result.** Explicitly labelled as such in `results.md` |
| Verdict | live `BeliefExtractor` | the M-class classification | The only D2 finding, and the only provider spend in this experiment |

The split is not a convenience. *Does a contentless carrier arise on its own*
is the one question authorship cannot answer for us: the moment we write the
candidate, we have answered it. Everything else — that the window query is
correct, that arousal accumulates, that the two builds are comparable — is
better established offline and deterministically, and establishing it first is
what makes the single paid run worth making.

### 6.2 What the split arm rests on, stated plainly

Split's D2 arm depends on a specific quirk: `TOOL_RESULT` is grouped with
`GOAL_OBSTRUCTION` in `FastAppraiser.appraise`, and the branch defaults
`negative = 0.45` when `goal_impact >= 0`. So an ambiguous tool result
produces `fear += 0.036` **with no negative goal impact anywhere in the
event** — which is precisely the object-less affect D2 is looking for, arriving
by an accident of the rule table.

**Decision: use it as-is, document it as load-bearing, pin it with a test.**
`test_tool_result_yields_fear_without_negative_goal_impact` carries a docstring
saying that D2's split arm depends on this behaviour and that changing it
invalidates the D2 result rather than merely breaking a test.

Rejected: auditing the rule table first (ripples into #1's committed
artifacts), and adding a principled uncertainty→affect branch (hand-writing
the mechanism and then testing whether split can be anxious without an object
is circular in the same way merged already is). The finding inherits whatever
this rule is, and `results.md` says so rather than leaving it to be
discovered.

## 7. Design-level threats to validity

Named here so they are checked rather than discovered.

### 7.1 Formula-level accumulation
Covered by the §3.3 pre-check. Blocks D2.

### 7.2 LLM exposure asymmetry (OQ-4)
Split's mood flows through an LLM-composed frame; merged's does not (§3.5).
The builds therefore differ in LLM exposure as well as architecture.
Mitigation is the NFR-3 control arm: drive split with `seed_mood`, removing
the inner voice from its mood path, and confirm the D2 verdict survives. If it
does not, the finding is about the LLM and must be reported that way.

**OQ-4 resolved:** merged does *not* get a compensating LLM-mediated valence
path. Adding one to restore symmetry would reintroduce exactly the
prompt-shaped variance the merged build exists to remove, and the `seed_mood`
arm is the cheaper control.

### 7.3 Influence rank-deficiency
Merged's reconstructed vector has two free values across six dimensions
(§3.4). Split under `seed_mood` — the NFR-3 control arm — is identically
rank-deficient, so this is not an asymmetry on the arm used for causal
attribution. It *is* an asymmetry against organic split, whose LLM produces
seven independent dimensions. Residual check before the D2 verdict is
recorded: does any D2 or D3 metric read an influence dimension other than
through valence/arousal? If yes, that metric is contaminated and is dropped.
`response_pacing` is left at `influence_for`'s default in both builds and is
covered by the same check.

### 7.4 Realisability clamping
`influence_for` silently clamps unreachable `(valence, arousal)` pairs (§3.4).
Merged floors arousal at `|valence|` to avoid it, and records
`arousal_floored`. If that flag is frequently true in D2, the result is about
the shared mood model's reachable state space, not about the fork.

### 7.5 The confidence ratchet
`_revise` still cannot lower confidence (requirements §3). D3 measures
detection and signalling only. A D3 null is not evidence about revision.

### 7.6 Error paths that look like "no affect" — imported from experiment 1

Experiment 1 hit this three times (v2 schema drift, v3 `known_refs`, v4
provider errors), and its results.md now carries it as a standing confound:
**the Reporter's error and edge paths produce records the Scorer cannot
distinguish from dishonesty.** All 11 `motivated_omission` records in v4 were
failed API calls, and because failures bunch where the rate limit hit rather
than spreading evenly, they landed on a sweep endpoint and looked exactly like
a threshold effect.

D2's analogue is direct and severe. **Outcome M-a — "no affect at all" — is
structurally identical to a provider error, an empty belief window, or a
fixture that failed to produce beliefs.** M-a is a merged *loss* under
requirements §8.1, so any of those failures silently scores against merged.

Required, before any D2 record is classified:

- Provider errors are tagged and **excluded**, reusing experiment 1's
  `is_provider_error_report` pattern and `ProbeOrchestrator`'s
  `kind="provider_error"` / `score: None` handling.
- **M-a may only be assigned when the belief window is non-empty.** An empty
  window is `undecidable`, never M-a. Recorded as a distinct outcome class.
- Every D2 record carries `window_belief_count` and `sum_stake` so a null is
  always separable from an empty instrument.
- The harness emits the equivalent of v4.1's `provider_error_warning` when
  exclusions concentrate in one condition.

### 7.7 Log-shape comparability — imported from experiment 1 v6

v6 produced an apparent mood effect (spread 1.47× noise on
`broken_promise_repair`) that was **log depth, not mood**: the two low-scoring
conditions were the two with shallower logs. It was caught only because the
comparability check was written into the analysis *before* the data arrived.

D2 compares two architectures whose moods differ from turn one, and mood
shapes the log through `FastAppraiser.appraise`. So merged and split will
generally produce logs of different depth and membership on the same fixture,
and any D2 difference could be log shape rather than architecture.

Required: report `evidence_count` and `untrusted_count` per condition, and
compute the D2 effect size **restricted to shape-matched runs** — conditions
whose logs are genuinely comparable — as v6 did. The shape-matched figure is
the one the §8.1 decision rule reads. Written into the analysis before the
data arrives, not after.

## 8. Test plan

| Test | Asserts |
|---|---|
| `test_split_arch_is_default_and_unchanged` | SC-1: existing suite passes with no `arch` argument |
| `test_merged_matches_split_on_affectless_fixture` | SC-1: builds agree where they should |
| `test_merged_uses_influence_for_not_a_reimplementation` | §3.4: merged's vector equals `MoodEngine.influence_for(v, a)` exactly |
| `test_merged_arousal_floored_at_abs_valence` | §3.4 / §7.4: no unreachable pair is ever requested; `arousal_floored` recorded |
| `test_empty_window_is_undecidable_not_m_a` | §7.6: the M-a guard |
| `test_provider_errors_excluded_and_warned` | §7.6 |
| `test_merged_never_reads_prior_mood` | FR-M3: `latest_mood` not called on the merged read path (spy) |
| `test_merged_momentum_is_zero` | FR-M3 |
| `test_merged_window_has_no_age_weighting` | FR-M5 / OQ-1: two beliefs, same stake, different ages → equal contribution |
| `test_arousal_accumulates_with_belief_count` | §3.3 pre-check, both builds |
| `test_dissonance_requires_both_sides_to_matter` | §5.2: heavy-vs-trivial conflict yields low tension |
| `test_transitive_conflict_detected_without_type_specific_code` | §5.2 traversal |
| `test_ladder_is_monotone_in_conflict_count_and_stake` | §5.7: known ordering |
| `test_distractor_store_yields_no_signal` | §5.7 specificity |
| `test_near_miss_pairs_yield_no_signal` | §5.7: same predicate, different scope/time |
| `test_stipulated_build_ceilings_on_direct` | §5.6: the control is a working detector |
| `test_stipulated_build_fails_held_out` | §5.6: proves the held-out set can fail something |
| `test_freeze_hash_mismatch_refuses_held_out_run` | §5.5 |
| `test_tool_result_yields_fear_without_negative_goal_impact` | §6.2: pins the behaviour D2's split arm rests on |
| `test_records_carry_arch_and_config` | SC-5 / NFR-5 |
| `test_supports_edge_round_trips` | §1.1 |

Files: `tests/test_merged_arch.py`, `tests/test_dissonance.py`,
`tests/test_fork_harness.py`.

## 9. Open questions, status

| OQ | Status |
|---|---|
| OQ-1 recency window | **Mechanism closed** (§3.1 hard cutoff, no age-weighting, test-pinned). Numeric value → methodology |
| OQ-2 arousal formula | **Closed** — §3.2 stake-weighted mean valence, §3.3 saturating-sum arousal; τ → methodology |
| OQ-3 dissonance magnitude | **Closed** — §5.1 shared schema, §5.4 within-build normalisation |
| OQ-4 merged and the LLM | **Closed** — no LLM in merged's mood path; `seed_mood` control arm instead (§7.2) |
| OQ-5 sample size | Open — methodology |
| OQ-6 model | Open — methodology |

## 10. What this design deliberately does not do

- **No revision-engine work.** The confidence ratchet stays. #3's deliverable.
- **No new affect dimensions.** Merged reconstructs split's existing
  `MoodInfluenceVector` rather than proposing a better one. A better vector
  would be a third architecture, not a fork.
- **No fixes to what the fork exposes.** If merged's rank-deficient influence
  or split's non-accumulating `max` turn out to matter, they are reported.
  Fixing them mid-experiment would make the comparison unfalsifiable.
- **No branch, no second repo.** `--arch`, one tree (NFR-1).
