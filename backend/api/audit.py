"""Frontend audit logging endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import auth_manager
from backend.core.event_logger import event_logger

router = APIRouter(prefix="/api/audit", tags=["audit"])


class FrontendAuditEventRequest(BaseModel):
    """Payload for frontend action audit event.

    Attributes:
        action: Stable action key identifier.
        details: Optional structured action context.
        source: Frontend source area/module.
    """

    action: str = Field(..., min_length=3, max_length=120)
    details: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="frontend", min_length=2, max_length=80)


def _resolve_identity(
    session_token: str | None,
    auth_identifier: str | None,
) -> dict[str, Any] | None:
    """Resolve authenticated identity from session token or PIN.

    Args:
        session_token: Vedeni session token.
        auth_identifier: PIN or session token from frontend.

    Returns:
        Unified identity dictionary when verified, else None.
    """
    if session_token:
        session = auth_manager.verify_session(session_token)
        if session:
            return {
                "user_id": session["username"],
                "name": session["name"],
                "role": session["role"].value,
                "station_id": None,
                "auth_type": "session",
            }

    if auth_identifier:
        session = auth_manager.verify_session(auth_identifier)
        if session:
            return {
                "user_id": session["username"],
                "name": session["name"],
                "role": session["role"].value,
                "station_id": None,
                "auth_type": "session",
            }

        komisar = auth_manager.verify_pin(auth_identifier)
        if komisar:
            return {
                "user_id": komisar.pin_code,
                "name": komisar.name,
                "role": komisar.role.value,
                "station_id": komisar.station_id,
                "auth_type": "pin",
            }

    return None


@router.post("/frontend-event")
async def frontend_audit_event(
    request: FrontendAuditEventRequest,
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    auth_identifier: Annotated[str | None, Header(alias="X-Auth-Identifier")] = None,
) -> dict[str, Any]:
    """Log verified frontend action for operational audit trail.

    Args:
        request: Frontend action payload.
        session_token: Optional session token header.
        auth_identifier: Optional PIN/session identifier header.

    Returns:
        Acknowledgement and normalized actor details.

    Raises:
        HTTPException: If actor cannot be verified.
    """
    identity = _resolve_identity(session_token, auth_identifier)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication for audit event",
        )

    event_logger.log_event(
        "ui_action",
        {
            "action": request.action,
            "source": request.source,
            "details": request.details,
            **identity,
        },
    )

    return {
        "success": True,
        "action": request.action,
        "actor": {
            "user_id": identity["user_id"],
            "role": identity["role"],
            "station_id": identity["station_id"],
        },
    }
