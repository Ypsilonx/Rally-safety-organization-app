"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from backend.core.rz_context import rz_context_manager
from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor
from backend.core.station_registry import station_registry

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("/rz-context")
async def get_rz_context() -> dict[str, Any]:
    """Return public RZ context used by all clients.

    Returns:
        Current RZ name and communication reset metadata.
    """
    context = rz_context_manager.get_context()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "rz_name": context.rz_name,
        "communication_reset_version": context.communication_reset_version,
        "communication_reset_at": context.communication_reset_at,
        "updated_at": context.updated_at,
    }


@router.get("/status")
async def get_stations_status() -> dict[str, Any]:
    """Return current online/offline status for tracked stations.

    Returns:
        Timestamped snapshot of all known station vitality records.
    """
    vitality_stations = await vitality_monitor.get_station_statuses()
    station_directory = {station.station_id: station for station in station_registry.list_stations()}
    vitality_by_station = {
        str(station.get("station_id")): station
        for station in vitality_stations
        if station.get("station_id")
    }

    all_station_ids = sorted(set(station_directory.keys()) | set(vitality_by_station.keys()))

    incident_active, ready_map = await operations_state.get_station_ready_map()
    enriched_stations = []

    for station_id in all_station_ids:
        vitality = vitality_by_station.get(station_id, {})
        directory = station_directory.get(station_id)
        current_user = directory.current_user if directory else None

        enriched_stations.append(
            {
                "station_id": station_id,
                "station_name": directory.station_name if directory else station_id,
                "name": current_user.name if current_user else vitality.get("name", directory.station_name if directory else station_id),
                "role": current_user.role if current_user else vitality.get("role"),
                "phone": current_user.phone if current_user else None,
                "email": current_user.email if current_user else None,
                "address": current_user.address if current_user else None,
                "group": current_user.group if current_user else None,
                "station_type": directory.station_type.value if directory else None,
                "online": bool(vitality.get("online", False)),
                "last_seen": vitality.get("last_seen"),
                "seconds_since_last_seen": vitality.get("seconds_since_last_seen", 0),
                "active_connections": vitality.get("active_connections", 0),
                "ready": ready_map.get(station_id, not incident_active),
            }
        )

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
