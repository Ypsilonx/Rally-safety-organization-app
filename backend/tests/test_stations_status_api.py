"""Integration tests for authentication on GET /api/stations/status and .../users.

Regrese pro bezpečnostní dluh ze STATUS.md: obě routy dřív vracely jméno,
telefon, e-mail a adresu přiřazených osob komukoliv bez přihlášení.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import status as status_module
from backend.core import station_registry as station_registry_module
from backend.core.auth import AuthManager
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


def _patch_auth_manager(monkeypatch, manager: AuthManager) -> None:
    """Point both status.py and station_registry.py at the same isolated manager.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        manager: Isolated AuthManager instance to install.
    """
    monkeypatch.setattr(status_module, "auth_manager", manager)
    monkeypatch.setattr(station_registry_module, "auth_manager", manager)


@pytest.mark.asyncio
async def test_stations_status_requires_auth(monkeypatch, tmp_path: Path) -> None:
    """Anonymous request must not see contact details on stations."""
    _patch_auth_manager(monkeypatch, _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stations_status_accepts_vedeni_session(monkeypatch, tmp_path: Path) -> None:
    """Vedení session token should be accepted."""
    isolated = _isolated_auth_manager(tmp_path)
    _patch_auth_manager(monkeypatch, isolated)
    token = isolated.create_session(username="VRZ", name="Vedouci RZ", role=UserRole.VEDOUCI)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/status", headers={"X-Session-Token": token})

    assert response.status_code == 200
    station_ids = [station["station_id"] for station in response.json()["stations"]]
    assert "TK-01" in station_ids


@pytest.mark.asyncio
async def test_stations_status_accepts_komisar_pin(monkeypatch, tmp_path: Path) -> None:
    """Komisař PIN (not a session token) should also grant access."""
    isolated = _isolated_auth_manager(tmp_path)
    _patch_auth_manager(monkeypatch, isolated)
    pin_code = next(iter(isolated.komisar_pins))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/status", headers={"X-Pin-Code": pin_code})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stations_status_rejects_invalid_pin(monkeypatch, tmp_path: Path) -> None:
    """A garbage PIN must not grant access."""
    _patch_auth_manager(monkeypatch, _isolated_auth_manager(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/status", headers={"X-Pin-Code": "00000000"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_station_users_requires_vedeni_or_admin(monkeypatch, tmp_path: Path) -> None:
    """GET /api/stations/{id}/users must reject anonymous and PIN-only requests."""
    isolated = _isolated_auth_manager(tmp_path)
    _patch_auth_manager(monkeypatch, isolated)
    pin_code = next(iter(isolated.komisar_pins))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        anonymous = await client.get("/api/stations/TK-01/users")
        pin_as_token = await client.get(
            "/api/stations/TK-01/users",
            headers={"X-Session-Token": pin_code},
        )

    assert anonymous.status_code == 401
    assert pin_as_token.status_code == 401


@pytest.mark.asyncio
async def test_station_users_returns_data_for_admin_session(monkeypatch, tmp_path: Path) -> None:
    """Admin session should see the station's assignment history."""
    isolated = _isolated_auth_manager(tmp_path)
    _patch_auth_manager(monkeypatch, isolated)
    token = isolated.create_session(username="admin", name="Admin RZ", role=UserRole.ADMIN)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/api/stations/TK-01/users",
            headers={"X-Session-Token": token},
        )

    assert response.status_code == 200
    assert response.json()["station_id"] == "TK-01"
