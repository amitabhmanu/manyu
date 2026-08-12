"""Broken criteria, on purpose, so the suite can be shown able to catch them.

The direct answer to a tally nobody should be comfortable with: experiment 3
shipped **sixteen** defects and its own suite caught **zero**; experiment 4 caught
eight, none by a test written after the code. A suite in that condition is
indistinguishable from one that works, and adding more tests does not fix it —
the tests share the author's assumptions, so they agree with the code exactly
where it is wrong.

So the mechanism is broken deliberately, each mutant reproducing a defect family
that really happened somewhere in this programme, and the checks in
`tests/test_underdetermination_mutants.py` must go red on each. Three properties
make the battery mean anything, carried verbatim from `salience_mutants`:

1. **Every mutant is caught** by at least one named check, or the gap is reported
   as a hole rather than discovered later.
2. **Every mutant is a working mechanism** on the development fixture. One that
   merely crashes proves nothing about coverage.
3. **Every check passes on the real mechanism.** A check that fires on everything
   catches nothing.

Injected rather than monkeypatched, for the reason `salience.AttentionLoop`
records: patching a module attribute does not reach a caller that did
`from module import name`, so a battery built on patching reports mutants as
caught when the mutant was never installed.

Entirely offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from manyu.schemas import Belief, BeliefType
from manyu.underdetermination import (
    OverlapConfig,
    conflicts,
    evidence_overlap,
    separating_evidence,
    shared_evidence,
)

Criterion = Callable[[Belief, Belief], bool]


# --- the mutants -------------------------------------------------------------


def _volume(left: Belief, right: Belief) -> bool:
    """Reads how *much* evidence there is instead of whether it separates.

    The defect `near_miss` was authored to catch, and the reason a ratio was
    chosen over a set comparison. Passes `symmetric_rivals` (2 shared records is
    not many) and `conflict_disjoint_evidence` (4 records, but they separate);
    fails `near_miss`, where six shared records look like plenty.
    """
    if not conflicts(left, right):
        return False
    return len(set(left.evidence_ids) | set(right.evidence_ids)) <= 4


def _ignores_conflict(left: Belief, right: Belief) -> bool:
    """Drops the contradiction half of the criterion.

    Reproduces the family `shared_evidence_no_conflict` pins: two beliefs resting
    on the same observations and agreeing completely is corroboration, the
    commonest shape in any web, and calling it underdetermination relabels the
    entire store.
    """
    if not left.evidence_ids or not right.evidence_ids:
        return False
    return not separating_evidence(left, right)


def _ignores_evidence(left: Belief, right: Belief) -> bool:
    """Drops the evidence half.

    The counterpart, and the more consequential direction: every ordinary
    resolvable dispute in the web — everything experiments 3 and 4 were about —
    becomes an unresolvable standoff. `conflict_disjoint_evidence` catches it.
    """
    return conflicts(left, right)


def _inverted(left: Belief, right: Belief) -> bool:
    """Symmetric difference read the wrong way round.

    An off-by-a-negation that a two-node development fixture can easily fail to
    distinguish, because on a web where every pair either fully overlaps or fully
    separates, "empty" and "non-empty" partition the same pairs in reverse — so
    the mutant looks like a mechanism with its labels swapped rather than a broken
    one. Experiment 3's `abs(shock)` defect was this shape.
    """
    if not conflicts(left, right):
        return False
    return bool(separating_evidence(left, right))


def _one_shared_record_is_enough(left: Belief, right: Belief) -> bool:
    """Any overlap at all counts, rather than complete overlap.

    The graded criterion with its tolerance opened to 1.0 — which is what
    `OverlapMode.GRADED` becomes if nobody bounds it. Retained here as a mutant
    as well as an ablation because the ablation is *supposed* to be available;
    what must not happen is it becoming the default by accident.
    """
    if not conflicts(left, right):
        return False
    return bool(shared_evidence(left, right))


def _directional(left: Belief, right: Belief) -> bool:
    """Only sees a contradiction declared in one direction.

    Stage -1 found that a one-way edge already collapses a symmetric pair through
    the confidence channel (requirements section 6.1). A criterion inheriting the
    same accident would make detection depend on which reading the extractor
    happened to phrase as the contradictor, which is not an epistemic fact.
    `symmetric_rivals_oneway` catches it.
    """
    if not left.evidence_ids or not right.evidence_ids:
        return False
    if right.belief_id not in left.contradicts:
        return False
    return not separating_evidence(left, right)


def _never_fires(left: Belief, right: Belief) -> bool:
    """Derives nothing, ever.

    Experiment 1's mood -> `rank_causes` coupling was arithmetically a no-op on
    every probed target across several versions, and experiment 4's Stage 0a
    reported a base rate of zero that described the instrument. `assert_not_noop`
    exists for this family; here the check is simply that some fixture derives.
    """
    return False


def _always_fires(left: Belief, right: Belief) -> bool:
    """Derives on everything.

    The mirror of the above and the reason a null needs a *negative* control as
    well as a positive one. A criterion firing everywhere is as uninformative as
    one firing nowhere, and only the two negatives can tell them apart.
    """
    return True


#: Every mutant, with the check expected to catch it named for the record.
CATALOGUE: dict[str, "Mutant"] = {}


@dataclass(frozen=True)
class Mutant:
    name: str
    criterion: Criterion
    reproduces: str
    caught_by: str


def _register(name: str, criterion: Criterion, reproduces: str, caught_by: str) -> None:
    CATALOGUE[name] = Mutant(name=name, criterion=criterion, reproduces=reproduces, caught_by=caught_by)


_register("volume", _volume, "a criterion counting evidence rather than reading whether it separates", "near_miss holds")
_register("ignores_conflict", _ignores_conflict, "corroboration relabelled as underdetermination", "shared_evidence_no_conflict does not derive")
_register("ignores_evidence", _ignores_evidence, "every ordinary dispute relabelled as unresolvable", "conflict_disjoint_evidence does not derive")
_register("inverted", _inverted, "the symmetric-difference test negated", "symmetric_rivals derives")
_register("any_overlap", _one_shared_record_is_enough, "the graded tolerance opened to everything", "discriminating collapses")
_register("directional", _directional, "detection inheriting the extractor's edge direction", "symmetric_rivals_oneway derives")
_register("never_fires", _never_fires, "a mechanism wired to control and doing nothing", "symmetric_rivals derives")
_register("always_fires", _always_fires, "a mechanism that cannot decline", "shared_evidence_no_conflict does not derive")


#: Mutants that cannot be distinguished from the real mechanism, with the reason.
#: Recorded rather than omitted — experiment 4 documented two as uncatchable and
#: that honesty is what keeps the battery's coverage claim readable.
EXPECTED_EQUIVALENT: dict[str, str] = {}


def build(name: str) -> Criterion:
    """The mutant criterion, for injection into a harness."""
    if name not in CATALOGUE:
        raise KeyError(f"unknown mutant {name!r}; have {sorted(CATALOGUE)}")
    return CATALOGUE[name].criterion


def find_rival_pairs(beliefs: list[Belief], criterion: Criterion) -> list[tuple[str, str]]:
    """`find_rival_sets`'s pair selection, with the criterion swapped out.

    Deliberately a parallel implementation of the *iteration* only, so a mutant
    changes the criterion and nothing else. Ordering matches production so the
    comparison is about which pairs are admitted, not about how they are sorted.
    """
    ordered = sorted((b for b in beliefs if b.belief_type is not BeliefType.UNDERDETERMINATION), key=lambda b: b.belief_id)
    found = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if criterion(left, right):
                found.append(tuple(sorted([left.belief_id, right.belief_id])))
    return found


def real_criterion(config: OverlapConfig | None = None) -> Criterion:
    from manyu.underdetermination import is_underdetermined

    def criterion(left: Belief, right: Belief) -> bool:
        return is_underdetermined(left, right, config=config)

    return criterion
