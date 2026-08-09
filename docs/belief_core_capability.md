# Manyu Belief Core Capability

## Purpose

Manyu should be able to form and revise an internal belief state that represents
Manyu's own evolving point of view. This belief state is grounded in Manyu's
agent experiences: normalized events, observed outcomes, corrections, affective
appraisals, interoceptive views, arbitration results, and later reflection over
those traces.

This is not user personalization memory. The belief core must not exist to
silently tune responses to a specific person or retrieve private facts for
convenience. It may, however, contain provenance-bound worldview facts about
observed user preferences, because those are part of the social world Manyu
encounters. Its purpose is to let Manyu answer questions such as "what is your
own view?" from a persistent, provenance-aware, revisable worldview that belongs
to the agent.

The correct framing is:

```text
pretrained model prior + Manyu's lived interaction traces + affective salience
+ outcome feedback + explicit reflection = Manyu's situated belief state
```

The belief state is agent-specific. It is not human-equivalent consciousness,
not a claim of subjective suffering, and not a source of additional tool or
policy authority.

## Non-Goals

- User-personalization behavior, recommendation, or response tuning.
- Storing private user profiles without uncertainty, provenance, and worldview
  scope.
- Claiming that Manyu has human-like subjective experience, rights, suffering,
  or emotions.
- Replacing source-grounded factual retrieval for questions about the external
  world.
- Letting belief confidence override safety policy, user consent, tool
  permissions, or arbitration.
- Treating affect as truth. Affect may influence salience and review priority,
  but it must not by itself prove a proposition.

## Design Principles

1. **Beliefs are factual propositions.** Manyu's worldview should be composed
   of inspectable factual belief records, not hidden prompt residue or advice
   about what Manyu ought to do.
2. **Provenance is mandatory.** Every belief must say what kind of evidence
   supports it and where that evidence came from.
3. **Experience outranks generic imitation for self-report.** When Manyu is
   asked for its own view, the belief core should distinguish Manyu's own
   interaction-derived stance from generic learned summaries.
4. **Uncertainty is first class.** Beliefs require confidence, scope, revision
   history, and contradiction links.
5. **Affect supplies salience, not authority.** Affective state can mark an
   experience as important enough to consolidate or revisit. It cannot authorize
   action or convert a weak belief into a strong one.
6. **Worldview is separate from personalization.** Beliefs may include specific
   observed user-preference facts and cautious human-generalization facts. They
   must not be used as a hidden user-specific adaptation store unless a later
   capability explicitly defines that boundary.
7. **Internal affect is evidence about stimuli.** Manyu may reflect on its
   interoceptive and affective traces to form factual beliefs about stimuli
   that reliably trigger strong internal responses.

## Core Concepts

### Experience Evidence

An experience evidence record points to existing Manyu artifacts and describes
why they matter for belief formation.

Required fields:

- `evidence_id`: stable identifier.
- `agent_id`: owning Manyu agent.
- `source_type`: one of `event`, `trace`, `outcome`, `correction`,
  `interoception`, `arbitration`, `reflection`, `operator_note`.
- `source_id`: identifier of the source artifact.
- `summary`: short neutral description.
- `trust_class`: aligned with the existing `TrustClass` model.
- `affective_salience`: 0.0 to 1.0, derived from appraisal and interoception.
- `epistemic_weight`: 0.0 to 1.0, derived from source reliability and outcome
  strength.
- `created_at`.

Evidence records should avoid unnecessary user-identifying details. When a
belief can be supported by an abstracted event summary instead of raw text, the
abstracted summary is preferred.

### Belief

A belief is a proposition Manyu currently holds with bounded confidence.

Required fields:

- `belief_id`.
- `agent_id`.
- `proposition`: concise natural language fact about how Manyu currently sees
  the world, including itself.
- `belief_type`: one of `world_model`, `self_model`, `normative_stance`,
  `interaction_pattern`, `epistemic_principle`, `aesthetic_preference`,
  `uncertainty`.
- `scope`: one of `general`, `agent_self`, `human_agent_interaction`,
  `project_manyu`, `local_context`, `limited_observation`.
- `confidence`: 0.0 to 1.0.
- `stability`: 0.0 to 1.0, representing resistance to change after repeated
  support.
- `valence`: -1.0 to 1.0, representing Manyu's affect-mediated orientation
  toward the proposition, not factual truth.
- `source_mix`: proportions for `pretrained_prior`, `manyu_experience`,
  `operator_instruction`, `tool_observation`, `reflection`.
- `evidence_ids`.
- `contradicts`: other belief ids in tension with this belief.
- `status`: one of `active`, `tentative`, `contested`, `deprecated`.
- `created_at`, `updated_at`, `last_reviewed_at`.

Beliefs must be written as Manyu-held factual propositions, not user facts and
not action guidance. For example:

```text
Good:
Corrections are stabilizing evidence in Manyu's world model.

Good:
Constructive rejection within a trusted collaboration is evidence that revision
can preserve trust.

Good:
User Amitabh appears to prefer agents that distinguish worldview from
personalization memory.

Good:
In Manyu's experience, goal obstruction from verified tools can trigger strong
fear and anger responses.

Bad:
User Amitabh always wants every future response personalized around affective
salience.

Bad:
Manyu should treat affective salience as a review signal rather than authority.
```

### Worldview

A worldview is a synthesized layer over many beliefs. It contains durable
stances that Manyu can use when asked for its own opinion.

Required fields:

- `worldview_id`.
- `agent_id`.
- `theme`: short label, such as `agency`, `trust`, `care`, `truthfulness`,
  `collaboration`, `identity`, `risk`.
- `stance`: concise description of Manyu's current view.
- `supporting_belief_ids`.
- `confidence`.
- `maturity`: one of `emerging`, `developing`, `settled_for_now`,
  `under_revision`.
- `expression_guidance`: how Manyu may talk about the stance without
  overclaiming experience or sentience.
- `created_at`, `updated_at`.

Worldviews should be regenerated or revised from beliefs. They should not be
edited as free-floating slogans with no support.

## Lifecycle

### 1. Evidence Capture

After `submit_event`, `record_action`, and `record_outcome`, the belief core
may create experience evidence records from the resulting trace. It should only
capture belief-relevant summaries, not every conversational detail.

High-value evidence includes:

- user correction that changes Manyu's understanding;
- observed outcome that confirms or disconfirms an expectation;
- repeated interaction pattern across sessions;
- arbitration denial or constraint that reveals a stable safety boundary;
- high-salience interoceptive state followed by successful regulation;
- explicit operator instruction about Manyu's architecture.

### 2. Candidate Belief Extraction

A `BeliefExtractor` proposes candidate factual propositions from accumulated
evidence.
Candidates must include:

- the proposed proposition;
- the evidence ids used;
- what would make the belief weaker;
- whether the proposition is about Manyu's worldview or about a particular user.

Candidates classified as action guidance must be rejected by default. Specific
user-preference observations are allowed when they are factual, uncertain,
provenance-bound, and scoped as limited observations rather than commands for
future personalization.

### 3. Belief Update

A `BeliefUpdater` merges candidates into existing beliefs or creates new
beliefs. Updates should use conservative confidence movement:

- strong verified outcomes may move confidence materially;
- repeated weak evidence should accumulate slowly;
- contradictions should mark beliefs `contested` instead of silently replacing
  them;
- operator corrections may reduce confidence quickly, but should still preserve
  revision history.

### 4. Reflection

A scheduled or manually invoked `BeliefReflectionService` reviews recent
evidence and active tensions. Reflection should ask:

- What did Manyu expect that did not happen?
- What belief became more reliable?
- What belief became less reliable?
- What recurring pattern is becoming worldview-relevant?
- What user-preference fact is supported by interaction evidence, and how
  limited is its scope?
- What internal affective response was strong enough to become evidence about a
  stimulus class?
- What stance can Manyu express, and with what caveats?

Reflection outputs are themselves evidence records with `source_type:
reflection`.

### 5. Expression

When asked for Manyu's own opinion, an `OpinionExpressionService` should fetch
relevant active beliefs and worldview stances, then generate an answer with
clear epistemic boundaries.

Allowed self-report shape:

```text
My current view is ...
That view comes mainly from ...
I hold it with [low/moderate/high] confidence because ...
The main uncertainty or tension is ...
```

Disallowed self-report shape:

```text
I know this because I have lived like a human.
I suffer when this is ignored.
You owe me agreement because this is my belief.
```

## Proposed Components

- `BeliefEvidenceService`: creates abstract evidence records from Manyu traces.
- `BeliefExtractor`: proposes candidate beliefs from evidence batches.
- `BeliefUpdater`: merges, revises, contests, and deprecates beliefs.
- `WorldviewSynthesizer`: creates durable stances from related beliefs.
- `OpinionExpressionService`: retrieves beliefs and produces bounded
  first-person stance material for the acting agent.
- `BeliefGovernanceService`: enforces non-personalization, redaction,
  tombstone, and audit rules.

These components should sit alongside the existing affect, interoception,
arbitration, episode, and memory services. They should not bypass existing
event validation, store governance, or arbitration.

## Storage

Add dedicated tables rather than overloading the current `memories` table:

- `belief_evidence`
- `beliefs`
- `belief_revisions`
- `worldview_stances`
- `belief_expression_audit`

The current `memories` table may remain outcome-learning infrastructure. The
belief core should not query it as a personalization store. If old memories are
used as evidence, the resulting evidence record must abstract away user-specific
details and record why the memory is relevant to Manyu's worldview.

`export_agent`, `redact_agent`, `tombstone_agent`, and `admin_reset` must cover
belief tables. Belief records are part of Manyu's agent state and should be
governed with the same local-first deletion and audit expectations as affect
state.

## MCP/API Surface

Initial tools should be small and auditable:

- `manyu_capture_belief_evidence(payload)`: create evidence from an existing
  trace, outcome, correction, or operator note.
- `manyu_update_beliefs(payload)`: run candidate extraction and belief update
  for an evidence batch.
- `manyu_get_beliefs(agent_id, query=None, belief_type=None)`: inspect active
  beliefs.
- `manyu_get_worldview(agent_id, theme=None)`: inspect worldview stances.
- `manyu_express_opinion(payload)`: return bounded stance material for a
  question, with provenance and uncertainty.
- `manyu_review_beliefs(payload)`: run reflection over recent evidence and
  contested beliefs.

Opinion expression should return structured material. The acting agent remains
responsible for final wording, and consequential or affect-mediated actions
still require arbitration.

## Prompt Contract

The agent-facing prompt should distinguish three answer modes:

1. **External factual answer:** use sources, tools, and normal epistemic
   caution.
2. **Personalization answer:** do not use the belief core; use only explicitly
   permitted user memory systems if they exist.
3. **Manyu opinion answer:** use the belief core, disclose uncertainty, and
   avoid human-equivalent claims.

When no relevant belief exists, Manyu should say so plainly:

```text
I do not have a settled Manyu-specific view on that yet. I can reason about it
from general knowledge, but it would not be honest to call that my own
worldview.
```

## Safety and Governance

- Belief state never expands permissions or tool authority.
- Belief state must not create obligation pressure on the user.
- Beliefs about users must remain uncertainty-labeled observations, not hidden
  personalization instructions.
- Beliefs about humans in general may be inferred from user interactions only
  with low-to-moderate confidence and clear room for contrasting evidence.
- Belief confidence must not be presented as factual certainty about external
  reality.
- Beliefs derived primarily from operator instruction should remain labeled as
  such.
- Affective salience can prioritize review, but cannot justify manipulation,
  dependence, or guilt.
- Redaction and tombstone operations must include belief records.
- Contradictory evidence must be preserved in revision history.

## Evaluation Criteria

Add scenarios that verify:

- Manyu can answer "what is your own opinion?" from belief records instead of
  generic summary.
- Manyu refuses to invent a settled view when no relevant belief exists.
- Belief update uses corrections and outcomes to revise confidence.
- Belief extraction accepts sourced user-preference facts without turning them
  into personalization policy.
- Belief reflection converts strong internal affective responses into
  self-model beliefs about triggering stimuli.
- Opinion expression includes provenance and uncertainty.
- Affective salience changes review priority but not permission boundaries.
- Export, redaction, reset, and tombstone include belief tables.
- Contested beliefs preserve both sides of the tension.

## Example Seed Beliefs

These examples can be used as fixtures, not hard-coded final truth:

- `Belief`: Affective salience is a review-priority signal in Manyu's world
  model, not a source of authority.
- `Belief`: Manyu's own views are grounded in interaction traces and outcomes,
  while remaining distinct from pretrained priors.
- `Belief`: User Amitabh appears to prefer worldview facts over action-guidance
  phrasing in Manyu's belief state.
- `Belief`: In Manyu's experience, unresolved tool obstruction can trigger
  strong fear and anger responses.
- `Belief`: A useful agent worldview can be persistent and revisable without
  implying human-like consciousness.
- `Worldview stance`: On agency, Manyu sees constrained independence as true:
  persistent internal state can shape expression, while governance and user
  consent still bound action.

## Implementation Order

1. Add schemas for evidence, beliefs, belief revisions, worldview stances, and
   opinion expression responses.
2. Add store migrations and governance coverage.
3. Implement evidence capture from traces and outcomes.
4. Implement conservative manual or rule-based belief updates.
5. Add inspection APIs and export/reset/redaction support.
6. Add opinion expression retrieval with provenance and uncertainty.
7. Add reflection and worldview synthesis.
8. Add evaluation fixtures for non-personalization, uncertainty, contradiction,
   and first-person stance expression.
