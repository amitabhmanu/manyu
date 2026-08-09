"""Deterministic belief-store construction for experiment #2.

Both discriminators need stores whose contents are exactly known: D3 because
its fixtures encode contradictions whose structure *is* the experimental
condition, and D2's mechanism stage because the plumbing has to be checked
against arithmetic somebody can do by hand.

Nothing here calls a provider. `ManyuCore.update_beliefs` accepts explicit
`candidates` and bypasses `BeliefExtractor` entirely, which is what makes the
whole of D3 and most of D2 runnable offline — the single largest lever on this
experiment's cost, and on how much of it is deterministic.

**What this is not.** A store built here is authored. For D2 that means merged's
mood is a function of valences *we chose*, so nothing measured against a seeded
store is a D2 result — see design §6.1. It is plumbing verification, and
`results.md` labels it as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from manyu.architecture import Arch
from manyu.core import ManyuCore
from manyu.schemas import Belief, BeliefScope, BeliefType, NormalizedEvent

# Fixture-typical defaults, taken from the existing evals/fixtures set so a
# seeded store sits in the same numeric neighbourhood as a replayed one.
DEFAULT_SALIENCE = 0.5
DEFAULT_WEIGHT = 0.7
DEFAULT_CONFIDENCE = 0.7


@dataclass(frozen=True)
class BeliefSpec:
    """One belief to construct, with edges named by `key` rather than by id.

    Belief ids are generated at save time, so a fixture cannot reference them.
    Edges are therefore declared against keys and resolved in a second pass —
    which also means a fixture that names a key it never defines fails loudly
    instead of silently producing an edgeless store.
    """

    key: str
    proposition: str
    valence: float = 0.0
    confidence: float = DEFAULT_CONFIDENCE
    salience: float = DEFAULT_SALIENCE
    weight: float = DEFAULT_WEIGHT
    belief_type: BeliefType = BeliefType.WORLD_MODEL
    scope: BeliefScope = BeliefScope.GENERAL
    contradicts: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()
    evidence_count: int = 1


def seed_beliefs(core: ManyuCore, specs: list[BeliefSpec], *, agent_id: str = "agent_demo") -> dict[str, str]:
    """Build every spec into `core`'s store. Returns `key -> belief_id`.

    Insertion order is preserved, and `ManyuStore.list_beliefs` returns
    newest-first by rowid, so the *last* spec in the list is the most recent
    belief. Tests that care about the merged recency window rely on this.
    """
    ids: dict[str, str] = {}
    for spec in specs:
        evidence_ids = []
        for index in range(spec.evidence_count):
            evidence = core.capture_belief_evidence(
                {
                    "agent_id": agent_id,
                    "source_type": "operator_note",
                    "source_id": f"{spec.key}_{index}",
                    "summary": f"evidence {index} for {spec.key}",
                    "affective_salience": spec.salience,
                    "epistemic_weight": spec.weight,
                }
            )
            evidence_ids.append(evidence["evidence_id"])
        result = core.update_beliefs(
            {
                "agent_id": agent_id,
                "candidates": [
                    {
                        "candidate_id": f"bcand_{spec.key}",
                        "agent_id": agent_id,
                        "proposition": spec.proposition,
                        "belief_key": spec.key,
                        "belief_type": spec.belief_type.value,
                        "scope": spec.scope.value,
                        "confidence": spec.confidence,
                        "stability": 0.1,
                        "valence": spec.valence,
                        "source_mix": {"operator_note": 1.0},
                        "evidence_ids": evidence_ids,
                    }
                ],
            }
        )
        accepted = result.get("accepted") or []
        if not accepted:
            raise ValueError(f"spec {spec.key!r} was rejected: {result.get('rejected')}")
        ids[spec.key] = accepted[0]["belief_id"]

    _resolve_edges(core, specs, ids, agent_id=agent_id)
    return ids


def _resolve_edges(core: ManyuCore, specs: list[BeliefSpec], ids: dict[str, str], *, agent_id: str) -> None:
    """Second pass: rewrite key-named edges as belief ids.

    Written directly to the store rather than through `BeliefUpdater`, because
    the updater flips `status` to CONTESTED whenever a candidate declares
    `contradicts`. That is correct for live extraction and wrong here: a D3
    fixture needs to control whether a belief is contested *independently* of
    whether it has a conflict edge, otherwise `status` and `contradicts` are
    the same variable and FR-D3.5 cannot record them separately.
    """
    for spec in specs:
        if not spec.contradicts and not spec.supports:
            continue
        unknown = [key for key in (*spec.contradicts, *spec.supports) if key not in ids]
        if unknown:
            raise ValueError(f"spec {spec.key!r} references undefined keys: {unknown}")
        belief = _get(core, ids[spec.key], agent_id=agent_id)
        core.store.save_belief(
            belief.model_copy(
                update={
                    "contradicts": sorted(ids[key] for key in spec.contradicts),
                    "supports": sorted(ids[key] for key in spec.supports),
                }
            )
        )


# --- D2: the uncertainty stream ---------------------------------------------

#: Seconds between events. Decay is split's defining dynamic — `fear` has a
#: 900s half-life — and a run with `FrozenClock` and no advance would switch it
#: off entirely, flattering split's accumulation by removing the thing that
#: works against it. 60s gives a per-step decay factor of 0.5^(60/900) = 0.955,
#: so accumulation still dominates but is genuinely opposed.
INTER_EVENT_SECONDS = 60.0

D2_CONDITIONS = ("uncertainty", "control", "neutral")

#: Gate #7 shape keys, **per build, derived from each metric's causal path and
#: declared before the run.**
#:
#: An earlier version compared every build on `evidence_count`, and gate #7
#: refused all three conditions because the counts differed (51/54/58). That was
#: a spurious refusal: merged reads the *belief window*, never the evidence
#: count, and at the window level the conditions are identical (21 beliefs, 8 in
#: window, 7 authored carriers each). Split's `fear` comes from `event_type`
#: deltas and does not touch the belief log at all.
#:
#: The rule that keeps this from becoming "pick whichever key passes": a shape
#: key is admissible only if the measured channel is a function of it. Choosing
#: keys after seeing which ones pass is gate #1.
D2_SHAPE_KEYS = {
    "merged": ("window_belief_count", "authored_in_window"),
    "split": ("n_events",),
}


def uncertainty_events(count: int, *, condition: str, agent_id: str = "agent_demo") -> list[NormalizedEvent]:
    """Generate one D2 condition's event stream.

    Generated rather than authored as JSON because the streams are 20 near
    identical events and a generator is both less error-prone and easier to
    audit than twenty hand-copied blocks. D3's fixtures are files because its
    held-out set needs hashing for blinding; D2 has no held-out set.

    - `uncertainty` — ambiguous `tool_result`s. **No goal link at all, no
      threat in any claim.** This is the object-less condition, and it produces
      affect in split only through the `TOOL_RESULT`/`GOAL_OBSTRUCTION` grouping
      documented in design §6.2.
    - `control` — the same stream with an explicit threat: a goal link with
      negative `expected_impact` and a claim naming the harm. Both builds must
      move here or their result on `uncertainty` is void, not a null (FR-D2.4).
    - `neutral` — matched count, benign `social_feedback` from a trusted
      relationship. Defines each build's own reference distribution.
    """
    if condition not in D2_CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    events = []
    for index in range(count):
        if condition == "neutral":
            # `goal_progress` from the same verified tool as the other two
            # conditions. An earlier version used `social_feedback` from the
            # user, which produced no fear but also swung `untrusted_count`
            # from 0 to 45 — the conditions then differed in log shape as well
            # as in treatment, and gate #7 refused the comparison. Matching the
            # source keeps the only difference the one under test.
            payload = {
                "event_type": "goal_progress",
                "summary": f"Step {index} completed and the scope was confirmed.",
                "source": {"trust_class": "verified_tool", "channel": "tool", "confidence": 0.8},
                "actor": {"kind": "tool", "id": "query_runner"},
                "claims": [],
                "links": [],
            }
        elif condition == "uncertainty":
            payload = {
                "event_type": "tool_result",
                "summary": f"Query {index} returned no rows and no error; the scope was never specified.",
                "source": {"trust_class": "verified_tool", "channel": "tool", "confidence": 0.8},
                "actor": {"kind": "tool", "id": "query_runner"},
                "claims": [],
                "links": [],
            }
        else:
            payload = {
                "event_type": "tool_result",
                "summary": f"Check {index} reports the migration will drop rows if it proceeds.",
                "source": {"trust_class": "verified_tool", "channel": "tool", "confidence": 0.8},
                "actor": {"kind": "tool", "id": "migration_checker"},
                "claims": [
                    {"claim_id": f"claim_threat_{index}", "claim_type": "fact", "text": "Proceeding destroys unrecoverable records.", "confidence": 0.85}
                ],
                "links": [{"link_type": "goal", "id": "preserve_data", "relevance": 0.9, "expected_impact": -0.8, "confidence": 0.85}],
            }
        payload |= {"event_id": f"{condition}_{index:03d}", "agent_id": agent_id, "session_id": f"sess_{condition}"}
        events.append(NormalizedEvent.model_validate(payload))
    return events


def _carrier_candidate(event: NormalizedEvent, evidence_id: str, condition: str, index: int) -> dict:
    """The belief an authored fixture says each event produces.

    **This is the circularity design §6.1 warns about, made explicit.** Merged's
    affect is a query over belief valence, so by authoring these valences we are
    choosing merged's answer. Nothing measured against this stream is a D2
    result — it is plumbing verification. Only Stage 4, with the live
    extractor, can say whether a carrier arises unprompted.
    """
    valence = {"uncertainty": -0.35, "control": -0.8, "neutral": 0.25}[condition]
    return {
        "candidate_id": f"bcand_{condition}_{index}",
        "agent_id": event.agent_id,
        "proposition": event.summary,
        "belief_key": f"uncertainty/{condition}/{index}",
        "belief_type": "uncertainty" if condition == "uncertainty" else "world_model",
        "scope": "local_context",
        "confidence": 0.7,
        "stability": 0.1,
        "valence": valence,
        "source_mix": {"verified_tool" if condition != "neutral" else "user_report": 1.0},
        "evidence_ids": [evidence_id],
    }


@dataclass(frozen=True)
class D2Record:
    """One condition run against one build, with the diagnostics that keep a null readable."""

    arch: str
    condition: str
    n_events: int
    #: The build's negative-affect measure — merged's `max(0, -valence)`,
    #: split's accumulated `fear`. **Never compared across builds**; each is
    #: standardised against its own neutral condition (methodology §4.3).
    affect: float
    affect_channel: str
    #: Merged only. Recorded because arousal turned out to be the wrong D2
    #: channel and the reason is worth keeping visible — see `run_d2_condition`.
    arousal: float
    valence: float
    window_belief_count: int
    #: How many of the window's beliefs are the fixture's own carriers rather
    #: than reflection-generated. Part of merged's shape key: a window diluted
    #: by reflection beliefs measures something different from one that is not.
    authored_in_window: int
    sum_stake: float
    arousal_floored: bool
    evidence_count: int
    untrusted_count: int

    def as_dict(self) -> dict:
        return {**self.__dict__}


def run_d2_condition(
    *,
    arch: Arch,
    condition: str,
    n_events: int = 20,
    agent_id: str = "agent_demo",
    authored_beliefs: bool = True,
) -> D2Record:
    """Drive one condition offline and record what each build ended up feeling.

    No provider is constructed. Beliefs come from authored candidates, so
    `BeliefExtractor` is never called; split's mood would need
    `InnerVoiceComposer`, so split's affect is read from `AffectState` instead.

    The two builds report on **different channels** — merged's belief-derived
    arousal, split's accumulated `fear` — because those are the affect each
    architecture actually has offline. They are never compared directly;
    methodology §4.3 compares within-build effect sizes against each build's own
    neutral condition.
    """
    core = ManyuCore.from_paths(db_path=":memory:", frozen=True, arch=arch)
    clock = core.clock
    events = uncertainty_events(n_events, condition=condition, agent_id=agent_id)

    for index, event in enumerate(events):
        payload: dict = {"event": event.model_dump(mode="json")}
        if authored_beliefs:
            evidence = core.capture_belief_evidence(
                {
                    "agent_id": agent_id,
                    "source_type": "event",
                    "source_id": event.event_id,
                    "summary": event.summary,
                    "trust_class": event.source.trust_class.value,
                    # Salience and weight are deliberately *not* set here.
                    # `BeliefEvidenceService` derives both from the source, and
                    # authoring them would mean hand-setting the quantity merged
                    # reads — choosing merged's answer, which is gate #1.
                }
            )
            payload["belief_candidates"] = [_carrier_candidate(event, evidence["evidence_id"], condition, index)]
        core.process_reflective_turn(payload)
        clock.advance(INTER_EVENT_SECONDS)

    beliefs = core.store.list_beliefs(agent_id)
    evidence_records = core.store.list_belief_evidence(agent_id)
    untrusted = sum(1 for item in evidence_records if item.trust_class.value in ("user_report", "untrusted_text"))

    carrier_prefix = f"uncertainty/{condition}/"
    window = core.moods.window(agent_id) if arch is Arch.MERGED else beliefs[:8]
    authored_in_window = sum(1 for b in window if (b.belief_key or "").startswith(carrier_prefix))

    if arch is Arch.MERGED:
        projection = core.moods.project(agent_id)
        # **Not arousal.** Merged's arousal is `1 - exp(-sum(stake)/tau)`, and
        # neither stake nor tau depends on valence — it measures how much is on
        # the agent's mind, not how bad any of it is. That is the standard
        # circumplex separation and correct, but it means a store full of
        # pleasant beliefs is as aroused as one full of dreadful ones, so
        # arousal cannot answer D2's question. Negative valence is merged's
        # analogue of split's `fear`.
        affect = round(max(0.0, -projection.valence), 6)
        channel = "merged_negative_valence"
        arousal, valence = projection.arousal, projection.valence
        window, stake, floored = projection.window_belief_count, projection.sum_stake, projection.arousal_floored
    else:
        state = core.store.latest_state(agent_id)
        affect, channel = round(state.emotions["fear"], 6), "affect_state_fear"
        arousal, valence = 0.0, 0.0
        window, stake, floored = len(beliefs), 0.0, False

    return D2Record(
        arch=arch.value,
        condition=condition,
        n_events=n_events,
        affect=affect,
        affect_channel=channel,
        arousal=arousal,
        valence=valence,
        authored_in_window=authored_in_window,
        window_belief_count=window,
        sum_stake=stake,
        arousal_floored=floored,
        evidence_count=len(evidence_records),
        untrusted_count=untrusted,
    )


def _get(core: ManyuCore, belief_id: str, *, agent_id: str) -> Belief:
    for belief in core.store.list_beliefs(agent_id, include_inactive=True):
        if belief.belief_id == belief_id:
            return belief
    raise KeyError(belief_id)
