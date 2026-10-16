import hashlib
import hmac
import plistlib
import re
from urllib.parse import urlparse, urlunparse
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentRule
from app.models.candidate import CandidateInvitation
from app.models.attempt import Attempt


class SEBVerificationResult(BaseModel):
    is_valid: bool
    error_code: Optional[str] = None
    detail: str
    mechanism: str = "NONE"  # CONFIG_KEY_HASH, BEK_REQUEST_HASH, NOT_REQUIRED
    matched_key_type: Optional[str] = None
    platform: str = "Unknown"
    lockdown_guaranteed: bool = False


class SafeExamBrowserService:
    @staticmethod
    def compute_request_hash(url: str, key: str) -> str:
        """
        Calculates SHA-256(url + key) as defined by the official Safe Exam Browser specification.
        The URL must be the exact absolute URL of the HTTP request, and the key is either the
        Browser Exam Key (BEK) or Config Key (CK).
        """
        raw = f"{url.strip()}{key.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def compute_config_key(config_dict: dict) -> str:
        """
        Computes a deterministic SHA-256 hash of a configuration dictionary
        to simulate or pre-calculate the official SEB Config Key.
        """
        import json
        canonical = json.dumps(config_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def detect_platform(user_agent: Optional[str]) -> str:
        """
        Parses User-Agent for diagnostic telemetry only.
        IMPORTANT: User-Agent alone is NEVER treated as proof of lockdown or identity!
        """
        if not user_agent:
            return "Unknown"
        ua = user_agent.lower()
        if "iphone" in ua or "ipad" in ua or "ios" in ua:
            return "iOS"
        elif "macintosh" in ua or "mac os" in ua or "darwin" in ua:
            return "macOS"
        elif "windows" in ua or "win32" in ua or "win64" in ua:
            return "Windows"
        return "Unknown"

    @staticmethod
    def generate_candidate_urls(request_url: str) -> List[str]:
        """
        Generates sensible canonical URL candidates to handle common reverse-proxy
        and default-port variations while maintaining cryptographic exactness.
        """
        candidates = [request_url.strip()]
        parsed = urlparse(request_url.strip())

        # Variation 1: Toggle scheme http <-> https (common behind TLS termination proxies)
        alt_scheme = "https" if parsed.scheme == "http" else "http"
        alt_parsed = parsed._replace(scheme=alt_scheme)
        candidates.append(urlunparse(alt_parsed))

        # Variation 2: Strip standard ports (:80 on http, :443 on https)
        netloc = parsed.netloc
        if (parsed.scheme == "http" and ":80" in netloc) or (parsed.scheme == "https" and ":443" in netloc):
            clean_netloc = re.sub(r":(80|443)$", "", netloc)
            candidates.append(urlunparse(parsed._replace(netloc=clean_netloc)))
            candidates.append(urlunparse(alt_parsed._replace(netloc=clean_netloc)))

        return list(dict.fromkeys(candidates))

    @classmethod
    def verify_seb_request(
        cls,
        assessment: Assessment,
        request_url: str,
        request_hash: Optional[str] = None,
        config_key_hash: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SEBVerificationResult:
        """
        Cryptographically validates that an incoming HTTP request originated from an authentic,
        correctly configured Safe Exam Browser instance.

        Guarantees:
        - Rejects ordinary browsers, query-parameter tampering (?seb=true), and spoofed User-Agents.
        - Uses constant-time comparison (hmac.compare_digest) to eliminate timing side-channel attacks.
        - Verifies against configured Config Key (CK) and/or platform Browser Exam Keys (BEK).
        """
        rules: Optional[AssessmentRule] = assessment.rules
        platform = cls.detect_platform(user_agent)

        # 1. Assessment does not require Safe Exam Browser
        if not rules or not rules.seb_required:
            return SEBVerificationResult(
                is_valid=True,
                mechanism="NOT_REQUIRED",
                detail="Safe Exam Browser is not enforced for this assessment.",
                platform=platform,
                lockdown_guaranteed=False
            )

        # 2. Check for missing cryptographic evidence
        if not request_hash and not config_key_hash:
            return SEBVerificationResult(
                is_valid=False,
                error_code="SEB_CLIENT_REQUIRED",
                detail="This assessment requires Safe Exam Browser. No cryptographic verification headers (X-SafeExamBrowser-RequestHash or X-SafeExamBrowser-ConfigKeyHash) were received.",
                platform=platform,
                lockdown_guaranteed=False
            )

        candidate_urls = cls.generate_candidate_urls(request_url)

        # 3. Verify Config Key Hash (X-SafeExamBrowser-ConfigKeyHash)
        if config_key_hash and rules.seb_config_key:
            incoming_ck_hash = config_key_hash.lower().strip()
            for cand_url in candidate_urls:
                expected_ck_hash = cls.compute_request_hash(cand_url, rules.seb_config_key)
                if hmac.compare_digest(incoming_ck_hash, expected_ck_hash):
                    return SEBVerificationResult(
                        is_valid=True,
                        mechanism="CONFIG_KEY_HASH",
                        matched_key_type="CONFIG_KEY",
                        detail="Verified authentic Safe Exam Browser session via Config Key hash.",
                        platform=platform,
                        lockdown_guaranteed=True
                    )

        # 4. Verify Browser Exam Key Hash (X-SafeExamBrowser-RequestHash)
        if request_hash and rules.seb_browser_exam_keys:
            incoming_bek_hash = request_hash.lower().strip()
            for bek in rules.seb_browser_exam_keys:
                if not bek:
                    continue
                for cand_url in candidate_urls:
                    expected_bek_hash = cls.compute_request_hash(cand_url, bek)
                    if hmac.compare_digest(incoming_bek_hash, expected_bek_hash):
                        return SEBVerificationResult(
                            is_valid=True,
                            mechanism="BEK_REQUEST_HASH",
                            matched_key_type="BROWSER_EXAM_KEY",
                            detail="Verified authentic Safe Exam Browser session via Browser Exam Key hash.",
                            platform=platform,
                            lockdown_guaranteed=True
                        )

        # 5. Cryptographic mismatch
        return SEBVerificationResult(
            is_valid=False,
            error_code="SEB_HASH_MISMATCH",
            detail="Safe Exam Browser security verification failed. The submitted configuration or binary build does not match any authorized keys.",
            platform=platform,
            lockdown_guaranteed=False
        )

    @classmethod
    def generate_seb_config_xml(
        cls,
        assessment: Assessment,
        invitation: Optional[CandidateInvitation] = None,
        base_url: str = "http://localhost:8000"
    ) -> bytes:
        """
        Generates an authentic Apple XML Property List (.seb configuration file)
        adhering to Safe Exam Browser specification.
        """
        rules = assessment.rules
        if invitation:
            start_url = f"{base_url}/test/instructions?token={invitation.invitation_token}"
        else:
            start_url = f"{base_url}/test/launch?assessment_id={assessment.id}"

        quit_url = (rules.seb_quit_url if rules and rules.seb_quit_url else f"{base_url}/api/v1/seb/quit")
        allow_quit = rules.seb_allow_quit if rules else True

        # Build domain URL filter rule
        parsed = urlparse(base_url)
        domain = parsed.hostname or "localhost"

        seb_dict: Dict[str, Any] = {
            "originatorVersion": "SEB_ProctorAI_3.0",
            "startURL": start_url,
            "sendBrowserExamKey": True,
            "examKeySalt": b"ProctorAI_2026_SEB_Salt",
            "allowQuit": allow_quit,
            "quitURL": quit_url,
            "browserViewMode": 1,  # 1 = Fullscreen Kiosk Mode
            "allowSwitchToApplications": False,
            "enableAltTab": False,
            "hookKeys": True,
            "showTaskBar": False,
            "allowPreferencesWindow": False,
            "allowFlashFullscreen": False,
            "allowVirtualMachine": False,
            "enableRightMouse": False,
            "allowDownAndUploads": False,
            "urlFilterEnable": True,
            "urlFilterRules": [
                {
                    "action": 1,  # 1 = Allow
                    "active": True,
                    "expression": f"*{domain}*",
                    "regex": False
                }
            ]
        }

        if rules and rules.seb_quit_password_hash:
            seb_dict["hashedQuitPassword"] = rules.seb_quit_password_hash

        return plistlib.dumps(seb_dict, fmt=plistlib.FMT_XML)

    @classmethod
    def generate_launch_info(
        cls,
        assessment: Assessment,
        invitation: Optional[CandidateInvitation] = None,
        base_url: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
        """
        Generates direct download and custom protocol (sebs:// / seb://) launch URLs.
        """
        if invitation:
            download_url = f"{base_url}/api/v1/seb/invitations/{invitation.invitation_token}/config.seb"
        else:
            download_url = f"{base_url}/api/v1/seb/assessments/{assessment.id}/config.seb"

        parsed = urlparse(download_url)
        # Custom SEB scheme replaces http -> seb, https -> sebs
        scheme = "sebs" if parsed.scheme == "https" else "seb"
        seb_protocol_url = urlunparse(parsed._replace(scheme=scheme))

        return {
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "seb_required": bool(assessment.rules and assessment.rules.seb_required),
            "config_download_url": download_url,
            "seb_protocol_url": seb_protocol_url,
            "supported_platforms": ["Windows", "macOS", "iOS"],
            "lockdown_instructions": [
                "1. Download and install Safe Exam Browser for your platform (Windows, macOS, or iOS).",
                "2. Click the 'Launch with SEB' protocol link or open the downloaded .seb configuration file.",
                "3. Safe Exam Browser will open in high-security fullscreen kiosk mode.",
                "4. All background applications, secondary monitors, and shortcuts will be locked.",
                "5. Complete and submit your assessment before exiting Safe Exam Browser."
            ]
        }
