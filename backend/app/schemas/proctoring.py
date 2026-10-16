from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.proctoring import EventType, IncidentSeverity
from app.models.attempt import RiskLevel, HumanReviewStatus


class ProctoringEventIngest(BaseModel):
    client_event_id: Optional[str] = None
    event_type: EventType
    metadata: Dict[str, Any] = {}
    snapshot_base64: Optional[str] = None
    evidence_ref: Optional[str] = None
    client_timestamp: Optional[datetime] = None


class ProctoringEventResponse(BaseModel):
    id: str
    attempt_id: str
    event_type: EventType
    severity: IncidentSeverity
    risk_points: float
    metadata_json: Dict[str, Any]
    occurred_at: datetime
    current_attempt_risk_score: float
    current_risk_level: RiskLevel
    disqualified: bool = False
    disqualification_reason: Optional[str] = None
    is_deduplicated: bool = False
    explanation: Optional[str] = None
    rule_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewIncidentRequest(BaseModel):
    status: HumanReviewStatus
    proctor_notes: Optional[str] = None
    is_escalated: Optional[bool] = False
    escalated_to_role: Optional[str] = None  # e.g., ORG_ADMIN, LEAD_PROCTOR
    escalation_reason: Optional[str] = None


class ReviewerDecisionResponse(BaseModel):
    id: str
    attempt_id: str
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    decision: str
    comments: Optional[str] = None
    is_escalated: bool = False
    escalated_to_role: Optional[str] = None
    escalation_reason: Optional[str] = None
    risk_score_snapshot: float = 0.0
    rule_version: str = "2026.1-explainable"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LiveProctorCandidateFeed(BaseModel):
    attempt_id: str
    candidate_name: str
    candidate_email: str
    assessment_title: str
    status: str
    remaining_seconds: int
    risk_score: float
    risk_level: RiskLevel
    human_review_status: HumanReviewStatus
    total_violations: int
    tab_switch_count: int
    is_escalated: bool = False
    escalated_to_role: Optional[str] = None
    last_event: Optional[Dict[str, Any]] = None


class EvidenceAccessAuditResponse(BaseModel):
    id: str
    attempt_id: str
    incident_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    action: str = "EVIDENCE_VIEW"
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrivacyNoticeResponse(BaseModel):
    title: str
    data_collected: List[str]
    purpose: str
    ai_use_policy: str
    retention_period_days: int
    candidate_rights: str


class EvidencePurgeRequest(BaseModel):
    retention_days: Optional[int] = None
    assessment_id: Optional[str] = None


class EvidencePurgeResponse(BaseModel):
    purged_incidents_count: int
    retention_cutoff: datetime
    message: str
