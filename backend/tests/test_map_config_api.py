"""Integration tests for GET /api/stations/map-config and
POST /api/admin/map-config."""

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import admin as admin_api
from backend.api import status as status_module
from backend.core.auth import auth_manager
from backend.core.map_config import MapConfigManager
from backend.main import app
from backend.models.user import UserRole


@pytest.mark.asyncio
async def test_get_map_config_returns_defaults(monkeypatch, tmp_path: Path) -> None:
    """GET should return an empty config when nothing was ever saved."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(status_module, "map_config_manager", isolated)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/stations/map-config")

    assert response.status_code == 200
    data = response.json()
    assert data["track_geojson_url"] == ""
    assert data["station_coordinates"] == {}
    assert data["version"] == 0


def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(username="admin", name="Admin RZ", role=UserRole.ADMIN)
    return {"X-Session-Token": token}


class _RecordingConnectionManager:
    """Test double capturing `broadcast_to_all` calls instead of using real WebSockets."""

    def __init__(self) -> None:
        self.broadcasts: list[str] = []

    async def broadcast_to_all(self, message: str, exclude_pin=None) -> int:
        """Record the broadcast payload.

        Args:
            message: JSON message string.
            exclude_pin: Unused - kept for interface compatibility.

        Returns:
            Always 0 - tests don't need real delivery counts.
        """
        self.broadcasts.append(message)
        return 0


@pytest.mark.asyncio
async def test_post_map_config_requires_admin(monkeypatch, tmp_path: Path) -> None:
    """POST must reject requests without an admin session."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/map-config",
            json={"track_geojson_url": "/data/track.geojson"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_map_config_rejects_both_fields(monkeypatch, tmp_path: Path) -> None:
    """Providing both track_geojson_url and station_coordinate must be rejected."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/map-config",
            json={
                "track_geojson_url": "/data/track.geojson",
                "station_coordinate": {"station_id": "TK-01", "latitude": 49.2, "longitude": 16.5},
            },
            headers=headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_map_config_rejects_neither_field(monkeypatch, tmp_path: Path) -> None:
    """Providing neither field must be rejected."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/admin/map-config", json={}, headers=headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_map_config_updates_track_source_and_broadcasts(monkeypatch, tmp_path: Path) -> None:
    """A valid track source update should persist and broadcast the new version."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)
    recorder = _RecordingConnectionManager()
    monkeypatch.setattr(admin_api, "connection_manager", recorder)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/map-config",
            json={"track_geojson_url": "/data/rz-hostalkova-track.geojson"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()["map_config"]
    assert data["track_geojson_url"] == "/data/rz-hostalkova-track.geojson"
    assert data["version"] == 1

    assert len(recorder.broadcasts) == 1
    broadcast_payload = json.loads(recorder.broadcasts[0])
    assert broadcast_payload["map_config_version"] == 1


@pytest.mark.asyncio
async def test_post_map_config_updates_station_coordinate(monkeypatch, tmp_path: Path) -> None:
    """A valid station coordinate update should persist and be reflected by GET."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)
    monkeypatch.setattr(status_module, "map_config_manager", isolated)
    monkeypatch.setattr(admin_api, "connection_manager", _RecordingConnectionManager())
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        post_response = await client.post(
            "/api/admin/map-config",
            json={"station_coordinate": {"station_id": "TK-01", "latitude": 49.2088, "longitude": 16.5792}},
            headers=headers,
        )
        get_response = await client.get("/api/stations/map-config")

    assert post_response.status_code == 200
    assert get_response.json()["station_coordinates"]["TK-01"] == [49.2088, 16.5792]


@pytest.mark.asyncio
async def test_post_map_config_rejects_invalid_coordinate(monkeypatch, tmp_path: Path) -> None:
    """A latitude outside -90..90 must return 422 (Pydantic Field boundary check)."""
    isolated = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))
    monkeypatch.setattr(admin_api, "map_config_manager", isolated)
    headers = _admin_headers()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/admin/map-config",
            json={"station_coordinate": {"station_id": "TK-01", "latitude": 95.0, "longitude": 16.5792}},
            headers=headers,
        )

    assert response.status_code == 422
