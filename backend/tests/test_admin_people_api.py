"""Integration tests for admin people catalog endpoints."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import admin as admin_api
from backend.core.auth import auth_manager
from backend.core.people_catalog import PeopleCatalog
from backend.main import app
from backend.models.user import UserRole


def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(
        username="admin",
        name="Vedouci RZ",
        role=UserRole.VEDOUCI,
    )
    return {"X-Session-Token": token}


@pytest.mark.asyncio
async def test_admin_people_requires_auth() -> None:
    """People endpoints should reject requests without session token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/admin/people")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_people_import_and_list(monkeypatch, tmp_path: Path) -> None:
    """Admin should import people CSV and get them back from list endpoint."""
    catalog = PeopleCatalog(storage_file=str(tmp_path / "people_catalog.json"))
    monkeypatch.setattr(admin_api, "people_catalog", catalog)

    headers = _admin_headers()
    payload = {
        "csv_content": (
            "jmeno;telefon\n"
            "Jan Novák;+420111222333\n"
            "Eva Testovací;+420444555666\n"
        ),
        "replace_existing": False,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        import_response = await client.post(
            "/api/admin/people/import-csv",
            json=payload,
            headers=headers,
        )
    assert import_response.status_code == 200
    import_data = import_response.json()["result"]
    assert import_data["imported"] == 2
    assert import_data["updated"] == 0
    assert import_data["errors"] == []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        list_response = await client.get("/api/admin/people", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] == 2
    assert [item["name"] for item in list_data["people"]] == ["Eva Testovací", "Jan Novák"]
