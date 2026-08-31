"""Integration tests for POST /api/admin/station/{from}/move-to/{to}."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.core import station_registry as station_registry_module
from backend.core.auth import AuthManager, auth_manager
from backend.main import app
from backend.models.user import UserRole


def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(username="admin", name="Admin RZ", role=UserRole.ADMIN)
    return {"X-Session-Token": token}


def _isolated_auth_manager(tmp_path: Path) -> AuthManager:
    """Create an isolated AuthManager with a free and an occupied test station.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Fresh AuthManager backed by a throwaway pins file with TK-01
        (occupied by Test Komisar) and TK-02 (free).
    """
    manager = AuthManager(pins_file=str(tmp_path / "pins.json"))
    manager.create_station_pin(
        station_id="TK-01",
        station_name="TK-01",
        station_type="track_point",
        capacity=1,
        description=None,
        assignee_name="Test Komisar",
        assignee_role=UserRole.KOMISAR_TRAT,
        assignee_phone="+420111222333",
    )
    manager.create_station_pin_unassigned(
        station_id="TK-02",
        station_name="TK-02",
        station_type="track_point",
        capacity=1,
        description=None,
    )
    return manager


@pytest.mark.asyncio
async def test_move_station_user_requires_admin(monkeypatch, tmp_path: Path) -> None:
    """Move endpoint must reject requests without an admin session."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/admin/station/TK-01/move-to/TK-02", json={})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_move_station_user_moves_assignee_and_frees_source(monkeypatch, tmp_path: Path) -> None:
    """Successful move should occupy the target and free the source station."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-01/move-to/TK-02",
            json={"note": "Test move"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["from_station"]["current_user"] is None
    assert data["to_station"]["current_user"]["name"] == "Test Komisar"
    assert data["to_station"]["current_user"]["phone"] == "+420111222333"


@pytest.mark.asyncio
async def test_move_station_user_rejects_occupied_target(monkeypatch, tmp_path: Path) -> None:
    """Move must be rejected when the target station already has an assignee."""
    isolated = _isolated_auth_manager(tmp_path)
    isolated.assign_user_to_station(
        station_id="TK-02", name="Already Here", role=UserRole.KOMISAR_TRAT,
    )
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-01/move-to/TK-02",
            json={},
            headers=headers,
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_move_station_user_rejects_empty_source(monkeypatch, tmp_path: Path) -> None:
    """Move must be rejected when the source station has no active assignment."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-02/move-to/TK-01",
            json={},
            headers=headers,
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_move_station_user_rejects_disallowed_role_on_leadership_target(
    monkeypatch, tmp_path: Path
) -> None:
    """A komisař must not be movable onto a reserved VRZ/ZVRZ leadership station."""
    isolated = _isolated_auth_manager(tmp_path)
    isolated.create_station_pin_unassigned(
        station_id="VRZ",
        station_name="Vedoucí RZ",
        station_type="start_finish",
        capacity=1,
        description=None,
    )
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-01/move-to/VRZ",
            json={},
            headers=headers,
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_move_station_user_unknown_stations_return_404(monkeypatch, tmp_path: Path) -> None:
    """Unknown source or target station identifiers must return 404."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        unknown_source = await client.post(
            "/api/admin/station/GHOST/move-to/TK-02", json={}, headers=headers,
        )
        unknown_target = await client.post(
            "/api/admin/station/TK-01/move-to/GHOST", json={}, headers=headers,
        )

    assert unknown_source.status_code == 404
    assert unknown_target.status_code == 404
