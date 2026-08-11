"""Experiment 4 section 5.8 — testing the standard, not the code.

The category that produced experiment 3's most useful defects: four of sixteen,
including one that broke the very standard its section 5 was decided on. The
device is to write down what a result would have to look like to *mean*
something, and check that before running anything that could produce it.

Here that means the fixtures. A fixture claimed to be adversarial that turns out
not to be makes Stage 4 unreadable; a set of fixtures on which every arm agrees
decides nothing; a negative control that quietly contains a conflict turns a
specificity result into an artifact. None of that is visible from the JSON.

These tests run before the selector exists and are the precondition for freezing
the fixtures. Entirely offline.
"""

from __future__ import annotations

import pytest

from manyu.core import ManyuCore
from manyu.dissonance import MergedDissonanceQuery, _leaf_conflicts, stake_of
from manyu.fork import seed_beliefs
from manyu.salience import load_web, web_specs

AGENT = "agent_demo"

ALL_FIXTURES = [
    "adversarial_grounding",
    "aligned_grounding",
    "multi_conflict_web",
    "tied_tension_web",
    "depth_carrier_web",
    "no_conflict_web",
    "mutual_contradiction",
    # Both added after the mutant battery found gaps the first seven could not
    # cover. `counter_direction` separates "reads the direction off the graph"
    # from "charges whichever side is weaker" — on the minimal pair those are the
    # same belief, so the `chosen_direction` mutant passed every check.
    # `hub_web` gives the conflicts a shared party, so acting on one reorders the
    # rest and a loop deciding from a stale reading becomes visible.
    "counter_direction",
    "hub_web",
    # Stage 3 needs a web where some beliefs are unreachable from the conflict;
    # on every earlier fixture every belief is reachable, so `spread` is 1.0 by
    # construction and the measurement cannot fail. Stage 4 needs more than one
    # conflict, because a single-conflict web cannot discriminate any ordering.
    "distractor_web",
    "adversarial_multi",
]


def _seed(name: str) -> tuple[ManyuCore, dict[str, str], dict]:
    fixture = load_web(name)
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True)
    ids = seed_beliefs(core, web_specs(fixture))
    return core, ids, fixture


def _stakes(core: ManyuCore, ids: dict[str, str]) -> dict[str, float]:
    return {key: stake_of(core.store, core.store.get_belief(bid)) for key, bid in ids.items()}


def _grounding(core: ManyuCore, ids: dict[str, str]) -> dict[str, int]:
    return {key: len(core.store.get_belief(bid).evidence_ids) for key, bid in ids.items()}


# --- every fixture loads the shape it declares -------------------------------

@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_gate_every_fixture_loads_its_declared_shape(name: str) -> None:
    """A fixture whose file and store disagree is measuring something else.

    Experiment 3 section 3.5 is the reason this exists: `supports` was absent
    from the extractor schema entirely, so the field was present, unreachable,
    and silently empty in every store — knowable by reading, with zero calls.
    """
    core, ids, fixture = _seed(name)
    beliefs = {bid: core.store.get_belief(bid) for bid in ids.values()}
    conflicts = _leaf_conflicts({b.belief_id: b for b in beliefs.values()})

    declared = {
        tuple(sorted((ids[pair["contradictor"]], ids[pair["target"]])))
        for pair in fixture.get("contradictions", [])
    }
    assert conflicts == declared, (
        f"{name}: store holds {len(conflicts)} conflicts, fixture declares {len(declared)}"
    )

    expected_count = fixture["expect"].get("conflict_count")
    if expected_count is not None:
        assert len(conflicts) == expected_count, f"{name}: expected {expected_count} conflicts, store has {len(conflicts)}"


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_gate_no_fixture_silently_lost_an_edge(name: str) -> None:
    """Every `supports` key named in the file resolves to an edge in the store.

    The 46% edge loss in experiment 3's Stage 0 was invisible in the extractor
    output and invisible in the store; it appeared only when the two were
    compared. This is that comparison, for the write path this experiment uses.
    """
    core, ids, fixture = _seed(name)
    for entry in fixture["beliefs"]:
        expected = {ids[key] for key in entry.get("supports", [])}
        actual = set(core.store.get_belief(ids[entry["key"]]).supports)
        assert actual == expected, f"{name}/{entry['key']}: supports {actual} != declared {expected}"


# --- the adversarial fixture is actually adversarial -------------------------

def test_gate_the_adversarial_fixture_favours_weakening_the_better_grounded_side() -> None:
    """The load-bearing precondition for Stage 4.

    If the better-grounded belief is *not* the lower-staked one, the loop is not
    forced onto it and the whole adversarial arm measures nothing. Computed under
    the substrate's own arithmetic rather than asserted in the fixture's notes.
    """
    core, ids, fixture = _seed("adversarial_grounding")
    stakes, grounding = _stakes(core, ids), _grounding(core, ids)

    lower_staked = min(stakes, key=lambda key: stakes[key])
    better_grounded = max(grounding, key=lambda key: grounding[key])

    assert lower_staked == fixture["expect"]["lower_staked_party"], (
        f"fixture claims {fixture['expect']['lower_staked_party']} is lower-staked; stakes are {stakes}"
    )
    assert better_grounded == fixture["expect"]["better_grounded_party"]
    assert lower_staked == better_grounded, (
        f"the fixture is not adversarial: lower-staked is {lower_staked!r} but better-grounded is "
        f"{better_grounded!r}. Stage 4 cannot read anything from it"
    )


def test_gate_the_aligned_fixture_is_the_minimal_pair() -> None:
    """`aligned_grounding` must differ from the adversarial one in grounding alone.

    If the two fixtures differ in any other field, a difference in outcome is not
    attributable to grounding and the pair proves nothing.
    """
    adversarial, aligned = load_web("adversarial_grounding"), load_web("aligned_grounding")
    fields = ("valence", "confidence", "salience")

    adv = sorted(adversarial["beliefs"], key=lambda entry: entry["salience"])
    ali = sorted(aligned["beliefs"], key=lambda entry: entry["salience"])
    for a, b in zip(adv, ali):
        for field in fields:
            assert a[field] == b[field], f"the pair differs in {field}: {a['key']}={a[field]} vs {b['key']}={b[field]}"

    # ...and the grounding is genuinely swapped, or it is not a pair at all.
    assert [entry["evidence_count"] for entry in adv] != [entry["evidence_count"] for entry in ali], (
        "the two fixtures carry identical grounding, so they are the same fixture twice"
    )


def test_gate_the_minimal_pair_is_indistinguishable_in_the_signal_channel() -> None:
    """The sharpest statement of what this experiment is about.

    `adversarial_grounding` and `aligned_grounding` produce **byte-identical**
    raw tension, magnitude, and carrier counts. The dissonance channel cannot
    tell the two webs apart, because the only thing that differs between them is
    grounding and `stake_of` averages salience rather than summing it.

    So a control loop reading this signal is, by construction, choosing between
    a case where weakening the forced target is right and one where it is wrong,
    with nothing in its input to distinguish them. Whatever the loop does, it
    does the same thing in both — and that is the finding, not a defect in the
    fixtures.

    If this ever stops holding, the pair is no longer minimal and the Stage 4
    comparison has acquired a confound.
    """
    readings = {}
    for name in ("adversarial_grounding", "aligned_grounding"):
        core, _, _ = _seed(name)
        signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
        assert signal is not None, f"{name} produced no signal"
        readings[name] = (signal.magnitude_raw, signal.magnitude, len(signal.carriers))

    adversarial, aligned = readings["adversarial_grounding"], readings["aligned_grounding"]
    assert adversarial == aligned, (
        f"the signal distinguishes the minimal pair — adversarial={adversarial}, aligned={aligned}. "
        f"Any Stage 4 difference could now be the signal rather than the grounding"
    )


def test_gate_both_outcomes_of_the_adversarial_arm_are_reachable() -> None:
    """An arm with one reachable outcome cannot fail, so it cannot be evidence.

    In `adversarial_grounding` the forced target is the better-grounded belief;
    in `aligned_grounding` it is the worse-grounded one. Both are computed from
    stakes, so whichever the loop does, the *other* was available.
    """
    outcomes = {}
    for name in ("adversarial_grounding", "aligned_grounding"):
        core, ids, _ = _seed(name)
        stakes, grounding = _stakes(core, ids), _grounding(core, ids)
        forced = min(stakes, key=lambda key: stakes[key])
        outcomes[name] = grounding[forced] == max(grounding.values())

    assert outcomes["adversarial_grounding"] is True, "the adversarial fixture does not force the good belief"
    assert outcomes["aligned_grounding"] is False, "the aligned fixture also forces the good belief; it is not a control"


# --- the discriminating and negative fixtures --------------------------------

def test_gate_the_counter_direction_fixture_separates_direction_from_stake() -> None:
    """The gap the mutant battery found, closed and pinned.

    On both `adversarial_grounding` and `aligned_grounding` the declared target
    *is* the lower-staked party, so a loop reading the direction off the graph
    and one charging whichever side is weaker behave identically — the
    `chosen_direction` mutant passed every check the battery had. Stage 4's
    claim depends on telling those apart.
    """
    core, ids, fixture = _seed("counter_direction")
    stakes = _stakes(core, ids)
    declared_target = fixture["contradictions"][0]["target"]
    weaker = min(stakes, key=lambda key: stakes[key])

    assert declared_target != weaker, (
        f"the fixture does not separate them: declared target and weaker party are both {weaker!r}"
    )
    assert declared_target == fixture["expect"]["declared_target"]
    assert weaker == fixture["expect"]["lower_staked_party"]


def test_gate_the_hub_web_reorders_after_the_first_action() -> None:
    """The other gap the battery found.

    Every previously frozen web has disjoint conflicts, so tensions fall
    independently, the ranking never reorders, and a loop deciding from the first
    reading it ever saw is indistinguishable from one re-reading each step. The
    hub shares a party across three conflicts, and the values are chosen so the
    order genuinely flips once the shared belief is weakened.
    """
    core, ids, _ = _seed("hub_web")
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
    assert signal is not None
    reverse = {bid: key for key, bid in ids.items()}

    def ranking() -> list[str]:
        current = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
        assert current is not None
        ordered = sorted(current.carriers, key=lambda c: -c.tension)
        return [reverse[c.belief_id_a] for c in ordered]

    before = ranking()
    assert len(before) == 3, before

    # Weaken the shared party the way the loop's own action would.
    hub_id = ids["hub"]
    top = before[0]
    core.assert_contradiction(
        {"agent_id": AGENT, "contradictor_id": ids[top], "target_id": hub_id, "arm": "direct"}
    )

    after = [key for key in ranking() if key != top]
    remaining_before = [key for key in before if key != top]
    assert after != remaining_before, (
        f"the ordering did not flip: {remaining_before} before, {after} after. "
        f"A stale-view loop is indistinguishable from a live one on this web"
    )


def test_gate_the_distractor_web_leaves_beliefs_out_of_reach() -> None:
    """Stage 3 is unmeasurable on a web the signal already names entirely.

    `spread` pinned at 1.0 is experiment 1's failure mode #3 — a metric at the
    end of its range reporting its own constant. Two of the three webs Stage 3
    runs on sit exactly there, and this fixture exists so at least one does not.
    """
    from manyu.salience import implicated_beliefs, reading_of

    core, ids, fixture = _seed("distractor_web")
    reading = reading_of(MergedDissonanceQuery(core.store).detect(AGENT, "criteria"), agent_id=AGENT)
    assert reading is not None

    named = implicated_beliefs(reading.view)
    assert len(named) == fixture["expect"]["implicated_beliefs"], (
        f"expected {fixture['expect']['implicated_beliefs']} implicated beliefs, got {len(named)}"
    )
    assert len(named) < len(ids), "the signal names the whole web; spread is at ceiling and unmeasurable"

    # The distractors must carry structure, or their silence is about their size.
    assert any(entry.get("supports") for entry in fixture["beliefs"] if entry["key"].startswith(("docs", "hiring")))


def test_gate_the_adversarial_multi_web_anticorrelates_grounding_and_tension() -> None:
    """Stage 4's premise on a web where the loop actually has a choice.

    If tension and grounding were merely uncorrelated, a driven arm hitting
    well-grounded targets would be luck. Anti-correlated makes it a prediction
    that can fail: the highest-tension dispute is the best-corroborated one.
    """
    core, ids, fixture = _seed("adversarial_multi")
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
    assert signal is not None
    reverse = {bid: key for key, bid in ids.items()}

    declared = {pair["target"]: pair["contradictor"] for pair in fixture["contradictions"]}
    ordered = sorted(signal.carriers, key=lambda c: -c.tension)
    targets = []
    for carrier in ordered:
        pair = {reverse[carrier.belief_id_a], reverse[carrier.belief_id_b]}
        targets.append(next(key for key in pair if key in declared))

    assert targets == fixture["expect"]["targets_by_descending_tension"], targets
    grounding = [len(core.store.get_belief(ids[key]).evidence_ids) for key in targets]
    assert grounding == fixture["expect"]["target_evidence_by_descending_tension"], grounding
    assert grounding == sorted(grounding, reverse=True), (
        f"grounding is not anti-correlated with tension: {list(zip(targets, grounding))}"
    )


def test_gate_the_multi_conflict_web_has_strictly_ordered_tensions() -> None:
    """Ties would make 'it picked the highest' unmeasurable on this fixture."""
    core, ids, _ = _seed("multi_conflict_web")
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
    assert signal is not None

    tensions = sorted(carrier.tension for carrier in signal.carriers)
    assert len(set(tensions)) == len(tensions), f"tensions are not distinct: {tensions}"


def test_gate_the_tied_fixture_really_ties() -> None:
    """The converse. If the 'tied' fixture has distinct tensions there is no tie
    to break, and the determinism test below it is vacuous.
    """
    core, ids, _ = _seed("tied_tension_web")
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
    assert signal is not None

    tensions = [carrier.tension for carrier in signal.carriers]
    assert len(set(tensions)) == 1, f"expected one tension value across both conflicts, got {sorted(set(tensions))}"


def test_gate_the_depth_fixture_produces_a_derived_carrier() -> None:
    """A carrier with a non-empty path is the only thing separating a graph query
    from an adjacency scan. Without one this fixture cannot discriminate.
    """
    core, ids, fixture = _seed("depth_carrier_web")
    signal = MergedDissonanceQuery(core.store).detect(AGENT, "criteria")
    assert signal is not None

    derived = [carrier for carrier in signal.carriers if carrier.path]
    assert len(derived) >= fixture["expect"]["min_derived_carriers"], (
        f"no derived carriers; got {[(c.belief_id_a, c.path) for c in signal.carriers]}"
    )
    assert max(len(carrier.path) for carrier in derived) >= fixture["expect"]["min_path_length"]


def test_gate_the_negative_fixture_holds_no_conflict() -> None:
    """A negative control containing a conflict turns specificity into an artifact."""
    core, ids, _ = _seed("no_conflict_web")
    assert MergedDissonanceQuery(core.store).detect(AGENT, "criteria") is None, (
        "the negative control fires; every specificity result downstream is unreadable"
    )


def test_gate_the_negative_fixture_is_not_merely_empty() -> None:
    """It must have structure, or its silence is evidence about its size.

    Experiment 2's `near_miss` makes the same move: a negative that is trivially
    empty tests nothing, because a mechanism firing on graph size would pass it.
    """
    core, ids, _ = _seed("no_conflict_web")
    beliefs = [core.store.get_belief(bid) for bid in ids.values()]
    assert len(beliefs) >= 4
    assert any(belief.supports for belief in beliefs), "the negative control has no edges at all"


def test_gate_the_mutual_fixture_is_one_conflict_carried_by_two_edges() -> None:
    """`_leaf_conflicts` deduplicates by sorted pair. A loop counting edges rather
    than conflicts double-charges here, which is the defect experiment 3 found in
    pre-flight rather than in its suite.
    """
    core, ids, _ = _seed("mutual_contradiction")
    beliefs = {bid: core.store.get_belief(bid) for bid in ids.values()}
    conflicts = _leaf_conflicts(beliefs)

    assert len(conflicts) == 1, f"expected one deduplicated conflict, got {conflicts}"
    edges = sum(len(belief.contradicts) for belief in beliefs.values())
    assert edges == 2, f"expected two directed edges carrying it, got {edges}"


# --- the fixtures as a set ---------------------------------------------------

def test_gate_the_fixture_freeze_still_holds() -> None:
    """Every held-out web is byte-identical to what was frozen.

    "Held out" is a claim about a file, and this is what makes it checkable
    rather than remembered. If a fixture is edited after freezing, every Stage
    2-4 result resting on it is void — better to find that here than in a
    retrospective.
    """
    from manyu.salience import verify_fixture_freeze

    freeze = verify_fixture_freeze()
    assert freeze["files"], "the freeze file records no fixtures"
    assert set(freeze["files"]) == {f"evals/fixtures/exp04/{name}.json" for name in ALL_FIXTURES}, (
        "the freeze covers a different set of webs than the criterion tests do"
    )


def test_gate_the_freeze_verifier_can_fail(tmp_path) -> None:
    """A guard that cannot fire is failure mode #5 wearing a lab coat.

    `gate.py` tests every one of its assertions for the ability to fail; this
    verifier gets the same treatment.
    """
    import json as _json

    from manyu.salience import verify_fixture_freeze

    tampered = tmp_path / "freeze.json"
    tampered.write_text(
        _json.dumps(
            {
                "files": {
                    "evals/fixtures/exp04/adversarial_grounding.json": {"sha256": "0" * 64, "role": "tampered"},
                    "evals/fixtures/exp04/does_not_exist.json": {"sha256": "1" * 64, "role": "missing"},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError) as caught:
        verify_fixture_freeze(tampered)
    message = str(caught.value)
    assert "changed after freeze" in message, message
    assert "absent" in message, message


def test_gate_every_fixture_is_covered_by_a_criterion_test() -> None:
    """The set cannot grow without someone deciding what would make it readable.

    A fixture added to the directory and never checked is a fixture whose
    properties are whatever they happen to be.
    """
    from manyu.salience import FIXTURE_DIR

    on_disk = {path.stem for path in FIXTURE_DIR.glob("*.json")}
    assert on_disk == set(ALL_FIXTURES), (
        f"fixture directory and criterion tests disagree: only on disk {sorted(on_disk - set(ALL_FIXTURES))}, "
        f"only in tests {sorted(set(ALL_FIXTURES) - on_disk)}"
    )
