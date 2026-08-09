"""Stage 2: discrimination — does the engine tell the topologies apart?

Entirely offline, `n=1` under `FrozenClock`.

Stage 1 asserted the same shapes on pairs built inline in its own test file,
alongside the engine. That is a mechanism checked against structure it was
developed on. These fixtures live in `evals/fixtures/exp03/` so the claim
"not developed against this" is about a file rather than a recollection.

**The honest limit, stated up front:** the engine already existed when these
fixtures were written, so this is not the blinding experiment 2 ran (fixtures
first, hash, build against dev only, freeze, then held-out). What *is*
genuinely held out is `negative_near_miss` and the arm comparison — neither
behaviour was exercised by any Stage 1 test, and `ContradictionArm.DIRECT`
had no implementation at all until this stage.

The instrument gate comes first. Experiment 2's gate #5 — assert a mechanism
*can* change its output — is what catches a knob wired to nothing, which is
exactly what `DIRECT` was.
"""

from __future__ import annotations

import pytest

from manyu.clock import FrozenClock
from manyu.core import ManyuCore
from manyu.revision import (
    ContradictionArm,
    RevisionEngine,
    load_topology,
    topology_specs,
)
from manyu.fork import seed_beliefs

AGENT = "agent_demo"
ARMS = [ContradictionArm.EVIDENTIAL, ContradictionArm.DIRECT]


def _run(name: str, arm: ContradictionArm):
    fixture = load_topology(name)
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, topology_specs(fixture))
    engine = RevisionEngine(core.store, FrozenClock(), arm)

    # Declared contradictions are re-asserted *through the engine* so they are
    # priced. Seeding writes the edge and the status but never charges
    # confidence, and relief may only undo a suppression that was applied —
    # otherwise retraction credits a belief for a cost it never paid.
    for entry in fixture["beliefs"]:
        for target_key in entry.get("contradicts", ()):
            engine.assert_contradiction(AGENT, ids[entry["key"]], ids[target_key])

    result = engine.retract(AGENT, ids[fixture["retract"]], to_confidence=fixture.get("retract_to", 0.0))
    return fixture, ids, result, core


def _moved_keys(ids: dict[str, str], result) -> set[str]:
    by_id = {bid: key for key, bid in ids.items()}
    return {by_id[s.belief_id] for s in result.moved if s.depth > 0}


# --- the instrument gate ----------------------------------------------------


def test_gate_the_arms_are_not_the_same_mechanism() -> None:
    """Gate #5. `DIRECT` was stored, stamped onto the result, and consulted by
    nothing — identical output on every fixture. A knob wired to nothing is
    experiment 1's `affect_influence` again, and no result from an arm
    comparison means anything until this passes."""
    _, ids_e, evidential, _ = _run("contradiction_pair", ContradictionArm.EVIDENTIAL)
    _, ids_d, direct, _ = _run("contradiction_pair", ContradictionArm.DIRECT)

    assert _moved_keys(ids_e, evidential) != _moved_keys(ids_d, direct), (
        "the two arms produce identical footprints — the arm is not wired to anything"
    )


def test_gate_every_fixture_actually_loads_its_declared_shape() -> None:
    """Gate #4 (IV-reality). A fixture whose edges silently failed to resolve
    would present as a clean negative, so every positive must be shown to have
    the structure it claims before its result is read."""
    for name in ("chain_deep", "net_dense", "chain_shallow", "contradiction_pair"):
        fixture = load_topology(name)
        core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
        ids = seed_beliefs(core, topology_specs(fixture))
        edges = sum(len(b.supports) for b in core.store.list_beliefs(AGENT, include_inactive=True))
        declared = sum(len(e.get("supports", [])) for e in fixture["beliefs"])
        assert edges == declared, f"{name}: {declared} edges declared, {edges} survived the write path"

    near_miss = load_topology("negative_near_miss")
    assert all(not e.get("supports") for e in near_miss["beliefs"]), "the negative must have no edges by construction"


# --- discriminating topologies ----------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_chain_ripples_and_attenuates(arm: ContradictionArm) -> None:
    """SC-2 on a held-out chain, under both arms."""
    fixture, ids, result, _ = _run("chain_deep", arm)
    assert _moved_keys(ids, result) == set(fixture["expect"]["moves"])

    depths = result.by_depth()
    magnitudes = [abs(depths[d][0].delta) for d in sorted(depths) if d > 0]
    assert all(m > 0 for m in magnitudes), "the ripple must reach every declared node"
    assert magnitudes == sorted(magnitudes, reverse=True), f"must decay with depth: {magnitudes}"
    assert result.total_movement() < 0.8, "aggregate must stay under the shock"


@pytest.mark.parametrize("arm", ARMS)
def test_a_net_absorbs_what_a_chain_transmits(arm: ContradictionArm) -> None:
    """SC-3 on the matched held-out pair. The fixtures differ only in supporter
    count, so any difference is fractional support."""
    _, net_ids, net, _ = _run("net_dense", arm)
    _, chain_ids, chain, _ = _run("chain_shallow", arm)

    net_move = abs({s.belief_id: s for s in net.steps}[net_ids["t"]].delta)
    chain_move = abs({s.belief_id: s for s in chain.steps}[chain_ids["t"]].delta)

    assert net_move > 0, "absorbing is not ignoring"
    assert net_move < chain_move, f"net {net_move} vs chain {chain_move}"


# --- negatives (SC-4) -------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_the_near_miss_negative_does_not_fire(arm: ContradictionArm) -> None:
    """The load-bearing negative.

    Same topic, near-identical wording, matching valence, no edges. A rule
    keying on similarity rather than on the declared graph fires here and
    passes every positive above.
    """
    _, ids, result, core = _run("negative_near_miss", arm)
    assert _moved_keys(ids, result) == set()

    untouched = [b for b in core.store.list_beliefs(AGENT, include_inactive=True) if b.belief_id != ids["verification_a"]]
    assert all(b.confidence == pytest.approx(0.8) for b in untouched)


# --- the arm comparison (requirements 5) ------------------------------------


def test_direct_refunds_a_suppressed_belief_when_its_contradictor_weakens() -> None:
    """`DIRECT`: the contradiction was active suppression, so weakening the
    suppressor refunds exactly the fraction it no longer justifies."""
    fixture, ids, result, core = _run("contradiction_pair", ContradictionArm.DIRECT)
    steps = {s.belief_id: s for s in result.steps}

    assert ids["p"] in steps, "P must be refunded under DIRECT"
    assert steps[ids["p"]].delta > 0, "P recovers as its suppressor weakens"
    expected = fixture["expect"]["direct"]["p_after_partial_retraction"]
    assert core.store.get_belief(ids["p"]).confidence == pytest.approx(expected)


def test_evidential_never_charged_the_belief_so_has_nothing_to_refund() -> None:
    """`EVIDENTIAL`: the contradiction was bookkeeping, so nothing moves."""
    fixture, ids, result, core = _run("contradiction_pair", ContradictionArm.EVIDENTIAL)
    steps = {s.belief_id: s for s in result.steps}

    assert ids["p"] not in steps
    expected = fixture["expect"]["evidential"]["p_after_partial_retraction"]
    assert core.store.get_belief(ids["p"]).confidence == pytest.approx(expected)


def test_contradiction_relief_does_not_chain() -> None:
    """One hop, by design. Support is transitive; "the enemy of my enemy" is
    not a relation we assert."""
    _, ids, result, _ = _run("contradiction_pair", ContradictionArm.DIRECT)
    refunded = [s for s in result.steps if s.delta > 0]
    assert refunded, "the fixture must actually produce a refund to test this"
    assert all(s.depth == 1 for s in refunded)


@pytest.mark.parametrize("arm", ARMS)
def test_the_arms_agree_wherever_no_contradiction_exists(arm: ContradictionArm) -> None:
    """The arms must differ *only* on contradiction. If they diverged on a pure
    support topology, the comparison above would be measuring something else."""
    _, chain_ids, chain, _ = _run("chain_deep", arm)
    by_id = {bid: key for key, bid in chain_ids.items()}
    footprint = {by_id[s.belief_id]: round(abs(s.delta), 6) for s in chain.moved if s.depth > 0}
    assert footprint == {"b": 0.4, "c": 0.2, "d": 0.1}
