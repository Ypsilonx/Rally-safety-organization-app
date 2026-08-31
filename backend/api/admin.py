"""Admin endpoints for station-centric PIN and assignment management."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.core.auth import auth_manager
from backend.core.connection_manager import connection_manager
from backend.core.event_logger import event_logger
from backend.core.map_config import map_config_manager
from backend.core.people_catalog import people_catalog
from backend.core.rz_context import rz_context_manager
from backend.core.station_registry import station_registry
from pydantic import BaseModel, Field, model_validator

from backend.models.people import PeopleCsvImportRequest
from backend.models.station import (
    StationAssignmentRequest,
    StationBulkGeneratePinsRequest,
    StationCreateRequest,
    StationMoveRequest,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class StationReleaseRequest(BaseModel):
    """Payload for releasing current person from a station.

    Attributes:
        note: Optional note explaining why the station was released.
    """

    note: str | None = Field(None, max_length=200)


class RzConfigUpdateRequest(BaseModel):
    """Payload for updating RZ display configuration.

    Attributes:
        rz_name: Human-readable race stage name.
    """

    rz_name: str = Field(..., min_length=1, max_length=120)


class StationCoordinateUpdate(BaseModel):
    """One station's coordinate override.

    Attributes:
        station_id: Station identifier (nemusí existovat v
            station_registry - souřadnice je čistě mapová vrstva).
        latitude: Geographic latitude.
        longitude: Geographic longitude.
    """

    station_id: str = Field(..., min_length=1, max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class MapConfigUpdateRequest(BaseModel):
    """Payload for updating one part of the shared map configuration.

    Právě jedno z `track_geojson_url` nebo `station_coordinate` musí být
    vyplněné.

    Attributes:
        track_geojson_url: New GeoJSON track source (empty string resets
            to default).
        station_coordinate: New coordinate override for one station.
    """

    track_geojson_url: str | None = Field(None, max_length=500)
    station_coordinate: StationCoordinateUpdate | None = None

    @model_validator(mode="after")
    def _validate_exactly_one_field(self) -> "MapConfigUpdateRequest":
        """Ensure the request updates exactly one map config field.

        Returns:
            Validated request.

        Raises:
            ValueError: If both or neither field is provided.
        """
        if (self.track_geojson_url is None) == (self.station_coordinate is None):
            raise ValueError(
                "Musí být zadáno právě jedno z track_geojson_url nebo station_coordinate"
            )
        return self


def require_admin(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Require valid ADMIN session for station/people/map admin endpoints.

    Vedení RZ (vedouci/zastupce) na tyto endpointy záměrně nemá přístup -
    přiřazování osob na pozice, mazání/regenerace PINů a konfigurace mapy
    je výhradně v rukou ADMINa (viz design doc pro odůvodnění).

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

    if session["role"].value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges",
        )
    return session


def _build_station_notice(
    content: str, priority: str = "normal", extra_fields: dict[str, Any] | None = None
) -> str:
    """Build JSON system-message payload for a personal station notification.

    Stejný formát jako ostatní systémové hlášky (rz-config, reset historie) -
    frontend je vykreslí do chatu/info panelu bez jakékoli úpravy, žádná
    nová logika na klientovi není potřeba.

    Args:
        content: Human-readable Czech notice text.
        priority: Message priority shown to the recipient client.
        extra_fields: Volitelná další pole vmergovaná do zprávy (např.
            `map_config_version` pro spuštění live-sync na klientovi).

    Returns:
        JSON-encoded message ready for `connection_manager.send_personal_message`
        or `connection_manager.broadcast_to_all`.
    """
    notice = {
        "message_id": f"stationnotice_{datetime.now(UTC).timestamp()}",
        "created_at": datetime.now(UTC).isoformat(),
        "sender": {
            "user_id": "system",
            "name": "Systém",
            "role": "system",
        },
        "message_type": "system",
        "priority": priority,
        "content": content,
    }
    if extra_fields:
        notice.update(extra_fields)
    return json.dumps(notice, ensure_ascii=False)


@router.get("/rz-config")
async def admin_get_rz_config(_: Annotated[dict[str, Any], Depends(require_admin)]) -> dict[str, Any]:
    """Return current persistent RZ context for setup UI.

    Returns:
        Current RZ name and communication reset metadata.
    """
    context = rz_context_manager.get_context()
    return {
        "success": True,
        "rz_name": context.rz_name,
        "communication_reset_version": context.communication_reset_version,
        "communication_reset_at": context.communication_reset_at,
        "updated_at": context.updated_at,
    }


@router.post("/rz-config")
async def admin_update_rz_config(
    request: RzConfigUpdateRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Update RZ display name used by frontend and log files.

    Args:
        request: New RZ display configuration.

    Returns:
        Updated RZ context.
    """
    context = rz_context_manager.set_rz_name(request.rz_name)
    event_logger.set_rz_name(context.rz_name)

    event_logger.log_event(
        "admin_action",
        {
            "action": "update_rz_config",
            "actor": session["username"],
            "role": session["role"].value,
            "rz_name": context.rz_name,
        },
    )

    notice = {
        "message_id": f"rzcfg_{datetime.now(UTC).timestamp()}",
        "created_at": datetime.now(UTC).isoformat(),
        "sender": {
            "user_id": "system",
            "name": "Systém",
            "role": "system",
        },
        "message_type": "system",
        "priority": "normal",
        "content": f"Název RZ byl nastaven na: {context.rz_name}",
        "rz_name": context.rz_name,
    }
    recipients = await connection_manager.broadcast_to_all(json.dumps(notice, ensure_ascii=False))

    return {
        "success": True,
        "rz_name": context.rz_name,
        "communication_reset_version": context.communication_reset_version,
        "communication_reset_at": context.communication_reset_at,
        "updated_at": context.updated_at,
        "notified_connections": recipients,
    }


@router.post("/reset-communication-history")
async def admin_reset_communication_history(
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Mark global communication history reset for next RZ session.

    Args:
        session: Verified admin session.

    Returns:
        Updated communication reset metadata and delivery counters.
    """
    context = rz_context_manager.reset_communication_history()
    event_logger.log_event(
        "admin_action",
        {
            "action": "reset_communication_history",
            "actor": session["username"],
            "role": session["role"].value,
            "communication_reset_version": context.communication_reset_version,
        },
        severity="warning",
    )

    reset_notice = {
        "message_id": f"rzreset_{datetime.now(UTC).timestamp()}",
        "created_at": datetime.now(UTC).isoformat(),
        "sender": {
            "user_id": "system",
            "name": "Systém",
            "role": "system",
        },
        "message_type": "system",
        "priority": "high",
        "content": "Komunikace byla resetována pro novou RZ.",
        "rz_name": context.rz_name,
        "communication_reset_version": context.communication_reset_version,
    }
    recipients = await connection_manager.broadcast_to_all(json.dumps(reset_notice, ensure_ascii=False))

    return {
        "success": True,
        "rz_name": context.rz_name,
        "communication_reset_version": context.communication_reset_version,
        "communication_reset_at": context.communication_reset_at,
        "updated_at": context.updated_at,
        "notified_connections": recipients,
    }


@router.get("/people")
async def admin_list_people(_: Annotated[dict[str, Any], Depends(require_admin)]) -> dict[str, Any]:
    """Return catalog of people for setup assignment dropdown.

    Returns:
        Sorted people list for setup screen prefill.
    """
    people = people_catalog.list_people()
    return {
        "total": len(people),
        "people": [person.model_dump(mode="json") for person in people],
    }


@router.post("/people/import-csv")
async def admin_import_people_csv(
    request: PeopleCsvImportRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Import people catalog from CSV text.

    Args:
        request: CSV payload and replace flag.

    Returns:
        Import summary with counters and validation errors.
    """
    result = people_catalog.import_csv(
        csv_content=request.csv_content,
        replace_existing=request.replace_existing,
    )
    event_logger.log_event(
        "admin_action",
        {
            "action": "import_people_csv",
            "actor": session["username"],
            "role": session["role"].value,
            "replace_existing": request.replace_existing,
            "imported": result.imported,
            "updated": result.updated,
            "errors": len(result.errors),
        },
    )
    return {
        "success": True,
        "result": result.model_dump(mode="json"),
    }


@router.get("/stations")
async def admin_list_stations(_: Annotated[dict[str, Any], Depends(require_admin)]) -> dict[str, Any]:
    """Return all stations for admin management.

    Returns:
        Station list with current assignment state.
    """
    stations = station_registry.list_stations()
    return {
        "total": len(stations),
        "stations": [station.model_dump(mode="json") for station in stations],
    }


@router.post("/station/bulk-generate-pins")
async def admin_bulk_generate_station_pins(
    request: StationBulkGeneratePinsRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Generate station-bound PINs from map templates in bulk.

    Args:
        request: Bulk generation options.

    Returns:
        Summary counters for created/regenerated/skipped stations.
    """
    summary = station_registry.bulk_generate_station_pins_from_map(
        regenerate_existing=request.regenerate_existing,
    )

    event_logger.log_event(
        "admin_action",
        {
            "action": "bulk_generate_station_pins",
            "actor": session["username"],
            "role": session["role"].value,
            "regenerate_existing": request.regenerate_existing,
            **summary,
        },
    )

    return {
        "success": True,
        "summary": summary,
    }


@router.post("/station/create-pin")
async def admin_create_station_pin(
    request: StationCreateRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Create a new station-bound PIN with initial assignee.

    Args:
        request: Station creation payload.

    Returns:
        Created station view including generated PIN.

    Raises:
        HTTPException: If the station already exists.
    """
    try:
        station = station_registry.create_station(request)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "create_station_pin",
            "actor": session["username"],
            "role": session["role"].value,
            "station_id": request.station_id,
            "station_name": request.station_name,
            "station_type": request.station_type.value,
            "assignee_name": request.name,
            "assignee_role": request.role.value,
        },
    )

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.post("/station/{station_id}/assign-user")
@router.post("/station/{station_id}/reassign-user")
async def admin_assign_station_user(
    station_id: str,
    request: StationAssignmentRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Assign or reassign a user to an existing station PIN.

    Args:
        station_id: Station identifier to update.
        request: New current assignment.

    Returns:
        Updated station view.

    Raises:
        HTTPException: If the station is unknown.
    """
    try:
        station = station_registry.assign_user(station_id, request)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "assign_or_reassign_station_user",
            "actor": session["username"],
            "role": session["role"].value,
            "station_id": station_id,
            "assignee_name": request.name,
            "assignee_role": request.role.value,
            "phone": request.phone,
            "note": request.note,
        },
    )

    await connection_manager.send_personal_message(
        _build_station_notice(
            f"Přiřazení pozice {station_id} bylo aktualizováno: {request.name} ({request.role.value})."
        ),
        station.pin_code,
    )

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.post("/station/{from_station_id}/move-to/{to_station_id}")
async def admin_move_station_user(
    from_station_id: str,
    to_station_id: str,
    request: StationMoveRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Move the current assignee from one station to another in one operation.

    Args:
        from_station_id: Station identifier to move the person off.
        to_station_id: Station identifier to move the person onto.
        request: Optional move note.

    Returns:
        Updated source and target station views.

    Raises:
        HTTPException: If either station is unknown, the source has no
            active assignment, the target is already occupied, or the
            role is not allowed on the target station.
    """
    try:
        from_station, to_station = station_registry.move_user(
            from_station_id, to_station_id, request.note
        )
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "move_station_user",
            "actor": session["username"],
            "role": session["role"].value,
            "from_station_id": from_station_id,
            "to_station_id": to_station_id,
            "assignee_name": to_station.current_user.name if to_station.current_user else None,
            "note": request.note,
        },
    )

    # Notifikace jde na PŮVODNÍ (zdrojovou) pozici - tam je člověk reálně
    # ještě připojený, protože PIN je vázaný na stanici, ne na osobu.
    # Na cílovou pozici notifikaci posílat nemá smysl, musela být volná.
    await connection_manager.send_personal_message(
        _build_station_notice(
            f"Byl jsi přesunut z pozice {from_station_id} na pozici {to_station_id}. "
            f"Odhlas se a přihlas se novým PINem {to_station.pin_code} pro pozici {to_station_id}.",
            priority="high",
        ),
        from_station.pin_code,
    )

    return {
        "success": True,
        "from_station": from_station.model_dump(mode="json"),
        "to_station": to_station.model_dump(mode="json"),
    }


@router.get("/station/{station_id}/history")
async def admin_station_history(
    station_id: str,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Return assignment history for one station.

    Args:
        station_id: Station identifier.

    Returns:
        Station history with active and historical assignments.

    Raises:
        HTTPException: If the station is unknown.
    """
    try:
        history = station_registry.get_station_history(station_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return {
        "station_id": station_id,
        "total": len(history),
        "history": [entry.model_dump(mode="json") for entry in history],
    }


@router.post("/station/{station_id}/release-user")
async def admin_release_station_user(
    station_id: str,
    request: StationReleaseRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Release current user from an existing station PIN.

    Args:
        station_id: Station identifier to update.
        request: Optional release note.

    Returns:
        Updated station view with no active current user.

    Raises:
        HTTPException: If the station is unknown or has no active assignment.
    """
    try:
        station = station_registry.release_user(station_id, request.note)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "release_station_user",
            "actor": session["username"],
            "role": session["role"].value,
            "station_id": station_id,
            "note": request.note,
        },
    )

    await connection_manager.send_personal_message(
        _build_station_notice(f"Byl jsi odebrán z pozice {station_id}."),
        station.pin_code,
    )

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.delete("/station/{station_id}/pin")
async def admin_delete_station_pin(
    station_id: str,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Delete station-bound PIN record.

    Args:
        station_id: Station identifier to delete.

    Returns:
        Removed station view for confirmation.

    Raises:
        HTTPException: If the station is unknown.
    """
    try:
        station = station_registry.delete_station(station_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "delete_station_pin",
            "actor": session["username"],
            "role": session["role"].value,
            "station_id": station_id,
        },
    )

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.post("/station/{station_id}/regenerate-pin")
async def admin_regenerate_station_pin(
    station_id: str,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Regenerate PIN for one station while keeping station assignment mapping.

    Args:
        station_id: Station identifier whose PIN should be rotated.

    Returns:
        Previous PIN and updated station view.

    Raises:
        HTTPException: If the station is unknown.
    """
    try:
        old_pin, station = station_registry.regenerate_station_pin(station_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    event_logger.log_event(
        "admin_action",
        {
            "action": "regenerate_station_pin",
            "actor": session["username"],
            "role": session["role"].value,
            "station_id": station_id,
            "old_pin_code": old_pin,
            "new_pin_code": station.pin_code,
        },
        severity="warning",
    )

    return {
        "success": True,
        "old_pin_code": old_pin,
        "station": station.model_dump(mode="json"),
    }


@router.post("/map-config")
async def admin_update_map_config(
    request: MapConfigUpdateRequest,
    session: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    """Update one part of the shared map configuration and notify all clients live.

    Args:
        request: New track source, or a new station coordinate override.
        session: Verified admin session.

    Returns:
        Updated map configuration.
    """
    if request.track_geojson_url is not None:
        config = map_config_manager.set_track_source(request.track_geojson_url)
        action = "update_map_track_source"
        details: dict[str, Any] = {"track_geojson_url": request.track_geojson_url}
        notice_content = "Podklad trati byl aktualizován."
    else:
        coordinate = request.station_coordinate
        config = map_config_manager.set_station_coordinate(
            coordinate.station_id, coordinate.latitude, coordinate.longitude
        )
        action = "update_map_station_coordinate"
        details = {
            "station_id": coordinate.station_id,
            "latitude": coordinate.latitude,
            "longitude": coordinate.longitude,
        }
        notice_content = f"Souřadnice pozice {coordinate.station_id} byly aktualizovány."

    event_logger.log_event(
        "admin_action",
        {
            "action": action,
            "actor": session["username"],
            "role": session["role"].value,
            **details,
        },
    )

    await connection_manager.broadcast_to_all(
        _build_station_notice(
            notice_content,
            extra_fields={"map_config_version": config.version},
        )
    )

    return {
        "success": True,
        "map_config": config.model_dump(mode="json"),
    }