"""Authentication utilities - password hashing and PIN management."""

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt

from backend.models.user import AssignmentHistoryEntry, KomisarAccess, VEDENI_CREDENTIALS, UserRole


class AuthManager:
    """Manages authentication for both vedení and komisaři."""

    PIN_LENGTH = 8
    
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

    def _create_history_entry(
        self,
        name: str,
        role: UserRole,
        phone: Optional[str],
        email: Optional[str],
        address: Optional[str],
        group: Optional[str],
        assigned_at: str,
        note: Optional[str] = None,
    ) -> AssignmentHistoryEntry:
        """Build one assignment history record.

        Args:
            name: Assigned person name.
            role: Assigned role.
            phone: Optional phone number.
            assigned_at: Assignment start timestamp.
            note: Optional reassignment note.

        Returns:
            Assignment history record.
        """
        return AssignmentHistoryEntry(
            name=name,
            role=role,
            phone=phone,
            email=email,
            address=address,
            group=group,
            assigned_at=assigned_at,
            assigned_until=None,
            is_active=True,
            note=note,
        )

    def _generate_unique_pin_code(self) -> str:
        """Generate unique numeric PIN code.

        Returns:
            Unique PIN string with configured length.
        """
        upper_bound = 10 ** self.PIN_LENGTH
        while True:
            pin_code = str(secrets.randbelow(upper_bound)).zfill(self.PIN_LENGTH)
            if pin_code not in self.komisar_pins:
                return pin_code

    def _default_history_from_legacy(self, pin_data: dict) -> list[AssignmentHistoryEntry]:
        """Migrate legacy pin payload without explicit history.

        Args:
            pin_data: Raw JSON payload for one PIN.

        Returns:
            Synthetic history with the current active assignment.
        """
        name = pin_data.get("name")
        role = pin_data.get("role")
        if not name or not role:
            return []
        return [
            self._create_history_entry(
                name=name,
                role=UserRole(role),
                phone=pin_data.get("phone"),
                email=pin_data.get("email"),
                address=pin_data.get("address"),
                group=pin_data.get("group"),
                assigned_at=pin_data.get("created_at") or datetime.now(UTC).isoformat(),
            )
        ]
    
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
            
            pins = {}
            for pin_code, pin_data in data.items():
                history_payload = pin_data.get("assignment_history")
                if history_payload is None:
                    history = self._default_history_from_legacy(pin_data)
                else:
                    history = [AssignmentHistoryEntry(**item) for item in history_payload]
                pins[pin_code] = KomisarAccess(
                    pin_code=pin_code,
                    name=pin_data["name"],
                    role=UserRole(pin_data["role"]),
                    phone=pin_data.get("phone"),
                    email=pin_data.get("email"),
                    address=pin_data.get("address"),
                    group=pin_data.get("group"),
                    station_id=pin_data.get("station_id"),
                    station_name=pin_data.get("station_name"),
                    station_type=pin_data.get("station_type"),
                    station_capacity=pin_data.get("station_capacity", 1),
                    station_description=pin_data.get("station_description"),
                    created_at=pin_data.get("created_at"),
                    assignment_history=history,
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
                    "email": komisar.email,
                    "address": komisar.address,
                    "group": komisar.group,
                    "station_id": komisar.station_id,
                    "station_name": komisar.station_name,
                    "station_type": komisar.station_type,
                    "station_capacity": komisar.station_capacity,
                    "station_description": komisar.station_description,
                    "created_at": komisar.created_at,
                    "assignment_history": [
                        entry.model_dump(mode="json")
                        for entry in komisar.assignment_history
                    ],
                }
            
            with open(self.pins_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error: Failed to save PINs to {self.pins_file}: {e}")

    def _has_active_assignment(self, access: KomisarAccess) -> bool:
        """Check whether station PIN has active assigned person.

        Args:
            access: Persisted station-bound PIN record.

        Returns:
            True when at least one history record is active.
        """
        return any(history_entry.is_active for history_entry in access.assignment_history)
    
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
                "role": user_data["role"],
                "phone": user_data.get("phone"),
            }
        return None
    
    def create_session(self, username: str, name: str, role: UserRole, phone: Optional[str] = None) -> str:
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
            "phone": phone,
            "created_at": datetime.now(UTC)
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
        if datetime.now(UTC) - created_at > timedelta(hours=8):
            del self.active_sessions[session_token]
            return None
        
        return session_data
    
    def verify_pin(self, pin_code: str) -> Optional[KomisarAccess]:
        """Verify komisař PIN code.
        
        Args:
            pin_code: Numeric PIN (legacy 4-digit or current 8-digit)
            
        Returns:
            KomisarAccess object if valid, None otherwise
        """
        access = self.komisar_pins.get(pin_code)
        if access is None:
            return None
        if not self._has_active_assignment(access):
            return None
        return access
    
    def generate_pin(self, name: str, role: UserRole, phone: Optional[str] = None,
                     email: Optional[str] = None,
                     address: Optional[str] = None,
                     group: Optional[str] = None,
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
        pin_code = self._generate_unique_pin_code()
        
        komisar = KomisarAccess(
            pin_code=pin_code,
            name=name,
            role=role,
            phone=phone,
            email=email,
            address=address,
            group=group,
            station_id=station_id,
            station_name=station_id,
            created_at=datetime.now(UTC).isoformat(),
            assignment_history=[
                self._create_history_entry(
                    name=name,
                    role=role,
                    phone=phone,
                    email=email,
                    address=address,
                    group=group,
                    assigned_at=datetime.now(UTC).isoformat(),
                )
            ],
        )
        
        self.komisar_pins[pin_code] = komisar
        self._save_pins()  # Persist to file
        return komisar

    def create_station_pin(
        self,
        station_id: str,
        station_name: str,
        station_type: str,
        capacity: int,
        description: Optional[str],
        assignee_name: str,
        assignee_role: UserRole,
        assignee_phone: Optional[str] = None,
        assignee_email: Optional[str] = None,
        assignee_address: Optional[str] = None,
        assignee_group: Optional[str] = None,
        note: Optional[str] = None,
    ) -> KomisarAccess:
        """Create a new station-bound PIN with initial assignment.

        Args:
            station_id: New station identifier.
            station_name: Human-readable station label.
            station_type: Station type value.
            capacity: Maximum allowed headcount.
            description: Optional station note.
            assignee_name: Initial assignee name.
            assignee_role: Initial assignee role.
            assignee_phone: Optional assignee phone.
            note: Optional operator note for initial assignment.

        Returns:
            Persisted station-bound PIN record.

        Raises:
            ValueError: If the station already exists.
        """
        if self.find_pin_by_station_id(station_id) is not None:
            raise ValueError(f"Station '{station_id}' already exists")

        now = datetime.now(UTC).isoformat()
        pin_code = self._generate_unique_pin_code()
        komisar = KomisarAccess(
            pin_code=pin_code,
            name=assignee_name,
            role=assignee_role,
            phone=assignee_phone,
            email=assignee_email,
            address=assignee_address,
            group=assignee_group,
            station_id=station_id,
            station_name=station_name,
            station_type=station_type,
            station_capacity=capacity,
            station_description=description,
            created_at=now,
            assignment_history=[
                self._create_history_entry(
                    name=assignee_name,
                    role=assignee_role,
                    phone=assignee_phone,
                    email=assignee_email,
                    address=assignee_address,
                    group=assignee_group,
                    assigned_at=now,
                    note=note,
                )
            ],
        )
        self.komisar_pins[pin_code] = komisar
        self._save_pins()
        return komisar

    def create_station_pin_unassigned(
        self,
        station_id: str,
        station_name: str,
        station_type: str,
        capacity: int,
        description: Optional[str],
    ) -> KomisarAccess:
        """Create a new station-bound PIN without active assignee.

        Args:
            station_id: New station identifier.
            station_name: Human-readable station label.
            station_type: Station type value.
            capacity: Maximum allowed headcount.
            description: Optional station note.

        Returns:
            Persisted station-bound PIN record without active assignment.

        Raises:
            ValueError: If the station already exists.
        """
        if self.find_pin_by_station_id(station_id) is not None:
            raise ValueError(f"Station '{station_id}' already exists")

        now = datetime.now(UTC).isoformat()
        pin_code = self._generate_unique_pin_code()
        komisar = KomisarAccess(
            pin_code=pin_code,
            name=station_name,
            role=UserRole.KOMISAR_TRAT,
            phone=None,
            email=None,
            address=None,
            group=None,
            station_id=station_id,
            station_name=station_name,
            station_type=station_type,
            station_capacity=capacity,
            station_description=description,
            created_at=now,
            assignment_history=[],
        )
        self.komisar_pins[pin_code] = komisar
        self._save_pins()
        return komisar

    def regenerate_station_pin(self, station_id: str) -> tuple[str, KomisarAccess]:
        """Regenerate PIN for one station while preserving station assignment data.

        Args:
            station_id: Station identifier whose PIN should be replaced.

        Returns:
            Tuple of previous PIN and updated station-bound record.

        Raises:
            KeyError: If no station PIN exists for the given station.
        """
        access = self.find_pin_by_station_id(station_id)
        if access is None:
            raise KeyError(f"Unknown station '{station_id}'")

        old_pin = access.pin_code
        new_pin = self._generate_unique_pin_code()
        access.pin_code = new_pin

        del self.komisar_pins[old_pin]
        self.komisar_pins[new_pin] = access
        self._save_pins()
        return old_pin, access
    
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

    def remove_station_pin(self, station_id: str) -> KomisarAccess:
        """Delete station-bound PIN by station identifier.

        Args:
            station_id: Station identifier to remove.

        Returns:
            Removed PIN record.

        Raises:
            KeyError: If the station does not exist.
        """
        access = self.find_pin_by_station_id(station_id)
        if access is None:
            raise KeyError(f"Unknown station '{station_id}'")

        del self.komisar_pins[access.pin_code]
        self._save_pins()
        return access
    
    def list_all_pins(self) -> list[KomisarAccess]:
        """List all active komisař PINs.
        
        Returns:
            List of all KomisarAccess objects
        """
        return list(self.komisar_pins.values())

    def find_pin_by_station_id(self, station_id: str) -> Optional[KomisarAccess]:
        """Find stored PIN record bound to a station.

        Args:
            station_id: Station identifier.

        Returns:
            Matching PIN record or None.
        """
        for access in self.komisar_pins.values():
            if access.station_id == station_id:
                return access
        return None

    def assign_user_to_station(
        self,
        station_id: str,
        name: str,
        role: UserRole,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        group: Optional[str] = None,
        note: Optional[str] = None,
    ) -> KomisarAccess:
        """Assign or reassign a person to an existing station-bound PIN.

        Args:
            station_id: Station identifier to update.
            name: New current assignee.
            role: New current assignee role.
            phone: Optional current phone number.
            note: Optional operator note explaining the change.

        Returns:
            Updated persisted PIN record.

        Raises:
            KeyError: If no station PIN exists for the given station.
        """
        access = self.find_pin_by_station_id(station_id)
        if access is None:
            raise KeyError(f"Unknown station '{station_id}'")

        now = datetime.now(UTC).isoformat()
        for history_entry in access.assignment_history:
            if history_entry.is_active:
                history_entry.is_active = False
                history_entry.assigned_until = now
                if note:
                    history_entry.note = note

        access.name = name
        access.role = role
        access.phone = phone
        access.email = email
        access.address = address
        access.group = group
        access.assignment_history.append(
            self._create_history_entry(
                name=name,
                role=role,
                phone=phone,
                email=email,
                address=address,
                group=group,
                assigned_at=now,
                note=note,
            )
        )
        self._save_pins()
        return access

    def release_user_from_station(self, station_id: str, note: Optional[str] = None) -> KomisarAccess:
        """Release current assignee from station-bound PIN.

        Args:
            station_id: Station identifier to update.
            note: Optional operator note for the release.

        Returns:
            Updated persisted PIN record.

        Raises:
            KeyError: If no station PIN exists for the given station.
            ValueError: If no active assignee exists on the station.
        """
        access = self.find_pin_by_station_id(station_id)
        if access is None:
            raise KeyError(f"Unknown station '{station_id}'")

        now = datetime.now(UTC).isoformat()
        released = False
        for history_entry in access.assignment_history:
            if history_entry.is_active:
                history_entry.is_active = False
                history_entry.assigned_until = now
                if note:
                    history_entry.note = note
                released = True

        if not released:
            raise ValueError(f"Station '{station_id}' has no active assignment")

        self._save_pins()
        return access


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
