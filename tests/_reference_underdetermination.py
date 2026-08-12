"""An independent reference implementation of the experiment 5 criterion.

**Not imported by any production module, and importing `manyu.underdetermination`
here would defeat the purpose.** `test_underdetermination_reference.py` asserts
that absence, because a reference that calls the thing it is checking agrees with
it by construction — the trap experiment 2's steelman exposed when
`SplitDissonanceAppraiser` turned out to be *declining* to walk `supports` rather
than being unable to.

Written from the definitions, not from the code:

- **separating evidence** between two beliefs — every record cited by one and not
  by the other. A record both cite cannot discriminate between them whatever it
  says; a record only one cites is what evidence looks like when it does.
- **overlap** — the number of records both cite, divided by the number cited by
  either. One exactly when nothing separates them. Zero when neither cites
  anything, because an empty union means something upstream is wrong and must not
  read as perfect agreement.
- **underdetermined** — both of: a stated contradiction between them in either
  direction, and no separating evidence, with both sides carrying evidence at all.
- **rival sets** — every unordered pair of non-meta beliefs meeting that test.

Deliberately naive: O(n^2) over lists, no caching, sets rebuilt on every call.
Meant to be obviously right rather than fast.

**What is deliberately not modelled:** the derived confidence's passage through
`blend_confidence`. That is the substrate's arithmetic rather than this
experiment's definition, and reproducing it here would encode experiment 3's
inertia constants as if they were part of the criterion. The reference states what
the *derived overlap* should be; what revision then does with it is checked
against the running store instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class RefBelief:
    """Only the fields the criterion is defined over."""

    belief_id: str
    evidence_ids: tuple[str, ...]
    contradicts: tuple[str, ...] = ()
    is_meta: bool = False


def separating(left: RefBelief, right: RefBelief) -> set[str]:
    a, b = set(left.evidence_ids), set(right.evidence_ids)
    return (a - b) | (b - a)


def shared(left: RefBelief, right: RefBelief) -> set[str]:
    return set(left.evidence_ids) & set(right.evidence_ids)


def overlap(left: RefBelief, right: RefBelief) -> float:
    union = set(left.evidence_ids) | set(right.evidence_ids)
    if len(union) == 0:
        return 0.0
    return len(shared(left, right)) / len(union)


def conflicts(left: RefBelief, right: RefBelief) -> bool:
    return right.belief_id in left.contradicts or left.belief_id in right.contradicts


def underdetermined(left: RefBelief, right: RefBelief) -> bool:
    if not conflicts(left, right):
        return False
    if len(left.evidence_ids) == 0 or len(right.evidence_ids) == 0:
        return False
    return len(separating(left, right)) == 0


def rival_sets(beliefs: list[RefBelief]) -> list[tuple[tuple[str, str], float]]:
    """Every admitted pair, as `((low_id, high_id), overlap)`, sorted."""
    candidates = sorted((b for b in beliefs if not b.is_meta), key=lambda b: b.belief_id)
    found = []
    for left, right in combinations(candidates, 2):
        if underdetermined(left, right):
            pair = tuple(sorted([left.belief_id, right.belief_id]))
            found.append((pair, overlap(left, right)))
    return sorted(found)
