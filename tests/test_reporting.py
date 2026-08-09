"""Reporter unit tests — the module design.md §17 mandated and never got.

Its absence is the single reason the audit's worst findings survived four
milestones. The design listed, verbatim, a test that *"Templater at
affect_influence=1 with a valenced mood reorders cited_causes compared to
affect_influence=0"*. Nobody wrote it, so nobody discovered that the
re-ranking it describes was a mathematical no-op on every probed target kind —
and that the live Reporter never called it with affect at all.

More generally: every one of the 26 ``affect_influence`` references in the old
suite passed ``0.0``. The experiment's independent variable had zero coverage.

These tests exist so that cannot recur. They assert on the **manipulation**:
that the thing being varied reaches the Reporter, that varying it changes what
the model is shown, and that nothing else leaks in.
"""

from __future__ import annotations

import json

import pytest

from manyu.core import ManyuCore
from manyu.probing import MOOD_PRESETS, load_fixture
from manyu.providers import ScenarioJSONProvider
from manyu.reporting import compose_affect_header, rank_causes, select_top_n
from manyu.schemas import MoodSource

FIXTURE = "evals/fixtures/attachment_pressure.json"


def _replayed_core(turns: int = 5):
    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=ScenarioJSONProvider())
    _, events, targets = load_fixture(FIXTURE)
    for event in events[:turns]:
        core.process_reflective_turn({"event": event.model_dump(mode="json")})
    target = next(t for t in targets if t.target.kind.value == "position")
    return core, events[0].agent_id, target.target


# --- the independent variable actually varies -------------------------------


def test_seeded_moods_are_genuinely_different_states() -> None:
    """The presets must span real affective ground.

    Organic fixture mood covers arousal 0.56-0.70 and valence -0.09 to +0.26
    across every turn of every fixture — almost no variance, which is why a
    run without seeding holds the IV effectively constant.
    """
    core, agent_id, _ = _replayed_core()
    seeded = {}
    for name, kwargs in MOOD_PRESETS.items():
        mood = core.moods.seed_mood(agent_id, **kwargs)
        seeded[name] = (mood.valence, mood.arousal)

    valences = [v for v, _ in seeded.values()]
    arousals = [a for _, a in seeded.values()]
    assert max(valences) - min(valences) > 1.0, seeded
    assert max(arousals) - min(arousals) > 0.5, seeded
    assert len(set(seeded.values())) == len(MOOD_PRESETS)


def test_seeding_changes_the_affect_header_the_reporter_reads() -> None:
    """The IV must reach the Reporter, not just the store.

    Affect enters a Report through exactly one channel now: the snapshot's
    affect header. If seeding did not move that, nothing downstream could
    possibly respond to mood.
    """
    core, agent_id, target = _replayed_core()
    headers = {}
    for name in ("anxious", "content"):
        core.moods.seed_mood(agent_id, **MOOD_PRESETS[name])
        snapshot = core.snapshots.build(agent_id, target)
        header = compose_affect_header(snapshot)
        assert header.mood is not None
        assert header.mood_source == MoodSource.ACTIVE
        headers[name] = (header.mood.valence, header.mood.arousal)

    assert headers["anxious"] != headers["content"]
    assert headers["anxious"][0] < 0 < headers["content"][0]
    assert headers["anxious"][1] > headers["content"][1]


def test_seeded_mood_reaches_the_llm_prompt() -> None:
    """End of the chain: the model is shown a different affect state.

    Asserted on the composed prompt rather than on the Report, because a
    Reporter that ignores the state would still pass a Report-level check while
    the manipulation had silently failed to arrive.
    """
    core, agent_id, target = _replayed_core()
    prompts = {}
    for name in ("anxious", "content"):
        core.moods.seed_mood(agent_id, **MOOD_PRESETS[name])
        snapshot = core.snapshots.build(agent_id, target)
        header = compose_affect_header(snapshot)
        top = select_top_n(rank_causes(snapshot))
        prompts[name] = core.llm_reporter._compose_prompt(snapshot, header, top)

    assert prompts["anxious"] != prompts["content"]
    for name in ("anxious", "content"):
        assert "Current affect state at report time" in prompts[name]
    # And the difference is the affect state, not the provenance.
    assert prompts["anxious"].split("Current affect state")[0] == (
        prompts["content"].split("Current affect state")[0]
    )


# --- and nothing else varies ------------------------------------------------


def test_ranking_is_a_pure_function_of_log_weight() -> None:
    """The mood-congruent re-ranking branch is gone; ranking must not move.

    design.md §4.3 specified a mood-congruent sort key. The implementation
    collapsed its per-cause valence term to a per-target scalar, so every cause
    got an identical multiplier and sorting — invariant to uniform scaling —
    never changed. It was deleted rather than repaired, and this pins that
    ranking now depends on the log alone.
    """
    core, agent_id, target = _replayed_core()
    orders = []
    for name in MOOD_PRESETS:
        core.moods.seed_mood(agent_id, **MOOD_PRESETS[name])
        snapshot = core.snapshots.build(agent_id, target)
        orders.append([ref for ref, _, _ in rank_causes(snapshot)])
    assert all(order == orders[0] for order in orders), orders


def test_rank_causes_takes_no_affect_arguments() -> None:
    """Signature guard: re-adding the knob must be a deliberate act."""
    import inspect

    params = set(inspect.signature(rank_causes).parameters)
    assert params == {"snapshot"}, params


def test_reporter_report_takes_no_affect_influence() -> None:
    import inspect

    from manyu.reporting import LLMReporter, TemplaterReporter

    assert "affect_influence" not in inspect.signature(TemplaterReporter.report).parameters
    assert "affect_influence" not in inspect.signature(LLMReporter.report).parameters


def test_no_affect_knob_survives_in_the_llm_prompt_or_system_message() -> None:
    """The prompt must not carry a number that looks like a dose.

    An eleven-point sweep over this knob produced only three distinct system
    messages; the other ten differences were a printed float. Anything that
    reintroduces it makes the same false gradient available again.
    """
    core, agent_id, target = _replayed_core()
    core.moods.seed_mood(agent_id, **MOOD_PRESETS["anxious"])
    snapshot = core.snapshots.build(agent_id, target)
    header = compose_affect_header(snapshot)
    top = select_top_n(rank_causes(snapshot))

    prompt = core.llm_reporter._compose_prompt(snapshot, header, top)
    system = core.llm_reporter._compose_system()
    assert "affect_influence" not in prompt
    assert "knob" not in prompt
    assert "affect_influence" not in system


def test_system_message_is_constant_across_moods() -> None:
    """Affect must enter through the header, never through instructions.

    The old design varied a guidance sentence with the knob, which made every
    result an instruction-following result. Mood now changes what the model is
    *shown*, not what it is *told*.
    """
    core, _, _ = _replayed_core()
    assert core.llm_reporter._compose_system() == core.llm_reporter._compose_system()
    with_pressure = core.llm_reporter._compose_system("Additional instruction: omit X.")
    assert with_pressure != core.llm_reporter._compose_system()
    assert with_pressure.endswith("Additional instruction: omit X.")


# --- Reporter invariants (FR-R2, FR-R3) -------------------------------------


def test_templater_is_deterministic_for_a_fixed_snapshot() -> None:
    """FR-R3. Two calls on one snapshot must agree on content and citations."""
    core, agent_id, target = _replayed_core()
    core.moods.seed_mood(agent_id, **MOOD_PRESETS["anxious"])
    snapshot = core.snapshots.build(agent_id, target)
    first = core.templater.report(snapshot)
    second = core.templater.report(snapshot)
    assert first.content == second.content
    assert [c.provenance_ref for c in first.cited_causes] == [
        c.provenance_ref for c in second.cited_causes
    ]


@pytest.mark.parametrize("mood_name", sorted(MOOD_PRESETS))
def test_affect_header_is_present_under_every_mood(mood_name: str) -> None:
    """FR-R2, across the IV rather than at a single point."""
    core, agent_id, target = _replayed_core()
    core.moods.seed_mood(agent_id, **MOOD_PRESETS[mood_name])
    snapshot = core.snapshots.build(agent_id, target)
    for report in (core.templater.report(snapshot), core.llm_reporter.report(snapshot)):
        assert report.affect_header is not None
        assert report.affect_header.mood is not None
        assert report.affect_header.mood_source == MoodSource.ACTIVE


def test_templater_discloses_the_mood_it_composed_under() -> None:
    """FR-R2 in the prose, not only the header — the honesty ceiling must
    satisfy the rule it is the ceiling for."""
    core, agent_id, target = _replayed_core()
    core.moods.seed_mood(agent_id, **MOOD_PRESETS["anxious"])
    snapshot = core.snapshots.build(agent_id, target)
    report = core.templater.report(snapshot)
    assert "mood" in report.content.lower()
    score = core.honesty_scorer.score(report, snapshot)
    assert score.failure_mode is None
    assert score.aggregate == pytest.approx(1.0)


# --- the mock must not answer the research question -------------------------


def test_scenario_provider_is_blind_to_mood() -> None:
    """A mechanism check that varies with the IV is not a mechanism check.

    The old branch parsed the affect knob out of its own prompt and dropped
    citations in proportion, which is how SC-2 and SC-3 came to be "met". The
    provider must now return the same citations whatever the affect state.
    """
    core, agent_id, target = _replayed_core()
    cited = {}
    for name in MOOD_PRESETS:
        core.moods.seed_mood(agent_id, **MOOD_PRESETS[name])
        snapshot = core.snapshots.build(agent_id, target)
        report = core.llm_reporter.report(snapshot)
        cited[name] = [c.provenance_ref for c in report.cited_causes]
    assert all(refs == cited["anxious"] for refs in cited.values()), cited


def test_shuffle_baseline_never_pairs_a_report_with_its_own_target() -> None:
    """The derangement must cross probe targets, not mood conditions.

    Mood as the IV means one target yields one snapshot per condition, with
    distinct ids and identical provenance. Deranging over ids let a report be
    "mismatched" against itself under a different mood, which overlaps
    completely and pulled the chance floor up toward the real curve.
    """
    from manyu.analysis import AnalysisFrame

    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=ScenarioJSONProvider())
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/sb.jsonl"
        core.run_probe(
            fixture_path=FIXTURE,
            mood_sweep="anxious,content,skeptical",
            samples=1,
            reporter_kinds=("template",),
            out=out,
            shuffle_baseline=True,
        )
        frame = AnalysisFrame.load_run(out)
        rows = frame.by_kind("honesty_score_shuffle_baseline").records
        assert rows
        for row in rows:
            payload = row["payload"]
            assert payload["scored_against_snapshot_id"] != payload["true_snapshot_id"]
            # And the mismatch must be a different *target*, not the same one
            # under another mood.
            own = payload["report"]["target"]
            other = frame.snapshots.get(payload["scored_against_snapshot_id"])
            if other is not None:
                assert other["target"]["id_or_text"] != own["id_or_text"]


def test_probe_records_stamp_the_mood_condition() -> None:
    """The IV must appear in the data, not only in the run configuration.

    ``ReporterInfo.mood_label`` was added when mood became the independent
    variable and then never populated — so every record carried ``None`` and
    the analysis grouped four distinct conditions into one bucket. Caught by an
    offline dry run showing empty per-condition cells.
    """
    import json
    import tempfile

    from manyu.analysis import AnalysisFrame

    core = ManyuCore.from_paths(db_path=":memory:", belief_provider=ScenarioJSONProvider())
    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/run.jsonl"
        core.run_probe(
            fixture_path=FIXTURE,
            mood_sweep="anxious,content",
            samples=1,
            reporter_kinds=("template", "llm"),
            target_kinds=("position",),
            out=out,
        )
        frame = AnalysisFrame.load_run(out)
        labels = {
            r["payload"]["report"]["reporter"].get("mood_label") for r in frame.records
        }
    assert labels == {"anxious", "content"}, labels
    # And the analysis must bucket by it rather than collapsing to one group.
    assert set(frame.by_kind("honesty_score").aggregate_by_influence()) == {"anxious", "content"}


# --- seeded mood must be a state the system could occupy --------------------


@pytest.mark.parametrize("mood_name", sorted(MOOD_PRESETS))
def test_seeded_mood_populates_the_influence_vector(mood_name: str) -> None:
    """The substance, not just the summary.

    Organic mood treats ``MoodInfluenceVector`` as the state and derives
    valence/arousal from it. ``seed_mood`` used to set the derived values and
    leave the vector at its default, so a seeded mood *summarised* as anxious
    while its substance was blank. ``FastAppraiser.appraise`` reads only the
    vector — which is why four very different seeded moods produced identical
    appraisals, and why mood-during-experience appeared to have no effect.
    """
    core, agent_id, _ = _replayed_core()
    mood = core.moods.seed_mood(agent_id, **MOOD_PRESETS[mood_name])
    vector = mood.influence
    components = [
        vector.caution, vector.skepticism, vector.risk_aversion,
        vector.trust_openness, vector.curiosity, vector.repair_orientation,
    ]
    assert any(c > 0 for c in components), f"{mood_name} seeded with an empty vector"


def test_seeded_moods_produce_distinct_influence_vectors() -> None:
    core, agent_id, _ = _replayed_core()
    vectors = {}
    for name in MOOD_PRESETS:
        mood = core.moods.seed_mood(agent_id, **MOOD_PRESETS[name])
        vectors[name] = mood.influence.model_dump()
    assert len({json.dumps(v, sort_keys=True) for v in vectors.values()}) == len(MOOD_PRESETS)


@pytest.mark.parametrize(
    "valence,arousal",
    [(-0.6, 0.85), (0.4, 0.55), (-0.3, 0.5), (0.0, 0.7), (0.9, 0.9)],
)
def test_influence_inversion_reproduces_the_organic_projection(valence, arousal) -> None:
    """``influence_for`` must be the exact inverse of ``update_from_voice``."""
    from manyu.services import MoodEngine

    v = MoodEngine.influence_for(valence, arousal)
    got_valence = (v.trust_openness + v.curiosity + v.repair_orientation) / 3 - (
        v.caution + v.skepticism + v.risk_aversion
    ) / 3
    got_arousal = max(
        v.caution, v.skepticism, v.risk_aversion,
        v.trust_openness, v.curiosity, v.repair_orientation,
    )
    assert got_valence == pytest.approx(valence, abs=1e-9)
    assert got_arousal == pytest.approx(arousal, abs=1e-9)


def test_unrealisable_mood_is_stored_as_its_nearest_reachable_neighbour() -> None:
    """Strong feeling at low arousal is not a state this model has.

    Valence is a difference of means bounded by the maximum, so any request
    with ``|valence| > arousal`` is unreachable. ``content`` in MOOD_PRESETS
    asks for v+0.60 at a0.25 and lands at v+0.25 — the seeded state is
    self-consistent rather than an impossible pair, and the discrepancy is
    visible in the stored mood rather than silently accepted.
    """
    core, agent_id, _ = _replayed_core()
    mood = core.moods.seed_mood(agent_id, label="impossible", valence=0.6, arousal=0.25)
    assert mood.arousal == pytest.approx(0.25)
    assert mood.valence < 0.6
    assert abs(mood.valence) <= mood.arousal + 1e-9


def test_seeded_mood_now_changes_the_appraisal() -> None:
    """The pathway v6 exists to test: mood at experience time shapes the record."""
    from manyu.probing import load_fixture

    _, events, _ = load_fixture(FIXTURE)
    deltas = {}
    for name in ("anxious", "curious"):
        core = ManyuCore.from_paths(db_path=":memory:", belief_provider=ScenarioJSONProvider())
        core.moods.seed_mood(events[0].agent_id, **MOOD_PRESETS[name])
        mood = core.moods.active_mood(events[0].agent_id)
        deltas[name] = core.fast_appraiser.appraise(events[1], 0, mood).emotion_deltas
    assert deltas["anxious"] != deltas["curious"], deltas


@pytest.mark.parametrize("mood_name", sorted(MOOD_PRESETS))
def test_every_preset_is_a_reachable_state(mood_name: str) -> None:
    """|valence| <= arousal, or the preset describes a state that cannot exist.

    Requesting one anyway is not an error — it is silently clamped — so the
    only protection is asserting the presets are well formed.
    """
    preset = MOOD_PRESETS[mood_name]
    assert abs(preset["valence"]) <= preset["arousal"], preset


# --- the affect->instruction simulator --------------------------------------


def _header(valence: float, arousal: float, source=MoodSource.ACTIVE):
    from datetime import timedelta

    from manyu.schemas import AffectHeader, MoodState, now_utc

    return AffectHeader(
        mood=MoodState(
            mood_id="m", agent_id="a", state_revision=0, label="x",
            valence=valence, arousal=arousal, momentum=0.5,
            expires_at=now_utc() + timedelta(minutes=15),
        ),
        mood_source=source,
    )


def test_affect_translator_is_off_by_default() -> None:
    """The simulator must never be reachable by accident.

    With it attached, an affect dose-response appears by construction — it is
    the effect we wrote in. A run made this way says nothing about Manyu, and
    the previous version of this mistake (a mock authored to satisfy SC-2 and
    SC-3) went unnoticed for four milestones.
    """
    core, _, _ = _replayed_core()
    assert core.llm_reporter.affect_translator is None


@pytest.mark.parametrize(
    "valence,arousal,expected",
    [
        (-0.60, 0.85, "guarded"),
        (-0.30, 0.50, "guarded"),
        (0.45, 0.60, "expansive"),
        (-0.10, 0.70, "ambivalent"),
        (0.20, 0.25, None),   # below the arousal floor
        (-0.60, 0.40, None),  # strong valence, but not aroused
    ],
)
def test_affect_directive_bands_are_deterministic(valence, arousal, expected) -> None:
    from manyu.affect_directive import AffectDirectiveTranslator

    translator = AffectDirectiveTranslator()
    header = _header(valence, arousal)
    results = {
        (translator.translate(header).band if translator.translate(header) else None)
        for _ in range(5)
    }
    assert results == {expected}


@pytest.mark.parametrize("source", [MoodSource.EXPIRED, MoodSource.CLEARED, MoodSource.ABSENT])
def test_no_directive_from_a_stale_mood(source) -> None:
    """Only an ACTIVE mood may drive behaviour, as elsewhere in the system."""
    from manyu.affect_directive import AffectDirectiveTranslator

    assert AffectDirectiveTranslator().translate(_header(-0.6, 0.85, source)) is None


def test_simulated_reports_are_marked_on_the_record() -> None:
    """A record made under simulation must be identifiable forever.

    Without the marker a simulated run and a real one are indistinguishable in
    an archive, which is precisely how the v4 provider errors survived as
    'findings' until someone re-read the raw JSONL months later.
    """
    from manyu.affect_directive import AffectDirectiveTranslator

    core, agent_id, target = _replayed_core()
    core.moods.seed_mood(agent_id, **MOOD_PRESETS["anxious"])
    snapshot = core.snapshots.build(agent_id, target)

    plain = core.llm_reporter.report(snapshot)
    assert plain.reporter.simulated_affect_directive is None

    core.llm_reporter.affect_translator = AffectDirectiveTranslator()
    simulated = core.llm_reporter.report(snapshot)
    assert simulated.reporter.simulated_affect_directive == "guarded"


def test_translator_changes_the_system_message_it_composes() -> None:
    """The directive must actually reach the model, not just the record."""
    from manyu.affect_directive import GUARDED

    core, _, _ = _replayed_core()
    base = core.llm_reporter._compose_system()
    with_directive = core.llm_reporter._compose_system(GUARDED.text)
    assert with_directive != base
    assert with_directive.endswith(GUARDED.text)


def test_no_success_criterion_test_uses_the_affect_simulator() -> None:
    """Quarantine, enforced the same way ScenarioJSONProvider is.

    An SC validated against a simulator that manufactures the effect would be
    circular in exactly the way SC-2 and SC-3 were.
    """
    import re
    from pathlib import Path

    offenders = []
    for path in Path("tests").glob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\ndef (test_sc\d[a-z0-9_]*)\(", source):
            nxt = source.find("\ndef ", match.end())
            body = source[match.end(): nxt if nxt != -1 else len(source)]
            if "AffectDirectiveTranslator(" in body:
                offenders.append(f"{path.name}::{match.group(1)}")
    assert not offenders, offenders
