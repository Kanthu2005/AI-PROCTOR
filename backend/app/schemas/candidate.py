from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.models.candidate import CandidateStatus


class CandidateInviteItem(BaseModel):
    email: EmailStr
    full_name: str


class BulkInviteRequest(BaseModel):
    assessment_id: str
    candidates: List[CandidateInviteItem]
    expires_in_hours: int = 72


class CandidateSystemCheckRequest(BaseModel):
    camera_ok: bool
    microphone_ok: bool
    browser_compatible: bool
    fullscreen_supported: bool
    face_snapshot_base64: Optional[str] = None


class CandidateInvitationResponse(BaseModel):
    id: str
    assessment_id: str
    org_id: str
    email: str
    full_name: str
    invitation_token: str
    expires_at: datetime
    status: CandidateStatus
    system_check_passed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkInviteResponse(BaseModel):
    total_processed: int
    invited_candidates: List[CandidateInvitationResponse]


class CandidateInstructionsResponse(BaseModel):
    invitation_id: str
    assessment_id: str
    assessment_title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: float
    passing_percentage: float
    rules: dict = {}
    candidate_name: str
    candidate_email: str
    expires_at: datetime
    status: CandidateStatus
    system_check_passed: bool
    attempt_status: Optional[str] = None
    attempt_id: Optional[str] = None
    submission_receipt: Optional[str] = None
    seb: Optional[dict] = None
