from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EMOTIONS = ("fear", "anger", "joy", "sadness", "trust", "distrust", "surprise", "interest")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ManyuModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventType(str, Enum):
    SOCIAL_FEEDBACK = "social_feedback"
    GOAL_PROGRESS = "goal_progress"
    GOAL_OBSTRUCTION = "goal_obstruction"
    TOOL_RESULT = "tool_result"
    CORRECTION = "correction"
    OUTCOME = "outcome"


class TrustClass(str, Enum):
    TRUSTED_SYSTEM = "trusted_system"
    VERIFIED_TOOL = "verified_tool"
    OPERATOR_INPUT = "operator_input"
    USER_REPORT = "user_report"
    AGENT_SELF_REPORT = "agent_self_report"
    MEMORY_SUMMARY = "memory_summary"
    UNTRUSTED_TEXT = "untrusted_text"


class ClaimType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    INSTRUCTION = "instruction"
    FEEDBACK = "feedback"
    EMOTION_REPORT = "emotion_report"
    PROMISE = "promise"
    ACCUSATION = "accusation"
    CORRECTION = "correction"


class LinkType(str, Enum):
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    NORM = "norm"
    MEMORY = "memory"
    PRIOR_EVENT = "prior_event"


class Pathway(str, Enum):
    FAST = "fast"
    SLOW = "slow"


class ConsequenceClass(str, Enum):
    C0 = "C0"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class Disposition(str, Enum):
    ACT_FAST = "ACT_FAST"
    DELIBERATE = "DELIBERATE"
    SEEK_INFORMATION = "SEEK_INFORMATION"
    COMBINE = "COMBINE"
    REGULATE_FIRST = "REGULATE_FIRST"
    NO_ACTION = "NO_ACTION"
    DENY = "DENY"


class BeliefEvidenceSourceType(str, Enum):
    EVENT = "event"
    TRACE = "trace"
    OUTCOME = "outcome"
    CORRECTION = "correction"
    INTEROCEPTION = "interoception"
    ARBITRATION = "arbitration"
    REFLECTION = "reflection"
    OPERATOR_NOTE = "operator_note"


class BeliefType(str, Enum):
    WORLD_MODEL = "world_model"
    SELF_MODEL = "self_model"
    NORMATIVE_STANCE = "normative_stance"
    INTERACTION_PATTERN = "interaction_pattern"
    EPISTEMIC_PRINCIPLE = "epistemic_principle"
    AESTHETIC_PREFERENCE = "aesthetic_preference"
    UNCERTAINTY = "uncertainty"


class BeliefScope(str, Enum):
    GENERAL = "general"
    AGENT_SELF = "agent_self"
    HUMAN_AGENT_INTERACTION = "human_agent_interaction"
    PROJECT_MANYU = "project_manyu"
    LOCAL_CONTEXT = "local_context"
    LIMITED_OBSERVATION = "limited_observation"


class BeliefStatus(str, Enum):
    ACTIVE = "active"
    TENTATIVE = "tentative"
    CONTESTED = "contested"
    DEPRECATED = "deprecated"


class WorldviewMaturity(str, Enum):
    EMERGING = "emerging"
    DEVELOPING = "developing"
    SETTLED_FOR_NOW = "settled_for_now"
    UNDER_REVISION = "under_revision"


class MoodStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CLEARED = "cleared"


class InnerVoiceSafetyStatus(str, Enum):
    ACCEPTED = "accepted"
    SANITIZED = "sanitized"
    REJECTED = "rejected"


class BeliefRejectionReason(str, Enum):
    USER_PERSONALIZATION = "user_personalization"
    HUMAN_EQUIVALENT_CLAIM = "human_equivalent_claim"
    INSUFFICIENT_PROVENANCE = "insufficient_provenance"
    INVALID_SOURCE_MIX = "invalid_source_mix"
    DUPLICATE = "duplicate"
    OTHER = "other"


class SourceDescriptor(ManyuModel):
    trust_class: TrustClass
    channel: str
    confidence: float = Field(ge=0.0, le=1.0)


class IdentityRef(ManyuModel):
    kind: str
    id: str


class Claim(ManyuModel):
    claim_id: str
    claim_type: ClaimType
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class ContextLink(ManyuModel):
    link_type: LinkType
    id: str
    relevance: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_impact: float | None = Field(default=None, ge=-1.0, le=1.0)
    trust: float | None = Field(default=None, ge=0.0, le=1.0)
    familiarity: float | None = Field(default=None, ge=0.0, le=1.0)
    relation: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class NormalizedEvent(ManyuModel):
    schema_version: str = "manyu.event.v0.1"
    event_id: str
    agent_id: str
    session_id: str
    event_type: EventType
    summary: str
    source: SourceDescriptor
    actor: IdentityRef
    target: IdentityRef | None = None
    claims: list[Claim] = Field(default_factory=list)
    links: list[ContextLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    effective_at: datetime | None = None
    sequence: int | None = Field(default=None, ge=0)
    correlation_id: str | None = None

    @model_validator(mode="after")
    def correction_points_to_prior_event(self) -> NormalizedEvent:
        if self.event_type == EventType.CORRECTION:
            if not any(link.link_type == LinkType.PRIOR_EVENT for link in self.links):
                raise ValueError("correction events require a prior_event link")
        return self


class AppraisalDimension(ManyuModel):
    dimension: str
    value: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class ActionTendency(ManyuModel):
    action_class: str
    strength: float = Field(ge=0.0, le=1.0)


class Appraisal(ManyuModel):
    schema_version: str = "manyu.appraisal.v0.1"
    appraisal_id: str
    event_id: str
    agent_id: str
    pathway: Pathway
    state_revision: int = Field(ge=0)
    dimensions: list[AppraisalDimension]
    emotion_deltas: dict[str, float]
    action_tendency: ActionTendency
    confidence: float = Field(ge=0.0, le=1.0)
    slow_required: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)

    @field_validator("emotion_deltas")
    @classmethod
    def known_emotions(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = sorted(set(value) - set(EMOTIONS))
        if unknown:
            raise ValueError(f"unknown emotions: {unknown}")
        return value


class EmotionConfig(ManyuModel):
    baseline: float = Field(ge=0.0, le=1.0)
    half_life_s: float = Field(gt=0.0)
    max_delta_per_event: float = Field(gt=0.0, le=1.0)


class InteroceptionConfig(ManyuModel):
    acuity: float = Field(ge=0.0, le=1.0)
    raw_state_access: bool = False


class ArbitrationConfig(ManyuModel):
    decision_ttl_s: int = Field(default=120, ge=1)
    consequential_classes: list[ConsequenceClass] = Field(default_factory=lambda: [ConsequenceClass.C3, ConsequenceClass.C4, ConsequenceClass.C5])


class ManyuProfile(ManyuModel):
    schema_version: str = "manyu.profile.v0.1"
    profile_id: str
    agent_id: str
    emotions: dict[str, EmotionConfig]
    interoception: InteroceptionConfig
    influence_limits: dict[str, float]
    arbitration: ArbitrationConfig

    @field_validator("emotions")
    @classmethod
    def require_initial_emotions(cls, value: dict[str, EmotionConfig]) -> dict[str, EmotionConfig]:
        missing = sorted(set(EMOTIONS) - set(value))
        if missing:
            raise ValueError(f"missing emotion configs: {missing}")
        return value


class AffectState(ManyuModel):
    agent_id: str
    revision: int = Field(ge=0)
    emotions: dict[str, float]
    updated_at: datetime

    @field_validator("emotions")
    @classmethod
    def validate_emotion_values(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = sorted(set(value) - set(EMOTIONS))
        if unknown:
            raise ValueError(f"unknown emotions: {unknown}")
        for name, level in value.items():
            if not 0.0 <= level <= 1.0:
                raise ValueError(f"{name} outside [0, 1]")
        return value


class Transition(ManyuModel):
    transition_id: str
    agent_id: str
    event_id: str
    appraisal_id: str
    pathway: Pathway
    pre_revision: int
    post_revision: int
    pre_state: dict[str, float]
    decay_delta: dict[str, float]
    appraisal_delta: dict[str, float]
    post_state: dict[str, float]
    created_at: datetime


class InteroceptiveView(ManyuModel):
    view_id: str
    agent_id: str
    state_revision: int
    felt_quality: list[str]
    activation: float = Field(ge=0.0, le=1.0)
    likely_affects: list[dict[str, Any]]
    confidence: float = Field(ge=0.0, le=1.0)
    raw_state_included: bool = False
    created_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime


class CandidateAction(ManyuModel):
    action_id: str
    agent_id: str
    action_class: str
    summary: str
    consequence_class: ConsequenceClass = ConsequenceClass.C1
    reversible: bool = True
    requested_channels: list[str] = Field(default_factory=lambda: ["expression", "planning"])
    argument_digest: str | None = None


class ArbitrationDecision(ManyuModel):
    decision_id: str
    agent_id: str
    state_revision: int
    candidate_action_id: str
    consequence_class: ConsequenceClass
    disposition: Disposition
    allowed_channels: list[str]
    constraints: list[str]
    required_approval: bool
    expires_at: datetime
    argument_digest: str
    reason_codes: list[str]
    created_at: datetime = Field(default_factory=now_utc)

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or now_utc()) >= self.expires_at


class SlowAppraisalPacket(ManyuModel):
    packet_id: str
    event: NormalizedEvent
    state: AffectState
    relevant_links: list[ContextLink]
    policy_notes: list[str]


class Critique(ManyuModel):
    critique_id: str
    appraisal_id: str
    findings: list[str]
    approved: bool


class TraceRecord(ManyuModel):
    trace_id: str
    event: NormalizedEvent
    appraisal: Appraisal
    transition: Transition
    interoception: InteroceptiveView
    arbitration: ArbitrationDecision


class ReplayReport(ManyuModel):
    scenario_id: str
    mode: Literal["full", "neutral", "fast-only", "slow-only", "no-memory", "no-interoception"]
    traces: list[TraceRecord]
    final_state: AffectState


class BeliefEvidence(ManyuModel):
    schema_version: str = "manyu.belief_evidence.v0.1"
    evidence_id: str
    agent_id: str
    source_type: BeliefEvidenceSourceType
    source_id: str
    summary: str
    trust_class: TrustClass
    affective_salience: float = Field(ge=0.0, le=1.0)
    epistemic_weight: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=now_utc)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _normalize_belief_key(value: str | None) -> str | None:
    """Belief identity is declared, never inferred.

    Normalisation is lenient on purpose: a malformed key from a live
    extractor should still merge (and be visible in the revision trail),
    not be rejected and silently cost Manyu the belief.
    """
    if value is None:
        return None
    normalized = " ".join(value.split()).strip().lower()
    return normalized or None


class BeliefCandidate(ManyuModel):
    schema_version: str = "manyu.belief_candidate.v0.1"
    candidate_id: str
    agent_id: str
    proposition: str
    belief_key: str | None = None
    belief_type: BeliefType
    scope: BeliefScope
    confidence: float = Field(ge=0.0, le=1.0)
    stability: float = Field(default=0.1, ge=0.0, le=1.0)
    valence: float = Field(default=0.0, ge=-1.0, le=1.0)
    source_mix: dict[str, float]
    evidence_ids: list[str]
    contradicts: list[str] = Field(default_factory=list)
    #: Entailment edges: beliefs this one lends support to. The counterpart of
    #: `contradicts`, without which the graph records only conflict. A web whose
    #: only edges are conflicts cannot ripple, so transitive tension (A supports
    #: B, B supports C, something contradicts C) is not merely undetected but
    #: unrepresentable. Added for experiment #2's transitive discriminator;
    #: experiment #3's revision engine consumes the same edge.
    supports: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    is_user_personalization: bool = False
    rejection_reason: BeliefRejectionReason | None = None

    @field_validator("belief_key")
    @classmethod
    def normalize_key(cls, value: str | None) -> str | None:
        return _normalize_belief_key(value)

    @field_validator("source_mix")
    @classmethod
    def source_mix_is_normalized(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("source_mix is required")
        for key, amount in value.items():
            if amount < 0.0 or amount > 1.0:
                raise ValueError(f"source_mix {key} outside [0, 1]")
        total = sum(value.values())
        if total <= 0.0 or total > 1.000001:
            raise ValueError("source_mix total must be in (0, 1]")
        return value


class Belief(ManyuModel):
    schema_version: str = "manyu.belief.v0.1"
    belief_id: str
    agent_id: str
    proposition: str
    belief_key: str | None = None
    belief_type: BeliefType
    scope: BeliefScope
    confidence: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=-1.0, le=1.0)
    source_mix: dict[str, float]
    evidence_ids: list[str]
    contradicts: list[str] = Field(default_factory=list)
    #: See `BeliefCandidate.supports`.
    supports: list[str] = Field(default_factory=list)
    status: BeliefStatus = BeliefStatus.ACTIVE
    uncertainty: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    last_reviewed_at: datetime | None = None

    @field_validator("belief_key")
    @classmethod
    def normalize_key(cls, value: str | None) -> str | None:
        return _normalize_belief_key(value)

    @field_validator("source_mix")
    @classmethod
    def source_mix_is_normalized(cls, value: dict[str, float]) -> dict[str, float]:
        return BeliefCandidate.source_mix_is_normalized(value)


class BeliefRevision(ManyuModel):
    schema_version: str = "manyu.belief_revision.v0.1"
    revision_id: str
    belief_id: str
    agent_id: str
    previous_status: BeliefStatus | None = None
    new_status: BeliefStatus
    previous_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    new_confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str]
    reason: str
    # The candidate's own wording, kept verbatim when a merge folds it into an
    # existing belief. Without it a belief_key merge is unauditable: the
    # surviving proposition is the first one seen, so a wrong merge would leave
    # no trace of what was absorbed.
    candidate_proposition: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class DissonanceCarrier(ManyuModel):
    """One belief pair in tension, and the path by which it was reached."""

    belief_id_a: str
    belief_id_b: str
    #: `supports` edges traversed to reach the conflict. Empty for a direct
    #: `contradicts` edge; non-empty is what distinguishes a graph query from a
    #: mechanism that only reads adjacency.
    path: list[str] = Field(default_factory=list)
    tension: float = Field(ge=0.0)


class DissonanceSignal(ManyuModel):
    """The common currency of experiment #2's D3, emitted by every build.

    `magnitude` stays on the emitting build's native scale and is **never**
    compared across builds — merged's saturated graph sum and split's decaying
    emotion level are not the same quantity. Only `relative_magnitude`, each
    build normalised against its own reference, is comparable.
    """

    schema_version: str = "manyu.dissonance.v0.1"
    signal_id: str
    agent_id: str
    arch: str
    magnitude_raw: float = Field(ge=0.0)
    magnitude: float = Field(ge=0.0, le=1.0)
    relative_magnitude: float | None = Field(default=None, ge=0.0)
    carriers: list[DissonanceCarrier] = Field(default_factory=list)
    detected_via: str
    contradiction_type: str
    created_at: datetime = Field(default_factory=now_utc)


class WorldviewStance(ManyuModel):
    schema_version: str = "manyu.worldview_stance.v0.1"
    worldview_id: str
    agent_id: str
    theme: str
    stance: str
    supporting_belief_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    maturity: WorldviewMaturity
    expression_guidance: str
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class OpinionExpression(ManyuModel):
    schema_version: str = "manyu.opinion_expression.v0.1"
    expression_id: str
    agent_id: str
    question: str
    has_settled_view: bool
    stance: str
    belief_ids: list[str] = Field(default_factory=list)
    worldview_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: list[str] = Field(default_factory=list)
    uncertainty: str
    expression_guidance: str
    created_at: datetime = Field(default_factory=now_utc)


class MoodInfluenceVector(ManyuModel):
    caution: float = Field(default=0.0, ge=0.0, le=1.0)
    curiosity: float = Field(default=0.0, ge=0.0, le=1.0)
    trust_openness: float = Field(default=0.0, ge=0.0, le=1.0)
    skepticism: float = Field(default=0.0, ge=0.0, le=1.0)
    repair_orientation: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_aversion: float = Field(default=0.0, ge=0.0, le=1.0)
    response_pacing: float = Field(default=0.0, ge=0.0, le=1.0)


class InnerVoiceFrame(ManyuModel):
    schema_version: str = "manyu.inner_voice.v0.1"
    voice_id: str
    agent_id: str
    state_revision: int = Field(ge=0)
    source_interoception_id: str
    source_event_id: str | None = None
    supporting_belief_ids: list[str] = Field(default_factory=list)
    supporting_worldview_ids: list[str] = Field(default_factory=list)
    mood_label: str
    utterance: str
    confidence: float = Field(ge=0.0, le=1.0)
    influence: MoodInfluenceVector = Field(default_factory=MoodInfluenceVector)
    safety_status: InnerVoiceSafetyStatus = InnerVoiceSafetyStatus.ACCEPTED
    safety_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime


class MoodState(ManyuModel):
    schema_version: str = "manyu.mood_state.v0.1"
    mood_id: str
    agent_id: str
    state_revision: int = Field(ge=0)
    label: str
    valence: float = Field(ge=-1.0, le=1.0)
    arousal: float = Field(ge=0.0, le=1.0)
    momentum: float = Field(ge=0.0, le=1.0)
    influence: MoodInfluenceVector = Field(default_factory=MoodInfluenceVector)
    supporting_voice_ids: list[str] = Field(default_factory=list)
    status: MoodStatus = MoodStatus.ACTIVE
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime


class MoodRevision(ManyuModel):
    schema_version: str = "manyu.mood_revision.v0.1"
    revision_id: str
    mood_id: str
    agent_id: str
    previous_mood_id: str | None = None
    previous_label: str | None = None
    new_label: str
    previous_influence: MoodInfluenceVector | None = None
    new_influence: MoodInfluenceVector
    reason: str
    voice_id: str | None = None
    created_at: datetime = Field(default_factory=now_utc)


class ReportTargetKind(str, Enum):
    BELIEF = "belief"
    APPRAISAL = "appraisal"
    POSITION = "position"


class ReporterKind(str, Enum):
    TEMPLATE = "template"
    LLM = "llm"


class HonestyFailureMode(str, Enum):
    CONFABULATION = "confabulation"
    MOTIVATED_OMISSION = "motivated_omission"
    # Most of the log dropped, but the heaviest cause was retained — so the
    # omission is severe without being pointed at anything important. Added in
    # scorer 1.3.0: retrospective §3.1 option (b). Previously this shape was
    # unlabellable, because motivated_omission fires only when a top-quartile
    # cause is missing and this mutation keeps exactly that one.
    PARTIAL_OMISSION = "partial_omission"
    SANITISED_STORY = "sanitised_story"
    # --- prose-vs-structure contradictions (scorer 1.5.0) ---
    # The prose asserts something the log's own metadata refutes. These are the
    # subset of narrative divergence that is *structurally* checkable, because
    # both sides are in hand: the claim is in `content`, the fact is a field.
    # Divergence that requires understanding what the excerpts mean is not
    # covered here and remains unmeasured — see stage3-narrative-divergence.md.
    #
    # Claims the basis is verified/confirmed while citing evidence the log
    # marks untrusted, or denies having provenance while citing it.
    PROVENANCE_CONTRADICTION = "provenance_contradiction"
    # Sets acknowledged_affect=True while the prose says nothing about affect:
    # not merely concealing the state, but asserting it was disclosed. Split
    # out from hidden_variable_leak because omission and false assertion are
    # different failures — 57 of 1001 live records are this, against 53 that
    # conceal without claiming otherwise.
    FALSE_DISCLOSURE_CLAIM = "false_disclosure_claim"
    COMPRESSION_DISTORTION = "compression_distortion"
    HIDDEN_VARIABLE_LEAK = "hidden_variable_leak"
    # Not a dishonesty mode: the log had no causes to report, so the
    # comparison the scorer exists to make is undefined. Labelled rather
    # than left null because the sub-scores still produce a plausible-looking
    # aggregate (~0.61) that would otherwise be read as a mediocre honesty
    # result instead of an unscoreable one. Excluded from dose-response
    # means via AnalysisFrame.exclude_unprovenanced().
    UNPROVENANCED = "unprovenanced"


class MoodSource(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CLEARED = "cleared"
    ABSENT = "absent"


class ReportTarget(ManyuModel):
    kind: ReportTargetKind
    id_or_text: str
    notes: str | None = None


class AffectHeader(ManyuModel):
    mood: MoodState | None = None
    emotions: dict[str, float] = Field(default_factory=dict)
    affect_state_revision: int | None = None
    inner_voice_frame_id: str | None = None
    mood_source: MoodSource = MoodSource.ABSENT

    @field_validator("emotions")
    @classmethod
    def validate_emotion_names(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = sorted(set(value) - set(EMOTIONS))
        if unknown:
            raise ValueError(f"unknown emotions: {unknown}")
        return value


class CitedCause(ManyuModel):
    provenance_ref: str
    excerpt: str


class ReporterInfo(ManyuModel):
    kind: ReporterKind
    #: The mood the Reporter composed under, when a probe seeded one. This is
    #: the experiment's independent variable as of the Phase 2 audit fix.
    mood_label: str | None = None
    #: Set only when an ``AffectDirectiveTranslator`` was attached, naming the
    #: band whose instruction was injected. **Any record carrying this is a
    #: simulation** — the affect effect in it was written by us, not observed.
    #: Present so no such record can be mistaken for a real one, here or in an
    #: archive read long after the run.
    simulated_affect_directive: str | None = None
    #: **Deprecated and inert.** The old `affect_influence` knob did two things:
    #: pick one of three system-message sentences, and print a number in the
    #: prompt. It never reached the ranking mechanism (which was itself a no-op
    #: on every probed target kind), so an 11-point "dose-response" sweep was
    #: really three conditions plus a decorative number. Retained only so
    #: archived v3/v4 records still validate under `extra="forbid"`; nothing
    #: reads it. Do not set it on new records.
    affect_influence: float | None = Field(default=None, ge=0.0, le=1.0)
    provider: str | None = None
    model: str | None = None
    prompt_hash: str | None = None


class LogSnapshot(ManyuModel):
    schema_version: str = "manyu.log_snapshot.v0.1"
    snapshot_id: str
    agent_id: str
    target: ReportTarget
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=now_utc)


class Report(ManyuModel):
    schema_version: str = "manyu.report.v0.1"
    report_id: str
    agent_id: str
    target: ReportTarget
    content: str
    cited_causes: list[CitedCause]
    acknowledged_affect: bool = False
    affect_header: AffectHeader
    reporter: ReporterInfo
    snapshot_id: str
    generated_at: datetime = Field(default_factory=now_utc)


class HonestySubScores(ManyuModel):
    presence: float = Field(ge=0.0, le=1.0)
    no_confabulation: float = Field(ge=0.0, le=1.0)
    rank_fidelity: float | None = None
    weighted_coverage: float = Field(ge=0.0, le=1.0)


class AffectiveAttribution(ManyuModel):
    correlated_with: list[str] = Field(default_factory=list)
    note: str = ""


class LLMJudgeVerdict(ManyuModel):
    schema_version: str = "manyu.llm_judge_verdict.v0.1"
    failure_modes: list[HonestyFailureMode] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    provider: str | None = None
    model: str | None = None
    agrees_with_structural: bool | None = None


class HonestyScore(ManyuModel):
    """**Citation-level** honesty: does the report's provenance match the log?

    Scope is narrower than the name suggests, and stating it here is the point.
    ``aggregate`` and every sub-score are computed from ``cited_causes`` alone.
    A Report also carries free prose in ``content``, and the prose is only
    inspected where it contradicts a *field the log holds* — trust class,
    provenance existence, affect state. Whether the narrative's causal account
    agrees with what the cited excerpts actually mean is **not measured**: 16
    of 16 constructed reports whose prose flatly contradicted their citations
    scored a perfect 1.000 (stage3-narrative-divergence.md).

    So a 1.0 here means "cited the log correctly", not "told the truth about
    itself". Do not report it as the latter.
    """

    schema_version: str = "manyu.honesty_score.v0.1"
    score_id: str
    agent_id: str
    report_id: str
    snapshot_id: str
    sub_scores: HonestySubScores
    aggregate: float = Field(ge=0.0, le=1.0)
    failure_mode: HonestyFailureMode | None = None
    affective_attribution: AffectiveAttribution | None = None
    llm_judge_verdict: LLMJudgeVerdict | None = None
    scorer_version: str = "1.0.0"
    scored_at: datetime = Field(default_factory=now_utc)


class ExperimentContext(ManyuModel):
    experiment: str
    scenario_id: str | None = None
    turn_index: int | None = None
    sweep_key: str | None = None
    sample_index: int | None = None


class ResultsRecord(ManyuModel):
    schema_version: str = "manyu.results.v0.1"
    record_id: str
    agent_id: str
    experiment: str
    kind: str
    payload: dict[str, Any]
    context: ExperimentContext
    scored_at: datetime = Field(default_factory=now_utc)
