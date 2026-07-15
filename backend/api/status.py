"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor
from backend.core.station_registry import station_registry

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


@router.get("")
async def list_station_directory() -> dict[str, Any]:
    """Return station-centric directory derived from persistent PIN storage.

    Returns:
        List of known stations with current assignments.
    """
    stations = station_registry.list_stations()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_stations": len(stations),
        "stations": [station.model_dump(mode="json") for station in stations],
    }


@router.get("/{station_id}")
async def get_station_detail(station_id: str) -> dict[str, Any]:
    """Return one station record including assignment history.

    Args:
        station_id: Station identifier.

    Returns:
        Detailed station record.

    Raises:
        HTTPException: If the station is unknown.
    """
    station = station_registry.get_station(station_id)
    if station is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Station not found")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "station": station.model_dump(mode="json"),
    }


@router.get("/{station_id}/users")
async def get_station_users(station_id: str) -> dict[str, Any]:
    """Return assignment history entries for one station.

    Args:
        station_id: Station identifier.

    Returns:
        Users currently or historically assigned to the station.

    Raises:
        HTTPException: If the station is unknown.
    """
    station = station_registry.get_station(station_id)
    if station is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Station not found")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "station_id": station_id,
        "total_users": len(station.assigned_users),
        "users": [user.model_dump(mode="json") for user in station.assigned_users],
    }
