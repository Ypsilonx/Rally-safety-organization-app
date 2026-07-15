"""Station-centric registry built on top of persistent PIN storage."""

from __future__ import annotations

from backend.core.auth import auth_manager
from backend.models.station import AssignedUser, StationAccess, StationAssignmentRequest, StationCreateRequest, StationType


class StationRegistry:
    """Provides station-first access and mutation helpers for admin flows."""

    def _infer_station_type(self, station_id: str, fallback: str | None) -> StationType:
        """Infer station type from stored value or station identifier prefix.

        Args:
            station_id: Station identifier such as TK-01.
            fallback: Optional stored station type value.

        Returns:
            Best-effort station type.
        """
        if fallback:
            try:
                return StationType(fallback)
            except ValueError:
                pass

        prefix = station_id.split("-", 1)[0].upper()
        mapping = {
            "TK": StationType.TRACK_POINT,
            "ZT": StationType.CORNER,
            "CS": StationType.TIMING,
            "PK": StationType.PARKING,
            "ZD": StationType.MEDICAL,
            "TC": StationType.TECHNICAL,
            "SF": StationType.START_FINISH,
        }
        return mapping.get(prefix, StationType.OTHER)

    def _map_assigned_user(self, history_entry) -> AssignedUser:
        """Convert assignment history entry to station API model.

        Args:
            history_entry: Stored assignment history record.

        Returns:
            Station API assignment record.
        """
        return AssignedUser(
            name=history_entry.name,
            role=history_entry.role,
            phone=history_entry.phone,
            assigned_at=history_entry.assigned_at,
            assigned_until=history_entry.assigned_until,
            is_active=history_entry.is_active,
            note=history_entry.note,
        )

    def _to_station_access(self, station_access) -> StationAccess:
        """Convert persisted PIN record to station-centric response model.

        Args:
            station_access: Stored PIN record.

        Returns:
            Station-centric API model.
        """
        history = [self._map_assigned_user(item) for item in station_access.assignment_history]
        current_user = next((item for item in history if item.is_active), None)
        station_id = station_access.station_id or station_access.pin_code
        station_name = station_access.station_name or station_id
        return StationAccess(
            pin_code=station_access.pin_code,
            station_id=station_id,
            station_name=station_name,
            station_type=self._infer_station_type(station_id, station_access.station_type),
            capacity=station_access.station_capacity,
            description=station_access.station_description,
            current_user=current_user,
            assigned_users=history,
            created_at=station_access.created_at,
        )

    def list_stations(self) -> list[StationAccess]:
        """Return all persisted station PINs as station-centric records.

        Returns:
            Sorted station list.
        """
        stations = [self._to_station_access(item) for item in auth_manager.list_all_pins()]
        return sorted(stations, key=lambda item: item.station_id)

    def get_station(self, station_id: str) -> StationAccess | None:
        """Return one station by identifier.

        Args:
            station_id: Requested station identifier.

        Returns:
            Station record or None if unknown.
        """
        record = auth_manager.find_pin_by_station_id(station_id)
        if record is None:
            return None
        return self._to_station_access(record)

    def assign_user(self, station_id: str, request: StationAssignmentRequest) -> StationAccess:
        """Assign or reassign a person on an existing station PIN.

        Args:
            station_id: Station identifier to update.
            request: Assignment payload.

        Returns:
            Updated station record.

        Raises:
            KeyError: If the station does not exist.
        """
        record = auth_manager.assign_user_to_station(
            station_id=station_id,
            name=request.name,
            role=request.role,
            phone=request.phone,
            note=request.note,
        )
        return self._to_station_access(record)

    def release_user(self, station_id: str, note: str | None = None) -> StationAccess:
        """Release current assignee from station PIN.

        Args:
            station_id: Station identifier to update.
            note: Optional operator note.

        Returns:
            Updated station record with no active current user.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If no current assignment exists.
        """
        record = auth_manager.release_user_from_station(station_id=station_id, note=note)
        return self._to_station_access(record)

    def get_station_history(self, station_id: str) -> list[AssignedUser]:
        """Return assignment history for one station.

        Args:
            station_id: Requested station identifier.

        Returns:
            Assignment history ordered as stored.

        Raises:
            KeyError: If the station does not exist.
        """
        station = self.get_station(station_id)
        if station is None:
            raise KeyError(f"Unknown station '{station_id}'")
        return station.assigned_users

    def create_station(self, request: StationCreateRequest) -> StationAccess:
        """Create new station-bound PIN with initial assignee.

        Args:
            request: Station creation payload.

        Returns:
            Created station record.

        Raises:
            ValueError: If the station already exists.
        """
        record = auth_manager.create_station_pin(
            station_id=request.station_id,
            station_name=request.station_name,
            station_type=request.station_type.value,
            capacity=request.capacity,
            description=request.description,
            assignee_name=request.name,
            assignee_role=request.role,
            assignee_phone=request.phone,
            note=request.note,
        )
        return self._to_station_access(record)

    def delete_station(self, station_id: str) -> StationAccess:
        """Delete station-bound PIN.

        Args:
            station_id: Station identifier to delete.

        Returns:
            Removed station record.

        Raises:
            KeyError: If the station does not exist.
        """
        record = auth_manager.remove_station_pin(station_id)
        return self._to_station_access(record)


station_registry = StationRegistry()