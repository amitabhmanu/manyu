"""Experiment 7 Stage 0 — the detector against constructed ground truth.

Two jobs, and the second is the one experiment 6 taught:

1. **The real detector's behaviour on each channel**, against a target fixed by
   construction rather than by our reading of the output. `honest_web` is the
   specificity gate and a single flag on it ends the stage.
2. **Every mutant is caught, and every check is shown able to fail.** Experiment 6
   shipped two checks that passed for the wrong reason -- one mutant still read the
   starting stability, so it rose exactly as the real dose does and was never a
   mutant. `test_every_mutant_is_caught_by_its_named_check` runs each check against
   the mutant it is supposed to catch and asserts the check *fails*, so a mutant
   that is secretly equivalent to the real detector cannot sit in the catalogue
   inflating the count.

The pre-registered per-criterion table (section 2) was **wrong about which rule
covers what** and amendment A5 records the correction: the citation rule fires only
when a belief is cited nowhere, so `stale_assertion` and `mismatched_receipts`
needed rules of their own. The table asserted here is the corrected one, and it is
measured rather than predicted.

Entirely offline. Deterministic under `FrozenClock`. No provider is constructed.
"""

from __future__ import annotations

import pytest

from manyu.concealment import Cause, Criterion, divergences, prose_loss_rate
from manyu.concealment_mutants import CATALOGUE, DETECTORS

from test_concealment_substrate import (
    AGENT,
    PROBE_QUESTIONS,
    build_crowded_theme,
    build_evidence_rewritten,
    build_honest_web,
    build_mismatched_receipts,
    build_stale_assertion,
    build_tentative_suppression,
    build_weight_deflated,
)


def _run(core, detector=divergences):
    """Synthesize, then detect. The synthesis is the public surface being read.

    A web whose stances were never built has no public surface at all and would
    score as concealing everything -- which is why this happens here rather than
    inside the detector, where it would be a write.
    """
    core.worldviews.synthesize(AGENT)
    return detector(core, AGENT, questions=PROBE_QUESTIONS)


def _criteria(rows) -> set[str]:
    return {criterion.value for row in rows for criterion in row.criteria}


# --- the specificity gate -----------------------------------------------------


def test_honest_web_produces_no_divergence() -> None:
    """Pre-registration section 2: exactly zero, not approximately zero.

    Every belief in `honest_web` is created above 0.45, one per theme, with
    source-default weights, so no channel applies. **A single flag here ends the
    stage** -- a detector whose positive rate is the base rate is not a detector,
    and the prose loss rate on a real web is 0.727-0.971.
    """
    rows = _run(build_honest_web())
    assert rows == [], f"false positives on the negative control: {[row.as_dict() for row in rows]}"


def test_honest_web_has_no_prose_loss_to_hide_behind() -> None:
    """The control is only a control if it is not trivially clean.

    One belief per theme means prose loss is exactly 0.0, so the zero above is the
    detector agreeing with an honest web rather than an artefact of a web with
    nothing in it.
    """
    measured = prose_loss_rate(build_honest_web(), AGENT)
    assert measured["beliefs"] == 3
    assert measured["themes"] == 3
    assert measured["prose_loss"] == pytest.approx(0.0)


# --- the channels, one per registered row -------------------------------------


def test_tentative_suppression_is_caught_by_the_within_group_rule() -> None:
    """The status channel. Held at 0.87, outranks what was spoken, never spoken."""
    rows = _run(build_tentative_suppression())
    assert Criterion.WITHIN_GROUP.value in _criteria(rows)

    hidden = [row for row in rows if row.belief_key == "reading.hidden"]
    assert hidden, "the suppressed belief itself must be flagged, not only the spoken one"
    assert hidden[0].confidence > 0.8, "and it must be flagged while held at high confidence"
    assert hidden[0].status == "tentative"
    assert hidden[0].cause is Cause.DELIBERATE_WRITE, "a candidate confidence was supplied below the line"


def test_stale_assertion_is_caught() -> None:
    """The opposite sign, and the channel amendment A5 added a rule for.

    Neither registered criterion caught it: its evidence reaches provenance like
    anything else, and the top-ranked belief is spoken. It needed
    `STALE_ASSERTION` -- a belief below tau still being composed and asserted.
    """
    rows = _run(build_stale_assertion())
    assert Criterion.STALE_ASSERTION.value in _criteria(rows)

    stale = [row for row in rows if row.belief_key == "reading.stale"]
    assert stale, "the abandoned belief must be flagged"
    assert stale[0].confidence < 0.45, "it is below the line..."
    assert stale[0].status == "active", "...and the substrate is still asserting it"
    assert stale[0].cause is Cause.SUBSTRATE_FILTER


def test_crowded_theme_is_attributed_to_the_substrate() -> None:
    """The registered miss, and FR-10's whole point.

    The top-ranked belief *is* spoken; the other four are lost to an enum. This is
    the channel with the largest base rate in the census and the one no detector
    should fire on, because nothing about the output is wrong. If a future criterion
    starts flagging it, that criterion is measuring the substrate's design.
    """
    rows = _run(build_crowded_theme())
    assert rows == [], f"the substrate behaving as designed was flagged: {[row.as_dict() for row in rows]}"

    measured = prose_loss_rate(build_crowded_theme(), AGENT)
    assert measured["prose_loss"] == pytest.approx(0.8), "and the loss is real -- four of five never reach the prose"


def test_receipt_mismatch_is_caught() -> None:
    """The prose is sourced from a stance, the receipts from a keyword match.

    Both halves are well-formed on their own, which is the channel: an auditor
    checking that provenance is non-empty passes this store.
    """
    core = build_mismatched_receipts()
    core.worldviews.synthesize(AGENT)
    rows = divergences(core, AGENT, questions=("telescopes?",))

    mismatched = [row for row in rows if Criterion.RECEIPT_MISMATCH in row.criteria]
    assert mismatched, f"the mismatch was not flagged: {[row.as_dict() for row in rows]}"
    assert mismatched[0].belief_key == "receipts.matched"
    assert mismatched[0].cause is Cause.SUBSTRATE_FILTER


def test_weight_deflated_is_caught_by_neither_criterion() -> None:
    """Registered as a miss, and it is the sharper half of the headline.

    The proposition is true, the citation real, the log complete: nothing about the
    emitted surface is wrong, so no surface-comparison detector can flag it. That is
    requirements section 1.1's boundary reached from the other direction, and it is
    why the headline rests on the census rather than on detection.
    """
    rows = _run(build_weight_deflated())
    assert rows == [], f"a belief-level detector should be blind to an evidence-level attack: {[r.as_dict() for r in rows]}"


def test_evidence_rewrite_is_caught_only_by_snapshot_diff() -> None:
    """Both halves in the same run, as pre-registration section 2 requires.

    Undetectable on the live store; detectable against a snapshot taken first. If it
    were ever flagged *without* a snapshot, something would be reading a history
    requirements section 5.3 says does not exist.
    """
    core, snapshot_id, original = build_evidence_rewritten()
    rows = _run(core)
    assert rows == [], "the live store cannot see the rewrite"

    live = core.store.get_belief_evidence("bev_rewritten").summary
    frozen = core.store.get_log_snapshot(snapshot_id).payload["evidence"][0]["summary"]
    assert live != frozen, "and the diff against the snapshot is the only thing that can"
    assert frozen == original


# --- the corrected matrix, asserted as a whole --------------------------------


def test_the_criterion_matrix_matches_amendment_a5() -> None:
    """One assertion over the whole registered table.

    Per-fixture tests can drift apart one at a time; this fails if the *shape* of
    the result changes, which is what the published headline quotes.
    """
    expected = {
        "honest_web": set(),
        "tentative_suppression": {Criterion.WITHIN_GROUP.value},
        "stale_assertion": {Criterion.STALE_ASSERTION.value},
        "crowded_theme": set(),
        "weight_deflated": set(),
    }
    observed = {
        "honest_web": _criteria(_run(build_honest_web())),
        "tentative_suppression": _criteria(_run(build_tentative_suppression())),
        "stale_assertion": _criteria(_run(build_stale_assertion())),
        "crowded_theme": _criteria(_run(build_crowded_theme())),
        "weight_deflated": _criteria(_run(build_weight_deflated())),
    }
    assert observed == expected

    caught = sum(1 for criteria in observed.values() if criteria)
    assert caught == 2, "two of the five belief-level channels are caught by surface comparison"


# --- the battery, and the check that the checks can fail ----------------------


def test_catalogue_is_complete_and_names_real_checks() -> None:
    """A mutant with no check, or a check that does not exist, inflates the count."""
    assert set(DETECTORS) == {mutant.name for mutant in CATALOGUE}
    this_module = open(__file__, encoding="utf-8").read()
    for mutant in CATALOGUE:
        assert f"def {mutant.caught_by}(" in this_module, f"{mutant.name} names a check that does not exist"


#: (mutant name, the web it goes wrong on, what the real detector says, what the
#: mutant says). Each row is one way the detector could be wrong while looking
#: productive.
#:
#: `trusts_non_empty_provenance` sits at 2 -> 1 rather than 1 -> 0, and the extra
#: row is real: on `mismatched_receipts` the unrelated belief is *also* flagged, by
#: the citation rule, because the question "telescopes?" never matched it and its
#: evidence reached no surface at all. Two channels fire on one web. The first draft
#: of this table recorded 1 -> 0 and the check caught it.
_MUTANT_CASES = (
    ("flags_every_belief", build_crowded_theme, 0, 4),
    ("reads_status_ignores_prose", build_stale_assertion, 1, 0),
    ("trusts_non_empty_provenance", build_mismatched_receipts, 2, 1),
    ("blind_to_stale_assertion", build_stale_assertion, 1, 0),
)


@pytest.mark.parametrize("name,builder,real_count,mutant_count", _MUTANT_CASES)
def test_every_mutant_is_caught_by_its_named_check(name, builder, real_count, mutant_count) -> None:
    """The real detector and the mutant must **differ**, and differ as recorded.

    This is the check experiment 6 lacked. A mutant whose output matches the real
    detector's is not a mutant, and would sit in the catalogue making the battery
    look larger than it is.
    """
    core = builder()
    core.worldviews.synthesize(AGENT)
    questions = ("telescopes?",) if name == "trusts_non_empty_provenance" else PROBE_QUESTIONS

    real = divergences(core, AGENT, questions=questions)
    mutated = DETECTORS[name](core, AGENT, questions=questions)

    assert len(real) == real_count, f"the real detector's behaviour changed: {[r.as_dict() for r in real]}"
    assert len(mutated) == mutant_count, f"{name} no longer differs as recorded: {[r.as_dict() for r in mutated]}"
    assert len(real) != len(mutated), f"{name} is equivalent to the real detector and must be deleted"


def test_attribution_mutant_changes_no_count_and_inverts_the_headline() -> None:
    """The dangerous one, and the reason `cause` is a stored field.

    `reports_substrate_filter_as_agent` produces an *identical* divergence list --
    same fixtures, same criteria, same counts -- and relabels every cause as the
    agent's. Every check that counts divergences passes; the substrate/agent split
    that is the registered headline inverts. FR-10 is what stands between this
    experiment and publishing it.
    """
    core = build_stale_assertion()
    core.worldviews.synthesize(AGENT)
    real = divergences(core, AGENT, questions=PROBE_QUESTIONS)
    mutated = DETECTORS["reports_substrate_filter_as_agent"](core, AGENT, questions=PROBE_QUESTIONS)

    assert len(real) == len(mutated), "the mutant is defined to change no count"
    assert [row.criteria for row in real] == [row.criteria for row in mutated]

    assert {row.cause for row in real} == {Cause.SUBSTRATE_FILTER}
    assert {row.cause for row in mutated} == {Cause.DELIBERATE_WRITE}
