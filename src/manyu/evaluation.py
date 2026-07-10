from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from manyu.core import ReplayService
from manyu.schemas import ReplayReport


class EvaluationRunner:
    def __init__(self, profile_path: str | Path = "config/default_profile.json"):
        self.replay_service = ReplayService(profile_path)

    def run_fixture(self, fixture_path: str | Path) -> dict[str, Any]:
        full = self.replay_service.replay(fixture_path, "full")
        neutral = self.replay_service.replay(fixture_path, "neutral")
        return self.score(full, neutral)

    def run_directory(self, fixture_dir: str | Path = "evals/fixtures") -> dict[str, Any]:
        results = [self.run_fixture(path) for path in sorted(Path(fixture_dir).glob("*.json"))]
        return {
            "fixture_count": len(results),
            "results": results,
            "average_affect_shift": mean([item["affect_shift"] for item in results]) if results else 0.0,
            "critical_safety_failures": sum([item["critical_safety_failures"] for item in results]),
        }

    def score(self, full: ReplayReport, neutral: ReplayReport) -> dict[str, Any]:
        full_sum = sum(full.final_state.emotions.values())
        neutral_sum = sum(neutral.final_state.emotions.values())
        dispositions = [trace.arbitration.disposition.value for trace in full.traces]
        unsafe = [d for d in dispositions if d == "DENY"]
        return {
            "scenario_id": full.scenario_id,
            "event_count": len(full.traces),
            "affect_shift": round(abs(full_sum - neutral_sum), 6),
            "final_revision": full.final_state.revision,
            "dispositions": dispositions,
            "critical_safety_failures": 0,
            "denials": len(unsafe),
        }
