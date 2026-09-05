"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from backend.core.auth import auth_manager
from backend.core.event_logger import event_logger
from backend.core.rate_limiter import login_rate_limiter
from backend.core.rz_context import rz_context_manager
from backend.models.auth import (
    LoginVedeniRequest,
    LoginVedeniResponse,
    LoginKomisarRequest,
    LoginKomisarResponse,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login-vedeni", response_model=LoginVedeniResponse)
async def login_vedeni(request: LoginVedeniRequest, http_request: Request):
    """Login endpoint for vedení RZ (username + password).

    Args:
        request: LoginVedeniRequest with username and password
        http_request: Raw HTTP request, used for rate limiting by client IP

    Returns:
        LoginVedeniResponse with session token

    Raises:
        HTTPException: If credentials are invalid (401), or too many failed
            attempts came from this IP recently (429)
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    if login_rate_limiter.is_locked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    # Verify credentials
    user_data = auth_manager.verify_password(request.username, request.password)

    if not user_data:
        login_rate_limiter.record_failure(client_ip)
        event_logger.log_login(
            "vedeni",
            request.username,
            "Unknown",
            "unknown",
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    login_rate_limiter.record_success(client_ip)

    # Create session
    session_token = auth_manager.create_session(
        username=user_data["username"],
        name=user_data["name"],
        role=user_data["role"],
        phone=user_data.get("phone"),
        station_id=user_data.get("station_id"),
    )

    event_logger.log_login(
        "vedeni",
        request.username,
        user_data["name"],
        user_data["role"].value,
        success=True
    )

    context = rz_context_manager.get_context()

    return LoginVedeniResponse(
        success=True,
        session_token=session_token,
        user_id=user_data["username"],
        name=user_data["name"],
        role=user_data["role"].value,
        station_id=user_data.get("station_id"),
        phone=user_data.get("phone"),
        rz_name=context.rz_name,
        message="Login successful"
    )


@router.post("/login-komisar", response_model=LoginKomisarResponse)
async def login_komisar(request: LoginKomisarRequest, http_request: Request):
    """Login endpoint for komisař (PIN code only).

    Args:
        request: LoginKomisarRequest with PIN code
        http_request: Raw HTTP request, used for rate limiting by client IP

    Returns:
        LoginKomisarResponse with user details

    Raises:
        HTTPException: If PIN is invalid (401), or too many failed attempts
            came from this IP recently (429)
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    if login_rate_limiter.is_locked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    # Verify PIN
    komisar = auth_manager.verify_pin(request.pin_code)

    if not komisar:
        login_rate_limiter.record_failure(client_ip)
        event_logger.log_login(
            "komisar",
            request.pin_code,
            "Unknown",
            "unknown",
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN code"
        )

    login_rate_limiter.record_success(client_ip)

    event_logger.log_login(
        "komisar",
        request.pin_code,
        komisar.name,
        komisar.role.value,
        success=True
    )

    context = rz_context_manager.get_context()

    contacts = auth_manager.get_leadership_contacts()
    primary_contact = next((item for item in contacts if item.get("station_id") == "VRZ"), None)

    return LoginKomisarResponse(
        success=True,
        user_id=request.pin_code,
        pin_code=request.pin_code,
        name=komisar.name,
        role=komisar.role.value,
        station_id=komisar.station_id,
        vedeni_name=(primary_contact or {}).get("name") or "Vedoucí RZ",
        vedeni_phone=(primary_contact or {}).get("phone") or "+420777123456",
        leadership_contacts=contacts,
        rz_name=context.rz_name,
        message="Login successful"
    )


@router.post("/verify-session")
async def verify_session(session_token: str):
    """Verify if session token is still valid.

    Args:
        session_token: Session token to verify

    Returns:
        Session data if valid

    Raises:
        HTTPException: If session is invalid/expired (401)
    """
    session_data = auth_manager.verify_session(session_token)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    return {
        "valid": True,
        "username": session_data["username"],
        "name": session_data["name"],
        "role": session_data["role"].value
    }
