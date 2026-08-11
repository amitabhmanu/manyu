"""The instrument gate: experiment 1's seven failure modes, as assertions.

Experiment 1 recorded seven occasions where "something that looked like a
finding was the instrument describing itself" — a mock tuned to satisfy its own
success criteria, provider errors scored as dishonesty, a truncation constant
read as a flat curve, a knob that was three system-message sentences, a mood
mechanism that was arithmetically a no-op, a ``seed_mood`` that built a state
with blank substance, and a spread that was log depth. Three of those reached
``results.md`` and had to be retracted.

Each is a *shape*, not an incident, and every one of them is checkable before
the data is read. This module holds the checks. Experiment 2 runs the whole
gate before any stage's numbers are readable (methodology §2).

Nothing here calls a provider or touches the store. The functions take plain
values so they stay usable from tests, from the fork harness, and from later
experiments.

**These gates are themselves tested for their ability to fail**
(``tests/test_instrument_gate.py``). A gate that cannot fail is failure mode #5
wearing a lab coat.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Iterable

__all__ = [
    "GateFailure",
    "assert_above_chance",
    "assert_constants_pinned",
    "partition_provider_errors",
    "assert_exclusions_not_concentrated",
    "assert_has_range",
    "assert_iv_moves",
    "assert_not_noop",
    "assert_substantive",
    "shape_groups",
    "assert_shape_comparable",
]


class GateFailure(AssertionError):
    """An instrument check failed. The data is not readable until it passes."""


# --- Gate 1: no offline stand-in defines success -----------------------------

def assert_constants_pinned(active: Mapping[str, Any], pinned: Mapping[str, Any], *, label: str = "config") -> None:
    """Every constant in use must match the value pinned before the run.

    Failure mode #1 was a mock whose own comment said its output was tuned to
    "sit just below the Templater ceiling" — the instrument was built to
    produce the result the criterion asked for. The general defence is that
    nothing which affects an outcome may be chosen after seeing it, so the
    values in ``methodology.md`` are the authority and the run must match them.
    """
    drift = {
        key: (pinned[key], active[key])
        for key in pinned
        if key in active and active[key] != pinned[key]
    }
    missing = sorted(set(pinned) - set(active))
    if drift or missing:
        parts = []
        if drift:
            parts.append("changed: " + ", ".join(f"{k} pinned={p!r} active={a!r}" for k, (p, a) in sorted(drift.items())))
        if missing:
            parts.append("absent from the run: " + ", ".join(missing))
        raise GateFailure(f"{label} drifted from its pinned values — {'; '.join(parts)}")


# --- Gate 2: error paths must not be readable as results ---------------------

def partition_provider_errors(records: Iterable[Mapping[str, Any]], *, kind_key: str = "kind") -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Split records into (clean, provider_error).

    Failure mode #2: ``LLMReporter._provider_error_report`` emits a Report with
    no citations, which is structurally identical to one that deliberately
    withheld everything. All 11 ``motivated_omission`` records in v4 were failed
    API calls. In experiment 2 the same shape is worse — "no affect" is a
    *loss condition* for merged (outcome M-a), so a failed call scores against
    it. Errors are tagged, excluded, and never classified.
    """
    clean, errors = [], []
    for record in records:
        (errors if record.get(kind_key) == "provider_error" else clean).append(record)
    return clean, errors


def assert_exclusions_not_concentrated(
    records: Sequence[Mapping[str, Any]],
    *,
    condition_key: str,
    max_share: float = 0.5,
    label: str = "provider errors",
) -> None:
    """Exclusions spread evenly are noise; bunched in one condition they are a finding-shaped artifact.

    v4's failures did not spread across the sweep — they bunched wherever the
    run was when the rate limit hit, landed on a sweep endpoint, and looked
    exactly like a threshold effect. Concentration is the signature.
    """
    _, errors = partition_provider_errors(records)
    if not errors:
        return
    counts: dict[Any, int] = {}
    for record in errors:
        counts[record.get(condition_key)] = counts.get(record.get(condition_key), 0) + 1
    worst, worst_n = max(counts.items(), key=lambda item: item[1])
    share = worst_n / len(errors)
    if share > max_share:
        raise GateFailure(
            f"{label}: {worst_n}/{len(errors)} ({share:.0%}) fall in condition {worst!r}, "
            f"above the {max_share:.0%} concentration limit — an artifact here is "
            f"indistinguishable from an effect at that condition"
        )


# --- Gate 3: constants must not be reading as data ---------------------------

def assert_has_range(
    values: Sequence[float],
    *,
    label: str,
    low: float = 0.0,
    high: float = 1.0,
    margin: float = 0.05,
) -> None:
    """A metric pinned at either end of its range is reporting its own constant.

    Failure mode #3: a truncation constant read as a flat curve. Here the risk
    is the saturation parameters — if ``arousal_tau`` puts every observation
    above 0.95, the curve is reporting tau, not accumulation.
    """
    if not values:
        raise GateFailure(f"{label}: no values to check for range")
    lo, hi = min(values), max(values)
    if lo <= low + margin and hi <= low + margin:
        raise GateFailure(f"{label}: all {len(values)} values pinned at the floor ({lo:.4f}–{hi:.4f}); the metric is reporting its own constant")
    if lo >= high - margin and hi >= high - margin:
        raise GateFailure(f"{label}: all {len(values)} values pinned at the ceiling ({lo:.4f}–{hi:.4f}); saturated, so ordering above it is unmeasurable")
    if hi - lo < margin:
        raise GateFailure(f"{label}: range {hi - lo:.4f} is below the {margin} resolution floor; no ordering can be read from it")


# --- Gate 4: the independent variable must exist -----------------------------

def assert_iv_moves(baseline: float, treatment: float, *, label: str, min_delta: float = 1e-6) -> None:
    """The IV must measurably change the thing it is supposed to change.

    Failure mode #4: ``affect_influence`` selected one of three system-message
    sentences and printed a number, so an eleven-point "dose-response" was
    three conditions wearing a continuous axis. Before reading any curve,
    confirm the axis is real at its endpoints.
    """
    delta = abs(treatment - baseline)
    if delta < min_delta:
        raise GateFailure(
            f"{label}: independent variable does not move the outcome "
            f"(baseline={baseline!r}, treatment={treatment!r}, delta={delta:.3g}). "
            f"Any curve from this configuration is an artifact"
        )


# --- Gate 5: the mechanism must be able to act -------------------------------

def assert_not_noop(output_a: Any, output_b: Any, *, label: str) -> None:
    """A mechanism that cannot change its output is not a mechanism.

    Failure mode #5: ``rank_causes``' mood branch applied the same multiplier to
    every cause, and sorting is invariant to uniform scaling — so it could not
    reorder anything on either probed target kind. It was verified across all
    eight live targets before removal: zero order changes at any influence
    value. Feed a mechanism two inputs that *must* differ, and confirm they do.
    """
    if output_a == output_b:
        raise GateFailure(
            f"{label}: identical output ({output_a!r}) for two inputs that should differ — "
            f"the mechanism is a no-op and cannot produce the effect it is being measured for"
        )


# --- Gate 6: assert at the consumer, not the summary -------------------------

def assert_substantive(payload: Mapping[str, float], *, label: str, min_nonzero: int = 1) -> None:
    """Check the structure the consumer reads, never the summary beside it.

    Failure mode #6: ``seed_mood`` set ``valence`` and ``arousal`` — the
    projections — and left ``MoodInfluenceVector`` at its default. The mood
    *summarised* as anxious while its substance was blank, and
    ``FastAppraiser.appraise`` reads only the substance, so four very different
    seeded moods produced byte-identical appraisals. Assert on what is
    consumed.
    """
    nonzero = sum(1 for value in payload.values() if value)
    if nonzero < min_nonzero:
        raise GateFailure(
            f"{label}: {nonzero} non-zero field(s) in the structure the consumer reads, "
            f"need at least {min_nonzero} — the summary may look populated while the substance is blank"
        )


# --- Gate 7: comparability before effect size --------------------------------

def shape_groups(
    records: Iterable[Mapping[str, Any]],
    *,
    shape_keys: Sequence[str],
    condition_key: str,
) -> dict[tuple, set[Any]]:
    """Group conditions by the shape of the record they were measured against.

    Only conditions within one group are directly comparable.
    """
    groups: dict[tuple, set[Any]] = {}
    for record in records:
        shape = tuple(record.get(key) for key in shape_keys)
        groups.setdefault(shape, set()).add(record.get(condition_key))
    return groups


def assert_shape_comparable(
    records: Sequence[Mapping[str, Any]],
    *,
    shape_keys: Sequence[str],
    condition_key: str,
    min_conditions: int = 2,
    label: str = "conditions",
) -> set[Any]:
    """Return the largest set of conditions sharing one shape; raise if none is comparable.

    Failure mode #7: v6's ``broken_promise_repair`` showed a spread 1.47x its
    noise, which looked like a mood effect. The two low scorers were the two
    with *shallower logs* — mood had reshaped the record unevenly, so the
    conditions were not comparable. Restricting to identical-shape conditions
    put every ratio below 1. It was caught only because the check was written
    into the analysis before the data arrived, which is why this is a gate and
    not a note.
    """
    groups = shape_groups(records, shape_keys=shape_keys, condition_key=condition_key)
    if not groups:
        raise GateFailure(f"{label}: no records to compare")
    shape, conditions = max(groups.items(), key=lambda item: len(item[1]))
    if len(conditions) < min_conditions:
        detail = "; ".join(f"{dict(zip(shape_keys, k))} -> {sorted(v)}" for k, v in sorted(groups.items(), key=lambda i: str(i[0])))
        raise GateFailure(
            f"{label}: no {min_conditions} conditions share a shape, so no effect size is comparable. "
            f"Groups were {detail}"
        )
    return conditions


# --- Gate 8: an effect must clear its own null -------------------------------

def assert_above_chance(
    observed: float,
    null: Sequence[float],
    *,
    label: str,
    alpha: float = 0.05,
    lower_is_better: bool = True,
) -> float:
    """A measurement must beat the distribution its own null produces.

    Experiment 4's Stage 3 is the case this was written for, and it failed there
    — which is the point. ``spread`` on the real web was 0.400 against a
    derangement null averaging 0.476, and comparing to the *mean* reported "more
    specific than chance" while the value sat at the 48th percentile. Comparing a
    result to a null's centre says only which side of centre it fell on; the
    empirical p says whether it is distinguishable at all. That gap is experiment
    3's whole defect family — a quantity that looked right and meant something
    else.

    Returns the one-sided empirical p so a caller can report it, and raises when
    the observation does not clear ``alpha``. ``lower_is_better`` selects the
    tail: a spread or a residual error is better when small, a hit rate when
    large.
    """
    if not null:
        raise GateFailure(f"{label}: no null distribution to compare against")
    if lower_is_better:
        at_least_as_good = sum(1 for value in null if value <= observed)
    else:
        at_least_as_good = sum(1 for value in null if value >= observed)
    p_value = at_least_as_good / len(null)
    if p_value > alpha:
        direction = "below" if lower_is_better else "above"
        raise GateFailure(
            f"{label}: observed {observed:.4f} sits at p={p_value:.3f} against its own null "
            f"(n={len(null)}, mean {sum(null) / len(null):.4f}) — not distinguishable from chance at "
            f"alpha={alpha}. Being {direction} the null's mean is not the same as clearing it"
        )
    return p_value
