"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status

from backend.core.auth import auth_manager
from backend.core.event_logger import event_logger
from backend.core.rz_context import rz_context_manager
from backend.models.auth import (
    LoginVedeniRequest,
    LoginVedeniResponse,
    LoginKomisarRequest,
    LoginKomisarResponse,
    AuthError
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login-vedeni", response_model=LoginVedeniResponse)
async def login_vedeni(request: LoginVedeniRequest):
    """Login endpoint for vedení RZ (username + password).
    
    Args:
        request: LoginVedeniRequest with username and password
        
    Returns:
        LoginVedeniResponse with session token
        
    Raises:
        HTTPException: If credentials are invalid (401)
    """
    # Verify credentials
    user_data = auth_manager.verify_password(request.username, request.password)
    
    if not user_data:
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
async def login_komisar(request: LoginKomisarRequest):
    """Login endpoint for komisař (PIN code only).
    
    Args:
        request: LoginKomisarRequest with PIN code
        
    Returns:
        LoginKomisarResponse with user details
        
    Raises:
        HTTPException: If PIN is invalid (401)
    """
    # Verify PIN
    komisar = auth_manager.verify_pin(request.pin_code)
    
    if not komisar:
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
