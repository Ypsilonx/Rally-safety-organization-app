"""Authentication models for Rally Safety App."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginVedeniRequest(BaseModel):
    """Login request for vedení RZ (username + password)."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "admin",
                "password": "demo123",
            }
        }
    )


class LoginVedeniResponse(BaseModel):
    """Response after successful vedení login."""
    success: bool
    session_token: str = Field(..., description="Session token for authenticated requests")
    user_id: str
    name: str
    role: str
    phone: Optional[str] = None
    message: str = "Login successful"


class LoginKomisarRequest(BaseModel):
    """Login request for komisař (PIN code only)."""
    pin_code: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pin_code": "1234",
            }
        }
    )


class LoginKomisarResponse(BaseModel):
    """Response after successful komisař login."""
    success: bool
    user_id: str
    pin_code: str
    name: str
    role: str
    station_id: Optional[str] = None
    vedeni_name: Optional[str] = None
    vedeni_phone: Optional[str] = None
    message: str = "Login successful"


class AuthError(BaseModel):
    """Authentication error response."""
    success: bool = False
    error: str
    message: str
