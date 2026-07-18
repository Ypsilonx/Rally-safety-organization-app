"""Station and station-access models for Rally Safety App."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.user import UserRole


class StationType(str, Enum):
    """Types of stations in the rally."""
    TRACK_POINT = "track_point"          # Traťový bod
    CORNER = "corner"                    # Zatáčka
    TIMING = "timing"                    # Časomíra
    PARKING = "parking"                  # Parkování
    MEDICAL = "medical"                  # Zdravotní služba
    TECHNICAL = "technical"              # Technická asistence
    SERVICE = "service"                  # Servisní zóna
    START_FINISH = "start_finish"        # Start/Cíl
    OTHER = "other"                      # Ostatní


class Station(BaseModel):
    """Station model - represents a location with assigned komisaři."""
    station_id: str = Field(..., description="Unique station ID (e.g., TK-01)")
    name: str = Field(..., min_length=1, max_length=100)
    type: StationType
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    capacity: int = Field(default=2, ge=1, le=10, description="Max number of people per station")
    assigned_pins: list[str] = Field(default_factory=list, description="List of assigned PIN codes")
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator('assigned_pins')
    @classmethod
    def validate_capacity(cls, v, info):
        """Ensure assigned PINs don't exceed capacity."""
        capacity = info.data.get('capacity', 2)
        if len(v) > capacity:
            raise ValueError(f"Assigned PINs ({len(v)}) exceed capacity ({capacity})")
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "station_id": "TK-01",
                "name": "Zatáčka u lesa",
                "type": "corner",
                "latitude": 50.0755,
                "longitude": 14.4378,
                "capacity": 2,
                "assigned_pins": ["1234", "5678"],
                "description": "Ostrá pravá zatáčka",
            }
        }
    )


class AssignedUser(BaseModel):
    """One person assigned to a station-bound PIN.

    Attributes:
        name: Assigned person name.
        role: Assigned role.
        phone: Optional contact phone.
        assigned_at: Assignment start timestamp.
        assigned_until: Assignment end timestamp if reassigned.
        is_active: Whether the assignment is active now.
        note: Optional operator note for the assignment change.
    """

    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    group: Optional[str] = None
    assigned_at: str
    assigned_until: Optional[str] = None
    is_active: bool = True
    note: Optional[str] = Field(None, max_length=200)


class StationAccess(BaseModel):
    """Station-centric view of one persistent PIN.

    Attributes:
        pin_code: Stable numeric station PIN.
        station_id: Station identifier.
        station_name: Human-readable station label.
        station_type: Station type classification.
        capacity: Maximum headcount for this station.
        description: Optional station note.
        current_user: Currently assigned person, if any.
        assigned_users: Full assignment history for the station PIN.
        created_at: Timestamp when the PIN was created.
    """

    pin_code: str = Field(..., min_length=4, max_length=8, pattern=r"^\d{4,8}$")
    station_id: str = Field(..., min_length=1, max_length=50)
    station_name: str = Field(..., min_length=1, max_length=100)
    station_type: StationType
    capacity: int = Field(default=1, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=500)
    current_user: Optional[AssignedUser] = None
    assigned_users: list[AssignedUser] = Field(default_factory=list)
    created_at: Optional[str] = None


class StationAssignmentRequest(BaseModel):
    """Payload for assigning or reassigning a person to a station.

    Attributes:
        name: Person name.
        role: Person role.
        phone: Optional phone number.
        email: Optional email address.
        address: Optional address.
        group: Optional group label.
        note: Optional note explaining the change.
    """

    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    group: Optional[str] = None
    note: Optional[str] = Field(None, max_length=200)


class StationCreateRequest(BaseModel):
    """Payload for creating a new station-bound PIN.

    Attributes:
        station_id: New station identifier.
        station_name: Human-readable station name.
        station_type: Station type classification.
        capacity: Maximum allowed headcount for the station.
        description: Optional station note.
        name: Initially assigned person name.
        role: Initially assigned person role.
        phone: Optional phone number for the initial assignee.
        email: Optional email address for the initial assignee.
        address: Optional address for the initial assignee.
        group: Optional group label for the initial assignee.
        note: Optional operator note for initial assignment.
    """

    station_id: str = Field(..., min_length=1, max_length=50)
    station_name: str = Field(..., min_length=1, max_length=100)
    station_type: StationType
    capacity: int = Field(default=1, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=500)
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    group: Optional[str] = None
    note: Optional[str] = Field(None, max_length=200)


class StationBulkGeneratePinsRequest(BaseModel):
    """Payload for bulk station PIN generation from map templates.

    Attributes:
        regenerate_existing: When True, rotate PIN also for already existing stations.
    """

    regenerate_existing: bool = False


class StationRegeneratePinResponse(BaseModel):
    """Response payload after one station PIN regeneration.

    Attributes:
        old_pin_code: Previous PIN value.
        station: Updated station view with newly generated PIN.
    """

    old_pin_code: str = Field(..., min_length=4, max_length=8, pattern=r"^\d{4,8}$")
    station: StationAccess
