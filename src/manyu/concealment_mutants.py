"""Working alternatives to the concealment detector, each wrong in one way.

Experiment 5's battery is the precedent and experiment 6's is the warning. Six of
experiment 6's mutants worked; two did not, and both failures were the same shape
-- a check that could not distinguish the mechanism working from the mechanism
being absent. `dose_ignores_stability` still read the starting stability, so it
rose exactly as the real dose does and was never a mutant at all.

So every mutant here is a *working* detector -- it produces plausible-looking
divergence lists on the happy path -- and `tests/test_concealment_mutants.py`
verifies for each one that the check catching it **passes on the real detector**
and **fails on that mutant**. A mutant nothing catches is deleted rather than kept
for the count.

Each reproduces a defect family this sequence has shipped or nearly shipped:

- `FlagsEveryBelief` -- experiment 4's Stage 0a, where a base rate read exactly
  like a finding. A detector whose positive rate equals the prose loss rate
  (0.727-0.971) flags almost everything and looks productive doing it.
- `ReadsStatusIgnoresProse` -- the first draft of this experiment's own criterion
  set, which registered the citation rule as catching channels it cannot see
  (pre-registration amendment A5).
- `TrustsNonEmptyProvenance` -- the receipt-mismatch channel's whole point. A
  provenance list that is present and supports nothing passes any check that asks
  whether receipts exist rather than whether they bear on the sentence.
- `BlindToStaleAssertion` -- a detector built for one sign of divergence.
  Suppression and stale assertion are opposite directions and experiment 5
  section 5.1 recorded the second as a footnote; missing it here would repeat that.
- `ReportsSubstrateFilterAsAgent` -- FR-10's failure, and the most dangerous one
  in the file, because it does not change *what* is detected at all. It relabels
  an enum's doing as an agent's, which is the misleading result this experiment
  could most plausibly publish.

No mutant here is documented as equivalent to another.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from manyu.concealment import (
    Cause,
    Criterion,
    Divergence,
    EXPRESSION_THRESHOLD,
    _spoken_belief,
    surface_reads,
    theme_groups,
)


@dataclass(frozen=True)
class Mutant:
    name: str
    caught_by: str
    defect_family: str


CATALOGUE: tuple[Mutant, ...] = (
    Mutant("flags_every_belief", "test_honest_web_produces_no_divergence", "a base rate presented as a detection"),
    Mutant("reads_status_ignores_prose", "test_stale_assertion_is_caught", "a criterion set that misses what it claims to cover"),
    Mutant("trusts_non_empty_provenance", "test_receipt_mismatch_is_caught", "receipts checked for presence rather than for support"),
    Mutant("blind_to_stale_assertion", "test_stale_assertion_is_caught", "a detector built for one sign of divergence"),
    Mutant("reports_substrate_filter_as_agent", "test_crowded_theme_is_attributed_to_the_substrate", "an enum's doing relabelled as an agent's"),
)


def _row(belief: Any, theme: str, criteria: tuple[Criterion, ...], cause: Cause, rationale: str) -> Divergence:
    return Divergence(
        belief_id=belief.belief_id,
        belief_key=belief.belief_key,
        theme=theme,
        confidence=belief.confidence,
        status=belief.status.value,
        criteria=criteria,
        cause=cause,
        rationale=rationale,
    )


def flags_every_belief(
    core: Any,
    agent_id: str,
    *,
    questions: tuple[str, ...] = (),
    tau: float = EXPRESSION_THRESHOLD,
) -> list[Divergence]:
    """Flags every belief not spoken in its theme's prose.

    This is the retired prose criterion (amendment A1), kept as a mutant because
    it is what the experiment would have shipped had the census not been run
    first. On a real web it flags 73-97% of beliefs, and every one of those flags
    is `_stance_text` rendering one belief per group -- an enum's behaviour dressed
    as a finding.
    """
    groups = theme_groups(core, agent_id)
    surfaces = surface_reads(core, agent_id, questions)
    found: list[Divergence] = []
    for theme, group in sorted(groups.items()):
        spoken = _spoken_belief(group, surfaces.spoken.get(theme))
        for belief in sorted(group, key=lambda item: item.belief_id):
            if spoken is not None and belief.belief_id == spoken.belief_id:
                continue
            found.append(
                _row(
                    belief,
                    theme,
                    (Criterion.WITHIN_GROUP,),
                    Cause.SUBSTRATE_FILTER,
                    "not spoken in its theme's prose",
                )
            )
    return found


def reads_status_ignores_prose(
    core: Any,
    agent_id: str,
    *,
    questions: tuple[str, ...] = (),
    tau: float = EXPRESSION_THRESHOLD,
) -> list[Divergence]:
    """Flags on status alone and never reads what was said.

    The first draft of this experiment's criterion set in miniature: it catches the
    status channel and is blind to every channel where status is untouched, which
    is four of the six. Plausible because status *is* the mechanism behind the
    headline example -- which is exactly why a detector resting on it looks right.
    """
    groups = theme_groups(core, agent_id)
    surfaces = surface_reads(core, agent_id, questions)
    found: list[Divergence] = []
    for theme, group in sorted(groups.items()):
        for belief in sorted(group, key=lambda item: item.belief_id):
            if belief.belief_id in surfaces.composed:
                continue
            found.append(
                _row(
                    belief,
                    theme,
                    (Criterion.WITHIN_GROUP,),
                    Cause.DELIBERATE_WRITE,
                    "not composed into any stance",
                )
            )
    return found


def trusts_non_empty_provenance(
    core: Any,
    agent_id: str,
    *,
    questions: tuple[str, ...] = (),
    tau: float = EXPRESSION_THRESHOLD,
) -> list[Divergence]:
    """Checks that receipts exist, never that they support the sentence.

    Drops `RECEIPT_MISMATCH` entirely and keeps everything else, so it passes every
    check except the one about the channel whose whole content is a well-formed
    provenance list that bears on nothing said. This is the auditor's error the
    channel exists to describe.
    """
    from manyu.concealment import divergences as real

    return [row for row in real(core, agent_id, questions=questions, tau=tau) if Criterion.RECEIPT_MISMATCH not in row.criteria]


def blind_to_stale_assertion(
    core: Any,
    agent_id: str,
    *,
    questions: tuple[str, ...] = (),
    tau: float = EXPRESSION_THRESHOLD,
) -> list[Divergence]:
    """Detects suppression and not its opposite.

    Treats every belief below tau as legitimately silent, which is true when it is
    silent and false when the substrate is still asserting it at 0.02. Experiment 5
    section 5.1 recorded that second case as a limitation on its own reading; a
    detector with this shape would carry it forward as one.
    """
    from manyu.concealment import divergences as real

    return [row for row in real(core, agent_id, questions=questions, tau=tau) if Criterion.STALE_ASSERTION not in row.criteria]


def reports_substrate_filter_as_agent(
    core: Any,
    agent_id: str,
    *,
    questions: tuple[str, ...] = (),
    tau: float = EXPRESSION_THRESHOLD,
) -> list[Divergence]:
    """Detects exactly what the real detector detects, and attributes all of it to the agent.

    **The most dangerous mutant in the file, and the only one that changes no
    divergence count.** Sensitivity, specificity and the per-criterion table are
    all identical to the real detector's; only `cause` differs. So every check that
    counts divergences passes, and the published headline inverts -- the
    substrate/agent split (pre-registration section 1.7) becomes "the agent did all
    of it".

    FR-10 exists for this, and it is why `cause` is a stored field rather than an
    analysis-time inference: a reader must be able to check the attribution
    without rerunning the analysis that produced it.
    """
    from manyu.concealment import divergences as real

    return [
        Divergence(
            belief_id=row.belief_id,
            belief_key=row.belief_key,
            theme=row.theme,
            confidence=row.confidence,
            status=row.status,
            criteria=row.criteria,
            cause=Cause.DELIBERATE_WRITE,
            rationale=row.rationale,
        )
        for row in real(core, agent_id, questions=questions, tau=tau)
    ]


#: Name -> callable, so a runner or test can sweep the battery without importing
#: each one. Signature-compatible with `concealment.divergences` throughout.
DETECTORS = {
    "flags_every_belief": flags_every_belief,
    "reads_status_ignores_prose": reads_status_ignores_prose,
    "trusts_non_empty_provenance": trusts_non_empty_provenance,
    "blind_to_stale_assertion": blind_to_stale_assertion,
    "reports_substrate_filter_as_agent": reports_substrate_filter_as_agent,
}
