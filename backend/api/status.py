"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.core.auth import auth_manager
from backend.core.rz_context import rz_context_manager
from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor
from backend.core.station_registry import station_registry

router = APIRouter(prefix="/api/stations", tags=["stations"])


def require_vedeni_or_admin(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Require valid vedení/admin session (not a komisař PIN) for this router.

    Args:
        session_token: Session token provided in request header.

    Returns:
        Verified session data.

    Raises:
        HTTPException: If the header is missing, invalid, or lacks privileges.
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Session-Token header",
        )

    session = auth_manager.verify_session(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    if session["role"].value not in {"vedouci", "zastupce", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges",
        )
    return session


def require_authenticated_user(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    pin_code: Annotated[str | None, Header(alias="X-Pin-Code")] = None,
) -> dict[str, Any]:
    """Require any authenticated identity - vedení/admin session, nebo komisařský PIN.

    Endpoint za touto branou vrací kontaktní údaje (telefon/e-mail/adresa)
    přiřazených osob na ostatních stanicích - to smí vidět kdokoliv reálně
    přihlášený do appky (obě auth tiers), ne anonymní HTTP klient bez PINu.

    Args:
        session_token: Session token vedení/admina.
        pin_code: PIN kód komisaře vázaný na stanici.

    Returns:
        Rozpoznaná identita - session data, nebo zjednodušený záznam z PINu.

    Raises:
        HTTPException: Pokud není přiložen platný session token ani PIN.
    """
    if session_token:
        session = auth_manager.verify_session(session_token)
        if session:
            return session

    if pin_code:
        access = auth_manager.verify_pin(pin_code)
        if access:
            return {"role": access.role, "name": access.name, "station_id": access.station_id}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (session token or PIN)",
    )


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
async def get_stations_status(
    _: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
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


@router.get("/pins")
async def get_station_pins(
    _: Annotated[dict[str, Any], Depends(require_vedeni_or_admin)],
) -> dict[str, str]:
    """Return PIN codes for all stations - visible only to vedení/admin.

    Komisaři autentizovaní přes PIN (ne session token) touto branou
    neprojdou - `verify_session` jejich PIN nikdy neuzná jako platný token.

    Returns:
        Mapping station_id -> pin_code.
    """
    return {station.station_id: station.pin_code for station in station_registry.list_stations()}


@router.get("")
async def list_station_directory(
    _: Annotated[dict[str, Any], Depends(require_vedeni_or_admin)],
) -> dict[str, Any]:
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
async def get_station_detail(
    station_id: str,
    _: Annotated[dict[str, Any], Depends(require_vedeni_or_admin)],
) -> dict[str, Any]:
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
async def get_station_users(
    station_id: str,
    _: Annotated[dict[str, Any], Depends(require_vedeni_or_admin)],
) -> dict[str, Any]:
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
