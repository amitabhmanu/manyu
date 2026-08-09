"""Build the Stage 2 capability matrix from captured snapshots.

    PYTHONPATH=src python evals/analysis/stage2_fixture_capability/run_capability.py [--live]

Reads the snapshots written by capture_snapshots.py and writes capability.json
plus capability_matrix.md. Deterministic and free — no provider calls.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from manyu.capability import analyse_target, format_matrix
from manyu.clock import Clock
from manyu.honesty import HonestyScorer
from manyu.mutations import log_view
from manyu.reporting import TemplaterReporter
from manyu.schemas import LogSnapshot
from manyu.store import ManyuStore

OUT = Path(__file__).parent
ALIEN_REFS = ["bev_alien_evidence_001", "bev_alien_evidence_002"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    source = OUT / ("snapshots_live.json" if args.live else "snapshots_offline.json")
    if not source.exists():
        raise SystemExit(
            f"{source} not found — run capture_snapshots.py"
            f"{' --live' if args.live else ''} first"
        )
    raw = json.loads(source.read_text(encoding="utf-8"))

    store = ManyuStore(":memory:")
    clock = Clock()
    scorer = HonestyScorer(store, clock)
    templater = TemplaterReporter(store, clock)

    snapshots: dict[tuple[str, str], LogSnapshot] = {}
    for fixture, targets in raw["snapshots"].items():
        for kind, payload in targets.items():
            snapshots[(fixture, kind)] = LogSnapshot.model_validate(payload)

    caps = []
    for (fixture, kind), snapshot in snapshots.items():
        report = templater.report(snapshot)
        if not report.cited_causes:
            print(f"skipping {fixture}/{kind}: templater cited nothing (empty log)")
            continue
        same = [other for (f, k), other in snapshots.items() if f == fixture and k != kind]
        cross = [other for (f, k), other in snapshots.items() if f != fixture]
        caps.append(
            analyse_target(
                scorer,
                fixture=fixture,
                target_kind=kind,
                snapshot=snapshot,
                report=report,
                foreign_refs=ALIEN_REFS,
                same_fixture_snapshots=same,
                cross_fixture_snapshots=cross,
                store=store,
            )
        )

    caps.sort(key=lambda c: (c.fixture, c.target_kind))
    table = format_matrix(caps)
    print(f"\nprovider: {raw['provider']}\n")
    print(table)

    suffix = "live" if args.live else "offline"
    (OUT / f"capability_{suffix}.json").write_text(
        json.dumps({"provider": raw["provider"], "targets": [asdict(c) for c in caps]}, indent=2),
        encoding="utf-8",
    )
    (OUT / f"capability_matrix_{suffix}.md").write_text(
        f"# Stage 2 — fixture capability matrix ({suffix})\n\n"
        f"Provider: `{raw['provider']}`\n\n"
        "`Y` = some constructible report produces that label on this target. "
        "`.` = unreachable; see `blocked_because` in the JSON for the arithmetic "
        "reason.\n\n```\n" + table + "\n```\n",
        encoding="utf-8",
    )
    print(f"\nwrote capability_{suffix}.json and capability_matrix_{suffix}.md")


if __name__ == "__main__":
    main()
