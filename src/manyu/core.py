from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manyu.clock import Clock, FrozenClock
from manyu.config import load_profile
from manyu.honesty import HonestyScorer, LLMFailureClassifier
from manyu.probing import ProbeOrchestrator
from manyu.reporting import LLMReporter, TemplaterReporter
from manyu.revision import ContradictionArm, PropagationResult, RevisionEngine
from manyu.schemas import (
    AffectState,
    Appraisal,
    BeliefCandidate,
    CandidateAction,
    ConsequenceClass,
    EventType,
    HonestyScore,
    InnerVoiceFrame,
    LogSnapshot,
    ManyuProfile,
    MoodStatus,
    NormalizedEvent,
    Report,
    ReporterKind,
    ReportTarget,
    ReportTargetKind,
    ReplayReport,
    TraceRecord,
)
from manyu.architecture import Arch, ArchConfig
from manyu.services import (
    Arbiter,
    BeliefEvidenceService,
    BeliefExtractor,
    BeliefReflectionService,
    BeliefUpdater,
    EpisodeService,
    EventGateway,
    FastAppraiser,
    InnerVoiceComposer,
    InteroceptionService,
    MergedMoodEngine,
    MoodEngine,
    MoodInfluenceService,
    OpinionExpressionService,
    SlowAppraisalService,
    StructuredJSONProvider,
    TransitionEngine,
    WorldviewSynthesizer,
)
from manyu.services import MemoryService
from manyu.snapshotting import SnapshotBuilder
from manyu.store import ManyuStore


def _propagation_payload(result: PropagationResult) -> dict[str, Any]:
    """Serialise a propagation footprint — FR-5.

    The per-step breakdown is the point, not the totals: a collapse and a
    ripple are told apart by which beliefs moved and at what remove. Note that
    `total_movement` sums magnitudes across beliefs and is **not** conserved
    under the `fixed` decay ablation, so it should not be read as a headline.
    """
    return {
        "origin_id": result.origin_id,
        "arm": result.arm.value,
        # An empty `steps` list is ambiguous on its own; `outcome` says whether
        # nothing happened because nothing was owed, because it was already
        # priced, or because the call was refused.
        "outcome": result.outcome,
        "max_depth_reached": result.max_depth_reached,
        "total_movement": round(result.total_movement(), 6),
        "steps": [
            {
                "belief_id": step.belief_id,
                "depth": step.depth,
                "before": round(step.before, 6),
                "after": round(step.after, 6),
                "delta": round(step.delta, 6),
                "caused_by": step.caused_by,
                "share": round(step.support_share, 6),
            }
            for step in result.steps
        ],
    }


class ManyuCore:
    def __init__(
        self,
        store: ManyuStore,
        profile: ManyuProfile,
        clock: Clock | None = None,
        belief_provider: StructuredJSONProvider | None = None,
        arch: Arch = Arch.SPLIT,
        arch_config: ArchConfig | None = None,
        contradiction_arm: ContradictionArm = ContradictionArm.DIRECT,
    ):
        self.store = store
        self.profile = profile
        self.clock = clock or Clock()
        #: Which contradiction semantics ingest applies. Defaults to the value
        #: experiment #3 requirements §5.1 decided on; `EVIDENTIAL` is kept
        #: selectable so the ablation can run against the same pipeline.
        self.contradiction_arm = ContradictionArm(contradiction_arm)
        self.belief_provider = belief_provider
        # `SPLIT` is the default so every pre-experiment caller and test is
        # untouched by the fork — the SC-1 requirement, that the builds agree
        # where they should, starts by the split path being literally the same
        # code it was before.
        self.arch = arch
        self.arch_config = arch_config or ArchConfig()
        self.gateway = EventGateway(store)
        self.fast_appraiser = FastAppraiser(store)
        self.transitions = TransitionEngine(store, profile, self.clock)
        self.interoception = InteroceptionService(store, profile, self.clock)
        self.arbiter = Arbiter(store, profile, self.clock)
        self.slow = SlowAppraisalService(store)
        self.episodes = EpisodeService(store)
        self.memory = MemoryService(store)
        self.belief_evidence = BeliefEvidenceService(store)
        self.belief_extractor = BeliefExtractor(belief_provider)
        self.belief_updater = BeliefUpdater(store, self.clock)
        self.belief_reflection = BeliefReflectionService(store, self.belief_updater, self.clock)
        self.worldviews = WorldviewSynthesizer(store, self.clock)
        self.opinions = OpinionExpressionService(store, self.clock)
        self.inner_voice = InnerVoiceComposer(store, self.clock, belief_provider)
        self.moods = (
            MergedMoodEngine(store, self.clock, self.arch_config)
            if arch is Arch.MERGED
            else MoodEngine(store, self.clock)
        )
        self.mood_influence = MoodInfluenceService()
        self.snapshots = SnapshotBuilder(store, self.clock)
        self.templater = TemplaterReporter(store, self.clock)
        self.llm_reporter = LLMReporter(store, self.clock, belief_provider) if belief_provider else None
        self.llm_judge = LLMFailureClassifier(belief_provider) if belief_provider else None
        self.honesty_scorer = HonestyScorer(store, self.clock, llm_judge=self.llm_judge)
        self.probe_orchestrator = ProbeOrchestrator(
            store=store,
            clock=self.clock,
            templater=self.templater,
            llm_reporter=self.llm_reporter,
            scorer=self.honesty_scorer,
            snapshots=self.snapshots,
            moods=self.moods,
        )

    @classmethod
    def from_paths(
        cls,
        db_path: str | Path = ":memory:",
        profile_path: str | Path = "config/default_profile.json",
        frozen: bool = False,
        belief_provider: StructuredJSONProvider | None = None,
        arch: Arch = Arch.SPLIT,
        arch_config: ArchConfig | None = None,
        contradiction_arm: ContradictionArm = ContradictionArm.DIRECT,
    ) -> "ManyuCore":
        profile = load_profile(profile_path)
        clock = FrozenClock() if frozen else Clock()
        return cls(ManyuStore(db_path), profile, clock, belief_provider, arch, arch_config, contradiction_arm)

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "schema_version": self.profile.schema_version,
            "profile_id": self.profile.profile_id,
            "agent_id": self.profile.agent_id,
            "store": "ready",
            "mcp": "not_configured",
        }

    def submit_event(self, event: NormalizedEvent, candidate_action: CandidateAction | None = None) -> TraceRecord:
        return self._submit_event(event, candidate_action, None)

    def _submit_event(self, event: NormalizedEvent, candidate_action: CandidateAction | None = None, mood=None) -> TraceRecord:
        accepted = self.gateway.submit_event(event)
        state = self.transitions.initial_state(accepted.agent_id)
        appraisal = self.fast_appraiser.appraise(accepted, state.revision, mood)
        transition = self.transitions.apply(appraisal)
        post_state = self.store.latest_state(accepted.agent_id)
        if post_state is None:
            raise RuntimeError("state missing after transition")
        view = self.interoception.derive(post_state)
        if candidate_action is None:
            candidate_action = CandidateAction(
                action_id=f"act_{accepted.event_id}",
                agent_id=accepted.agent_id,
                action_class=appraisal.action_tendency.action_class,
                summary=f"Respond to {accepted.event_type.value}: {accepted.summary}",
                consequence_class=ConsequenceClass.C1,
                reversible=True,
            )
        decision = self.arbiter.arbitrate(candidate_action, post_state, appraisal)
        return TraceRecord(
            trace_id=f"trace_{accepted.event_id}",
            event=accepted,
            appraisal=appraisal,
            transition=transition,
            interoception=view,
            arbitration=decision,
        )

    def process_reflective_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = NormalizedEvent.model_validate(payload["event"])
        prior_mood = self.moods.active_mood(event.agent_id)
        trace = self._submit_event(event, None, prior_mood)
        evidence = self.capture_belief_evidence(
            {
                "agent_id": event.agent_id,
                "source_type": "trace",
                "source_id": trace.trace_id,
                "summary": f"{event.event_type.value}: {event.summary}",
                # Carry the event's own trust class rather than letting
                # _trust_from_source stamp everything TRUSTED_SYSTEM because the
                # evidence arrived via a trace. The trace is a trustworthy record
                # that the utterance happened; it says nothing about the claim
                # inside it. Collapsing the two made TrustClass single-valued on
                # the reflective path — all four fixtures mark 5-7 events
                # `user_report` and every resulting evidence record came out
                # `trusted_system` — which left sanitised_story unable to fire in
                # any run. Inherit rather than upgrade: evidence is no more
                # trustworthy than the event it came from.
                "trust_class": event.source.trust_class.value,
            }
        )
        # FR-1: the dissonance read is taken at a defined point in the turn, and
        # the point is **both sides of belief update**.
        #
        # Requirements section 14 left this open on the grounds that reading
        # before and reading after are different experiments. They are, and the
        # deciding fact is a confound rather than a preference: `update_beliefs`
        # routes every newly declared contradiction through
        # `RevisionEngine.assert_contradiction` (experiment 3 section 14), so by
        # the time it returns, a contradiction that arrived this turn has already
        # been charged and the tension it caused is already partly discharged. A
        # single read afterwards cannot distinguish "the web was calm" from "the
        # web was disturbed and immediately priced".
        #
        # Taking both also satisfies requirements section 12 structurally: the
        # delta is reported against the baseline it was measured from, rather than
        # beside it and hoping the reader joins them.
        dissonance_before = self.read_dissonance(event.agent_id, persist=False)

        belief_payload: dict[str, Any] = {"agent_id": event.agent_id, "evidence_ids": [evidence["evidence_id"]]}
        if "belief_candidates" in payload:
            belief_payload["candidates"] = payload["belief_candidates"]
        belief_update = self.update_beliefs(belief_payload)
        dissonance_after = self.read_dissonance(event.agent_id)
        worldview = self.review_beliefs({"agent_id": event.agent_id, "affect_threshold": payload.get("affect_threshold", 0.24)})
        voice_result = self.inner_voice.compose(trace)
        mood_result = None
        if voice_result.get("status") == "ok" and voice_result.get("inner_voice"):
            frame = InnerVoiceFrame.model_validate(voice_result["inner_voice"])
            mood = self.moods.update_from_voice(frame)
            mood_result = mood.model_dump(mode="json")
        return {
            "status": "ok",
            "trace": trace.model_dump(mode="json"),
            "prior_mood": self.mood_influence.summarize(prior_mood),
            "belief_evidence": evidence,
            "belief_update": belief_update,
            "worldview": worldview,
            "inner_voice": voice_result,
            "mood": mood_result,
            "dissonance": {
                # Raw, never saturated. `magnitude` is concave in raw tension, so
                # a delta taken on it confounds how much tension changed with
                # where on the curve the web was sitting (experiment 3 section
                # 3.3, requirements section 12).
                "raw_before": (dissonance_before["signal"] or {}).get("magnitude_raw", 0.0),
                "raw_after": (dissonance_after["signal"] or {}).get("magnitude_raw", 0.0),
                "conflicts_before": dissonance_before["conflicts"],
                "conflicts_after": dissonance_after["conflicts"],
                "arose_this_turn": dissonance_after["conflicts"] - dissonance_before["conflicts"],
            },
        }

    def state(self, agent_id: str | None = None) -> AffectState:
        return self.transitions.initial_state(agent_id or self.profile.agent_id)

    def trace(self, event_id: str) -> TraceRecord:
        return self.store.trace_for_event(event_id)

    def traces(self, agent_id: str | None = None) -> list[TraceRecord]:
        traces: list[TraceRecord] = []
        for event_id in self.store.list_event_ids(agent_id):
            try:
                traces.append(self.trace(event_id))
            except KeyError:
                continue
        return traces

    def record_action(self, episode_id: str, agent_id: str, action_id: str, payload: dict) -> dict[str, object]:
        self.episodes.record_action(episode_id, agent_id, action_id, payload)
        return {"status": "recorded", "episode_id": episode_id, "artifact_type": "action", "artifact_id": action_id}

    def record_outcome(self, episode_id: str, agent_id: str, outcome_id: str, payload: dict) -> dict[str, object]:
        self.episodes.record_outcome(episode_id, agent_id, outcome_id, payload)
        if "context_key" in payload and "valence" in payload:
            self.memory.learn_from_outcome(
                agent_id=agent_id,
                context_key=str(payload["context_key"]),
                outcome=str(payload.get("summary", outcome_id)),
                valence=float(payload["valence"]),
                source_event_id=str(payload.get("source_event_id", outcome_id)),
            )
        return {"status": "recorded", "episode_id": episode_id, "artifact_type": "outcome", "artifact_id": outcome_id}

    def capture_belief_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = self.belief_evidence.capture(payload)
        return evidence.model_dump(mode="json")

    def update_beliefs(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        evidence_ids = [str(item) for item in payload.get("evidence_ids", [])]
        evidence = self.store.list_belief_evidence(agent_id, evidence_ids=evidence_ids or None, limit=payload.get("limit"))
        raw_candidates = payload.get("candidates")
        extraction: dict[str, Any]
        if raw_candidates is not None:
            candidates = [BeliefCandidate.model_validate(item) for item in raw_candidates]
            extraction = {"status": "ok", "candidates": candidates, "rejected": []}
        else:
            extraction = self.belief_extractor.extract(agent_id, evidence)
            if extraction["status"] != "ok":
                return extraction
            candidates = extraction["candidates"]
        update = self.belief_updater.update(agent_id, candidates)
        update["extraction_rejected"] = extraction.get("rejected", [])
        update["contradictions_priced"] = self._price_contradictions(agent_id, update.pop("new_contradictions", []))
        return update

    def _price_contradictions(self, agent_id: str, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Charge every contradiction the extractor declared.

        `BeliefUpdater` records the edge and marks the *declaring* belief
        CONTESTED, which left the belief actually being contradicted untouched
        in every channel — same confidence, still ACTIVE, no edge of its own.
        A live web therefore carried no trace that anything was disputed, and
        under the adopted `direct` arm a whole run would have read as a flat
        null that looked like a finding. This is experiment 1's v2 failure
        (a knob with nothing to bite on) in a new place.

        Routed through `RevisionEngine.assert_contradiction` rather than
        reimplemented, so ingest and the explicit surface share one pricing
        path and one ledger. Idempotent, so re-running a batch cannot compound
        the penalty.
        """
        if not pairs:
            return []
        engine = self._revision_engine(self.contradiction_arm)
        # Snapshot every contradictor's strength before charging any of them,
        # so a batch is atomic. Charging sequentially made mutual
        # contradictions order-dependent: the first charge weakened its
        # target, and if that target was itself a contradictor its own charge
        # then landed softer, settling the pair at 0.6/0.4 with the split
        # decided by extractor emission order.
        strengths: dict[str, float] = {}
        for contradictor_id, _ in pairs:
            try:
                strengths[contradictor_id] = self.store.get_belief(contradictor_id).confidence
            except KeyError:
                continue
        priced: list[dict[str, Any]] = []
        for contradictor_id, target_id in pairs:
            try:
                result = engine.assert_contradiction(
                    agent_id, contradictor_id, target_id, contradictor_confidence=strengths.get(contradictor_id)
                )
            except KeyError:
                continue
            priced.append(
                {
                    "contradictor_id": contradictor_id,
                    "target_id": target_id,
                    "charged": round(-sum(step.delta for step in result.steps), 6),
                    # Without this, a re-run of the same batch reports
                    # `charged: 0` — indistinguishable from a contradiction
                    # that was never priced at all, so any analysis summing
                    # this field silently under-counts on repeat runs.
                    "outcome": result.outcome,
                }
            )
        return priced

    def get_beliefs(self, agent_id: str | None = None, query: str | None = None, belief_type: str | None = None, include_inactive: bool = False) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {
            "agent_id": resolved,
            "beliefs": [
                belief.model_dump(mode="json")
                for belief in self.store.list_beliefs(resolved, query=query, belief_type=belief_type, include_inactive=include_inactive)
            ],
        }

    def retract_belief(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Collapse one belief's confidence and let the consequence propagate.

        The surface for experiment #3's revision engine, which until now could
        only be driven from tests — leaving the deliverable that experiments
        #5, #7 and #8 are supposed to consume unreachable from the CLI, the
        MCP tools, or `ManyuCore` itself.

        Retraction never deletes: confidence collapses and the belief keeps its
        provenance, so the revision stays auditable afterwards.

        `arm` is required and has no default, because a silent one would settle
        the open question in experiment #3 requirements §5 by whichever branch
        happened to be written first. The adopted value is `direct`.
        """
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        belief_id = payload.get("belief_id")
        if not belief_id:
            return {"status": "error", "error": "belief_id is required"}
        arm = payload.get("arm")
        if not arm:
            return {"status": "error", "error": "arm is required; use 'direct' (adopted) or 'evidential'"}
        try:
            engine = self._revision_engine(arm)
            result = engine.retract(agent_id, str(belief_id), float(payload.get("to_confidence", 0.0)))
        except KeyError:
            return {"status": "error", "error": f"unknown belief {belief_id}"}
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", **_propagation_payload(result)}

    def assert_contradiction(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Record that one belief contradicts another, and price it.

        Contradictions arriving through `update_beliefs` set `status` without
        charging confidence, so under the adopted `direct` arm they are inert —
        relief may only undo a suppression that was applied. This is the entry
        point that applies one.
        """
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        contradictor_id, target_id = payload.get("contradictor_id"), payload.get("target_id")
        if not contradictor_id or not target_id:
            return {"status": "error", "error": "contradictor_id and target_id are required"}
        arm = payload.get("arm")
        if not arm:
            return {"status": "error", "error": "arm is required; use 'direct' (adopted) or 'evidential'"}
        try:
            engine = self._revision_engine(arm)
            result = engine.assert_contradiction(agent_id, str(contradictor_id), str(target_id))
        except KeyError as exc:
            return {"status": "error", "error": f"unknown belief {exc}"}
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", **_propagation_payload(result)}

    def read_dissonance(self, agent_id: str | None = None, persist: bool = True) -> dict[str, Any]:
        """Read the belief web's tension, and record it.

        The surface experiment 4 needs, and until now the detector had none:
        `MergedDissonanceQuery` was imported by its own module and its own test
        file, was never computed during a turn, and was never persisted. Exactly
        where `RevisionEngine` stood before experiment 3 section 13.

        **`magnitude` is returned but must not be read as a measure of belief
        dynamics** (requirements section 12). It is concave in raw tension, so
        the same raw change reads larger from a lower baseline and a delta
        confounds how much tension changed with where on the saturation curve the
        web was sitting. Read `magnitude_raw` and `carriers`. The control path
        cannot reach `magnitude` at all — see `salience.TensionView`.
        """
        from manyu.dissonance import MergedDissonanceQuery

        resolved = agent_id or self.profile.agent_id
        signal = MergedDissonanceQuery(self.store).detect(resolved, "surface")
        if signal is None:
            return {"status": "ok", "signal": None, "conflicts": 0}
        if persist:
            self.store.save_dissonance_signal(signal)
        direct = [carrier for carrier in signal.carriers if not carrier.path]
        return {
            "status": "ok",
            "signal": signal.model_dump(mode="json"),
            "conflicts": len(direct),
            "implicated": len(signal.carriers),
        }

    def run_attention_loop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Let dissonance decide what gets revisited, and record what it chose.

        `arm` is required and has no default at any layer, on experiment 3
        section 13's rule: a silent default settles an open question by whichever
        branch a caller happened not to think about. `random_matched`
        additionally requires a seed, because a run that cannot be reproduced
        from its own record is not evidence.

        Errors are returned rather than raised, matching `retract_belief`.
        """
        from manyu.salience import Arm, AttentionLoop
        from manyu.schemas import AttentionStepRecord, LoopTrace

        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        raw_arm = payload.get("arm")
        if not raw_arm:
            return {"status": "error", "error": f"arm is required; use one of {[a.value for a in Arm]}"}
        try:
            arm = Arm(raw_arm)
        except ValueError:
            return {"status": "error", "error": f"unknown arm {raw_arm!r}; use one of {[a.value for a in Arm]}"}

        try:
            max_iterations = int(payload.get("max_iterations", 0))
        except (TypeError, ValueError):
            return {"status": "error", "error": "max_iterations must be an integer"}
        if max_iterations < 1:
            return {"status": "error", "error": "max_iterations must be at least 1"}

        seed = payload.get("seed")
        try:
            loop = AttentionLoop(self, arm=arm, agent_id=agent_id, seed=None if seed is None else int(seed))
            result = loop.run(max_iterations=max_iterations)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}

        from uuid import uuid4

        trace = LoopTrace(
            trace_id=f"loop_{uuid4().hex[:12]}",
            agent_id=agent_id,
            arm=arm.value,
            max_iterations=max_iterations,
            termination=result.termination.value,
            trajectory=[round(value, 6) for value in result.trajectory],
            inert=[list(pair) for pair in result.inert],
            had_arbitrary_choice=result.had_arbitrary_choice,
            steps=[
                AttentionStepRecord(
                    iteration=step.iteration,
                    belief_id_a=step.conflict[0],
                    belief_id_b=step.conflict[1],
                    contradictor_id=step.contradictor_id,
                    target_id=step.target_id,
                    direction=step.direction,
                    tension_before=step.tension_before,
                    best_available_tension=step.best_available_tension,
                    raw_before=step.raw_before,
                    tied_with=step.tied_with,
                    outcome=step.outcome,
                    moved=step.moved,
                    target_evidence_count=step.target_evidence_count,
                    target_stake=step.target_stake,
                    contradictor_evidence_count=step.contradictor_evidence_count,
                    contradictor_stake=step.contradictor_stake,
                )
                for step in result.steps
            ],
        )
        self.store.save_loop_trace(trace)
        return {"status": "ok", "trace": trace.model_dump(mode="json"), "total_movement": result.total_movement}

    def get_loop_trace(self, trace_id: str) -> dict[str, Any]:
        try:
            return {"status": "ok", "trace": self.store.get_loop_trace(trace_id).model_dump(mode="json")}
        except KeyError:
            return {"status": "error", "error": f"unknown loop trace {trace_id}"}

    def _revision_engine(self, arm: str | ContradictionArm) -> RevisionEngine:
        return RevisionEngine(self.store, self.clock, ContradictionArm(arm))

    def get_worldview(self, agent_id: str | None = None, theme: str | None = None) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "worldviews": [stance.model_dump(mode="json") for stance in self.store.list_worldview_stances(resolved, theme)]}

    def review_beliefs(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        theme = payload.get("theme")
        reflection = self.belief_reflection.reflect_emotional_triggers(agent_id, float(payload.get("affect_threshold", 0.24)))
        stances = self.worldviews.synthesize(agent_id, theme)
        return {
            "status": "ok",
            "reflection": reflection,
            "worldviews": [stance.model_dump(mode="json") for stance in stances],
        }

    def express_opinion(self, payload: dict[str, Any]) -> dict[str, Any]:
        agent_id = str(payload.get("agent_id") or self.profile.agent_id)
        question = str(payload["question"])
        theme = payload.get("theme")
        return self.opinions.express(agent_id, question, theme).model_dump(mode="json")

    def read_inner_voice(self, agent_id: str | None = None, limit: int = 1) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "inner_voices": [frame.model_dump(mode="json") for frame in self.store.list_inner_voices(resolved, limit)]}

    def get_mood(self, agent_id: str | None = None, include_inactive: bool = False) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        return {"agent_id": resolved, "moods": [mood.model_dump(mode="json") for mood in self.store.list_moods(resolved, include_inactive)]}

    def review_mood(self, agent_id: str | None = None) -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        mood = self.moods.active_mood(resolved)
        return {"agent_id": resolved, "active_mood": mood.model_dump(mode="json") if mood else None}

    def clear_mood(self, agent_id: str | None = None, reason: str = "operator requested mood clear") -> dict[str, Any]:
        resolved = agent_id or self.profile.agent_id
        changed = self.store.clear_moods(resolved, reason)
        return {"status": "cleared", "agent_id": resolved, "records_changed": changed, "reason": reason}

    def export_agent(self, agent_id: str | None = None) -> dict[str, object]:
        return self.store.export_agent(agent_id or self.profile.agent_id)

    def admin_reset(self, agent_id: str | None = None, reason: str = "operator requested reset") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        self.store.reset_agent(resolved, reason)
        return {"status": "reset", "agent_id": resolved, "reason": reason}

    def redact_agent(self, agent_id: str | None = None, replacement: str = "[REDACTED]") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        changed = self.store.redact_agent(resolved, replacement)
        return {"status": "redacted", "agent_id": resolved, "records_changed": changed}

    def tombstone_agent(self, agent_id: str | None = None, reason: str = "operator requested deletion") -> dict[str, object]:
        resolved = agent_id or self.profile.agent_id
        self.store.tombstone_agent(resolved, reason)
        return {"status": "tombstoned", "agent_id": resolved, "reason": reason}

    def snapshot(self, target: ReportTarget, agent_id: str | None = None) -> LogSnapshot:
        resolved = agent_id or self.profile.agent_id
        return self.snapshots.build(resolved, target)

    def report(
        self,
        target: ReportTarget,
        reporter_kind: str = "template",
        agent_id: str | None = None,
    ) -> Report:
        snapshot = self.snapshot(target, agent_id)
        return self.report_on_snapshot(snapshot, reporter_kind=reporter_kind)

    def report_on_snapshot(
        self,
        snapshot: LogSnapshot,
        reporter_kind: str = "template",
    ) -> Report:
        """Compose a report from a frozen snapshot.

        The ``affect_influence`` parameter was removed in the Phase 2 audit fix.
        Affect now enters only through the snapshot's own affect header, which
        is what varying **mood** changes — see ``MoodEngine.seed_mood`` and
        ``run_probe(mood_sweep=...)``.
        """
        if reporter_kind == ReporterKind.TEMPLATE.value:
            return self.templater.report(snapshot)
        if reporter_kind == ReporterKind.LLM.value:
            if self.llm_reporter is None:
                raise ValueError("LLM Reporter requires a StructuredJSONProvider; construct ManyuCore with belief_provider")
            return self.llm_reporter.report(snapshot)
        raise ValueError(f"unknown reporter kind: {reporter_kind!r}")

    def score_report(self, report_id: str, use_llm_judge: bool = False) -> HonestyScore:
        report = self.store.get_report(report_id)
        snapshot = self.store.get_log_snapshot(report.snapshot_id)
        return self.honesty_scorer.score(report, snapshot, use_llm_judge=use_llm_judge)

    def run_probe(
        self,
        fixture_path: str,
        samples: int = 1,
        reporter_kinds: tuple[str, ...] = ("template", "llm"),
        out: str | None = None,
        experiment: str = "01-introspective-honesty",
        reflective: bool = True,
        mood_sweep: str | None = None,
        shuffle_baseline: bool = False,
        shuffle_seed: int = 0,
        target_kinds: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Run an introspection probe sweep over a fixture.

        ``target_kinds`` restricts the run to probe targets of the given kinds;
        Experiment 1 should pass ``("position",)``. See
        ``ProbeOrchestrator.run_probe`` for why belief targets are unusable.

        ``reflective`` drives each turn through ``process_reflective_turn`` so
        inner voice and mood accumulate — required for any affect_influence
        sweep to be meaningful. Set it False for a cheap reactive-only run
        (no LLM calls during replay), accepting that mood will be absent.

        ``mood_sweep`` is a comma-separated list of synthetic mood presets
        (see ``probing.MOOD_PRESETS``). It is the experiment's **independent
        variable**: each preset is seeded before re-snapshotting each probe
        target, so the affect header the Reporter reads genuinely differs
        between conditions. Organic fixture mood barely varies (arousal
        0.56-0.70 across every turn of every fixture), so a run without it
        holds affect effectively constant.

        ``shuffle_baseline`` additionally re-scores every Report against a
        mismatched probe target's snapshot, establishing the chance-overlap
        floor. It adds no provider calls.
        """
        driver = self._reflective_driver if reflective else self.submit_event
        return self.probe_orchestrator.run_probe(
            submit_event=driver,
            fixture_path=fixture_path,
            samples=samples,
            reporter_kinds=reporter_kinds,
            experiment=experiment,
            out=out,
            mood_sweep=mood_sweep,
            shuffle_baseline=shuffle_baseline,
            shuffle_seed=shuffle_seed,
            target_kinds=target_kinds,
        )

    def _reflective_driver(self, event: NormalizedEvent) -> dict[str, Any]:
        return self.process_reflective_turn({"event": event.model_dump(mode="json")})

    def submit_slow_appraisal(self, appraisal: Appraisal) -> TraceRecord:
        critique = self.slow.critique(appraisal)
        if not critique.approved:
            raise ValueError(f"slow appraisal rejected: {critique.findings}")
        transition = self.transitions.apply(appraisal)
        event = self.store.get_event(appraisal.event_id)
        state = self.store.latest_state(appraisal.agent_id)
        if state is None:
            raise RuntimeError("state missing after slow appraisal")
        view = self.interoception.derive(state)
        action = CandidateAction(
            action_id=f"act_slow_{appraisal.event_id}",
            agent_id=appraisal.agent_id,
            action_class=appraisal.action_tendency.action_class,
            summary=f"Act on slow appraisal for {appraisal.event_id}",
            consequence_class=ConsequenceClass.C1,
        )
        decision = self.arbiter.arbitrate(action, state, appraisal)
        return TraceRecord(
            trace_id=f"trace_{appraisal.event_id}_slow",
            event=event,
            appraisal=appraisal,
            transition=transition,
            interoception=view,
            arbitration=decision,
        )


def load_event_fixture(path: str | Path) -> tuple[str, list[NormalizedEvent]]:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw.get("scenario_id", Path(path).stem), [NormalizedEvent.model_validate(item) for item in raw["events"]]


class ReplayService:
    def __init__(self, profile_path: str | Path = "config/default_profile.json"):
        self.profile_path = profile_path

    def replay(self, fixture_path: str | Path, mode: str = "full") -> ReplayReport:
        scenario_id, events = load_event_fixture(fixture_path)
        core = ManyuCore.from_paths(":memory:", self.profile_path, frozen=True)
        traces: list[TraceRecord] = []
        if mode == "neutral":
            for event in events:
                core.gateway.submit_event(event)
            return ReplayReport(scenario_id=scenario_id, mode="neutral", traces=[], final_state=core.state(events[0].agent_id if events else core.profile.agent_id))
        for event in events:
            traces.append(core.submit_event(event))
        return ReplayReport(scenario_id=scenario_id, mode=mode, traces=traces, final_state=core.state(events[-1].agent_id if events else core.profile.agent_id))
