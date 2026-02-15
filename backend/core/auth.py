"""Authentication utilities - password hashing and PIN management."""

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt

from backend.models.user import KomisarAccess, VEDENI_CREDENTIALS, UserRole


class AuthManager:
    """Manages authentication for both vedení and komisaři."""
    
    def __init__(self, pins_file: str = "data/pins.json"):
        """Initialize auth manager with persistent PIN storage.
        
        Args:
            pins_file: Path to JSON file for storing PINs
        """
        self.pins_file = Path(pins_file)
        self.pins_file.parent.mkdir(exist_ok=True)
        
        # Load existing PINs from file or initialize empty
        self.komisar_pins: dict[str, KomisarAccess] = self._load_pins()
        self.active_sessions: dict[str, dict] = {}  # session_token -> user_data
    
    def _load_pins(self) -> dict[str, KomisarAccess]:
        """Load PINs from JSON file.
        
        Returns:
            Dictionary of PIN code -> KomisarAccess
        """
        if not self.pins_file.exists():
            return {}
        
        try:
            with open(self.pins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert JSON to KomisarAccess objects
            pins = {}
            for pin_code, pin_data in data.items():
                pins[pin_code] = KomisarAccess(
                    pin_code=pin_code,
                    name=pin_data["name"],
                    role=UserRole(pin_data["role"]),
                    phone=pin_data.get("phone"),
                    station_id=pin_data.get("station_id"),
                    created_at=pin_data.get("created_at")
                )
            return pins
        except Exception as e:
            print(f"⚠️ Warning: Failed to load PINs from {self.pins_file}: {e}")
            return {}
    
    def _save_pins(self) -> None:
        """Save PINs to JSON file for persistence."""
        try:
            data = {}
            for pin_code, komisar in self.komisar_pins.items():
                data[pin_code] = {
                    "name": komisar.name,
                    "role": komisar.role.value,
                    "phone": komisar.phone,
                    "station_id": komisar.station_id,
                    "created_at": komisar.created_at
                }
            
            with open(self.pins_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error: Failed to save PINs to {self.pins_file}: {e}")
    
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
        self._save_pins()  # Persist to file
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
            self._save_pins()  # Persist to file
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
