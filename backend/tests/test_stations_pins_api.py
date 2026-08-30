"""Integration tests for the authenticated station PIN lookup endpoint."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.core import station_registry as station_registry_module
from backend.core.auth import AuthManager, auth_manager
from backend.main import app
from backend.models.user import UserRole


def _isolated_auth_manager(tmp_path: Path) -> AuthManager:
    """Create an isolated AuthManager backed by a throwaway pins file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Fresh AuthManager with one test station PIN, never touching
        the real data/pins.json.
    """
    manager = AuthManager(pins_file=str(tmp_path / "pins.json"))
    manager.generate_pin(name="Test Komisar", role=UserRole.KOMISAR_TRAT, station_id="TK-01")
    return manager


@pytest.mark.asyncio
async def test_station_pins_requires_auth(monkeypatch, tmp_path: Path) -> None:
    """Endpoint should reject requests without a session token."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/pins")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_station_pins_rejects_komisar_pin_as_token(monkeypatch, tmp_path: Path) -> None:
    """A komisař PIN must not work as a session token for this endpoint."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    komisar_pin_code = next(iter(isolated.komisar_pins))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations/pins",
            headers={"X-Session-Token": komisar_pin_code},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_station_pins_returns_map_for_vedeni_session(monkeypatch, tmp_path: Path) -> None:
    """Vedení session should receive a station_id -> pin_code mapping."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)

    token = auth_manager.create_session(
        username="VRZ",
        name="Vedouci RZ",
        role=UserRole.VEDOUCI,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations/pins",
            headers={"X-Session-Token": token},
        )

    assert response.status_code == 200
    data = response.json()
    assert "TK-01" in data
    assert data["TK-01"].isdigit()


@pytest.mark.asyncio
async def test_station_pins_returns_map_for_admin_session(monkeypatch, tmp_path: Path) -> None:
    """Admin session should also receive the mapping."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)

    token = auth_manager.create_session(
        username="admin",
        name="Admin RZ",
        role=UserRole.ADMIN,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations/pins",
            headers={"X-Session-Token": token},
        )

    assert response.status_code == 200
    assert "TK-01" in response.json()


@pytest.mark.asyncio
async def test_station_directory_requires_auth(monkeypatch, tmp_path: Path) -> None:
    """GET /api/stations (root) must reject requests without a session token."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_station_directory_returns_data_for_vedeni_session(monkeypatch, tmp_path: Path) -> None:
    """GET /api/stations (root) should return station data for a vedení session."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)

    token = auth_manager.create_session(
        username="VRZ",
        name="Vedouci RZ",
        role=UserRole.VEDOUCI,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations",
            headers={"X-Session-Token": token},
        )

    assert response.status_code == 200
    data = response.json()
    station_ids = [station["station_id"] for station in data["stations"]]
    assert "TK-01" in station_ids


@pytest.mark.asyncio
async def test_station_detail_requires_auth(monkeypatch, tmp_path: Path) -> None:
    """GET /api/stations/{station_id} must reject requests without a session token."""
    monkeypatch.setattr(station_registry_module, "auth_manager", _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/TK-01")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_station_detail_returns_data_for_admin_session(monkeypatch, tmp_path: Path) -> None:
    """GET /api/stations/{station_id} should return station data for an admin session."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)

    token = auth_manager.create_session(
        username="admin",
        name="Admin RZ",
        role=UserRole.ADMIN,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations/TK-01",
            headers={"X-Session-Token": token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["station"]["station_id"] == "TK-01"
