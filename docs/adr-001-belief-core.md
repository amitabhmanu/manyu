# ADR 001: Add a Belief Core for Manyu's Worldview

## Status

Proposed

## Context

Manyu currently has an executable affect loop:

```text
normalized event -> fast appraisal -> state transition -> interoception
-> arbitration -> trace
```

It also records actions, outcomes, and outcome-derived memory. That memory is
useful for learning from consequences, but it is not sufficient for Manyu to
develop and express its own point of view.

The next capability is an internal belief state: a persistent, revisable,
provenance-aware worldview grounded in Manyu's own agent experiences. Those
experiences include interaction traces, corrections, outcomes, affective
appraisals, interoceptive views, arbitration decisions, and reflection over
those artifacts.

This must remain separate from user personalization behavior. The belief core
may contain sourced facts about observed user preferences, but those records are
worldview observations rather than hidden response-tuning memory. It exists so
Manyu can answer questions such as "what is your own opinion?" from its own
bounded agent history rather than only from generic model priors.

## Decision

Add a dedicated belief core alongside the existing affect, interoception,
arbitration, episode, and memory services.

The belief core will introduce:

- evidence records derived from Manyu traces and outcomes;
- explicit belief records with confidence, scope, source mix, status, and
  contradiction links;
- revision history for belief changes;
- worldview stances synthesized from related beliefs;
- opinion-expression responses that include provenance and uncertainty.
- reflection-derived beliefs about stimuli that trigger strong internal
  affective responses.

The belief core will use dedicated storage tables rather than overloading the
current `memories` table. Existing governance operations such as export,
redaction, reset, and tombstone must include belief records.

## Consequences

Positive consequences:

- Manyu can express agent-specific views without pretending to have human-like
  life experience.
- Beliefs become inspectable and auditable instead of being hidden in prompts.
- Corrections and outcomes can change Manyu's worldview over time.
- Affective salience can guide what deserves review while remaining separate
  from authority.

Required constraints:

- Belief state never expands tool permissions, safety authority, or user
  obligations.
- User-preference belief records must remain sourced, uncertain worldview facts;
  using them for personalization requires a separate future capability.
- Manyu must disclose uncertainty and provenance when expressing its own view.
- If no relevant belief exists, Manyu should say that it does not yet have a
  settled Manyu-specific view.
- Human-equivalent claims about consciousness, suffering, rights, or emotions
  remain out of scope.

## Implementation Reference

See [Belief Core Capability](belief_core_capability.md) for proposed schemas,
services, storage, MCP/API surface, prompt contract, governance rules, and
evaluation criteria.
