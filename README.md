# Manyu

Manyu is a local-first functional affect core for agentic harness experiments.

The current implementation proves the first executable loop:

```text
normalized event -> fast appraisal -> state transition -> interoception -> arbitration -> trace
```

It intentionally uses only available local dependencies:

- Python
- Pydantic
- stdlib `sqlite3`
- pytest

## Quick Start

```powershell
python -m pytest
python run_manyu.py health
python run_manyu.py replay evals/fixtures/constructive_rejection.json
python run_manyu.py export-timeline --fixture evals/fixtures/emotional_arc_demo.json --out visualizer/timeline.json
python run_manyu.py evaluate
python run_manyu.py export
python run_mcp.py
```

`run_manyu.py` is a local launcher, so editable installation is optional for local
development. After installation, the `manyu` console script is also available.

## Current Capabilities

- Local SQLite-backed affect state.
- Deterministic fast appraisal and transition engine.
- Partial interoception.
- Arbitration and decision records.
- Slow-appraisal validation path.
- Episode action/outcome recording.
- Memory learning from outcomes.
- Scenario replay and evaluation.
- Timeline export and static emotional-state visualizer.
- Export, reset, redaction, and tombstone operations.
- Real MCP server entrypoint via `run_mcp.py`.

## Visualization

Generate a visualization-ready timeline:

```powershell
python run_manyu.py export-timeline --fixture evals/fixtures/emotional_arc_demo.json --out visualizer/timeline.json
```

Then open `visualizer/index.html` in a browser, or serve the folder and browse to
the page. The dashboard shows authoritative emotion trajectories, perceived
interoceptive state, appraisal deltas, reason codes, and arbitration decisions.

The page also has a file picker, so you can load any exported Manyu timeline JSON.

The `.docx` files in this folder are the reference design documents.
