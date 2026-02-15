"""Station models for Rally Safety App."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


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
    
    class Config:
        json_schema_extra = {
            "example": {
                "station_id": "TK-01",
                "name": "Zatáčka u lesa",
                "type": "corner",
                "latitude": 50.0755,
                "longitude": 14.4378,
                "capacity": 2,
                "assigned_pins": ["1234", "5678"],
                "description": "Ostrá pravá zatáčka"
            }
        }
