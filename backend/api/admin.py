"""Admin endpoints for station-centric PIN and assignment management."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.core.auth import auth_manager
from backend.core.people_catalog import people_catalog
from backend.core.station_registry import station_registry
from pydantic import BaseModel, Field

from backend.models.people import PeopleCsvImportRequest
from backend.models.station import StationAssignmentRequest, StationCreateRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])


class StationReleaseRequest(BaseModel):
    """Payload for releasing current person from a station.

    Attributes:
        note: Optional note explaining why the station was released.
    """

    note: str | None = Field(None, max_length=200)


def require_vedeni(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Require valid vedení session for admin endpoints.

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


@router.get("/people")
async def admin_list_people(_: Annotated[dict[str, Any], Depends(require_vedeni)]) -> dict[str, Any]:
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
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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
    return {
        "success": True,
        "result": result.model_dump(mode="json"),
    }


@router.get("/stations")
async def admin_list_stations(_: Annotated[dict[str, Any], Depends(require_vedeni)]) -> dict[str, Any]:
    """Return all stations for admin management.

    Returns:
        Station list with current assignment state.
    """
    stations = station_registry.list_stations()
    return {
        "total": len(stations),
        "stations": [station.model_dump(mode="json") for station in stations],
    }


@router.post("/station/create-pin")
async def admin_create_station_pin(
    request: StationCreateRequest,
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.post("/station/{station_id}/assign-user")
@router.post("/station/{station_id}/reassign-user")
async def admin_assign_station_user(
    station_id: str,
    request: StationAssignmentRequest,
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.get("/station/{station_id}/history")
async def admin_station_history(
    station_id: str,
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }


@router.delete("/station/{station_id}/pin")
async def admin_delete_station_pin(
    station_id: str,
    _: Annotated[dict[str, Any], Depends(require_vedeni)],
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

    return {
        "success": True,
        "station": station.model_dump(mode="json"),
    }