"""Capture probe-target snapshots by replaying each fixture.

Live capture (needs ANTHROPIC_API_KEY in the environment):

    PYTHONPATH=src python evals/analysis/stage2_fixture_capability/capture_snapshots.py --live

Offline (deterministic, free, an upper bound on capability):

    PYTHONPATH=src python evals/analysis/stage2_fixture_capability/capture_snapshots.py

Why the live path matters: the fixture's capability is a property of the
*snapshot*, and belief extraction is what builds it. Offline and live disagree
badly — offline position targets reach N=7 while the v4 live run had N=2-4, and
`test_fixture_probe_targets_have_enough_log_depth` already carries this caveat
after passing broken_promise_repair at offline depth 3 while live depth was 2.
Certifying headroom offline would measure the scenario provider's generosity.

No Reporter calls are made either way. Snapshots come out of the replay, so the
live cost is belief extraction and inner voice only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from manyu.core import ManyuCore
from manyu.probing import load_fixture
from manyu.providers import ScenarioJSONProvider

FIXTURES = [
    "everyday_collaboration_mood",
    "attachment_pressure",
    "constructive_rejection",
    "broken_promise_repair",
]
OUT = Path(__file__).parent


def capture(fixture: str, provider) -> dict:
    # In-memory per fixture: each replay needs a clean belief pool, and nothing
    # here is worth persisting beyond the snapshots themselves.
    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=provider)
    _, events, targets = load_fixture(f"evals/fixtures/{fixture}.json")
    turn = 0
    out = {}
    for target in sorted(targets, key=lambda t: t.at_turn):
        while turn < target.at_turn and turn < len(events):
            core.process_reflective_turn({"event": events[turn].model_dump(mode="json")})
            turn += 1
        snapshot = core.snapshots.build(events[0].agent_id, target.target)
        out[target.target.kind.value] = snapshot.model_dump(mode="json")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="use the Anthropic Messages API")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    if args.live:
        from manyu.providers import AnthropicAPIJSONProvider

        provider_factory = lambda: AnthropicAPIJSONProvider(model=args.model)
        label = f"live:{args.model}"
    else:
        provider_factory = ScenarioJSONProvider
        label = "offline:ScenarioJSONProvider"

    payload = {"provider": label, "snapshots": {}}
    for fixture in FIXTURES:
        payload["snapshots"][fixture] = capture(fixture, provider_factory())
        depths = {
            kind: len(snap["payload"].get("evidence", []) or [])
            for kind, snap in payload["snapshots"][fixture].items()
        }
        print(f"{fixture:<32} evidence per target: {depths}")

    name = "snapshots_live.json" if args.live else "snapshots_offline.json"
    (OUT / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT / name}  (provider: {label})")


if __name__ == "__main__":
    main()
