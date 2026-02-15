"""Message models for Rally Safety App."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessagePriority(str, Enum):
    """Message priority levels."""
    CRITICAL = "critical"  # STOP RZ, immediate action required
    HIGH = "high"          # Urgent, needs quick response
    NORMAL = "normal"      # Standard communication
    LOW = "low"            # Info only


class MessageType(str, Enum):
    """Types of messages in the system."""
    CHAT = "chat"                      # Regular chat message
    INCIDENT = "incident"              # Report incident
    STATUS_UPDATE = "status_update"    # Station status change
    BROADCAST = "broadcast"            # Admin broadcast
    SYSTEM = "system"                  # System notification


class StationMessage(BaseModel):
    """Message sent between stations."""
    message_id: str = Field(..., description="Unique message ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender_pin: str = Field(..., description="PIN of sender")
    sender_name: Optional[str] = Field(None, description="Name of sender")
    message_type: MessageType = Field(default=MessageType.CHAT)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    content: str = Field(..., min_length=1, max_length=1000)
    target_roles: Optional[list[str]] = Field(None, description="Target roles for selective broadcast")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123456",
                "sender_pin": "1234",
                "sender_name": "Jan Novák",
                "message_type": "chat",
                "priority": "normal",
                "content": "Traťový úsek OK",
                "target_roles": None
            }
        }
