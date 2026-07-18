"""Event logger - JSONL logging for all rally events."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from backend.core.config import get_settings
from backend.core.rz_context import rz_context_manager


class EventLogger:
    """Logs all rally events to JSONL file for post-race analysis."""
    
    def __init__(self):
        self.settings = get_settings()
        self.log_dir = Path(self.settings.LOG_DIR)
        self.log_dir.mkdir(exist_ok=True)
        self.rz_name = rz_context_manager.get_context().rz_name
        self.log_file = self._build_log_path(self.rz_name)
        
        # Standard Python logger for console output
        self.console_logger = logging.getLogger("rally_safety")
        self.console_logger.setLevel(getattr(logging, self.settings.LOG_LEVEL))
        
        if not self.console_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.console_logger.addHandler(handler)

    def _build_log_path(self, rz_name: str) -> Path:
        """Build current session log file path.

        Args:
            rz_name: Current race stage name.

        Returns:
            Absolute path to session JSONL log file.
        """
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rz_slug = rz_context_manager.slug_for_filename(rz_name)
        return self.log_dir / f"rz_{rz_slug}_session_{session_timestamp}.jsonl"

    def set_rz_name(self, rz_name: str) -> None:
        """Rotate logger to new file when RZ name changes.

        Args:
            rz_name: Updated race stage name.
        """
        normalized = " ".join(str(rz_name or "").split())
        if not normalized or normalized == self.rz_name:
            return

        previous_name = self.rz_name
        self.rz_name = normalized
        self.log_file = self._build_log_path(self.rz_name)
        self.log_event(
            "session_log_rotated",
            {
                "previous_rz_name": previous_name,
                "new_rz_name": self.rz_name,
            },
            severity="info",
        )
    
    def log_event(self, event_type: str, data: dict[str, Any], 
                  severity: str = "info") -> None:
        """Log event to JSONL file and console.
        
        Args:
            event_type: Type of event (login, message, incident, etc.)
            data: Event data dictionary
            severity: Log severity (debug, info, warning, error, critical)
        """
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "rz_name": self.rz_name,
            "event_type": event_type,
            "severity": severity,
            **data
        }
        
        # Write to JSONL file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            self.console_logger.error(f"Failed to write event log: {e}")
        
        # Also log to console
        log_message = f"[{event_type}] {json.dumps(data, ensure_ascii=False)}"
        log_method = getattr(self.console_logger, severity, self.console_logger.info)
        log_method(log_message)
    
    def log_login(self, user_type: str, user_id: str, name: str, 
                  role: str, success: bool) -> None:
        """Log login attempt.
        
        Args:
            user_type: "vedeni" or "komisar"
            user_id: Username or PIN
            name: Display name
            role: User role
            success: Whether login succeeded
        """
        self.log_event("login", {
            "user_type": user_type,
            "user_id": user_id,
            "name": name,
            "role": role,
            "success": success
        }, severity="info" if success else "warning")
    
    def log_message(self, sender_pin: str, sender_name: str, 
                    message_type: str, priority: str, content: str,
                    target_roles: Optional[list[str]] = None) -> None:
        """Log message sent.
        
        Args:
            sender_pin: PIN of sender
            sender_name: Name of sender
            message_type: Type of message
            priority: Message priority
            content: Message content
            target_roles: Target roles (None = all)
        """
        self.log_event("message", {
            "sender_pin": sender_pin,
            "sender_name": sender_name,
            "message_type": message_type,
            "priority": priority,
            "content": content,
            "target_roles": target_roles
        })
    
    def log_connection(self, pin_code: str, name: str, action: str) -> None:
        """Log WebSocket connection/disconnection.
        
        Args:
            pin_code: User PIN
            name: User name
            action: "connected" or "disconnected"
        """
        self.log_event("connection", {
            "pin_code": pin_code,
            "name": name,
            "action": action
        })
    
    def log_broadcast(self, sender: str, message_type: str, 
                     target_roles: Optional[list[str]], recipient_count: int) -> None:
        """Log broadcast message.
        
        Args:
            sender: Who initiated broadcast
            message_type: Type of message
            target_roles: Target roles (None = all)
            recipient_count: How many received
        """
        self.log_event("broadcast", {
            "sender": sender,
            "message_type": message_type,
            "target_roles": target_roles,
            "recipient_count": recipient_count
        })
    
    def log_error(self, error_type: str, message: str, context: dict[str, Any]) -> None:
        """Log error event.
        
        Args:
            error_type: Type of error
            message: Error message
            context: Additional context
        """
        self.log_event("error", {
            "error_type": error_type,
            "message": message,
            **context
        }, severity="error")


# Global event logger instance
event_logger = EventLogger()
