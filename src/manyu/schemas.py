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
