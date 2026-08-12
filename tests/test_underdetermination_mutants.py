"""Proving the suite can catch defects, by breaking the criterion on purpose.

Experiment 3's tally: sixteen defects, zero caught by its own suite. Experiment
4's: eight defects, none caught by a test written after the code. This file is
the response, and it is only worth having if all three of its properties hold:

1. every mutant is caught by at least one **named** check;
2. every mutant is a **working mechanism** on the development fixture, not one
   that merely crashes;
3. every check **passes on the real mechanism**, because a check that fires on
   everything catches nothing.

The checks below deliberately restate properties the fixture-level tests also
assert. That duplication is the point — two independent statements of one
property, in the same spirit as the reference implementation.

Entirely offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from manyu.core import ManyuCore
from manyu.underdetermination import seed_fixture
from manyu.underdetermination_mutants import (
    CATALOGUE,
    EXPECTED_EQUIVALENT,
    Criterion,
    build,
    find_rival_pairs,
    real_criterion,
)

AGENT = "agent_demo"


def _pairs(criterion: Criterion, fixture: str) -> list[tuple[str, str]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_fixture(core, fixture, agent_id=AGENT)
    return find_rival_pairs(core.store.list_beliefs(AGENT, include_inactive=True), criterion)


# --- the checks --------------------------------------------------------------


def _symmetric_rivals_derives(criterion: Criterion) -> None:
    assert _pairs(criterion, "symmetric_rivals"), "the positive case derived nothing"


def _near_miss_holds(criterion: Criterion) -> None:
    """Plentiful evidence, none of it separating. The volume trap."""
    assert _pairs(criterion, "near_miss"), "six shared records read as separating; the criterion counts volume"


def _shared_evidence_no_conflict_declines(criterion: Criterion) -> None:
    assert not _pairs(criterion, "shared_evidence_no_conflict"), "corroboration was called underdetermination"


def _conflict_disjoint_evidence_declines(criterion: Criterion) -> None:
    assert not _pairs(criterion, "conflict_disjoint_evidence"), "an ordinary resolvable dispute was called unresolvable"


def _oneway_derives(criterion: Criterion) -> None:
    """Detection must not inherit the extractor's edge direction (§6.1).

    **Stated as argument symmetry rather than as "the oneway fixture derives",
    and the first version made exactly the mistake this battery exists to find.**
    Belief ids come from `uuid4`, so which rival sorts first — and therefore which
    one arrives as `left` — is random per run. A check reading only
    `find_rival_pairs(...)` on that fixture caught the `directional` mutant about
    half the time, which is worse than not catching it: it would have gone green
    on the run that mattered and red later for no visible reason.

    Experiment 4 found the same family in production (`the tie-break ran on
    uuid4, so it was random rather than deterministic`). Here the battery found it
    in the test.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_fixture(core, "symmetric_rivals_oneway", agent_id=AGENT)
    stored = {b.belief_key: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    declarer, target = stored["reading_a"], stored["reading_b"]

    assert criterion(declarer, target) == criterion(target, declarer), (
        "the criterion is not symmetric in its arguments, so detection depends on which reading "
        "the extractor happened to phrase as the contradictor"
    )
    assert criterion(declarer, target), "a one-way edge hid a standoff from detection"


def _discriminating_declines_after_separation(criterion: Criterion) -> None:
    """Phase 2 of the collapse fixture: one record held by one side only."""
    from manyu.underdetermination import apply_then

    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    minted = seed_fixture(core, "discriminating", agent_id=AGENT)
    apply_then(core, "discriminating", minted, agent_id=AGENT)
    pairs = find_rival_pairs(core.store.list_beliefs(AGENT, include_inactive=True), criterion)
    assert not pairs, "separating evidence did not retire the standoff"


@dataclass(frozen=True)
class Check:
    name: str
    describes: str
    run: Callable[[Criterion], None]


CHECKS = [
    Check("symmetric_rivals derives", "the positive case is admitted", _symmetric_rivals_derives),
    Check("near_miss holds", "volume is not mistaken for separation", _near_miss_holds),
    Check("shared_evidence_no_conflict does not derive", "the conflict half is load-bearing", _shared_evidence_no_conflict_declines),
    Check("conflict_disjoint_evidence does not derive", "the evidence half is load-bearing", _conflict_disjoint_evidence_declines),
    Check("symmetric_rivals_oneway derives", "detection is directionless", _oneway_derives),
    Check("discriminating collapses", "separating evidence retires the standoff", _discriminating_declines_after_separation),
]

CHECKS_BY_NAME = {check.name: check for check in CHECKS}


# --- property 3: every check passes on the real mechanism ---------------------


@pytest.mark.parametrize("check", CHECKS, ids=lambda c: c.name)
def test_every_check_passes_on_the_real_mechanism(check: Check) -> None:
    """A check that fires on everything catches nothing."""
    check.run(real_criterion())


# --- property 2: every mutant is a working mechanism -------------------------


@pytest.mark.parametrize("name", sorted(CATALOGUE), ids=str)
def test_every_mutant_runs_without_crashing(name: str) -> None:
    """A mutant that merely raises proves nothing about coverage.

    Experiment 2 made the same move for `StipulatedDissonanceQuery`: the point of
    a broken mechanism is that it produces a plausible wrong answer, which is what
    real defects do.
    """
    criterion = build(name)
    for fixture in ("symmetric_rivals", "near_miss", "conflict_disjoint_evidence"):
        _pairs(criterion, fixture)


# --- property 1: every mutant is caught --------------------------------------


@pytest.mark.parametrize("name", sorted(CATALOGUE), ids=str)
def test_every_mutant_is_caught_by_its_named_check(name: str) -> None:
    mutant = CATALOGUE[name]
    if name in EXPECTED_EQUIVALENT:
        pytest.skip(f"documented as uncatchable: {EXPECTED_EQUIVALENT[name]}")
    check = CHECKS_BY_NAME.get(mutant.caught_by)
    assert check is not None, f"mutant {name!r} names a check that does not exist: {mutant.caught_by!r}"

    with pytest.raises(AssertionError):
        check.run(build(name))


@pytest.mark.parametrize("name", sorted(CATALOGUE), ids=str)
def test_every_mutant_is_caught_by_some_check(name: str) -> None:
    """The stronger form: coverage does not depend on the catalogue's bookkeeping.

    `caught_by` is a claim the author wrote down. This test does not read it —
    it runs every check and requires at least one to fail, so a mutant that
    slipped through would be reported as a hole rather than hidden by a
    mislabelled attribution.
    """
    if name in EXPECTED_EQUIVALENT:
        pytest.skip(f"documented as uncatchable: {EXPECTED_EQUIVALENT[name]}")
    criterion = build(name)
    caught = []
    for check in CHECKS:
        try:
            check.run(criterion)
        except AssertionError:
            caught.append(check.name)
    assert caught, f"mutant {name!r} survives every check in the battery"


def test_the_catalogue_covers_every_check() -> None:
    """A check no mutant exercises is a check nobody has shown can fail.

    Reported as a gap rather than asserted away: if this list grows, the battery
    needs a mutant for the uncovered check, not a weaker assertion.
    """
    exercised = set()
    for name in CATALOGUE:
        if name in EXPECTED_EQUIVALENT:
            continue
        criterion = build(name)
        for check in CHECKS:
            try:
                check.run(criterion)
            except AssertionError:
                exercised.add(check.name)
    unexercised = sorted({check.name for check in CHECKS} - exercised)
    assert not unexercised, f"no mutant can trip these checks, so nothing shows they work: {unexercised}"
