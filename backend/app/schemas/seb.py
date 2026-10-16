from typing import Optional, List
from pydantic import BaseModel, Field


class SEBClientDiagnosticRequest(BaseModel):
    assessment_id: Optional[str] = None
    invitation_token: Optional[str] = None
    request_url: Optional[str] = None
    seb_request_hash: Optional[str] = None
    seb_config_key_hash: Optional[str] = None
    user_agent: Optional[str] = None


class SEBClientDiagnosticResponse(BaseModel):
    is_seb_verified: bool
    verification_mechanism: str
    platform_detected: str
    matched_key_type: Optional[str] = None
    failure_reason: Optional[str] = None
    lockdown_guaranteed: bool
    supported_mechanisms: List[str] = ["CONFIG_KEY_HASH", "BEK_REQUEST_HASH", "JS_API_SESSION_KEY"]


class SEBLaunchInfoResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    seb_required: bool
    config_download_url: str
    seb_protocol_url: str
    supported_platforms: List[str] = ["Windows", "macOS", "iOS"]
    lockdown_instructions: List[str]


class SEBQuitResponse(BaseModel):
    message: str
    can_quit: bool
    quit_url: Optional[str] = None
