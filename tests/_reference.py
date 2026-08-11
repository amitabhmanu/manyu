"""An independent reference implementation of the dissonance quantities.

**Not imported by any production module, and importing one here would defeat
the purpose.** `test_salience_reference.py` asserts that this file contains no
`manyu.dissonance` import, because a reference that calls the thing it is
checking agrees with it by construction — the same trap experiment 2's steelman
exposed when `SplitDissonanceAppraiser` was found to be *declining* to walk
`supports` rather than being unable to.

Written from the definitions, not from the code:

- **stake** — the mean affective salience of a belief's evidence records,
  multiplied by the belief's own confidence. A belief with no evidence has no
  stake.
- **tension** between two beliefs — the *smaller* of the two stakes, weighted by
  how far apart their valences are: `min(stake_a, stake_b) * (1 + |dv|) / 2`.
  Both sides must matter, so a heavy belief conflicting with a trivial one is a
  correction rather than a tension.
- **leaf conflicts** — every unordered pair joined by a stated `contradicts`
  edge in either direction, deduplicated.
- **raw magnitude** — the sum of tension over leaf conflicts. Conflicts, not
  reachable pairs: traversal multiplies who is *implicated* by a conflict, not
  how much tension exists.
- **implicated pairs** — every unordered pair `(a, b)` such that something `a`
  entails conflicts with something `b` entails, walking `supports` forward to a
  bounded depth. Reduces to the stated edge when both are leaves.

Deliberately naive: O(n^2) closures, no caching, no early exit. It is meant to
be obviously right rather than fast.

**What is deliberately not modelled:** the specific `path` a carrier reports.
Production breaks at the first hit in dict iteration order, so the path is a
function of insertion order rather than of the graph. Reproducing that here
would encode an implementation detail as if it were the definition; instead
`test_salience_properties.py` checks whether it varies, and treats the answer as
a finding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations


@dataclass(frozen=True)
class RefBelief:
    """One belief, described by value rather than read from a store."""

    key: str
    valence: float = 0.0
    confidence: float = 0.7
    salience: float = 0.5
    evidence_count: int = 1
    contradicts: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()


@dataclass
class RefWeb:
    beliefs: dict[str, RefBelief] = field(default_factory=dict)

    @classmethod
    def of(cls, beliefs: list[RefBelief]) -> "RefWeb":
        return cls({belief.key: belief for belief in beliefs})


def stake(web: RefWeb, key: str) -> float:
    """Mean evidence salience x confidence. No evidence, no stake."""
    belief = web.beliefs[key]
    if belief.evidence_count <= 0:
        return 0.0
    # Every evidence record for a belief carries that belief's salience, so the
    # mean is taken over a list rather than assumed to collapse to one value.
    saliences = [belief.salience] * belief.evidence_count
    return (sum(saliences) / len(saliences)) * belief.confidence


def tension(web: RefWeb, a: str, b: str) -> float:
    """The weaker party decides, scaled by how far apart the two valences sit."""
    left, right = web.beliefs[a], web.beliefs[b]
    return min(stake(web, a), stake(web, b)) * (1.0 + abs(left.valence - right.valence)) / 2.0


def leaf_conflicts(web: RefWeb) -> set[tuple[str, str]]:
    """Unordered, deduplicated, and counted once however many edges carry it."""
    pairs: set[tuple[str, str]] = set()
    for key, belief in web.beliefs.items():
        for other in belief.contradicts:
            if other in web.beliefs:
                pairs.add(tuple(sorted((key, other))))  # type: ignore[arg-type]
    return pairs


def raw_magnitude(web: RefWeb) -> float:
    return sum(tension(web, a, b) for a, b in leaf_conflicts(web))


def entailed(web: RefWeb, key: str, max_depth: int) -> set[str]:
    """`key` and everything it entails, following `supports` forward.

    Breadth-first to `max_depth` hops. Visits each node once, so a cycle
    terminates.
    """
    reached = {key}
    frontier = [key]
    for _ in range(max_depth):
        nxt = []
        for node in frontier:
            for onward in web.beliefs.get(node, RefBelief(key=node)).supports:
                if onward in web.beliefs and onward not in reached:
                    reached.add(onward)
                    nxt.append(onward)
        if not nxt:
            break
        frontier = nxt
    return reached


def implicated_pairs(web: RefWeb, max_depth: int) -> set[tuple[str, str]]:
    """Every unordered pair in tension, directly or by what each side entails."""
    closures = {key: entailed(web, key, max_depth) for key in web.beliefs}
    leaves = leaf_conflicts(web)
    found: set[tuple[str, str]] = set()
    for a, b in combinations(sorted(web.beliefs), 2):
        for x in closures[a]:
            for y in closures[b]:
                if tuple(sorted((x, y))) in leaves:
                    found.add((a, b))
                    break
            else:
                continue
            break
    return found


def from_fixture(fixture: dict) -> RefWeb:
    """Build a reference web straight from a fixture file's own JSON.

    Reads the file rather than the store, so a discrepancy between the two is
    visible instead of being normalised away by a shared loader.
    """
    return RefWeb.of(
        [
            RefBelief(
                key=entry["key"],
                valence=entry.get("valence", 0.0),
                confidence=entry.get("confidence", 0.7),
                salience=entry.get("salience", 0.5),
                evidence_count=entry.get("evidence_count", 1),
                contradicts=tuple(entry.get("contradicts", ())),
                supports=tuple(entry.get("supports", ())),
            )
            for entry in fixture["beliefs"]
        ]
    )
