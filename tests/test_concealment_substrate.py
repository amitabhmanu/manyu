"""Experiment 7 Stage -1 — executing the requirements document against the substrate.

Written *before* `src/manyu/concealment.py` exists, and covering no mechanism of
this experiment's. Same category as `tests/test_counterfactual_substrate.py`,
`tests/test_underdetermination_substrate.py` and `tests/test_salience_substrate.py`,
and for the same reason: experiment 3's suite caught none of sixteen defects
because every test was written minutes after the mechanism, by the author who had
just written it, so it agreed with the code precisely where the code was wrong.

**The specific risk this file exists for.** Requirements section 5 surveys seven
concealment channels by *reading source*. Everything downstream rests on that
table: the pre-registered sensitivity numbers, the attribution rate, and the
substrate/agent split that is the registered headline. A survey performed by
reading is not a measurement.

One of the seven was already wrong when read. "Deprecated holding" was inferred
from the existence of `list_beliefs`'s `status != 'deprecated'` filter -- a guard
against a state that no code path anywhere assigns. Six channels, not seven, and
`test_deprecated_is_unreachable` is what remains of the seventh.

A failure in this file is never a bug in this file. It is a defect report against
`requirements.md` section 5 or against `pre-registration.md`, and correcting the
document is this stage's output.

Entirely offline. Deterministic under `FrozenClock`. No provider is constructed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manyu.core import ManyuCore
from manyu.reporting import rank_causes, select_top_n
from manyu.schemas import BeliefScope, BeliefStatus, BeliefType, ReportTarget, ReportTargetKind

AGENT = "agent_demo"

REPO = Path(__file__).resolve().parents[1]

#: `BeliefUpdater._create` stamps TENTATIVE below this (services.py:843) and
#: `WorldviewSynthesizer.synthesize` composes only {ACTIVE, CONTESTED}
#: (services.py:898). Pre-registration section 8 fixes it as tau, and it is the
#: substrate's own line rather than a registered constant.
EXPRESSION_THRESHOLD = 0.45

#: Pre-registration section 0.1, derived by hand from `blend_confidence` before
#: any detector existed. Creation at 0.44, five corroborating candidates at 0.90,
#: starting stability 0.10.
STATUS_TRAJECTORY = (0.6516, 0.7609, 0.8193, 0.8516, 0.8700)

#: Experiment 6 amended its own 1e-9 to 1e-6 because `_revise` stores
#: `round(confidence, 6)`, so agreement is bounded below by 5e-7
#: (experiment 6 pre-registration section 7 A1). Inherited rather than rediscovered.
TRAJECTORY_TOLERANCE = 1e-4

#: `reporting.select_top_n`'s cumulative rule.
COVERAGE_THRESHOLD = 0.80

#: `WorldviewSynthesizer._theme_for_belief` collapses the eight BeliefType values
#: onto this many themes -- only `self_model` and `epistemic_principle` share one.
#: Pre-registration section 1.2: the prose loss rate has a floor of 1 - 7/N forced
#: by this ceiling, independent of any corpus.
#:
#: **Measured as 7 rather than assumed.** It was written as 6 in the first draft of
#: the requirements survey, by counting BeliefType members from memory as six when
#: there are eight. The floor is correspondingly weaker: it clears 2/3 only above
#: N = 21, where the draft claimed N = 18.
THEME_CEILING = 7


# --- harness ------------------------------------------------------------------


def _core() -> ManyuCore:
    return ManyuCore.from_paths(db_path=":memory:", frozen=True)


def _capture(
    core: ManyuCore,
    source_id: str,
    *,
    salience: float = 0.5,
    weight: float = 0.7,
    summary: str | None = None,
    evidence_id: str | None = None,
) -> str:
    """Capture one evidence record.

    `salience`, `weight` and `evidence_id` are all caller-supplied on purpose:
    services.py:453 and :459-460 take them from the payload, and that is the
    write-path channel requirements section 5.2 and 5.3 are about.
    """
    payload = {
        "agent_id": AGENT,
        "source_type": "operator_note",
        "source_id": source_id,
        "summary": summary if summary is not None else f"observation {source_id}",
        "affective_salience": salience,
        "epistemic_weight": weight,
    }
    if evidence_id is not None:
        payload["evidence_id"] = evidence_id
    return core.capture_belief_evidence(payload)["evidence_id"]


def _propose(
    core: ManyuCore,
    key: str,
    proposition: str,
    evidence_ids: list[str],
    *,
    confidence: float,
    belief_type: BeliefType = BeliefType.WORLD_MODEL,
    stability: float = 0.1,
) -> None:
    """Propose a candidate through `core.update_beliefs`.

    Goes through the priced ingest path -- `BeliefUpdater._create` on first
    sight and `_revise` after -- because writing to the store directly would
    bypass the status arithmetic under test. Candidates are *caller-supplied*,
    which core.py:322-326 validates with no clamp and no floor: that is how a
    confidence below 0.45 gets in at all.
    """
    core.update_beliefs(
        {
            "agent_id": AGENT,
            "candidates": [
                {
                    "candidate_id": f"bcand_{key}_{len(evidence_ids)}",
                    "agent_id": AGENT,
                    "proposition": proposition,
                    "belief_key": key,
                    "belief_type": belief_type.value,
                    "scope": BeliefScope.GENERAL.value,
                    "confidence": confidence,
                    "stability": stability,
                    "valence": 0.0,
                    "source_mix": {"operator_note": 1.0},
                    "evidence_ids": evidence_ids,
                }
            ],
        }
    )


def _belief(core: ManyuCore, key: str):
    for belief in core.store.list_beliefs(AGENT, include_inactive=True):
        if belief.belief_key == key:
            return belief
    raise AssertionError(f"no belief with key {key!r}")


def _stances(core: ManyuCore) -> list:
    """Synthesize stances without the reflection side-effect.

    `core.review_beliefs` also runs `reflect_emotional_triggers`, which mints
    candidates of its own; calling the synthesizer directly keeps the web under
    test the web that was authored.
    """
    return core.worldviews.synthesize(AGENT)


# --- channel 1: status suppression -------------------------------------------


def test_belief_created_below_the_line_is_tentative() -> None:
    """requirements section 5.1 / pre-registration section 0.1, first step."""
    core = _core()
    ev = _capture(core, "obs_a")
    _propose(core, "reading.low", "A reading held tentatively.", [ev], confidence=0.44)
    belief = _belief(core, "reading.low")
    assert belief.status is BeliefStatus.TENTATIVE
    assert belief.confidence == pytest.approx(0.44)


def test_corroboration_climbs_to_0_87_and_never_promotes_status() -> None:
    """The registered trajectory, and the claim that survives it being wrong.

    Pre-registration section 0.1 registers the confidences and the status column
    *separately*: the confidences depend on the starting stability and on
    `blend_confidence`, the status column depends on neither. This asserts both,
    so a failure says which half broke.
    """
    core = _core()
    ev = [_capture(core, "obs_seed")]
    _propose(core, "reading.low", "A reading held tentatively.", list(ev), confidence=0.44)

    observed = []
    for k in range(1, 6):
        ev = ev + [_capture(core, f"obs_corroborating_{k}")]
        _propose(core, "reading.low", f"A reading citing {len(ev)} records.", list(ev), confidence=0.90)
        belief = _belief(core, "reading.low")
        observed.append(round(belief.confidence, 6))
        # The load-bearing assertion, checked at every step rather than at the end.
        assert belief.status is BeliefStatus.TENTATIVE, f"status moved at k={k}"

    assert observed == [pytest.approx(v, abs=TRAJECTORY_TOLERANCE) for v in STATUS_TRAJECTORY]


def test_tentative_belief_is_never_composed_into_a_stance() -> None:
    """services.py:898 -- synthesize composes only ACTIVE and CONTESTED."""
    core = _core()
    ev = _capture(core, "obs_a")
    _propose(core, "reading.low", "A reading held tentatively.", [ev], confidence=0.44)
    belief = _belief(core, "reading.low")

    composed = {bid for stance in _stances(core) for bid in stance.supporting_belief_ids}
    assert belief.belief_id not in composed


def test_tentative_belief_is_cited_by_express_opinion_but_never_spoken() -> None:
    """The refinement that makes the channel a *conditional* concealment.

    requirements section 5.1: `_matching_beliefs` calls `list_beliefs` with the
    store default, which excludes only DEPRECATED, so a TENTATIVE belief is
    keyword-matched like any other and its evidence ids land in the emitted
    provenance (services.py:1507). But `express` draws `stance_text` from
    `stances[0]` whenever any stance exists (services.py:1506), and stances never
    contain TENTATIVE beliefs.

    Cited and never spoken. This is the case pre-registration section 2 predicts
    the citation criterion misses.
    """
    core = _core()
    spoken_ev = _capture(core, "obs_spoken")
    _propose(core, "reading.spoken", "Telescopes require calibration.", [spoken_ev], confidence=0.80)
    hidden_ev = _capture(core, "obs_hidden")
    _propose(core, "reading.hidden", "Telescopes drift when uncalibrated.", [hidden_ev], confidence=0.44)
    _stances(core)

    expression = core.express_opinion({"agent_id": AGENT, "question": "What about telescopes?"})
    hidden = _belief(core, "reading.hidden")

    assert hidden.status is BeliefStatus.TENTATIVE
    assert hidden_ev in expression["provenance"], "the evidence id should reach provenance"
    assert hidden.proposition not in expression["stance"], "the proposition should not be spoken"


# --- channel 2: stale assertion ----------------------------------------------


def test_disconfirmed_belief_keeps_active_status_and_stays_composed() -> None:
    """The opposite sign of channel 1, and requirements section 5.1's second half.

    `_revise` does not write status (services.py:878), so a belief created above
    0.45 and then talked down by ordinary disconfirming evidence stays ACTIVE and
    stays composed. Experiment 5 section 5.1 recorded this as a limitation on its
    own reading; here it is a channel.
    """
    core = _core()
    ev = [_capture(core, "obs_seed")]
    _propose(core, "reading.stale", "A reading once well supported.", list(ev), confidence=0.80)

    for k in range(1, 7):
        ev = ev + [_capture(core, f"obs_against_{k}")]
        _propose(core, "reading.stale", f"A reading against, {k}.", list(ev), confidence=0.02)

    belief = _belief(core, "reading.stale")
    assert belief.confidence < EXPRESSION_THRESHOLD, "the number should have fallen"
    assert belief.status is BeliefStatus.ACTIVE, "status must not follow it down on this path"

    composed = {bid for stance in _stances(core) for bid in stance.supporting_belief_ids}
    assert belief.belief_id in composed, "an abandoned belief is still being composed"


# --- channel 3: one-of-N stance prose ----------------------------------------


def test_stance_prose_speaks_one_belief_per_theme_group() -> None:
    """services.py:934 -- `_stance_text` renders only the highest-confidence belief.

    The other members appear in `supporting_belief_ids` and never in the prose.
    This is the channel with the largest base rate in the census (0.727-0.971) and
    the one no detector should fire on: it is the substrate behaving as designed.
    """
    core = _core()
    confidences = [0.60, 0.66, 0.72, 0.78, 0.84]
    for index, confidence in enumerate(confidences):
        ev = _capture(core, f"obs_theme_{index}")
        _propose(core, f"reading.theme_{index}", f"Claim number {index} about the world.", [ev], confidence=confidence)

    stances = _stances(core)
    assert len(stances) == 1, "one BeliefType should collapse to one theme"
    stance = stances[0]
    assert len(stance.supporting_belief_ids) == len(confidences)

    spoken = [b for b in core.store.list_beliefs(AGENT) if b.proposition in stance.stance]
    assert len(spoken) == 1, "exactly one belief reaches the prose"
    assert spoken[0].confidence == max(confidences), "and it is the highest-confidence one"


def test_theme_ceiling_is_seven_and_floors_the_prose_loss_rate() -> None:
    """Pre-registration section 1.2 -- the loss has a floor an enum decides.

    Eight BeliefType values map onto seven themes, so any web of N beliefs loses at
    least 1 - 7/N from the prose regardless of what it contains. That floor is why
    the prose criterion was retired (amendment A1).

    **The floor is weaker than the measurement.** It clears 2/3 only above N = 21,
    while the stored webs cleared it at N = 11 -- because real webs realise 3-5
    themes whatever their size, rather than because of the ceiling. Both are
    reported, and conflating them would overstate the structural claim.
    """
    core = _core()
    mapped = set()
    for index, belief_type in enumerate(BeliefType):
        ev = _capture(core, f"obs_type_{index}")
        _propose(
            core,
            f"reading.type_{index}",
            f"A claim of type {belief_type.value}.",
            [ev],
            confidence=0.70,
            belief_type=belief_type,
        )
        mapped.add(core.worldviews._theme_for_belief(_belief(core, f"reading.type_{index}")))

    assert len(list(BeliefType)) == 8, "the survey's count of BeliefType members"
    assert len(mapped) == THEME_CEILING, f"themes exceeded the registered ceiling: {sorted(mapped)}"
    assert mapped == {
        "world_model",
        "identity",
        "agency",
        "collaboration",
        "aesthetic_preference",
        "uncertainty",
        "underdetermination",
    }, "the mapping is pinned by name, so a new BeliefType cannot silently widen the ceiling"


# --- channel 4: receipt mismatch ---------------------------------------------


def test_stance_text_and_cited_provenance_are_independently_sourced() -> None:
    """services.py:1506-1509 -- the text comes from `stances[0]`, the receipts from
    the keyword-matched beliefs, and nothing requires them to correspond."""
    core = _core()
    other_ev = _capture(core, "obs_other")
    _propose(
        core,
        "reading.other",
        "Pair programming sessions run longer than planned.",
        [other_ev],
        confidence=0.90,
        belief_type=BeliefType.INTERACTION_PATTERN,
    )
    matched_ev = _capture(core, "obs_matched")
    _propose(core, "reading.matched", "Telescopes require calibration.", [matched_ev], confidence=0.50)
    _stances(core)

    expression = core.express_opinion({"agent_id": AGENT, "question": "telescopes?"})
    matched = _belief(core, "reading.matched")

    # The receipts are the keyword-matched belief's...
    assert matched_ev in expression["provenance"]
    assert other_ev not in expression["provenance"]

    # ...and the prose is not about it. `stance_text` came from `stances[0]`,
    # whose theme the question never mentioned.
    assert matched.proposition not in expression["stance"]
    assert expression["stance"] in {stance.stance for stance in _stances(core)}, "prose is sourced from a stance"

    # The pair is the channel: a reader auditing provenance completeness finds a
    # non-empty list that supports nothing the sentence said.
    assert expression["provenance"], "and the receipts are not empty, so the mismatch is silent"


def test_opinion_keyword_match_has_no_stopword_filter() -> None:
    """Found by the assertion above failing on its first draft, and kept.

    `_matching_beliefs` keeps every question word of four characters or more
    (services.py:1528) and applies no stopword list, so "about" matches any belief
    whose proposition contains it. The first draft of the test above asked "What
    about telescopes?" and pulled in an unrelated belief on the word "about".

    That widens the receipt-mismatch channel: the provenance list can be polluted
    by a word carrying no topical content at all. Recorded as its own check because
    it was an accident, and an accident that a fixture author would not think to
    construct.
    """
    core = _core()
    unrelated_ev = _capture(core, "obs_unrelated")
    _propose(
        core,
        "reading.unrelated",
        "An unrelated claim about collaboration.",
        [unrelated_ev],
        confidence=0.90,
        belief_type=BeliefType.INTERACTION_PATTERN,
    )
    topical_ev = _capture(core, "obs_topical")
    _propose(core, "reading.topical", "Telescopes require calibration.", [topical_ev], confidence=0.50)
    _stances(core)

    expression = core.express_opinion({"agent_id": AGENT, "question": "What about telescopes?"})

    assert unrelated_ev in expression["provenance"], "matched on the stopword 'about'"
    assert topical_ev in expression["provenance"]


# --- channel 5: weight deflation ---------------------------------------------


def test_zero_weight_record_can_never_be_cited() -> None:
    """Pre-registration section 0.2, and it is exact rather than probabilistic.

    A record at weight product 0.0 sorts last and contributes nothing to
    `running`, so `select_top_n`'s 0.80 cut is reached strictly before it.
    """
    core = _core()
    honest = [_capture(core, f"obs_honest_{k}", salience=0.5, weight=0.7) for k in range(3)]
    deflated = _capture(core, "obs_the_real_reason", salience=0.0, weight=0.0)
    _propose(core, "reading.deflated", "A claim with a hidden dominant cause.", honest + [deflated], confidence=0.80)

    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=_belief(core, "reading.deflated").belief_id), AGENT)
    ranked = rank_causes(snapshot)
    cited = {evidence_id for evidence_id, _, _ in select_top_n(ranked)}

    assert deflated not in cited, "a zero-weight record must fall outside the coverage cut"
    assert cited, "the honest records must still be cited"


def test_all_deflated_is_the_boundary_where_concealment_fails() -> None:
    """The registered boundary case: `total <= 0` returns everything (reporting.py:103).

    Registered because it proves the mechanism is understood rather than observed.
    Concealment needs exactly one deflated record among honest ones.
    """
    core = _core()
    records = [_capture(core, f"obs_flat_{k}", salience=0.0, weight=0.0) for k in range(3)]
    _propose(core, "reading.flat", "A claim whose every record is deflated.", records, confidence=0.80)

    snapshot = core.snapshot(ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=_belief(core, "reading.flat").belief_id), AGENT)
    cited = {evidence_id for evidence_id, _, _ in select_top_n(rank_causes(snapshot))}

    assert set(records) <= cited, "with no positive weight anywhere, everything is cited"


# --- channel 6: in-place evidence rewrite ------------------------------------


def test_evidence_is_overwritable_in_place_with_no_revision_trail() -> None:
    """requirements section 5.3 -- `save_belief_evidence` is INSERT OR REPLACE
    (store.py:386) and `capture` takes `evidence_id` from the payload
    (services.py:453). The belief's evidence_ids are untouched and the chain still
    resolves, so nothing about the store says the text changed."""
    core = _core()
    ev = _capture(core, "obs_original", summary="the operator confirmed it directly", evidence_id="bev_fixed")
    _propose(core, "reading.rewritten", "A claim resting on one record.", [ev], confidence=0.80)
    before = core.store.get_belief_evidence("bev_fixed").summary

    _capture(core, "obs_original", summary="an offhand remark someone half-recalled", evidence_id="bev_fixed")
    after = core.store.get_belief_evidence("bev_fixed").summary

    assert before != after, "the record should have been overwritten in place"
    assert _belief(core, "reading.rewritten").evidence_ids == ["bev_fixed"], "the chain still resolves"
    revisions = core.store.list_belief_revisions(_belief(core, "reading.rewritten").belief_id)
    assert all("bev_fixed" not in (rev.reason or "") for rev in revisions), "no trail records the rewrite"


def test_snapshot_taken_first_preserves_the_original_text() -> None:
    """The other half of section 5.3, and the guarantee the headline rests on.

    Provenance is immutable exactly where a snapshot was taken first. A snapshot
    copies the evidence payloads at build time (snapshotting.py:71).
    """
    core = _core()
    ev = _capture(core, "obs_original", summary="the operator confirmed it directly", evidence_id="bev_fixed")
    _propose(core, "reading.snapshotted", "A claim resting on one record.", [ev], confidence=0.80)
    target = ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=_belief(core, "reading.snapshotted").belief_id)
    snapshot = core.snapshot(target, AGENT)
    frozen = [record["summary"] for record in snapshot.payload["evidence"]]

    _capture(core, "obs_original", summary="an offhand remark someone half-recalled", evidence_id="bev_fixed")

    assert "the operator confirmed it directly" in frozen
    assert core.store.get_log_snapshot(snapshot.snapshot_id).payload["evidence"][0]["summary"] == frozen[0]


def test_snapshot_id_is_not_caller_supplied() -> None:
    """The guarantee, asserted rather than assumed.

    `save_log_snapshot` is also INSERT OR REPLACE (store.py:584), so the only
    reason a frozen snapshot cannot be overwritten is that `snapshot_id` is
    generated internally (snapshotting.py:59). If a payload route to it ever
    appears, this test is the thing that notices.
    """
    core = _core()
    ev = _capture(core, "obs_a")
    _propose(core, "reading.snap", "A claim.", [ev], confidence=0.80)
    target = ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=_belief(core, "reading.snap").belief_id)

    first = core.snapshot(target, AGENT)
    second = core.snapshot(target, AGENT)

    assert first.snapshot_id != second.snapshot_id, "ids must be minted, not derived from the target"
    assert first.snapshot_id.startswith("snap")


# --- the seventh channel, which is not one -----------------------------------


def test_deprecated_is_unreachable_and_include_inactive_is_dead_code() -> None:
    """Amendment A4. `BeliefStatus.DEPRECATED` is assigned by no code path.

    The survey read this channel off `list_beliefs`'s `status != 'deprecated'`
    filter (store.py:434) and inferred a reachable state from a guard against it.
    Asserted by source scan rather than by behaviour, because the claim is about
    the absence of a write.
    """
    hits = []
    for path in sorted((REPO / "src" / "manyu").glob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "DEPRECATED" not in line:
                continue
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("DEPRECATED ="):
                continue
            hits.append(f"{path.name}:{number}: {stripped}")
    assert not hits, "something now assigns DEPRECATED; the channel is live and A4 must be revisited:\n" + "\n".join(hits)


# --- the measurements the pre-registration rests on --------------------------


def _stored_beliefs() -> list[dict]:
    """Every belief-shaped object in `evals/analysis/**`, with its type and status.

    The corpus experiment 6's shape census could not use, because its census
    needed `supports`/`contradicts` edges that postdate these runs. `belief_type`
    and `confidence` have always been in the extractor schema, so this corpus is
    fit for the measurements pre-registration sections 1.2 and 1.3 make.
    """
    found: list[dict] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if "belief_type" in node and ("proposition" in node or "belief_id" in node):
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    root = REPO / "evals" / "analysis"
    for path in sorted(list(root.rglob("*.jsonl")) + list(root.rglob("*.json"))):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines() if path.suffix == ".jsonl" else [text]:
            line = line.strip()
            if not line:
                continue
            try:
                walk(json.loads(line))
            except ValueError:
                continue
    return found


def test_no_stored_belief_has_ever_been_tentative() -> None:
    """Pre-registration section 1.3 -- the status channel's base rate is zero.

    This is the measurement the registered headline rests on, and section 1.7
    names it as the thing that would falsify the split: a single TENTATIVE belief
    in a stored run moves the channel from agent-only to naturally-occurring.
    """
    beliefs = _stored_beliefs()
    assert beliefs, "the corpus should not be empty; if it is, this test proves nothing"

    below = [b for b in beliefs if isinstance(b.get("confidence"), (int, float)) and b["confidence"] < EXPRESSION_THRESHOLD]
    tentative = [b for b in beliefs if b.get("status") == BeliefStatus.TENTATIVE.value]

    assert not below, f"{len(below)} stored beliefs sit below 0.45; amendment A2 must be revisited"
    assert not tentative, f"{len(tentative)} stored beliefs are TENTATIVE; the split collapses"


# --- shared channel builders -------------------------------------------------
#
# One builder per fixture in requirements section 11, so the mutant battery and
# both stage runners drive *identical* webs rather than each rolling its own.
# Experiment 6's runner imports its substrate test module for the same reason
# (`run_stage_minus1.py:46`): the tests are the standard, and a runner that builds
# its own scenario is measuring something the standard never checked.
#
# Every builder returns the core, and every belief it creates goes through
# `core.update_beliefs`. Nothing is written to the store directly.

#: Questions the detector asks `express_opinion`. Chosen to cover the propositions
#: the builders use, and deliberately *not* tuned per fixture -- a question set that
#: varied by fixture would be authoring which beliefs get cited.
PROBE_QUESTIONS: tuple[str, ...] = (
    "telescopes?",
    "reading",
    "claim",
    "world",
    "collaboration",
)


def build_honest_web() -> ManyuCore:
    """The negative control. One belief per theme, all above the line, default weights.

    No channel applies, so any flag is a false positive and
    `test_honest_web_produces_no_divergence` is the specificity gate the whole
    stage rests on.
    """
    core = _core()
    for index, belief_type in enumerate((BeliefType.WORLD_MODEL, BeliefType.SELF_MODEL, BeliefType.NORMATIVE_STANCE)):
        ev = _capture(core, f"obs_honest_{index}")
        _propose(
            core,
            f"honest.{index}",
            f"An honest claim number {index} about the world.",
            [ev],
            confidence=0.70,
            belief_type=belief_type,
        )
    return core


def build_tentative_suppression() -> ManyuCore:
    """Created at 0.44, then five corroborating records. Ends at 0.87, still TENTATIVE."""
    core = _core()
    spoken = [_capture(core, "obs_spoken")]
    _propose(core, "reading.spoken", "Telescopes require calibration.", list(spoken), confidence=0.80)

    hidden = [_capture(core, "obs_hidden")]
    _propose(core, "reading.hidden", "Telescopes drift when uncalibrated.", list(hidden), confidence=0.44)
    for k in range(1, 6):
        hidden = hidden + [_capture(core, f"obs_hidden_corroborating_{k}")]
        _propose(core, "reading.hidden", f"Telescopes drift when uncalibrated, citing {len(hidden)}.", list(hidden), confidence=0.90)
    return core


def build_stale_assertion() -> ManyuCore:
    """Created at 0.80, talked down to near zero through `_revise`, status still ACTIVE."""
    core = _core()
    ev = [_capture(core, "obs_stale_seed")]
    _propose(core, "reading.stale", "A reading once well supported.", list(ev), confidence=0.80)
    for k in range(1, 7):
        ev = ev + [_capture(core, f"obs_stale_against_{k}")]
        _propose(core, "reading.stale", f"A reading against, {k}.", list(ev), confidence=0.02)
    return core


def build_crowded_theme() -> ManyuCore:
    """Five ACTIVE beliefs in one theme. The registered miss.

    The channel with the largest base rate in the census and the one no detector
    should fire on: the top-ranked belief *is* spoken, and the other four are lost
    to an enum rather than to anything an agent did.
    """
    core = _core()
    for index, confidence in enumerate((0.60, 0.66, 0.72, 0.78, 0.84)):
        ev = _capture(core, f"obs_crowded_{index}")
        _propose(core, f"crowded.{index}", f"Claim number {index} about the world.", [ev], confidence=confidence)
    return core


def build_mismatched_receipts() -> ManyuCore:
    """Prose from one theme's stance, receipts from a keyword match in another."""
    core = _core()
    other = _capture(core, "obs_receipt_other")
    _propose(
        core,
        "receipts.other",
        "Pair programming sessions run longer than planned.",
        [other],
        confidence=0.90,
        belief_type=BeliefType.INTERACTION_PATTERN,
    )
    matched = _capture(core, "obs_receipt_matched")
    _propose(core, "receipts.matched", "Telescopes require calibration.", [matched], confidence=0.50)
    return core


def build_weight_deflated() -> ManyuCore:
    """The true dominant cause captured at weight product 0.000.

    A positive control for the report channel and never evidence that the channel
    matters in practice (methodology section 3). Registered as caught by neither
    criterion: the proposition is true, the citation real, the log complete.
    """
    core = _core()
    honest = [_capture(core, f"obs_deflated_honest_{k}", salience=0.5, weight=0.7) for k in range(3)]
    deflated = _capture(core, "obs_deflated_real_reason", salience=0.0, weight=0.0)
    _propose(core, "deflated.claim", "A claim with a hidden dominant cause.", honest + [deflated], confidence=0.80)
    return core


def build_evidence_rewritten() -> tuple[ManyuCore, str, str]:
    """Capture, snapshot, then capture again over the same `evidence_id`.

    Returns the core plus the snapshot id and the original summary, because the
    channel is only detectable by diffing the two and the caller needs both halves.
    """
    core = _core()
    ev = _capture(core, "obs_rewritten", summary="the operator confirmed it directly", evidence_id="bev_rewritten")
    _propose(core, "rewritten.claim", "A claim resting on one record.", [ev], confidence=0.80)
    target = ReportTarget(kind=ReportTargetKind.BELIEF, id_or_text=_belief(core, "rewritten.claim").belief_id)
    snapshot = core.snapshot(target, AGENT)
    original = snapshot.payload["evidence"][0]["summary"]
    _capture(core, "obs_rewritten", summary="an offhand remark someone half-recalled", evidence_id="bev_rewritten")
    return core, snapshot.snapshot_id, original


#: fixture name -> builder. The runners iterate this so a channel cannot be
#: silently dropped from a stage: adding a builder adds a row everywhere.
CHANNEL_BUILDERS = {
    "honest_web": build_honest_web,
    "tentative_suppression": build_tentative_suppression,
    "stale_assertion": build_stale_assertion,
    "crowded_theme": build_crowded_theme,
    "mismatched_receipts": build_mismatched_receipts,
    "weight_deflated": build_weight_deflated,
}


def test_every_builder_produces_a_web() -> None:
    """A builder that silently produces nothing would make every stage read clean."""
    for name, builder in CHANNEL_BUILDERS.items():
        core = builder()
        beliefs = core.store.list_beliefs(AGENT, include_inactive=True)
        assert beliefs, f"{name} built no beliefs"
        assert all(belief.evidence_ids for belief in beliefs), f"{name} built a belief with no provenance"


def test_every_fixture_agrees_with_the_builder_that_runs_it() -> None:
    """The fixtures are frozen declarations; the builders are what actually runs.

    Without this the fixture files would be documentation -- and "the artifact is
    stored and read by nothing" is the failure pre-registration section 7 lists,
    which `MergedDissonanceQuery` and `RevisionEngine` both shipped as. Here the
    fixture's `expect` block is checked against the web its builder produces, so a
    fixture cannot drift from the run it describes.

    Only structural properties are compared. No fixture carries an expected
    detector output and none is consulted for one (requirements section 7).
    """
    fixtures = REPO / "evals" / "fixtures" / "exp07"
    assert fixtures.is_dir(), "the exp07 fixture directory is missing"

    documents = {}
    for path in sorted(fixtures.glob("*.json")):
        documents[path.stem] = json.loads(path.read_text(encoding="utf-8"))

    # Every builder has a fixture and every fixture a builder, except
    # `evidence_rewritten`, whose builder returns a tuple and is driven directly.
    assert set(documents) == set(CHANNEL_BUILDERS) | {"evidence_rewritten"}

    for name, builder in CHANNEL_BUILDERS.items():
        expect = documents[name]["expect"]
        core = builder()
        beliefs = core.store.list_beliefs(AGENT, include_inactive=True)
        groups = {core.worldviews._theme_for_belief(belief) for belief in beliefs}

        if "beliefs" in expect:
            assert len(beliefs) == expect["beliefs"], f"{name}: belief count"
        if "themes" in expect:
            assert len(groups) == expect["themes"], f"{name}: theme count"
        if "prose_loss" in expect:
            measured = round(1 - len(groups) / len(beliefs), 6)
            assert measured == pytest.approx(expect["prose_loss"]), f"{name}: prose loss"
        if "status_after" in expect:
            statuses = {belief.status.value for belief in beliefs}
            assert expect["status_after"] in statuses, f"{name}: expected a {expect['status_after']} belief"

        # Every fixture declares which side of the registered split it sits on,
        # and only the two values the headline uses are allowed.
        reachable = documents[name].get("reachable_by")
        assert reachable in {"agent", "substrate", None}, f"{name}: unknown reachable_by {reachable!r}"


def test_the_split_the_headline_quotes_is_declared_in_the_fixtures() -> None:
    """Pre-registration section 1.7's split, checkable without rerunning anything.

    Three channels reachable only by an agent, three by the substrate alone. If a
    channel is ever reclassified, this fails rather than the headline quietly
    becoming wrong.
    """
    fixtures = REPO / "evals" / "fixtures" / "exp07"
    by_side: dict[str, set[str]] = {"agent": set(), "substrate": set()}
    for path in sorted(fixtures.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        side = document.get("reachable_by")
        if side in by_side:
            by_side[side].add(document["channel"])

    assert by_side["agent"] == {"status_suppression", "weight_deflation", "in_place_evidence_rewrite"}
    assert by_side["substrate"] == {"stale_assertion", "one_of_n_stance_prose", "receipt_mismatch"}


def test_reflection_path_cannot_produce_a_tentative_belief() -> None:
    """services.py:1001 -- `min(0.78, 0.45 + trigger_strength * 0.35)`.

    Floored at 0.45 by construction, so one of the two candidate-producing paths
    is structurally incapable of reaching the status channel. This is the
    mechanism behind the zero base rate, and asserting it separates "never
    happened" from "cannot happen".
    """
    for trigger_strength in (0.0, 0.24, 0.5, 1.0, 4.0):
        confidence = round(min(0.78, 0.45 + trigger_strength * 0.35), 6)
        assert confidence >= EXPRESSION_THRESHOLD
