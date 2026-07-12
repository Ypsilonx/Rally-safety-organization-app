"""Message models for Rally Safety App."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


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
    HEARTBEAT = "heartbeat"            # Periodic liveness ping


class StationMessage(BaseModel):
    """Message sent between stations."""
    message_id: str = Field(..., description="Unique message ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sender_pin: str = Field(..., description="PIN of sender")
    sender_name: Optional[str] = Field(None, description="Name of sender")
    message_type: MessageType = Field(default=MessageType.CHAT)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    content: str = Field(default="", max_length=1000)
    target_roles: Optional[list[str]] = Field(None, description="Target roles for selective broadcast")
    operation_command: Optional[str] = Field(
        default=None,
        description="Operational command key (e.g. rz_stop, rz_resume)",
    )
    readiness_state: Optional[str] = Field(
        default=None,
        description="Station readiness update (ready, not_ready)",
    )

    @model_validator(mode="after")
    def validate_content_by_message_type(self) -> "StationMessage":
        """Require message content for non-heartbeat message types.

        Returns:
            Validated message instance.

        Raises:
            ValueError: If non-heartbeat message does not contain content.
        """
        if self.message_type != MessageType.HEARTBEAT and not self.content.strip():
            raise ValueError("content is required for non-heartbeat messages")

        if self.readiness_state is not None and self.readiness_state not in {"ready", "not_ready"}:
            raise ValueError("readiness_state must be 'ready' or 'not_ready'")
        return self
    
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
