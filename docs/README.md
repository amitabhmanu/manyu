# Manyu Documentation Index

The formal Manyu `.docx` documents live in the project root for now. This
folder is reserved for implementation-facing Markdown notes, generated schema
exports, and future ADRs.

## Implementation Notes

- [ADR 001: Belief Core](adr-001-belief-core.md): decision record for adding
  Manyu's internal worldview capability.
- [Belief Core Capability](belief_core_capability.md): proposed internal
  worldview and belief-state capability for Manyu. This is explicitly separate
  from user personalization memory.

## Research Program

- [Manyu as an Instrument: The Crux](Manyu_experiments_crux.md): the merged-core
  thesis and the nine experiments that use provenance as ground truth.
- [Experiments Backlog](experiments_backlog.md): dependency-ordered sequence of
  the ten experiments, with status tracking.
- [Experiments folder](experiments/README.md): per-experiment requirements,
  design, results, retrospective — and the **standing methodology rules** that
  bind every experiment, currently **MS-1** (every scored dimension must be
  shown capable of at least two values before any of its numbers are reported).

## Demo Notes

- `evals/fixtures/everyday_collaboration_mood.json` drives the reflective
  inner-voice/mood demo.
- `python run_manyu.py --scenario-provider process-scenario ...` runs the full
  local scenario path without pretending to call Codex CLI.
- Omitting `--scenario-provider` uses the Codex CLI JSON provider and reports
  structured provider errors if the live CLI cannot run.
