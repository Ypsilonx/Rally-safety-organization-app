"""Operational readiness state for controlled RZ resume workflow."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class StationReadiness:
    """Readiness state for one station.

    Attributes:
        station_id: Unique station identifier.
        station_name: Human-readable station label.
        ready: Whether station explicitly confirmed readiness.
        updated_at: Last update timestamp.
    """

    station_id: str
    station_name: str
    ready: bool
    updated_at: datetime


class OperationsState:
    """Tracks incident mode and per-station readiness gate."""

    def __init__(self) -> None:
        """Initialize empty in-memory operations state."""
        self._incident_active = False
        self._stations: dict[str, StationReadiness] = {}
        self._lock = asyncio.Lock()

    async def ensure_station(self, station_id: str | None, station_name: str) -> None:
        """Ensure station has readiness state.

        Args:
            station_id: Station identifier.
            station_name: Station display name.
        """
        if not station_id:
            return

        now = datetime.now(UTC)
        async with self._lock:
            record = self._stations.get(station_id)
            if record is None:
                # Outside incident mode we assume station is ready by default.
                self._stations[station_id] = StationReadiness(
                    station_id=station_id,
                    station_name=station_name,
                    ready=not self._incident_active,
                    updated_at=now,
                )
                return

            record.station_name = station_name

    async def set_station_ready(self, station_id: str | None, station_name: str) -> None:
        """Mark one station as ready.

        Args:
            station_id: Station identifier.
            station_name: Station display name.
        """
        if not station_id:
            return

        now = datetime.now(UTC)
        async with self._lock:
            record = self._stations.get(station_id)
            if record is None:
                self._stations[station_id] = StationReadiness(
                    station_id=station_id,
                    station_name=station_name,
                    ready=True,
                    updated_at=now,
                )
                return

            record.station_name = station_name
            record.ready = True
            record.updated_at = now

    async def set_station_not_ready(self, station_id: str | None, station_name: str) -> None:
        """Mark one station as not ready.

        Args:
            station_id: Station identifier.
            station_name: Station display name.
        """
        if not station_id:
            return

        now = datetime.now(UTC)
        async with self._lock:
            record = self._stations.get(station_id)
            if record is None:
                self._stations[station_id] = StationReadiness(
                    station_id=station_id,
                    station_name=station_name,
                    ready=False,
                    updated_at=now,
                )
                return

            record.station_name = station_name
            record.ready = False
            record.updated_at = now

    async def activate_incident_mode(self) -> list[str]:
        """Activate incident mode and force all stations to not-ready.

        Returns:
            List of station IDs now requiring ready confirmation.
        """
        now = datetime.now(UTC)
        async with self._lock:
            self._incident_active = True
            for record in self._stations.values():
                record.ready = False
                record.updated_at = now
            return sorted(self._stations.keys())

    async def resolve_incident_mode(self) -> None:
        """Resolve incident mode after successful resume authorization."""
        async with self._lock:
            self._incident_active = False

    async def can_resume(self) -> tuple[bool, list[str]]:
        """Check whether RZ can be resumed.

        Returns:
            Tuple (allowed, missing_stations).
        """
        async with self._lock:
            if not self._incident_active:
                return True, []

            missing = sorted(
                station_id
                for station_id, record in self._stations.items()
                if not record.ready
            )
            return len(missing) == 0, missing

    async def get_snapshot(self) -> dict[str, object]:
        """Return current readiness snapshot for API/debug use.

        Returns:
            Dictionary with incident mode and per-station readiness.
        """
        async with self._lock:
            stations = [
                {
                    "station_id": record.station_id,
                    "name": record.station_name,
                    "ready": record.ready,
                    "updated_at": record.updated_at.isoformat(),
                }
                for record in sorted(self._stations.values(), key=lambda item: item.station_id)
            ]
            return {
                "incident_active": self._incident_active,
                "total_stations": len(stations),
                "ready_stations": sum(1 for item in stations if item["ready"]),
                "stations": stations,
            }

    async def get_station_ready_map(self) -> tuple[bool, dict[str, bool]]:
        """Return incident flag and station ready dictionary.

        Returns:
            Tuple of incident_active and {station_id: ready} mapping.
        """
        async with self._lock:
            return self._incident_active, {
                station_id: record.ready
                for station_id, record in self._stations.items()
            }


operations_state = OperationsState()
