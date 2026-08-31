"""Integration tests for WS notifications sent to komisaři on station changes.

Pokrývá ROADMAP.md Fázi 5 §7 - notifikace komisaři při přiřazení/změně
stanice, zapojené na `connection_manager.send_personal_message`.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import admin as admin_api
from backend.core import station_registry as station_registry_module
from backend.core.auth import AuthManager, auth_manager
from backend.main import app
from backend.models.user import UserRole


class _RecordingConnectionManager:
    """Test double capturing `send_personal_message` calls instead of using real WebSockets."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_personal_message(self, message: str, pin_code: str) -> bool:
        """Record the call and pretend delivery succeeded.

        Args:
            message: JSON message string.
            pin_code: Target station PIN.

        Returns:
            Always True - tests don't need real delivery semantics.
        """
        self.calls.append((pin_code, message))
        return True


def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(username="admin", name="Admin RZ", role=UserRole.ADMIN)
    return {"X-Session-Token": token}


def _isolated_auth_manager(tmp_path: Path) -> AuthManager:
    """Create an isolated AuthManager with an occupied and a free test station.

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
async def test_assign_user_notifies_station_pin(monkeypatch, tmp_path: Path) -> None:
    """Assigning a person should notify whoever is connected on that station's PIN."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    recorder = _RecordingConnectionManager()
    monkeypatch.setattr(admin_api, "connection_manager", recorder)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-02/assign-user",
            json={"name": "Nová Osoba", "role": "komisar_trat"},
            headers=headers,
        )

    assert response.status_code == 200
    pin_code = response.json()["station"]["pin_code"]
    assert len(recorder.calls) == 1
    notified_pin, message = recorder.calls[0]
    assert notified_pin == pin_code
    assert "TK-02" in message
    assert "Nová Osoba" in message


@pytest.mark.asyncio
async def test_release_user_notifies_station_pin(monkeypatch, tmp_path: Path) -> None:
    """Releasing a station should notify the person still connected there."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    recorder = _RecordingConnectionManager()
    monkeypatch.setattr(admin_api, "connection_manager", recorder)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-01/release-user",
            json={},
            headers=headers,
        )

    assert response.status_code == 200
    assert len(recorder.calls) == 1
    notified_pin, message = recorder.calls[0]
    assert "TK-01" in message
    assert "odebrán" in message


@pytest.mark.asyncio
async def test_move_user_notifies_source_pin_with_new_target_pin(monkeypatch, tmp_path: Path) -> None:
    """Moving a person should notify the SOURCE station's PIN with the new target PIN."""
    isolated = _isolated_auth_manager(tmp_path)
    monkeypatch.setattr(station_registry_module, "auth_manager", isolated)
    recorder = _RecordingConnectionManager()
    monkeypatch.setattr(admin_api, "connection_manager", recorder)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/station/TK-01/move-to/TK-02",
            json={},
            headers=headers,
        )

    assert response.status_code == 200
    payload = response.json()
    from_pin = payload["from_station"]["pin_code"]
    to_pin = payload["to_station"]["pin_code"]

    assert len(recorder.calls) == 1
    notified_pin, message = recorder.calls[0]
    # Notifikace jde na PŮVODNÍ PIN - tam je člověk reálně ještě připojený.
    assert notified_pin == from_pin
    assert "TK-01" in message
    assert "TK-02" in message
    assert to_pin in message
