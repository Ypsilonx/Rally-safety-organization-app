"""WebSocket connection manager with selective broadcasting."""

from typing import Optional
from fastapi import WebSocket

from backend.core.event_logger import event_logger
from backend.models.user import UserRole


class ConnectionManager:
    """Manages WebSocket connections with support for 160+ clients."""
    
    def __init__(self):
        """Inicializuje prázdné registry aktivních spojení a jejich metadat."""
        # Active WebSocket connections: pin_code -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}

        # User metadata: pin_code -> {name, role, station_id}
        self.user_metadata: dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, pin_code: str, 
                     name: str, role: str, station_id: Optional[str] = None) -> None:
        """Accept WebSocket connection and store metadata.
        
        Args:
            websocket: WebSocket connection
            pin_code: User PIN code
            name: User name
            role: User role
            station_id: Assigned station (optional)
        """
        await websocket.accept()
        self.active_connections[pin_code] = websocket
        self.user_metadata[pin_code] = {
            "name": name,
            "role": role,
            "station_id": station_id
        }
        event_logger.log_connection(pin_code, name, "connected")
    
    def disconnect(self, pin_code: str) -> None:
        """Remove WebSocket connection.
        
        Args:
            pin_code: User PIN to disconnect
        """
        if pin_code in self.active_connections:
            metadata = self.user_metadata.get(pin_code, {})
            name = metadata.get("name", "Unknown")
            del self.active_connections[pin_code]
            del self.user_metadata[pin_code]
            event_logger.log_connection(pin_code, name, "disconnected")
    
    async def send_personal_message(self, message: str, pin_code: str) -> bool:
        """Send message to specific user.

        Zatím bez volajícího - připraveno pro ROADMAP.md Fáze 5 §7
        (notifikace konkrétnímu komisaři při přiřazení/změně stanice),
        které ještě není naimplementované.

        Args:
            message: JSON message string
            pin_code: Target user PIN

        Returns:
            True if sent successfully, False otherwise
        """
        if pin_code in self.active_connections:
            try:
                await self.active_connections[pin_code].send_text(message)
                return True
            except Exception as e:
                event_logger.log_error("send_failed", str(e), {"pin_code": pin_code})
                self.disconnect(pin_code)
                return False
        return False
    
    async def broadcast_to_all(self, message: str, exclude_pin: Optional[str] = None) -> int:
        """Broadcast message to all connected users.
        
        Args:
            message: JSON message string
            exclude_pin: Optional PIN to exclude from broadcast
            
        Returns:
            Number of users who received the message
        """
        sent_count = 0
        disconnected_pins = []
        
        for pin_code, websocket in self.active_connections.items():
            if pin_code == exclude_pin:
                continue
            
            try:
                await websocket.send_text(message)
                sent_count += 1
            except Exception as e:
                event_logger.log_error("broadcast_failed", str(e), {"pin_code": pin_code})
                disconnected_pins.append(pin_code)
        
        # Clean up disconnected websockets
        for pin_code in disconnected_pins:
            self.disconnect(pin_code)
        
        return sent_count
    
    async def broadcast_to_roles(self, message: str, target_roles: list[str],
                                 exclude_pin: Optional[str] = None) -> int:
        """Broadcast message only to specific roles.
        
        Args:
            message: JSON message string
            target_roles: List of role names to target
            exclude_pin: Optional PIN to exclude from broadcast
            
        Returns:
            Number of users who received the message
        """
        sent_count = 0
        disconnected_pins = []
        
        for pin_code, websocket in self.active_connections.items():
            if pin_code == exclude_pin:
                continue
            
            # Check if user has one of the target roles
            user_role = self.user_metadata.get(pin_code, {}).get("role")
            if user_role not in target_roles:
                continue
            
            try:
                await websocket.send_text(message)
                sent_count += 1
            except Exception as e:
                event_logger.log_error("broadcast_failed", str(e), {"pin_code": pin_code})
                disconnected_pins.append(pin_code)
        
        # Clean up disconnected websockets
        for pin_code in disconnected_pins:
            self.disconnect(pin_code)
        
        event_logger.log_broadcast("system", "role_broadcast", target_roles, sent_count)
        return sent_count
    
    async def broadcast_to_station(self, message: str, station_id: str,
                                   exclude_pin: Optional[str] = None) -> int:
        """Broadcast message only to users at specific station.

        Zatím bez volajícího - stejný důvod jako u send_personal_message,
        viz ROADMAP.md Fáze 5 §7.

        Args:
            message: JSON message string
            station_id: Target station ID
            exclude_pin: Optional PIN to exclude from broadcast
            
        Returns:
            Number of users who received the message
        """
        sent_count = 0
        disconnected_pins = []
        
        for pin_code, websocket in self.active_connections.items():
            if pin_code == exclude_pin:
                continue
            
            # Check if user is at target station
            user_station = self.user_metadata.get(pin_code, {}).get("station_id")
            if user_station != station_id:
                continue
            
            try:
                await websocket.send_text(message)
                sent_count += 1
            except Exception as e:
                event_logger.log_error("broadcast_failed", str(e), {"pin_code": pin_code})
                disconnected_pins.append(pin_code)
        
        # Clean up disconnected websockets
        for pin_code in disconnected_pins:
            self.disconnect(pin_code)
        
        return sent_count
    
    async def broadcast_critical(self, message: str, exclude_pin: Optional[str] = None) -> int:
        """Broadcast critical message (STOP RZ) to ALL users.
        
        Args:
            message: JSON message string (should have priority=critical)
            exclude_pin: Optional PIN to exclude from broadcast
            
        Returns:
            Number of users who received the message
        """
        sent_count = await self.broadcast_to_all(message, exclude_pin=exclude_pin)
        event_logger.log_broadcast("system", "critical_broadcast", None, sent_count)
        return sent_count
    
    def get_active_count(self) -> int:
        """Get number of active connections.
        
        Returns:
            Number of connected users
        """
        return len(self.active_connections)
    

# Global connection manager instance
connection_manager = ConnectionManager()
