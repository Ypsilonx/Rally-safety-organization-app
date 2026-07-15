"""User and role models for Rally Safety App."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """9 user roles in the system."""
    VEDOUCI = "vedouci"                    # Head of RZ
    ZASTUPCE = "zastupce"                  # Deputy head
    KOMISAR_TRAT = "komisar_trat"          # Track marshal
    KOMISAR_ZATACKA = "komisar_zatacka"    # Corner marshal
    CASOMER = "casomer"                    # Timekeeper
    PARKOVANI = "parkovani"                # Parking marshal
    ZDRAVOTNIK = "zdravotnik"              # Medical personnel
    TECHNIK = "technik"                    # Technical support
    ADMIN = "admin"                        # System administrator


class User(BaseModel):
    """User model - represents both vedení and komisaři."""
    user_id: str = Field(..., description="Unique user ID")
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    station_id: Optional[str] = Field(None, description="Assigned station ID")
    pin_code: Optional[str] = Field(None, description="4-digit PIN for komisaři")
    phone: Optional[str] = Field(None, description="Phone number (optional)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_001",
                "name": "Jan Novák",
                "role": "komisar_trat",
                "station_id": "TK-01",
                "pin_code": "1234",
                "phone": "+420123456789"
            }
        }
    )


class AssignmentHistoryEntry(BaseModel):
    """Historical snapshot of one user assignment on a station-bound PIN.

    Attributes:
        name: Assigned person display name.
        role: Role held during the assignment.
        phone: Optional phone number for the assigned person.
        assigned_at: Timestamp when the assignment became active.
        assigned_until: Timestamp when the assignment ended.
        is_active: Whether the assignment is still active.
        note: Optional operator note explaining the reassignment.
    """

    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    assigned_at: str
    assigned_until: Optional[str] = None
    is_active: bool = True
    note: Optional[str] = Field(None, max_length=200)


class KomisarAccess(BaseModel):
    """Komisař access credentials bound to one station PIN.

    Attributes:
        pin_code: Stable 4-digit PIN code.
        name: Currently assigned person name.
        role: Current person role.
        phone: Current person phone number.
        station_id: Station identifier bound to the PIN.
        station_name: Human-readable station name.
        station_type: Optional station type label.
        station_capacity: Maximum supported headcount on station.
        station_description: Optional station note.
        created_at: Timestamp when the PIN was created.
        assignment_history: Chronological assignment history.
    """

    pin_code: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    station_type: Optional[str] = None
    station_capacity: int = Field(default=1, ge=1, le=10)
    station_description: Optional[str] = Field(None, max_length=500)
    created_at: Optional[str] = None
    assignment_history: list[AssignmentHistoryEntry] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pin_code": "1234",
                "name": "Jan Novák",
                "role": "komisar_trat",
                "phone": "+420123456789",
                "station_id": "TK-01",
                "station_name": "Traťový bod 01",
                "station_type": "track_point",
                "station_capacity": 1,
                "assignment_history": [
                    {
                        "name": "Jan Novák",
                        "role": "komisar_trat",
                        "phone": "+420123456789",
                        "assigned_at": "2026-02-15T15:00:00+00:00",
                        "assigned_until": None,
                        "is_active": True,
                        "note": None,
                    }
                ],
            }
        }
    )


# Hardcoded vedení credentials for MVP (in real app, this would be in database)
VEDENI_CREDENTIALS = {
    "admin": {
        "password_hash": "$2b$12$/Hja06MPyPq3bnBF64VusuQ5OdzvYzduaqUCXWCXfqe1wGQkIwby6",  # "demo123"
        "name": "Vedoucí RZ",
        "role": UserRole.VEDOUCI,
        "phone": "+420777123456",
    }
}
