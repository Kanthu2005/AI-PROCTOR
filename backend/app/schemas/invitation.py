from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any


class CandidateInviteEmailItem(BaseModel):
    email: EmailStr
    full_name: str


class SendExamInvitationsRequest(BaseModel):
    candidates: List[CandidateInviteEmailItem] = Field(..., min_length=1)
    expires_in_hours: int = Field(default=72, ge=1, le=720)


class ExamInvitationPreviewRequest(BaseModel):
    sample_name: Optional[str] = None
    sample_email: Optional[str] = None


class ExamInvitationPreviewResponse(BaseModel):
    subject: str
    html: str
    text: str
    context: Dict[str, Any]


class DeliveryAttemptSummary(BaseModel):
    id: str
    attempt_type: str
    status: str
    provider: str
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class ExamInvitationItemResponse(BaseModel):
    id: str
    assessment_id: str
    assessment_title: Optional[str] = None
    candidate_id: Optional[str] = None
    recipient_email: str
    recipient_name: str
    status: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    opened_at: Optional[str] = None
    expires_at: Optional[str] = None
    provider_message_id: Optional[str] = None
    last_error: Optional[str] = None
    created_at: Optional[str] = None
    delivery_attempts_count: int = 0
    delivery_attempts: List[DeliveryAttemptSummary] = []
    secure_exam_link: Optional[str] = None
    candidate_invitation_token: Optional[str] = None


class SendExamInvitationsResponse(BaseModel):
    total_processed: int
    total_sent: int
    total_failed: int
    invitations: List[Dict[str, Any]]


class InvitationValidateResponse(BaseModel):
    valid: bool
    assessment_id: str
    assessment_title: str
    assessment_description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: float
    passing_percentage: float
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    schedule_status: str
    time_until_start_seconds: int = 0
    can_start: bool
    expires_at: str
    candidate_name: str
    candidate_email: str
    candidate_status: str
    attempt_status: Optional[str] = None
    system_check_passed: bool
    proctoring_required: bool
    fullscreen_enforced: bool
    seb_required: bool


class EmailWebhookRequest(BaseModel):
    type: str
    data: Dict[str, Any]
