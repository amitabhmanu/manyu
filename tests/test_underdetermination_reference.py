"""Production agrees with an independently written definition of the criterion.

Two statements of one thing, on the pattern of `tests/_reference.py` and
`test_salience_reference.py`. The value is entirely in the *independence*: a
reference importing the module it checks agrees with it by construction, so the
first test here guards the import boundary and the rest would be worthless
without it.

Entirely offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.underdetermination import (
    FIXTURE_DIR,
    evidence_overlap,
    find_rival_sets,
    is_underdetermined,
    load_web,
    seed_fixture,
    separating_evidence,
)
from manyu.schemas import BeliefType

from _reference_underdetermination import RefBelief
from _reference_underdetermination import overlap as ref_overlap
from _reference_underdetermination import rival_sets as ref_rival_sets
from _reference_underdetermination import separating as ref_separating
from _reference_underdetermination import underdetermined as ref_underdetermined

AGENT = "agent_demo"
FIXTURES = sorted(p.stem for p in Path(FIXTURE_DIR).glob("*.json"))


def test_the_reference_does_not_import_what_it_checks() -> None:
    """The guard that makes every other test in this file mean something.

    Reuses experiment 4's AST walk rather than grepping. Written as a grep first,
    and it failed on this reference's own docstring — which names the import it
    forbids — reproducing experiment 4's mistake exactly. `_production_leaks`
    already existed with a comment explaining why; a second, worse copy of a
    guard is how a guard rots.
    """
    from test_salience_reference import _production_leaks

    source = Path(__file__).with_name("_reference_underdetermination.py").read_text(encoding="utf-8")
    leaks = _production_leaks(source)
    assert not leaks, f"the reference implementation reaches production code: {leaks}"


def _seeded(name: str) -> tuple[ManyuCore, list[RefBelief]]:
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    seed_fixture(core, name, agent_id=AGENT)
    beliefs = core.store.list_beliefs(AGENT, include_inactive=True)
    mirror = [
        RefBelief(
            belief_id=b.belief_id,
            evidence_ids=tuple(b.evidence_ids),
            contradicts=tuple(b.contradicts),
            is_meta=b.belief_type is BeliefType.UNDERDETERMINATION,
        )
        for b in beliefs
    ]
    return core, mirror


@pytest.mark.parametrize("name", FIXTURES)
def test_rival_sets_match_the_reference(name: str) -> None:
    core, mirror = _seeded(name)
    beliefs = core.store.list_beliefs(AGENT, include_inactive=True)

    produced = sorted((rs.belief_ids, rs.overlap) for rs in find_rival_sets(beliefs))
    assert produced == ref_rival_sets(mirror)


@pytest.mark.parametrize("name", FIXTURES)
def test_pairwise_quantities_match_the_reference(name: str) -> None:
    core, mirror = _seeded(name)
    beliefs = {b.belief_id: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}
    index = {ref.belief_id: ref for ref in mirror}

    for left_id, left in beliefs.items():
        for right_id, right in beliefs.items():
            if left_id >= right_id:
                continue
            a, b = index[left_id], index[right_id]
            assert separating_evidence(left, right) == ref_separating(a, b)
            assert evidence_overlap(left, right) == pytest.approx(ref_overlap(a, b))
            assert is_underdetermined(left, right) is ref_underdetermined(a, b)


@pytest.mark.parametrize("name", FIXTURES)
def test_the_fixture_expectations_are_structurally_true(name: str) -> None:
    """The `expect` blocks describe the fixture, so they must match the store.

    These are structural facts checkable without running the criterion — they are
    not predictions about what it does. Experiment 4's `adversarial_grounding`
    carries the same note for the same reason.
    """
    core, _ = _seeded(name)
    fixture = load_web(name)
    expect = fixture["expect"]
    if "phase_1" in expect:
        expect = expect["phase_1"]
    beliefs = {b.belief_key: b for b in core.store.list_beliefs(AGENT, include_inactive=True)}

    if "shared_evidence" in expect and "reading_a" in beliefs and "reading_b" in beliefs:
        a, b = beliefs["reading_a"], beliefs["reading_b"]
        assert len(set(a.evidence_ids) & set(b.evidence_ids)) == expect["shared_evidence"]
    if "unique_to_reading_a" in expect:
        a, b = beliefs["reading_a"], beliefs["reading_b"]
        assert len(set(a.evidence_ids) - set(b.evidence_ids)) == expect["unique_to_reading_a"]
        assert len(set(b.evidence_ids) - set(a.evidence_ids)) == expect["unique_to_reading_b"]
    if expect.get("mutual") is True and "reading_a" in beliefs:
        a, b = beliefs["reading_a"], beliefs["reading_b"]
        assert b.belief_id in a.contradicts and a.belief_id in b.contradicts
    if expect.get("mutual") is False:
        a, b = beliefs["reading_a"], beliefs["reading_b"]
        assert b.belief_id in a.contradicts and a.belief_id not in b.contradicts
