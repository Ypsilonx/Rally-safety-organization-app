"""Heartbeat and station vitality monitoring service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class StationVitalityRecord:
    """Internal state for one station vitality record.

    Attributes:
        station_id: Unique station identifier.
        station_name: Human-readable station/user label.
        role: User role currently associated with station.
        last_seen: Last heartbeat or activity timestamp.
        online: Current computed online status.
        updated_at: Last status-change timestamp.
    """

    station_id: str
    station_name: str
    role: str
    last_seen: datetime
    online: bool
    updated_at: datetime


class VitalityMonitor:
    """Tracks station liveness from heartbeat/activity and computes offline status."""

    def __init__(self, check_interval_seconds: int = 10, offline_timeout_seconds: int = 120):
        """Initialize vitality monitor.

        Args:
            check_interval_seconds: Frequency of timeout checks.
            offline_timeout_seconds: Offline threshold since last seen activity.
        """
        self.check_interval_seconds = check_interval_seconds
        self.offline_timeout_seconds = offline_timeout_seconds
        self._records: dict[str, StationVitalityRecord] = {}
        self._station_connections: dict[str, set[str]] = {}
        self._connection_to_station: dict[str, str] = {}
        self._monitor_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start background monitoring loop."""
        if self._monitor_task and not self._monitor_task.done():
            return
        self._stop_event.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop background monitoring loop and await shutdown."""
        self._stop_event.set()
        if self._monitor_task:
            await self._monitor_task
            self._monitor_task = None

    async def mark_seen(self, connection_id: str, station_id: str | None, name: str, role: str) -> None:
        """Record incoming activity for a station-bound user.

        Args:
            connection_id: Connection identifier (PIN/session token).
            station_id: Station identifier. If missing, activity is ignored.
            name: User display name.
            role: User role string.
        """
        if not station_id:
            return

        now = datetime.now(UTC)
        async with self._lock:
            record = self._records.get(station_id)
            if record is None:
                record = StationVitalityRecord(
                    station_id=station_id,
                    station_name=name,
                    role=role,
                    last_seen=now,
                    online=True,
                    updated_at=now,
                )
                self._records[station_id] = record

            record.station_name = name
            record.role = role
            record.last_seen = now

            station_connections = self._station_connections.setdefault(station_id, set())
            station_connections.add(connection_id)
            self._connection_to_station[connection_id] = station_id

            if not record.online:
                record.online = True
                record.updated_at = now

    async def mark_disconnected(self, connection_id: str) -> None:
        """Remove connection from active station connections.

        Args:
            connection_id: Connection identifier to remove.
        """
        now = datetime.now(UTC)
        async with self._lock:
            station_id = self._connection_to_station.pop(connection_id, None)
            if not station_id:
                return

            station_connections = self._station_connections.get(station_id)
            if station_connections:
                station_connections.discard(connection_id)
                if not station_connections:
                    self._station_connections.pop(station_id, None)

            record = self._records.get(station_id)
            if record and not self._station_connections.get(station_id):
                record.online = False
                record.updated_at = now

    async def get_station_statuses(self) -> list[dict[str, str | bool | int]]:
        """Return current station status snapshot.

        Returns:
            List of station status dictionaries sorted by station_id.
        """
        async with self._lock:
            now = datetime.now(UTC)
            items = sorted(self._records.values(), key=lambda item: item.station_id)
            statuses: list[dict[str, str | bool | int]] = []
            for item in items:
                seconds_since_last_seen = int((now - item.last_seen).total_seconds())
                statuses.append(
                    {
                        "station_id": item.station_id,
                        "name": item.station_name,
                        "role": item.role,
                        "online": item.online,
                        "last_seen": item.last_seen.isoformat(),
                        "seconds_since_last_seen": seconds_since_last_seen,
                        "active_connections": len(self._station_connections.get(item.station_id, set())),
                    }
                )
            return statuses

    async def run_timeout_check(self) -> None:
        """Evaluate offline timeout once."""
        now = datetime.now(UTC)
        async with self._lock:
            for station_id, item in self._records.items():
                idle_seconds = (now - item.last_seen).total_seconds()
                if idle_seconds > self.offline_timeout_seconds:
                    if item.online:
                        item.online = False
                        item.updated_at = now
                    self._station_connections.pop(station_id, None)

    async def _monitor_loop(self) -> None:
        """Run periodic timeout checks until stop event is set."""
        while not self._stop_event.is_set():
            await self.run_timeout_check()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.check_interval_seconds)
            except TimeoutError:
                continue


vitality_monitor = VitalityMonitor()
