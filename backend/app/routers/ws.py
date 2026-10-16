from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.config import settings
from app.models.user import User, Role
from app.models.assessment import Assessment
from app.utils.security import decode_access_token
from app.services.websocket_manager import live_proctor_manager

logger = logging.getLogger("proctorai.ws")
router = APIRouter(prefix="/ws", tags=["Realtime Proctoring WebSockets"])


@router.websocket("/proctor/{assessment_id}")
async def proctor_live_websocket(
    websocket: WebSocket,
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """
    Authenticated WebSocket endpoint for proctor live console.
    Authenticates via query param '?token=<jwt>', cookie, or header.
    Enforces RBAC (PROCTOR, RECRUITER, ORG_ADMIN, PLATFORM_ADMIN) and organization-level boundary.
    Broadcasts live events, candidate risk alerts, and camera check-ins.
    """
    # 1. Resolve JWT Token
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get(settings.COOKIE_ACCESS_TOKEN_KEY)
    if not token and "authorization" in websocket.headers:
        auth_hdr = websocket.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            token = auth_hdr.split(" ", 1)[1].strip()

    if not token:
        logger.warning(f"Rejected WS connection to assessment {assessment_id}: Missing authentication token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    # 2. Decode and Validate Token
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        logger.warning(f"Rejected WS connection to assessment {assessment_id}: Invalid token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
        return

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        return

    # 3. Enforce Role-Based Permissions
    allowed_roles = (Role.PROCTOR, Role.RECRUITER, Role.ORG_ADMIN, Role.PLATFORM_ADMIN)
    if user.role not in allowed_roles:
        logger.warning(f"Rejected WS connection: User {user.email} with role {user.role} lacks proctoring privileges")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Insufficient privileges for proctoring console")
        return

    # 4. Enforce Organization Multi-Tenant Security Boundary
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Assessment not found")
        return

    if user.role != Role.PLATFORM_ADMIN and user.org_id and assessment.org_id != user.org_id:
        logger.warning(f"Cross-tenant WS access denied: User org {user.org_id} != Assessment org {assessment.org_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Cross-tenant access forbidden")
        return

    # 5. Connection Authorized: Accept and Register
    await live_proctor_manager.connect_proctor(assessment_id, websocket)
    try:
        # Send initial confirmation handshake
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "assessment_id": assessment_id,
            "user_email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "message": "Connected to authenticated live proctoring stream"
        })

        while True:
            # Keep connection alive & receive heartbeat/ping from proctor console
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        live_proctor_manager.disconnect_proctor(assessment_id, websocket)
        logger.info(f"Proctor {user.email} disconnected from assessment {assessment_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for user {user.email}: {e}")
        live_proctor_manager.disconnect_proctor(assessment_id, websocket)
