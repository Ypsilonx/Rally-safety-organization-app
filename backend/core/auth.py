"""Authentication utilities - password hashing and PIN management."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt

from backend.models.user import KomisarAccess, VEDENI_CREDENTIALS, UserRole


class AuthManager:
    """Manages authentication for both vedení and komisaři."""
    
    def __init__(self):
        # In-memory storage for MVP (would be database in production)
        self.komisar_pins: dict[str, KomisarAccess] = {}
        self.active_sessions: dict[str, dict] = {}  # session_token -> user_data
    
    def verify_password(self, username: str, password: str) -> Optional[dict]:
        """Verify vedení username + password.
        
        Args:
            username: Username to check
            password: Plain text password
            
        Returns:
            User data dict if valid, None otherwise
        """
        if username not in VEDENI_CREDENTIALS:
            return None
        
        user_data = VEDENI_CREDENTIALS[username]
        stored_hash = user_data["password_hash"].encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return {
                "username": username,
                "name": user_data["name"],
                "role": user_data["role"]
            }
        return None
    
    def create_session(self, username: str, name: str, role: UserRole) -> str:
        """Create session token for vedení user.
        
        Args:
            username: Username
            name: Display name
            role: User role
            
        Returns:
            Session token (32 chars hex)
        """
        session_token = secrets.token_hex(32)
        self.active_sessions[session_token] = {
            "username": username,
            "name": name,
            "role": role,
            "created_at": datetime.utcnow()
        }
        return session_token
    
    def verify_session(self, session_token: str) -> Optional[dict]:
        """Verify session token is valid.
        
        Args:
            session_token: Token to verify
            
        Returns:
            User data if valid, None if expired/invalid
        """
        if session_token not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_token]
        # Check if session expired (8 hours default)
        created_at = session_data["created_at"]
        if datetime.utcnow() - created_at > timedelta(hours=8):
            del self.active_sessions[session_token]
            return None
        
        return session_data
    
    def verify_pin(self, pin_code: str) -> Optional[KomisarAccess]:
        """Verify komisař PIN code.
        
        Args:
            pin_code: 4-digit PIN
            
        Returns:
            KomisarAccess object if valid, None otherwise
        """
        return self.komisar_pins.get(pin_code)
    
    def generate_pin(self, name: str, role: UserRole, phone: Optional[str] = None, 
                     station_id: Optional[str] = None) -> KomisarAccess:
        """Generate new PIN for komisař.
        
        Args:
            name: Komisař name
            role: User role
            phone: Phone number (optional)
            station_id: Assigned station (optional)
            
        Returns:
            KomisarAccess object with generated PIN
        """
        # Generate unique 4-digit PIN
        while True:
            pin_code = str(secrets.randbelow(10000)).zfill(4)
            if pin_code not in self.komisar_pins:
                break
        
        komisar = KomisarAccess(
            pin_code=pin_code,
            name=name,
            role=role,
            phone=phone,
            station_id=station_id,
            created_at=datetime.utcnow().isoformat()
        )
        
        self.komisar_pins[pin_code] = komisar
        return komisar
    
    def remove_pin(self, pin_code: str) -> bool:
        """Remove komisař PIN.
        
        Args:
            pin_code: PIN to remove
            
        Returns:
            True if removed, False if not found
        """
        if pin_code in self.komisar_pins:
            del self.komisar_pins[pin_code]
            return True
        return False
    
    def list_all_pins(self) -> list[KomisarAccess]:
        """List all active komisař PINs.
        
        Returns:
            List of all KomisarAccess objects
        """
        return list(self.komisar_pins.values())


def hash_password(password: str) -> str:
    """Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash string
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# Global auth manager instance
auth_manager = AuthManager()
