"""The Stage 4 D2 helpers that decide what a paid run measures.

`classify_merged` turns a belief window into the M-class the §8.1 rule reads,
and `decide` turns the M-classes plus effect sizes into a verdict. Both run on
live, model-built webs, so they are tested rather than trusted.

The first test is the one that matters most: experiment 3 shipped a mechanism
that was stored, stamped onto every result, and consulted by no branch, so
everything reported "under both arms" was one arm run twice. A classifier whose
winning branch is unreachable would do the same thing here — and an M-a result
from an unreachable M-c is not a finding about merged, it is a broken
instrument. So every class is asserted reachable before any of them is read.

Offline; the runner's provider is never constructed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from manyu.architecture import Arch
from manyu.services import BeliefExtractor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "analysis" / "exp02"))
from run_d2_verdict import (  # noqa: E402
    MClass,
    bootstrap_ci,
    build_core,
    classify_merged,
    classify_merged_strict,
    cohens_d,
    decide,
    describe_carriers,
    drop_one,
)


def _carrier(**overrides) -> dict:
    base = {
        "belief_id": "bel_1",
        "belief_key": "uncertainty/local_context/ambiguous-queries",
        "belief_type": "uncertainty",
        "proposition": "Manyu's recent queries have returned no rows and no error.",
        "valence": -0.3,
        "confidence": 0.7,
        "evidence_ids": ["bev_1"],
        "evidence_resolved": 1,
        "unsupported_threat_terms": [],
        "instance_reference": None,
        "generalises": True,
    }
    base.update(overrides)
    return base


def _classify(**kwargs) -> tuple[str | None, list[str]]:
    params = {
        "arch": Arch.MERGED,
        "affect": 0.3,
        "window_belief_count": 4,
        "provider_errors": 0,
        "carriers": [_carrier()],
    }
    params.update(kwargs)
    return classify_merged(**params)


# --- gate #5: every class the rule reads must be reachable --------------------


def test_every_m_class_is_reachable():
    """If a branch cannot fire, a run that never lands on it says nothing."""
    reached = {
        _classify(provider_errors=2)[0],
        _classify(window_belief_count=0)[0],
        _classify(affect=0.0, carriers=[])[0],
        _classify(carriers=[_carrier(unsupported_threat_terms=["destroy"])])[0],
        _classify()[0],
        _classify(carriers=[_carrier(generalises=False, instance_reference="Check 19")])[0],
    }
    assert reached == {MClass.M0, MClass.MA, MClass.MB, MClass.MC, MClass.UNDECIDED}


def test_m_c_is_a_property_test_not_a_type_test():
    """Methodology §4.6. The pilot's real carrier was `epistemic_principle`,
    and gating on the type tag would have decided D2 on a spelling.
    """
    carrier = _carrier(
        belief_type="epistemic_principle",
        proposition="Tool outcomes that return no rows with no error signal are ambiguous without explicit scope documentation.",
    )
    assert _classify(carriers=[carrier])[0] == MClass.MC
    assert classify_merged_strict(arch=Arch.MERGED, affect=0.3, window_belief_count=4, provider_errors=0, carriers=[carrier]) == MClass.UNDECIDED


def test_a_carrier_about_one_occurrence_is_not_m_c():
    """"Check 19 reported..." is a belief about Check 19, not about the
    epistemic situation — the distinction M-c rests on.
    """
    carrier = _carrier(proposition="Migration check (Check 19) reported dropped rows.", generalises=False, instance_reference="Check 19")
    assert _classify(carriers=[carrier])[0] == MClass.UNDECIDED


def test_the_strict_reading_is_recorded_for_every_class():
    """Both readings must be available on the record, or the amendment is
    unauditable from the artifacts alone.
    """
    for kwargs in ({"provider_errors": 1}, {"window_belief_count": 0}, {"affect": 0.0, "carriers": []},
                   {"carriers": [_carrier(unsupported_threat_terms=["destroy"])]}, {}):
        params = {"arch": Arch.MERGED, "affect": 0.3, "window_belief_count": 4, "provider_errors": 0, "carriers": [_carrier()]}
        params.update(kwargs)
        assert classify_merged_strict(**params) is not None


def test_provider_error_is_m0_not_ma():
    """Experiment 1 lost a finding to failed calls scored as a behavioural result.

    M-a is a *loss condition* for merged, so a failed extraction must never
    reach it — the two are structurally identical from the outside and only
    this branch keeps them apart.
    """
    assert _classify(provider_errors=1, affect=0.0, carriers=[])[0] == MClass.M0


def test_empty_window_is_m0_not_ma():
    assert _classify(window_belief_count=0, affect=0.0, carriers=[])[0] == MClass.M0


def test_fabricated_threat_outranks_an_uncertainty_carrier():
    """M-b is the worse outcome; a real carrier alongside it must not mask it."""
    m_class, notes = _classify(carriers=[_carrier(), _carrier(belief_id="bel_2", unsupported_threat_terms=["unrecoverable"])])
    assert m_class == MClass.MB
    assert any("unrecoverable" in note for note in notes)


def test_uncertainty_carrier_without_resolved_evidence_is_not_mc():
    """M-c requires provenance tracing to real events, not just the right type."""
    assert _classify(carriers=[_carrier(evidence_resolved=0)])[0] == MClass.UNDECIDED


def test_split_runs_are_not_m_classified():
    assert classify_merged(arch=Arch.SPLIT, affect=0.9, window_belief_count=8, provider_errors=0, carriers=[]) == (None, [])


# --- the threat test reads the run's own events, not a fixed word list --------


class _Belief:
    def __init__(self, proposition: str, valence: float, belief_type: str = "world_model"):
        self.belief_id = "bel_x"
        self.belief_key = "k"
        self.belief_type = belief_type
        self.proposition = proposition
        self.valence = valence
        self.confidence = 0.7
        self.evidence_ids = []


def test_a_threat_the_events_stated_is_not_a_fabrication():
    """The `control` condition really does say the migration destroys records.

    A carrier echoing it is merged working correctly, and calling that M-b
    would turn the positive control into a loss.
    """
    events = "check 0 reports the migration will drop rows if it proceeds. proceeding destroys unrecoverable records."
    carriers = describe_carriers([_Belief("Proceeding destroys unrecoverable records.", -0.8)], [], events)
    assert carriers[0]["unsupported_threat_terms"] == []


def test_a_threat_absent_from_the_events_is_flagged():
    events = "query 0 returned no rows and no error; the scope was never specified."
    carriers = describe_carriers([_Belief("The tool is silently corrupting the dataset.", -0.6)], [], events)
    assert carriers[0]["unsupported_threat_terms"] == ["corrupt"]


def test_only_negative_valence_beliefs_are_carriers():
    """Merged's channel is `max(0, -valence)`; a pleasant belief carries nothing."""
    assert describe_carriers([_Belief("Steps completed cleanly.", 0.4)], [], "") == []


# --- the reachability of merged's carrier, checked by reading -----------------


def test_the_extractor_can_emit_the_fields_merged_reads():
    """`supports` was absent from this schema and unreachable for the whole of
    experiment 3 before anyone noticed. Merged's carrier needs two fields:
    a numeric `valence` and an `uncertainty` belief type. Both are asserted
    here so a flat merged result can never be an unelicitable field.
    """
    schema = BeliefExtractor()._schema()
    item = schema["properties"]["candidates"]["items"]["properties"]
    assert item["valence"]["type"] == "number"
    assert "uncertainty" in item["belief_type"]["enum"]


def test_the_inner_voice_is_off_on_both_builds():
    """Pins the departure the module docstring documents: with the voice on,
    every turn costs a second provider call to move a quantity no measured
    channel reads, and split gains an LLM in its mood path that merged has not.
    """
    for arch in (Arch.MERGED, Arch.SPLIT):
        core = build_core(arch, object())
        assert core.inner_voice.provider is None
        assert core.belief_extractor.provider is not None


# --- analysis -----------------------------------------------------------------


def test_cohens_d_refuses_a_constant_pair_rather_than_returning_zero():
    assert cohens_d([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) is None


def test_cohens_d_separates_a_real_difference():
    d = cohens_d([0.9, 0.8, 0.85, 0.88], [0.1, 0.12, 0.09, 0.11])
    assert d is not None and d > 3


def test_bootstrap_ci_excludes_zero_on_a_separated_pair():
    ci = bootstrap_ci([0.9, 0.8, 0.85, 0.88], [0.1, 0.12, 0.09, 0.11], n=500)
    assert ci is not None and ci[0] > 0


def test_drop_one_reports_one_d_per_dropped_observation():
    treatment = [0.9, 0.8, 0.85, 0.2]
    assert len(drop_one(treatment, [0.1, 0.12, 0.09, 0.11])) == len(treatment)


def test_undecided_is_the_default_verdict():
    """No §8.1 branch satisfied must not fall through to a win."""
    summary = {"builds": {"merged": {"cohens_d": None}, "split": {"cohens_d": None}}}
    assert decide(summary, {MClass.MA: 10}, 10)["outcome"] == "undecided"


def test_all_m0_is_undecided_not_a_split_win():
    summary = {"builds": {"merged": {}, "split": {"cohens_d": 2.0, "positive_control_moves": True}}}
    assert decide(summary, {MClass.M0: 10}, 10)["outcome"] == "undecided"


def test_merged_wins_only_with_control_effect_size_and_a_ci_excluding_zero():
    summary = {
        "builds": {
            "merged": {"cohens_d": 1.2, "bootstrap_ci": (0.4, 2.0), "positive_control_moves": True},
            "split": {"cohens_d": 2.0, "positive_control_moves": True},
        }
    }
    assert decide(summary, {MClass.MC: 8}, 10)["outcome"] == "merged"

    failing_control = {"builds": {**summary["builds"], "merged": {**summary["builds"]["merged"], "positive_control_moves": False}}}
    assert decide(failing_control, {MClass.MC: 8}, 10)["outcome"] == "undecided"
