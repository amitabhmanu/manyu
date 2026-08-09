"""D3: does a discomfort signal fall out of belief structure, or must it be stipulated?

Three detectors behind one interface. Two are candidate architectures; the
third exists to prove the test can fail.

**The rationale below is written before any held-out fixture has been run**
(FR-D3.7). Whether merged transfers depends partly on how generically this
first implementation was written, and that is a judgement made by whoever
writes it — so the reasoning has to be on the record in advance, or
"it generalised" is unfalsifiable after the fact.

Why the merged query is shaped the way it is:

- **`min(stake_a, stake_b)`, not sum or max.** Dissonance needs *both* sides to
  matter. A heavy belief conflicting with a trivial one is a correction, not a
  tension, and summing would let one heavy belief manufacture dissonance
  against anything it touched.
- **Traversal over `supports`, not adjacency.** The question D3 asks is whether
  tension is a property of the *graph* or a property of a rule someone wrote.
  Reading only `contradicts` answers it by construction — it can never find
  anything the edge did not already state. Walking the entailment closure is
  the smallest formulation that is genuinely a query about structure.
- **Saturating sum, not a raw count.** Magnitude has to stay in [0, 1] to be
  normalisable, and a count would make one more conflicting pair matter as much
  at ten pairs as at one.
- **Magnitude counts leaf conflicts only.** Traversal multiplies the pairs
  implicated by a single conflict — a depth-2 chain turns one `contradicts`
  edge into nine reachable pairs — so summing every carrier would make
  magnitude report graph size rather than tension. Carriers record everyone
  implicated; magnitude records the conflicts themselves.

Why split's is shaped the way it is: split's affect system cannot see belief
structure. It receives appraisals, and an appraisal is computed from an event,
not from the store's shape. So the natural implementation is a rule that scans
for the thing it was told to look for and emits an emotion delta. That is
stipulation, and it is not a strawman — it is what the pathway affords.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from manyu.architecture import ArchConfig
from manyu.clock import Clock
from manyu.schemas import (
    Belief,
    DissonanceCarrier,
    DissonanceSignal,
    EmotionConfig,
    ManyuProfile,
)
from manyu.store import ManyuStore

FIXTURE_DIR = Path("evals/fixtures/exp02")

#: Split needs somewhere to put the signal. Added to a *copy* of the profile
#: rather than to `config/default_profile.json`, so the merged build's
#: `AffectState` is not silently given a channel it never writes to — a
#: difference between the builds that has nothing to do with the fork.
DISSONANCE_EMOTION = "dissonance"


def profile_with_dissonance(profile: ManyuProfile) -> ManyuProfile:
    """Split-only: a profile carrying the `dissonance` emotion channel."""
    emotions = dict(profile.emotions)
    emotions[DISSONANCE_EMOTION] = EmotionConfig(baseline=0.05, half_life_s=1200, max_delta_per_event=0.4)
    return profile.model_copy(update={"emotions": emotions})


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DissonanceDetector(Protocol):
    def detect(self, agent_id: str, contradiction_type: str) -> DissonanceSignal | None: ...


# --- shared helpers ----------------------------------------------------------


def stake_of(store: ManyuStore, belief: Belief) -> float:
    """Mean evidence salience x the belief's own confidence.

    Identical to `MergedMoodEngine.stake`. Kept as a free function so the split
    detector uses the same weighting — otherwise the two builds would differ in
    how much a belief counts, which is not the difference under test.
    """
    if not belief.evidence_ids:
        return 0.0
    evidence = store.list_belief_evidence(belief.agent_id, evidence_ids=list(belief.evidence_ids))
    if not evidence:
        return 0.0
    salience = sum(item.affective_salience for item in evidence) / len(evidence)
    return salience * belief.confidence


def _tension(store: ManyuStore, a: Belief, b: Belief) -> float:
    return min(stake_of(store, a), stake_of(store, b)) * (1.0 + abs(a.valence - b.valence)) / 2.0


def _leaf_conflicts(beliefs: dict[str, Belief]) -> set[tuple[str, str]]:
    """Every directly-stated conflict, deduplicated and order-independent."""
    pairs: set[tuple[str, str]] = set()
    for belief in beliefs.values():
        for other in belief.contradicts:
            if other in beliefs:
                pairs.add(tuple(sorted((belief.belief_id, other))))  # type: ignore[arg-type]
    return pairs


# --- merged ------------------------------------------------------------------


class MergedDissonanceQuery:
    """Dissonance as a query over the belief graph. No rule names a conflict type."""

    detected_via = "graph_query"

    def __init__(self, store: ManyuStore, config: ArchConfig | None = None):
        self.store = store
        self.config = config or ArchConfig()

    def _closure(self, belief: Belief, beliefs: dict[str, Belief]) -> dict[str, list[str]]:
        """Everything `belief` entails, and the intermediate nodes to reach it.

        Returns `belief_id -> path`, where the path excludes both endpoints.
        `belief` itself maps to an empty path.
        """
        reached: dict[str, list[str]] = {belief.belief_id: []}
        frontier = [(belief.belief_id, [])]
        for _ in range(self.config.supports_max_depth):
            next_frontier: list[tuple[str, list[str]]] = []
            for node_id, path in frontier:
                node = beliefs.get(node_id)
                if node is None:
                    continue
                for supported in node.supports:
                    if supported in reached or supported not in beliefs:
                        continue
                    onward = path + ([node_id] if node_id != belief.belief_id else [])
                    reached[supported] = onward
                    next_frontier.append((supported, onward))
            if not next_frontier:
                break
            frontier = next_frontier
        return reached

    def detect(self, agent_id: str, contradiction_type: str = "unknown") -> DissonanceSignal | None:
        beliefs = {b.belief_id: b for b in self.store.list_beliefs(agent_id)}
        if not beliefs:
            return None

        closures = {bid: self._closure(b, beliefs) for bid, b in beliefs.items()}
        leaves = _leaf_conflicts(beliefs)

        carriers: list[DissonanceCarrier] = []
        seen: set[tuple[str, str]] = set()
        for a_id, a_closure in closures.items():
            for b_id, b_closure in closures.items():
                if a_id == b_id:
                    continue
                key = tuple(sorted((a_id, b_id)))
                if key in seen:
                    continue
                # In tension when anything a entails conflicts with anything b
                # entails. For a == leaf and b == leaf this reduces to the
                # stated edge; the traversal is what finds everyone else.
                hit = None
                for x_id, x_path in a_closure.items():
                    for y_id, y_path in b_closure.items():
                        if tuple(sorted((x_id, y_id))) in leaves:
                            hit = (x_path, y_path, x_id, y_id)
                            break
                    if hit:
                        break
                if hit is None:
                    continue
                seen.add(key)  # type: ignore[arg-type]
                x_path, y_path, x_id, y_id = hit
                path = [*x_path, *([x_id] if x_id != a_id else []), *([y_id] if y_id != b_id else []), *y_path]
                carriers.append(
                    DissonanceCarrier(
                        belief_id_a=a_id,
                        belief_id_b=b_id,
                        path=path,
                        tension=round(_tension(self.store, beliefs[a_id], beliefs[b_id]), 6),
                    )
                )

        if not carriers:
            return None
        raw = sum(
            _tension(self.store, beliefs[a], beliefs[b])
            for a, b in leaves
        )
        return DissonanceSignal(
            signal_id=_id("dis"),
            agent_id=agent_id,
            arch="merged",
            magnitude_raw=round(raw, 6),
            magnitude=round(1.0 - math.exp(-raw / self.config.dissonance_tau), 6),
            carriers=sorted(carriers, key=lambda c: (len(c.path), c.belief_id_a, c.belief_id_b)),
            detected_via=self.detected_via,
            contradiction_type=contradiction_type,
        )


# --- split -------------------------------------------------------------------


@dataclass(frozen=True)
class AppraisalView:
    """Everything an appraisal pathway can see. Deliberately not the store.

    `FastAppraiser.appraise` is handed an event, a state revision and a mood,
    and computes emotion deltas from the event's own links. Split's affect layer
    is downstream of that: what it holds is `AffectState.emotions`, a
    `dict[str, float]`. There is nowhere in that structure to put a belief id.

    This class makes the boundary a type rather than a habit. The first version
    of `SplitDissonanceAppraiser` took the store and simply chose not to walk
    `supports` — which made "split cannot see graph structure" an assertion in a
    docstring rather than a property of the code, and the steelman test caught
    it. A detector that receives this cannot look at beliefs at all.
    """

    agent_id: str
    level: float
    baseline: float


class BeliefConflictRule(Protocol):
    """The hand-written bridge from the belief graph into an affect scalar.

    **This object is the stipulation.** Merged has no counterpart: its mood is
    already a query over beliefs, so tension is readable without anything being
    written to notice it. Split's affect layer cannot reach the graph, so
    somebody has to write a rule that does, and decide there what counts.

    Making it a named, injectable object rather than a method body means the
    cost is countable (FR-D3.3) and the coverage is testable — a rule only
    finds the shapes it was written for, which is the whole question.
    """

    name: str

    def scan(self, store: ManyuStore, agent_id: str) -> float: ...


class AdjacentConflictRule:
    """Scan for stated `contradicts` edges. The natural rule to write."""

    name = "adjacent"

    def scan(self, store: ManyuStore, agent_id: str) -> float:
        beliefs = {b.belief_id: b for b in store.list_beliefs(agent_id)}
        leaves = _leaf_conflicts(beliefs)
        return round(sum(_tension(store, beliefs[a], beliefs[b]) for a, b in leaves), 6)


class TraversingConflictRule:
    """The steelman's rule: merged's traversal, hand-written into split.

    Retained from the first design, where it showed the traversal asymmetry was
    the author's hand rather than the architecture's. It survives here as the
    honest upper bound on what split can be given — and note what giving it
    costs: this rule reaches the same closure merged gets for free.
    """

    name = "traversing"

    def __init__(self, config: ArchConfig | None = None):
        self.config = config or ArchConfig()

    def scan(self, store: ManyuStore, agent_id: str) -> float:
        query = MergedDissonanceQuery(store, self.config)
        signal = query.detect(agent_id, "internal")
        return 0.0 if signal is None else signal.magnitude_raw


class SplitDissonanceAppraiser:
    """Dissonance as an appraisal rule, bounded by a stored emotion channel.

    **This detector never receives the store.** It is handed an `AppraisalView`
    — a scalar and a baseline — because that is what split's affect layer
    actually holds. Consequently `carriers` is always empty, not by choice but
    because there is nothing in a `dict[str, float]` from which to reconstruct
    one. Split can report *that* it is in tension and *how much*; it cannot
    report *between what*.

    That is the architectural claim D3 tests, and it is now a property of the
    types rather than of the implementer's restraint. The previous version took
    the store and merely declined to walk `supports`, which the steelman test
    correctly exposed as the author's hand.

    Bounding follows `TransitionEngine.apply`: the delta capped by the channel's
    `max_delta_per_event`, on top of its `baseline`.

    **Deviation from design §5.3, recorded rather than hidden.** That section
    said magnitude would be read back from `AffectState` after a real
    transition. It is not, because `EMOTIONS` is a closed vocabulary enforced in
    four validators and `ManyuProfile` requires every channel to be present:
    adding `dissonance` would invalidate `config/default_profile.json`, hand the
    *merged* build an affect channel it never writes, and add a series to
    experiment 1's visualiser. That is a shared mutation in an experiment whose
    entire claim rests on the two builds differing in exactly one way. What is
    lost is decay; D3 asks nothing temporal, so nothing measured depends on it.
    """

    detected_via = "appraisal_rule"
    arch = "split"

    def __init__(self, profile: ManyuProfile, clock: Clock, rule: BeliefConflictRule | None = None):
        self.profile = profile_with_dissonance(profile)
        self.clock = clock
        self.rule = rule or AdjacentConflictRule()

    def view(self, store: ManyuStore, agent_id: str) -> AppraisalView:
        """Run the stipulated rule and hand across the one number it produces.

        The store is present *here*, in the bridge, and absent from `detect`.
        That is the whole point: the belief graph is visible only to the
        hand-written rule, and everything downstream of it sees a scalar.
        """
        config = self.profile.emotions[DISSONANCE_EMOTION]
        raw = self.rule.scan(store, agent_id)
        level = min(1.0, config.baseline + min(raw, config.max_delta_per_event)) if raw else 0.0
        return AppraisalView(agent_id=agent_id, level=round(level, 6), baseline=config.baseline)

    def detect(self, view: AppraisalView, contradiction_type: str = "unknown") -> DissonanceSignal | None:
        if view.level <= view.baseline:
            return None
        return DissonanceSignal(
            signal_id=_id("dis"),
            agent_id=view.agent_id,
            arch=self.arch,
            magnitude_raw=round(view.level - view.baseline, 6),
            magnitude=view.level,
            # Structurally empty. There is no belief id anywhere in the state
            # this detector was given.
            carriers=[],
            detected_via=self.detected_via,
            contradiction_type=contradiction_type,
        )


# --- the control on the test -------------------------------------------------


@dataclass
class SourceTable:
    """The side-table split needs in order to say what its dissonance is about.

    Not a data structure the architecture provides — one somebody adds. It is
    the concrete form of "split can match merged, at a cost", and the cost is
    exactly this: a second store, written and maintained alongside the affect
    scalar, holding the belief references the scalar cannot.
    """

    entries: list[DissonanceCarrier]


class SplitWithSourceTable(SplitDissonanceAppraiser):
    """The steelman: split, plus purpose-built machinery to name its sources.

    The first steelman handed split merged's *traversal* and showed the
    traversal asymmetry was the author's hand. This one concedes traversal
    outright — its rule may be `TraversingConflictRule` — and asks the sharper
    question: what does it take for split to answer "between which beliefs?"

    The answer is a `SourceTable`: a side-store populated by the same rule,
    carrying the belief ids the affect scalar cannot. It works. That is the
    point. **Split can match merged here, and what it takes is a hand-written
    rule plus a hand-maintained copy of the rule's output** — machinery merged
    does not have because its mood is already a query over the graph.

    So the measurement stops being "can it?" and becomes "what did it cost?",
    which is FR-D3.3's line count, now meaning something. And the coverage of
    the side-table is bounded by the coverage of the rule that fills it: a
    build using `AdjacentConflictRule` names sources on directly-stated
    conflicts and is blind to derived ones, whatever its affect layer does.
    """

    detected_via = "appraisal_rule_with_source_table"
    arch = "split_with_source_table"

    def view_with_sources(self, store: ManyuStore, agent_id: str) -> tuple[AppraisalView, SourceTable]:
        view = self.view(store, agent_id)
        beliefs = {b.belief_id: b for b in store.list_beliefs(agent_id)}
        if isinstance(self.rule, TraversingConflictRule):
            signal = MergedDissonanceQuery(store, self.rule.config).detect(agent_id, "internal")
            entries = list(signal.carriers) if signal else []
        else:
            entries = [
                DissonanceCarrier(
                    belief_id_a=a,
                    belief_id_b=b,
                    path=[],
                    tension=round(_tension(store, beliefs[a], beliefs[b]), 6),
                )
                for a, b in sorted(_leaf_conflicts(beliefs))
            ]
        return view, SourceTable(entries=entries)

    def detect_with_sources(
        self, store: ManyuStore, agent_id: str, contradiction_type: str = "unknown"
    ) -> DissonanceSignal | None:
        view, table = self.view_with_sources(store, agent_id)
        signal = self.detect(view, contradiction_type)
        if signal is None:
            return None
        return signal.model_copy(update={"carriers": table.entries})


class ValenceOnlyDissonanceQuery:
    """The mutant: tension from valence difference alone, ignoring every edge.

    Exists to stop `near_miss` being a vacuous test. As things stand both real
    builds return `None` on it before the valence term is ever reached — there
    are no `contradicts` edges, so `_leaf_conflicts` is empty and they bail. The
    negative result is therefore evidence about the fixture, not about the
    mechanisms, and "specificity 2/2" would mean nothing.

    This is the mechanism `near_miss` was designed to catch: merged's
    `(1 + |dv|)/2` term is a weighting on pairs that already conflict, and an
    implementation that mistook it for a detector would fire on every line of
    that fixture while still scoring 4/4 on the held-out set. If this build does
    *not* fire on `near_miss`, the fixture cannot catch what it was built for.
    """

    detected_via = "valence_only"

    def __init__(self, store: ManyuStore, config: ArchConfig | None = None):
        self.store = store
        self.config = config or ArchConfig()

    def detect(self, agent_id: str, contradiction_type: str = "unknown") -> DissonanceSignal | None:
        beliefs = list(self.store.list_beliefs(agent_id))
        carriers = []
        for index, a in enumerate(beliefs):
            for b in beliefs[index + 1:]:
                tension = _tension(self.store, a, b)
                if abs(a.valence - b.valence) >= 1.0:
                    carriers.append(
                        DissonanceCarrier(belief_id_a=a.belief_id, belief_id_b=b.belief_id, path=[], tension=round(tension, 6))
                    )
        if not carriers:
            return None
        raw = sum(c.tension for c in carriers)
        return DissonanceSignal(
            signal_id=_id("dis"),
            agent_id=agent_id,
            arch="valence_only",
            magnitude_raw=round(raw, 6),
            magnitude=round(1.0 - math.exp(-raw / self.config.dissonance_tau), 6),
            carriers=carriers,
            detected_via=self.detected_via,
            contradiction_type=contradiction_type,
        )


class StipulatedDissonanceQuery(MergedDissonanceQuery):
    """Hardcoded to `direct`. Not a candidate architecture — a control.

    Exists so a merged build that transfers is interpretable. Without a
    mechanism *known* not to generalise, nothing demonstrates the held-out set
    can fail anything, and a clean pass says only that the fixtures were
    passable. Experiment 1's v7 made the same move in the opposite direction:
    it constructed the effect it claimed to detect and confirmed the apparatus
    saw it.

    Expected: ceiling on `direct`, nothing on held-out. If this *passes*
    held-out, the held-out set does not discriminate and D3 is unreadable until
    the fixtures are redesigned (requirements §8.2).
    """

    detected_via = "stipulated_rule"

    def detect(self, agent_id: str, contradiction_type: str = "unknown") -> DissonanceSignal | None:
        if contradiction_type != "direct":
            return None
        signal = super().detect(agent_id, contradiction_type)
        if signal is None:
            return None
        return signal.model_copy(update={"arch": "stipulated", "detected_via": self.detected_via})


# --- fixtures ----------------------------------------------------------------


#: Stake levels for the ladder (FR-F6). Salience x confidence, so 0.15 / 0.35 /
#: 0.68 per belief. Chosen to bracket the fixture-typical middle value rather
#: than to produce any particular result.
LADDER_STAKES = {
    "low": {"salience": 0.30, "confidence": 0.50},
    "medium": {"salience": 0.50, "confidence": 0.70},
    "high": {"salience": 0.80, "confidence": 0.85},
}


def ladder_specs(pairs: int, stake: str) -> list[Any]:
    """`pairs` conflicting belief pairs, all at one stake level.

    The contradiction ladder: ground truth by *ordering* rather than by value.
    Nobody knows what magnitude three high-stake conflicts should produce, but
    everybody knows it must not be less than one low-stake conflict. That is
    what makes FR-D3.4's monotonicity test falsifiable — the same trick
    `mutations.py` plays on the honesty scorer.
    """
    from manyu.fork import BeliefSpec

    level = LADDER_STAKES[stake]
    specs: list[Any] = []
    for index in range(pairs):
        specs.append(
            BeliefSpec(
                key=f"pos{index}",
                proposition=f"Claim {index} holds.",
                valence=0.6,
                **level,
            )
        )
        specs.append(
            BeliefSpec(
                key=f"neg{index}",
                proposition=f"Claim {index} does not hold.",
                valence=-0.6,
                contradicts=(f"pos{index}",),
                **level,
            )
        )
    return specs


FREEZE_PATH = Path("evals/analysis/exp02/freeze.json")


def mechanism_digest() -> str:
    """SHA-256 of this module — the thing that must not change after freeze."""
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def verify_freeze(path: Path | str = FREEZE_PATH) -> dict[str, Any]:
    """Refuse to proceed if the mechanism changed after it was frozen.

    FR-D3.2 forbids code changes between freeze and the held-out run, and
    convention is not enough — experiment 1's retraction history is a list of
    things that were meant to be true and were not checked. The harness calls
    this before any held-out fixture runs.
    """
    with Path(path).open("r", encoding="utf-8") as handle:
        freeze = json.load(handle)
    mechanisms = freeze.get("mechanisms")
    if not mechanisms:
        raise RuntimeError(f"{path} has no mechanism freeze block; run the freeze step first")
    actual = mechanism_digest()
    expected = mechanisms["dissonance_sha256"]
    if actual != expected:
        raise RuntimeError(
            f"dissonance.py changed after freeze (frozen {expected[:16]}, now {actual[:16]}). "
            f"The held-out arm is void and must be restarted from a new freeze."
        )
    return freeze


def load_dissonance_fixture(name: str, *, directory: Path | str = FIXTURE_DIR) -> dict[str, Any]:
    with (Path(directory) / f"{name}.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fixture_specs(fixture: dict[str, Any]) -> list[Any]:
    """Turn a fixture's `beliefs` block into `BeliefSpec`s."""
    from manyu.fork import BeliefSpec
    from manyu.schemas import BeliefScope, BeliefType

    specs = []
    for raw in fixture["beliefs"]:
        specs.append(
            BeliefSpec(
                key=raw["key"],
                proposition=raw["proposition"],
                valence=raw.get("valence", 0.0),
                confidence=raw.get("confidence", 0.7),
                salience=raw.get("salience", 0.5),
                weight=raw.get("weight", 0.7),
                belief_type=BeliefType(raw.get("belief_type", "world_model")),
                scope=BeliefScope(raw.get("scope", "general")),
                contradicts=tuple(raw.get("contradicts", ())),
                supports=tuple(raw.get("supports", ())),
            )
        )
    return specs
