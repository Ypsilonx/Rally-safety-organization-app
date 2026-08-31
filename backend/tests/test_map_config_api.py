"""Integration tests for GET /api/stations/map-config and
POST /api/admin/map-config."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import status as status_module
from backend.core.map_config import MapConfigManager
from backend.main import app


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
