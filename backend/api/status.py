"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("/status")
async def get_stations_status() -> dict[str, Any]:
    """Return current online/offline status for tracked stations.

    Returns:
        Timestamped snapshot of all known station vitality records.
    """
    stations = await vitality_monitor.get_station_statuses()
    incident_active, ready_map = await operations_state.get_station_ready_map()
    enriched_stations = [
        {
            **station,
            "ready": ready_map.get(str(station.get("station_id")), not incident_active),
        }
        for station in stations
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_stations": len(enriched_stations),
        "incident_active": incident_active,
        "stations": enriched_stations,
    }


@router.get("/readiness")
async def get_readiness_status() -> dict[str, Any]:
    """Return current incident mode and readiness gate snapshot.

    Returns:
        Readiness state for controlled RZ resume workflow.
    """
    snapshot = await operations_state.get_snapshot()
    snapshot["generated_at"] = datetime.now(UTC).isoformat()
    return snapshot
