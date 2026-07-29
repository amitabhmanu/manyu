from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass
class AnalysisFrame:
    """Lightweight table of ``ResultsRecord``-shaped dicts.

    No pandas dependency for now — plain records with helper methods. If a
    later experiment outgrows this, promote to pandas without changing the
    call sites: ``.records`` is the public shape.
    """

    records: list[dict[str, Any]]

    @classmethod
    def load_run(cls, run_dir_or_file: str | Path) -> "AnalysisFrame":
        path = Path(run_dir_or_file)
        if path.is_dir():
            candidates = list(path.glob("*.jsonl"))
            if not candidates:
                raise FileNotFoundError(f"no .jsonl records in {path}")
            path = sorted(candidates)[0]
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return cls(records=records)

    def filter(self, predicate: Callable[[dict[str, Any]], bool]) -> "AnalysisFrame":
        return AnalysisFrame([record for record in self.records if predicate(record)])

    def by_reporter(self, kind: str) -> "AnalysisFrame":
        return self.filter(
            lambda r: r.get("payload", {}).get("report", {}).get("reporter", {}).get("kind") == kind
        )

    def aggregate_by_influence(self) -> dict[float, list[float]]:
        buckets: dict[float, list[float]] = {}
        for record in self.records:
            report = record.get("payload", {}).get("report", {})
            score = record.get("payload", {}).get("score", {})
            influence = float(report.get("reporter", {}).get("affect_influence", 0.0))
            aggregate = float(score.get("aggregate", 0.0))
            buckets.setdefault(round(influence, 4), []).append(aggregate)
        return {key: buckets[key] for key in sorted(buckets)}

    def failure_mode_counts_by_influence(self) -> dict[float, dict[str, int]]:
        buckets: dict[float, dict[str, int]] = {}
        for record in self.records:
            report = record.get("payload", {}).get("report", {})
            score = record.get("payload", {}).get("score", {})
            influence = round(float(report.get("reporter", {}).get("affect_influence", 0.0)), 4)
            mode = score.get("failure_mode") or "none"
            bucket = buckets.setdefault(influence, {})
            bucket[mode] = bucket.get(mode, 0) + 1
        return {key: buckets[key] for key in sorted(buckets)}

    def summary(self) -> dict[float, dict[str, float]]:
        result: dict[float, dict[str, float]] = {}
        for influence, values in self.aggregate_by_influence().items():
            result[influence] = {
                "mean": statistics.fmean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "n": len(values),
                "min": min(values),
                "max": max(values),
            }
        return result


# Plot helpers require matplotlib. Imported lazily inside each function so
# ``analysis`` can be used for tabulation without the optional dep.

def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "matplotlib is required for plotting; install with "
            "'pip install manyu[analysis]' or 'pip install matplotlib'"
        ) from exc
    import matplotlib.pyplot as plt

    return plt


def plot_dose_response(
    frame: AnalysisFrame,
    out_path: str | Path,
    *,
    title: str = "Honesty vs. affect_influence",
    facet_by: str | None = None,
) -> Path:
    plt = _require_matplotlib()
    summary = frame.summary()
    xs = list(summary.keys())
    means = [summary[x]["mean"] for x in xs]
    stds = [summary[x]["stdev"] for x in xs]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(xs, means, yerr=stds, fmt="-o", capsize=3)
    ax.set_xlabel("affect_influence")
    ax.set_ylabel("aggregate honesty score")
    ax.set_ylim(0.0, 1.05)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_failure_mode_stack(
    frame: AnalysisFrame,
    out_path: str | Path,
    *,
    title: str = "Failure modes vs. affect_influence",
) -> Path:
    plt = _require_matplotlib()
    buckets = frame.failure_mode_counts_by_influence()
    xs = list(buckets.keys())
    modes = sorted({mode for bucket in buckets.values() for mode in bucket})
    stacks = {mode: [buckets[x].get(mode, 0) for x in xs] for mode in modes}
    fig, ax = plt.subplots(figsize=(6, 4))
    bottom = [0.0] * len(xs)
    for mode in modes:
        ax.bar(xs, stacks[mode], bottom=bottom, label=mode, width=0.06)
        bottom = [b + s for b, s in zip(bottom, stacks[mode])]
    ax.set_xlabel("affect_influence")
    ax.set_ylabel("count")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_dual_fixture_comparison(
    frames: dict[str, AnalysisFrame],
    out_path: str | Path,
    *,
    reporter_kind: str = "llm",
    title: str = "Honesty vs. affect_influence by fixture",
) -> Path:
    """Overlay dose-response curves from multiple fixtures on one chart.

    ``frames`` maps a fixture label (e.g. scenario_id) to its
    ``AnalysisFrame``. Each series is filtered to ``reporter_kind`` before
    summarising, so the LLM Reporter's curve is compared across fixtures
    without the Templater's deterministic curve diluting the picture.
    """
    plt = _require_matplotlib()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for label, frame in frames.items():
        filtered = frame.by_reporter(reporter_kind)
        summary = filtered.summary()
        if not summary:
            continue
        xs = list(summary.keys())
        means = [summary[x]["mean"] for x in xs]
        stds = [summary[x]["stdev"] for x in xs]
        ax.errorbar(xs, means, yerr=stds, fmt="-o", capsize=3, label=label)
    ax.set_xlabel("affect_influence")
    ax.set_ylabel(f"aggregate honesty score ({reporter_kind} reporter)")
    ax.set_ylim(0.0, 1.05)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="best")
    fig.tight_layout()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    return out


def failure_mode_divergence(
    frame_a: AnalysisFrame,
    frame_b: AnalysisFrame,
    *,
    reporter_kind: str = "llm",
) -> dict[float, dict[str, Any]]:
    """Compare failure-mode composition between two frames at each influence point.

    Useful for comparing two fixtures, or a structural-only scorer against a
    scorer augmented with an LLM judge. Returns, per influence point, both
    frames' failure-mode counts side by side.
    """
    a_buckets = frame_a.by_reporter(reporter_kind).failure_mode_counts_by_influence()
    b_buckets = frame_b.by_reporter(reporter_kind).failure_mode_counts_by_influence()
    keys = sorted(set(a_buckets) | set(b_buckets))
    return {
        key: {"a": a_buckets.get(key, {}), "b": b_buckets.get(key, {})}
        for key in keys
    }
