# Perzistentní mapová konfigurace + live sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přesunout ukládání mapové konfigurace (podklad trati + souřadnice
stanic) z localStorage prohlížeče admina na server a promítat změny všem
připojeným klientům okamžitě přes WebSocket, včetně nové možnosti nastavit
souřadnici kliknutím do mapy.

**Architecture:** Nový backend modul `map_config.py` (stejný vzor jako
`rz_context.py` — Pydantic model + manager singleton nad atomicky
zapisovaným JSON souborem), veřejný `GET` a admin-only `POST` endpoint,
live sync recyklující už existující `communication_reset_version` vzor
(monotónní verze v broadcastované `system` zprávě → klient si na změnu
verze znovu stáhne config a překreslí mapu).

**Tech Stack:** FastAPI + Pydantic v2 (backend), vanilla JS + Leaflet
(frontend), pytest + httpx `AsyncClient` (testy). Žádné nové závislosti.

**Spec:** `docs/superpowers/specs/2026-08-31-map-config-live-sync-design.md`

## Global Constraints

- Chybějící/prázdný `data/map_config.json` musí appku nechat fungovat
  přesně jako dnes (fallback na statické šablony/výchozí souřadnice) —
  žádná migrace existujících dat.
- `data/map_config.json` je per-event data (jako `pins.json`) — nesmí do
  gitu, jen `data/map_config.example.json` šablona.
- Validace vstupu (rozsah souřadnic, právě jedno pole v requestu) patří
  na hranici systému (Pydantic request model) — vnitřní `MapConfigManager`
  nic nevaliduje, důvěřuje volajícímu (stejný princip jako
  `AuthManager`/`StationRegistry`).
- Žádná nová závislost, žádná databáze — jen JSON + atomický zápis.
- Kliknutí do mapy nikdy tiše neukládá — vyplní jen formulářová pole,
  uložení je pořád na existujícím tlačítku "Uložit souřadnice pozice".

---

### Task 1: Backend `MapConfigManager` (perzistence, bez API)

**Files:**
- Create: `backend/core/map_config.py`
- Test: `backend/tests/test_map_config_manager.py`

**Interfaces:**
- Produces: `MapConfig` (Pydantic model: `track_geojson_url: str`,
  `station_coordinates: dict[str, tuple[float, float]]`, `version: int`,
  `updated_at: str | None`), `MapConfigManager` třída s metodami
  `get_config() -> MapConfig`, `set_track_source(url: str) -> MapConfig`,
  `set_station_coordinate(station_id: str, latitude: float, longitude: float) -> MapConfig`,
  konstruktor `MapConfigManager(storage_file: str = "data/map_config.json")`,
  modulová instance `map_config_manager`.

- [ ] **Step 1: Napsat padající test perzistence**

```python
"""Unit tests for MapConfigManager persistence and mutation logic."""

from pathlib import Path

from backend.core.map_config import MapConfigManager


def test_default_config_is_empty(tmp_path: Path) -> None:
    """A fresh manager with no existing file should start with empty config."""
    manager = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))

    config = manager.get_config()

    assert config.track_geojson_url == ""
    assert config.station_coordinates == {}
    assert config.version == 0


def test_set_track_source_persists_and_increments_version(tmp_path: Path) -> None:
    """Setting the track source should persist across manager restarts."""
    storage_file = str(tmp_path / "map_config.json")
    manager = MapConfigManager(storage_file=storage_file)

    updated = manager.set_track_source("/data/rz-hostalkova-track.geojson")

    assert updated.track_geojson_url == "/data/rz-hostalkova-track.geojson"
    assert updated.version == 1

    reloaded = MapConfigManager(storage_file=storage_file)
    assert reloaded.get_config().track_geojson_url == "/data/rz-hostalkova-track.geojson"
    assert reloaded.get_config().version == 1


def test_set_station_coordinate_persists_and_increments_version(tmp_path: Path) -> None:
    """Setting a station coordinate should persist and bump version."""
    storage_file = str(tmp_path / "map_config.json")
    manager = MapConfigManager(storage_file=storage_file)

    updated = manager.set_station_coordinate("TK-01", 49.2088, 16.5792)

    assert updated.station_coordinates["TK-01"] == (49.2088, 16.5792)
    assert updated.version == 1

    reloaded = MapConfigManager(storage_file=storage_file)
    assert reloaded.get_config().station_coordinates["TK-01"] == (49.2088, 16.5792)


def test_multiple_station_coordinates_accumulate(tmp_path: Path) -> None:
    """Setting coordinates for different stations should not overwrite each other."""
    manager = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))

    manager.set_station_coordinate("TK-01", 49.2088, 16.5792)
    updated = manager.set_station_coordinate("TK-02", 49.1936, 16.6241)

    assert updated.station_coordinates["TK-01"] == (49.2088, 16.5792)
    assert updated.station_coordinates["TK-02"] == (49.1936, 16.6241)
    assert updated.version == 2
```

- [ ] **Step 2: Ověřit, že test selže**

Run: `uv run pytest backend/tests/test_map_config_manager.py -v`
Expected: FAIL s `ModuleNotFoundError: No module named 'backend.core.map_config'`

- [ ] **Step 3: Implementovat `backend/core/map_config.py`**

```python
"""Persistentní konfigurace mapy (podklad trati + souřadnice pozic)
sdílená mezi backend API, frontendem a WebSocket live sync."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.core.atomic_write import atomic_write_text


class MapConfig(BaseModel):
    """Perzistentní mapová konfigurace sdílená všemi klienty.

    Attributes:
        track_geojson_url: Volitelná cesta/URL na GeoJSON podklad trati.
        station_coordinates: Souřadnice stanic přepsané adminem,
            station_id -> (lat, lon).
        version: Monotónní verze inkrementovaná při každé změně (pohání
            live sync přes WebSocket).
        updated_at: Časové razítko poslední změny.
    """

    track_geojson_url: str = ""
    station_coordinates: dict[str, tuple[float, float]] = Field(default_factory=dict)
    version: int = Field(default=0, ge=0)
    updated_at: str | None = None


class MapConfigManager:
    """Načítá, ukládá a mutuje mapovou konfiguraci v lokálním JSON úložišti.

    Validace vstupu (rozsah souřadnic apod.) je záměrně mimo tuto třídu -
    patří na hranici systému (Pydantic request model v `backend/api/admin.py`),
    stejně jako u `AuthManager`/`StationRegistry`.
    """

    def __init__(self, storage_file: str = "data/map_config.json") -> None:
        """Inicializuje manager a načte aktuální konfiguraci.

        Args:
            storage_file: Cesta k JSON souboru pro perzistenci.
        """
        self.storage_path = Path(storage_file)
        self.storage_path.parent.mkdir(exist_ok=True)
        self._config = self._load()

    def _load(self) -> MapConfig:
        """Načte konfiguraci ze souboru, nebo vytvoří výchozí.

        Returns:
            Načtená konfigurace, nebo výchozí prázdná při chybějícím/
            poškozeném souboru.
        """
        if not self.storage_path.exists():
            config = MapConfig(updated_at=datetime.now(UTC).isoformat())
            self._save(config)
            return config

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return MapConfig.model_validate(payload)
        except Exception:
            config = MapConfig(updated_at=datetime.now(UTC).isoformat())
            self._save(config)
            return config

    def _save(self, config: MapConfig) -> None:
        """Zapíše konfiguraci atomicky na disk.

        Args:
            config: Konfigurace k zápisu.
        """
        atomic_write_text(
            self.storage_path,
            json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )

    def get_config(self) -> MapConfig:
        """Vrátí aktuální konfiguraci z paměti.

        Returns:
            Aktuální mapová konfigurace.
        """
        return self._config

    def set_track_source(self, url: str) -> MapConfig:
        """Nastaví URL/cestu GeoJSON podkladu trati.

        Args:
            url: Nová cesta/URL k podkladu trati (prázdný řetězec =
                návrat na výchozí zabudovaný podklad).

        Returns:
            Aktualizovaná konfigurace.
        """
        self._config.track_geojson_url = str(url or "").strip()
        self._config.version += 1
        self._config.updated_at = datetime.now(UTC).isoformat()
        self._save(self._config)
        return self._config

    def set_station_coordinate(self, station_id: str, latitude: float, longitude: float) -> MapConfig:
        """Nastaví/přepíše souřadnici jedné stanice.

        Args:
            station_id: Identifikátor stanice - nemusí existovat v
                station_registry, souřadnice je čistě mapová vrstva.
            latitude: Zeměpisná šířka.
            longitude: Zeměpisná délka.

        Returns:
            Aktualizovaná konfigurace.
        """
        self._config.station_coordinates[station_id] = (latitude, longitude)
        self._config.version += 1
        self._config.updated_at = datetime.now(UTC).isoformat()
        self._save(self._config)
        return self._config


map_config_manager = MapConfigManager()
```

- [ ] **Step 4: Ověřit, že testy projdou**

Run: `uv run pytest backend/tests/test_map_config_manager.py -v`
Expected: 4 passed

- [ ] **Step 5: Lint a commit**

Run: `uv run ruff check backend/core/map_config.py backend/tests/test_map_config_manager.py`
Expected: `All checks passed!`

```bash
git add backend/core/map_config.py backend/tests/test_map_config_manager.py
git commit -m "Přidej MapConfigManager pro perzistentní mapovou konfiguraci

Stejný vzor jako rz_context.py - Pydantic model + manager singleton nad
atomicky zapisovaným data/map_config.json. Zatím bez API endpointů a
bez volajícího (viz spec docs/superpowers/specs/2026-08-31-map-config-live-sync-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Backend `GET /api/stations/map-config` (veřejné čtení)

**Files:**
- Modify: `backend/api/status.py`
- Test: `backend/tests/test_map_config_api.py`

**Interfaces:**
- Consumes: `map_config_manager` a `MapConfig` z Task 1
  (`backend.core.map_config`).
- Produces: `GET /api/stations/map-config` vracející
  `MapConfig.model_dump(mode="json")` - tvar `{track_geojson_url,
  station_coordinates, version, updated_at}`. Modulová proměnná
  `status.map_config_manager` (jméno, přes které testy/frontend Task 3
  izolují/patchují stav).

- [ ] **Step 1: Napsat padající test**

```python
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
```

Save this as `backend/tests/test_map_config_api.py` (nový soubor - Task 3
do něj přidá další testy).

- [ ] **Step 2: Ověřit, že test selže**

Run: `uv run pytest backend/tests/test_map_config_api.py -v`
Expected: FAIL - `404` (route zatím neexistuje) nebo import error

- [ ] **Step 3: Přidat endpoint do `backend/api/status.py`**

Přidat import na začátek souboru (vedle ostatních `from backend.core...`):

```python
from backend.core.map_config import map_config_manager
```

Přidat nový endpoint (např. hned za `get_rz_context`, před `get_stations_status`):

```python
@router.get("/map-config")
async def get_map_config() -> dict[str, Any]:
    """Return current shared map configuration.

    Veřejné bez autentizace - souřadnice a URL trati nejsou PII, stejná
    úroveň jako `/rz-context`. Volají ho všichni klienti při startu mapy
    i po live-sync notifikaci o změně verze.

    Returns:
        Track GeoJSON URL, souřadnicové přepisy stanic a verze configu.
    """
    config = map_config_manager.get_config()
    return config.model_dump(mode="json")
```

- [ ] **Step 4: Ověřit, že test projde**

Run: `uv run pytest backend/tests/test_map_config_api.py -v`
Expected: 1 passed

- [ ] **Step 5: Lint, celá sada a commit**

Run: `uv run ruff check backend/api/status.py backend/tests/test_map_config_api.py && uv run pytest -q`
Expected: `All checks passed!`, všechny testy (existující i nové) zelené

```bash
git add backend/api/status.py backend/tests/test_map_config_api.py
git commit -m "Přidej GET /api/stations/map-config

Veřejné čtení sdílené mapové konfigurace - zatím bez zápisu (Task 3).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Backend `POST /api/admin/map-config` + live sync broadcast

**Files:**
- Modify: `backend/api/admin.py`
- Modify: `backend/tests/test_map_config_api.py`

**Interfaces:**
- Consumes: `map_config_manager` z Task 1, `_build_station_notice` (už
  existuje v `admin.py` od dřívějška, zde se rozšiřuje o `extra_fields`).
- Produces: `POST /api/admin/map-config` (admin-only), request model
  `MapConfigUpdateRequest` (pole `track_geojson_url: str | None`,
  `station_coordinate: StationCoordinateUpdate | None` - právě jedno
  vyplněné), response `{success: true, map_config: {...}}`. Broadcast
  všem klientům obsahuje `map_config_version` - to čte Task 7 na
  frontendu.

- [ ] **Step 1: Napsat padající testy (doplnit do `test_map_config_api.py`)**

Přidat na začátek souboru (k existujícím importům) a na konec souboru:

```python
import json

from backend.api import admin as admin_api
from backend.core.auth import auth_manager
from backend.models.user import UserRole


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
```

- [ ] **Step 2: Ověřit, že nové testy selžou**

Run: `uv run pytest backend/tests/test_map_config_api.py -v`
Expected: FAIL na nových testech (`404` - endpoint zatím neexistuje),
předchozí `test_get_map_config_returns_defaults` z Task 2 dál PASSED

- [ ] **Step 3: Rozšířit `_build_station_notice` o `extra_fields`**

V `backend/api/admin.py` najít stávající funkci `_build_station_notice`
(zavedená dříve pro notifikace komisařům) a nahradit ji touto verzí:

```python
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
```

(Beze změny chování pro 3 stávající volání - `extra_fields` má výchozí
`None`.)

- [ ] **Step 4: Přidat import a request modely do `backend/api/admin.py`**

Upravit řádek s importem z `pydantic`:

```python
from pydantic import BaseModel, Field, model_validator
```

Přidat import manageru vedle ostatních `from backend.core...` importů:

```python
from backend.core.map_config import map_config_manager
```

Přidat request modely vedle stávajícího `StationReleaseRequest`:

```python
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
```

- [ ] **Step 5: Přidat endpoint (vedle ostatních `/station/...` admin endpointů)**

```python
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
```

- [ ] **Step 6: Ověřit, že všechny testy projdou**

Run: `uv run pytest backend/tests/test_map_config_api.py backend/tests/test_admin_notifications.py -v`
Expected: všechny PASSED (existující `test_admin_notifications.py`
ověří, že rozšíření `_build_station_notice` nerozbilo stávající
notifikace)

- [ ] **Step 7: Lint, celá sada a commit**

Run: `uv run ruff check backend/ && uv run pytest -q`
Expected: `All checks passed!`, všechny testy zelené

```bash
git add backend/api/admin.py backend/tests/test_map_config_api.py
git commit -m "Přidej POST /api/admin/map-config s live-sync broadcastem

Admin-only zápis mapové konfigurace (podklad trati / souřadnice jedné
stanice), po úspěchu broadcast všem klientům s map_config_version -
frontend Task 7 na to zareaguje okamžitým refreshem mapy.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Frontend `MapModule.loadServerMapConfig()` + priorita zdrojů

**Files:**
- Modify: `frontend/js/map.js`

**Interfaces:**
- Consumes: `GET /api/stations/map-config` z Task 2.
- Produces: `MapModule.mapConfigVersion` (number), `MapModule.loadServerMapConfig({redraw})`
  - čte a aplikuje server config jako nejvyšší prioritní vrstvu; volá ji
    i Task 7 (live sync) i Task 6 (žádná změna zde, jen konzument).

- [ ] **Step 1: Přidat `mapConfigVersion` a novou metodu do `MapModule`**

V `frontend/js/map.js` přidat vlastnost vedle `isInitialized: false,`:

```js
    isInitialized: false,
    mapConfigVersion: 0,
```

Přidat novou metodu (např. hned před `init()`):

```js
    /**
     * Fetch server-persisted map config (track source + station coordinate
     * overrides) and apply it as the highest-priority layer over static
     * defaults/templates. Used both at map init and for live WS updates.
     * @param {Object} [options]
     * @param {boolean} [options.redraw=false] - Re-render track/markers
     *     after applying (init() draws right after calling this itself,
     *     so it passes false; live WS updates pass true).
     * @returns {Promise<void>}
     */
    async loadServerMapConfig({ redraw = false } = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/stations/map-config`);
            if (!response.ok) {
                return;
            }

            const payload = await response.json();
            if (payload.track_geojson_url) {
                this.config.trackGeoJsonUrl = payload.track_geojson_url;
            }
            if (payload.station_coordinates && typeof payload.station_coordinates === 'object') {
                this.stationCoordinates = { ...this.stationCoordinates, ...payload.station_coordinates };
            }
            this.mapConfigVersion = Number(payload.version || 0);

            if (redraw && this.isInitialized) {
                await this.refreshTrack();
                await this.refreshStationMarkers();
            }
        } catch (_error) {
            // Best-effort - existing map state (defaults/static templates) stays as-is.
        }
    },
```

- [ ] **Step 2: Zavolat ji na začátku `init()`, před načtením trati**

Najít v `init()`:

```js
        L.tileLayer(MAP_CONFIG.tileUrl, {
            maxZoom: 19,
            attribution: MAP_CONFIG.attribution,
        }).addTo(this.map);

        const geojson = await window.MapTrackModule.loadTrackGeoJson(this);
```

Nahradit za:

```js
        L.tileLayer(MAP_CONFIG.tileUrl, {
            maxZoom: 19,
            attribution: MAP_CONFIG.attribution,
        }).addTo(this.map);

        await this.loadServerMapConfig();

        const geojson = await window.MapTrackModule.loadTrackGeoJson(this);
```

- [ ] **Step 3: Opravit prioritu v `loadStationCoordinates()` - jen doplňovat chybějící klíče**

Najít:

```js
            const payload = await response.json();
            const incoming = payload?.coordinates;
            if (!incoming || typeof incoming !== 'object') {
                continue;
            }

            this.stationCoordinates = {
                ...this.stationCoordinates,
                ...incoming,
            };
            break;
```

Nahradit za:

```js
            const payload = await response.json();
            const candidateCoordinates = payload?.coordinates;
            if (!candidateCoordinates || typeof candidateCoordinates !== 'object') {
                continue;
            }

            const missingOnly = {};
            Object.entries(candidateCoordinates).forEach(([stationId, coordinate]) => {
                if (!this.stationCoordinates[stationId]) {
                    missingOnly[stationId] = coordinate;
                }
            });

            this.stationCoordinates = {
                ...this.stationCoordinates,
                ...missingOnly,
            };
            break;
```

Tím server config (aplikovaný v kroku 2, dřív než tahle metoda běží)
zůstane nejvyšší prioritou - statická šablona doplní jen to, co server
nepokrývá. Stejný princip jako existující vrstva
`loadCommissionerCoordinates()` o pár řádků níž (ta `if
(!this.stationCoordinates[key])` kontrolu už má).

- [ ] **Step 4: Odstranit nepoužívaný `getRuntimeConfig()`**

Po Task 5 (kde se ruší jediné volající místo `applyStoredMapConfig`)
bude tahle metoda mrtvý kód. Smazat teď rovnou, ať se nezapomene:

Najít a smazat celý blok:

```js
    /**
     * Return current runtime map configuration for setup persistence.
     * @returns {{trackGeoJsonUrl: string, stationCoordinates: Object<string, Array<number>>}}
     */
    getRuntimeConfig() {
        return {
            trackGeoJsonUrl: this.config.trackGeoJsonUrl || '',
            stationCoordinates: { ...this.stationCoordinates },
        };
    },

```

- [ ] **Step 5: Syntax check**

Run: `node --check frontend/js/map.js`
Expected: bez výstupu (žádná chyba)

- [ ] **Step 6: Commit**

```bash
git add frontend/js/map.js
git commit -m "MapModule: načítej mapovou konfiguraci ze serveru jako nejvyšší prioritu

loadServerMapConfig() se volá na začátku init() (před track/station
loadingem) a bude ji volat i live-sync z Task 7. Statická šablona
(loadStationCoordinates) teď jen doplňuje chybějící klíče místo aby
server config přepisovala - stejný princip jako existující
commissioner-coordinates vrstva. getRuntimeConfig() smazán jako mrtvý
kód (jediné volající místo mizí v Task 5).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Frontend Setup obrazovka ukládá přes server (ne localStorage)

**Files:**
- Modify: `frontend/js/setup-admin.js`
- Modify: `frontend/js/app.js`

**Interfaces:**
- Consumes: `POST /api/admin/map-config` z Task 3,
  `MapModule.loadServerMapConfig()` z Task 4, existující
  `this.adminFetch(app, url, options)` helper.
- Produces: `saveSelectedSetupStationCoordinate(app)` a
  `applySetupTrackSource(app)` teď ukládají na server. `syncMapConfigForm(app)`
  (beze změny signatury) nahrazuje `applyStoredMapConfig` na všech 3
  voláních místech. Nová `SetupAdminModule.showSetupScreenOnly(app) -> boolean`
  (jen přepnutí viditelnosti obrazovky, žádný reload dat) - konzumuje ji
  Task 6.

- [ ] **Step 1: Smazat localStorage vrstvu ze `setup-admin.js`**

Najít a smazat celý blok (4 metody: `getMapConfigStorageKey`,
`readStoredMapConfig`, `storeMapConfig`, `applyStoredMapConfig`):

```js
    /**
     * Return local storage key for setup map configuration.
     * @returns {string}
     */
    getMapConfigStorageKey() {
        return 'rally_setup_map_config_v1';
    },

    /**
     * Read map config from local storage.
     * @returns {{trackGeoJsonUrl: string, stationCoordinates: Object<string, Array<number>>}}
     */
    readStoredMapConfig() {
        try {
            const raw = localStorage.getItem(this.getMapConfigStorageKey());
            if (!raw) {
                return { trackGeoJsonUrl: '', stationCoordinates: {} };
            }
            const parsed = JSON.parse(raw);
            return {
                trackGeoJsonUrl: String(parsed.trackGeoJsonUrl || ''),
                stationCoordinates: parsed.stationCoordinates && typeof parsed.stationCoordinates === 'object'
                    ? parsed.stationCoordinates
                    : {},
            };
        } catch (_error) {
            return { trackGeoJsonUrl: '', stationCoordinates: {} };
        }
    },

    /**
     * Persist map config to local storage.
     * @param {Object} payload
     */
    storeMapConfig(payload) {
        localStorage.setItem(this.getMapConfigStorageKey(), JSON.stringify(payload));
    },

    /**
     * Merge map runtime config with storage and apply on startup/setup open.
     * @param {Object} app
     */
    applyStoredMapConfig(app) {
        if (!window.MapModule) {
            return;
        }

        const stored = this.readStoredMapConfig();
        const runtime = window.MapModule.getRuntimeConfig
            ? window.MapModule.getRuntimeConfig()
            : { trackGeoJsonUrl: '', stationCoordinates: {} };

        const mergedCoordinates = {
            ...(runtime.stationCoordinates || {}),
            ...(stored.stationCoordinates || {}),
        };

        window.MapModule.setTrackSource(stored.trackGeoJsonUrl || runtime.trackGeoJsonUrl || '');
        window.MapModule.setStationCoordinates(mergedCoordinates);
        this.storeMapConfig({
            trackGeoJsonUrl: String(stored.trackGeoJsonUrl || runtime.trackGeoJsonUrl || ''),
            stationCoordinates: mergedCoordinates,
        });
        this.syncMapConfigForm(app);
    },

```

(Metoda `syncMapConfigForm`, která je hned pod tímhle blokem, zůstává
beze změny.)

- [ ] **Step 2: Nahradit volání `applyStoredMapConfig` na 3 místech**

V `frontend/js/setup-admin.js` najít celou metodu `openSetupScreen(app)`:

```js
    openSetupScreen(app) {
        if (!app.isAdminUser()) {
            return;
        }

        const appScreen = document.getElementById('app-screen');
        const setupScreen = document.getElementById('setup-screen');
        if (!appScreen || !setupScreen) {
            return;
        }

        appScreen.classList.remove('active');
        appScreen.classList.add('hidden');
        setupScreen.classList.remove('hidden');
        setupScreen.classList.add('active');
        app.currentScreen = 'setup';
        app.logUiAction('open_setup_screen', {});

        this.applyStoredMapConfig(app);

        Promise.all([
            this.loadAdminStations(app),
            this.loadAdminPeople(app),
            this.loadRzConfig(app),
        ]).catch((error) => {
```

(pokračuje `console.error(...)` a uzavírací `});`, `},` - ty zůstávají
beze změny). Nahradit za:

```js
    /**
     * Toggle screen visibility to Setup without reloading any data - used
     * by openSetupScreen() and by the map coordinate picker (Task 6),
     * který nesmí za běhu triggerovat reload seznamu pozic - přepsal by
     * právě vyplněné lat/lon pole zpátky na dřív uloženou hodnotu.
     * @param {Object} app
     * @returns {boolean} True, pokud byly obě obrazovky nalezené a přepnuté.
     */
    showSetupScreenOnly(app) {
        const appScreen = document.getElementById('app-screen');
        const setupScreen = document.getElementById('setup-screen');
        if (!appScreen || !setupScreen) {
            return false;
        }

        appScreen.classList.remove('active');
        appScreen.classList.add('hidden');
        setupScreen.classList.remove('hidden');
        setupScreen.classList.add('active');
        app.currentScreen = 'setup';
        return true;
    },

    /**
     * Switch to dedicated setup screen for positions and map configuration.
     * @param {Object} app
     */
    openSetupScreen(app) {
        if (!app.isAdminUser()) {
            return;
        }

        if (!this.showSetupScreenOnly(app)) {
            return;
        }
        app.logUiAction('open_setup_screen', {});

        this.syncMapConfigForm(app);

        Promise.all([
            this.loadAdminStations(app),
            this.loadAdminPeople(app),
            this.loadRzConfig(app),
        ]).catch((error) => {
```

(zbytek metody - `console.error(...)` a uzavírací `});`, `},` - beze
změny.)

V `frontend/js/setup-admin.js`, uvnitř `resetSetupMapConfig(app)`, najít:

```js
        localStorage.removeItem(this.getMapConfigStorageKey());
        window.MapModule.resetRuntimeConfig();

        this.applyStoredMapConfig(app);
```

Nahradit za:

```js
        window.MapModule.resetRuntimeConfig();

        this.syncMapConfigForm(app);
```

(Reset teď mění jen lokální pohled admina zpátky na výchozí hodnoty -
NEmaže server konfiguraci sdílenou se všemi. Vědomé rozhodnutí, viz
poznámka v handoff shrnutí plánu.)

V `frontend/js/app.js`, uvnitř `init()`, najít:

```js
        if (window.SetupAdminModule?.applyStoredMapConfig) {
            window.SetupAdminModule.applyStoredMapConfig(this);
        }
```

Nahradit za:

```js
        if (window.MapModule?.loadServerMapConfig) {
            window.MapModule.loadServerMapConfig().catch((error) => {
                console.error('Initial map config load failed:', error);
            });
        }
```

- [ ] **Step 3: Přepsat `saveSelectedSetupStationCoordinate` na server zápis**

Najít celou metodu `saveSelectedSetupStationCoordinate(app)` a nahradit ji:

```js
    /**
     * Save selected station coordinates from setup form to the server.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async saveSelectedSetupStationCoordinate(app) {
        const stationId = app.selectedAdminStationId;
        if (!stationId || !window.MapModule) {
            app.showToast('Nejprve vyber pozici ze seznamu', 'info');
            return;
        }

        const latInput = document.getElementById('map-station-lat');
        const lonInput = document.getElementById('map-station-lon');
        const latitude = Number(latInput?.value);
        const longitude = Number(lonInput?.value);

        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
            app.showToast('Zadej platné souřadnice lat/lon', 'error');
            return;
        }

        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            app.showToast('Souřadnice jsou mimo povolený rozsah', 'error');
            return;
        }

        const response = await this.adminFetch(app, `${API_BASE_URL}/api/admin/map-config`, {
            method: 'POST',
            body: JSON.stringify({
                station_coordinate: { station_id: stationId, latitude, longitude },
            }),
        });

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Souřadnice se nepodařilo uložit', 'error');
            return;
        }

        window.MapModule.setStationCoordinates({
            ...window.MapModule.stationCoordinates,
            [stationId]: [latitude, longitude],
        });

        app.logUiAction('setup_station_coordinates_saved', {
            station_id: stationId,
            latitude,
            longitude,
        });

        if (window.MapModule.isInitialized) {
            await window.MapModule.refreshStationMarkers();
        }

        app.showToast(`Souřadnice ${stationId} uloženy`, 'success');
    },
```

- [ ] **Step 4: Přepsat `applySetupTrackSource` na server zápis**

Najít celou metodu `applySetupTrackSource(app)` a nahradit ji:

```js
    /**
     * Apply custom track source from setup form and persist it on the server.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async applySetupTrackSource(app) {
        const trackInput = document.getElementById('map-track-path');
        if (!trackInput || !window.MapModule) {
            return;
        }

        const trackGeoJsonUrl = String(trackInput.value || '').trim();

        const response = await this.adminFetch(app, `${API_BASE_URL}/api/admin/map-config`, {
            method: 'POST',
            body: JSON.stringify({ track_geojson_url: trackGeoJsonUrl }),
        });

        if (!response) {
            return;
        }

        if (!response.ok) {
            app.showToast('Podklad trati se nepodařilo uložit', 'error');
            return;
        }

        window.MapModule.setTrackSource(trackGeoJsonUrl);
        app.logUiAction('setup_track_source_updated', {
            track_geojson_url: trackGeoJsonUrl || 'default',
        });

        if (window.MapModule.isInitialized) {
            await window.MapModule.refreshTrack();
        }

        app.showToast('Podklad trati aktualizován', 'success');
    },
```

- [ ] **Step 5: Syntax check obou souborů**

Run: `node --check frontend/js/setup-admin.js && node --check frontend/js/app.js`
Expected: bez výstupu (žádná chyba)

- [ ] **Step 6: Manuální ověření v prohlížeči**

Spustit backend (`uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000`)
a frontend (`uv run python scripts/serve_frontend.py --host 127.0.0.1 --port 8080`),
otevřít `http://localhost:8080`, přihlásit se jako `admin`/`demo123`,
na Setup obrazovce vybrat libovolnou pozici, zadat souřadnice ručně a
kliknout "Uložit souřadnice pozice" - ověřit v Network tabu, že jde
`POST /api/admin/map-config` (ne zápis do localStorage), a že
`GET /api/stations/map-config` po refreshi stránky vrací uloženou
hodnotu. Zkontrolovat konzoli bez nových chyb. Servery pak ukončit.

- [ ] **Step 7: Commit**

```bash
git add frontend/js/setup-admin.js frontend/js/app.js
git commit -m "Setup obrazovka ukládá mapovou konfiguraci na server

saveSelectedSetupStationCoordinate a applySetupTrackSource místo
localStorage volají POST /api/admin/map-config - změna je teď vidět
všem klientům, ne jen v prohlížeči admina. localStorage vrstva
(getMapConfigStorageKey/readStoredMapConfig/storeMapConfig/
applyStoredMapConfig) zrušena, 3 volající místa přepnuta na
syncMapConfigForm()/loadServerMapConfig(). Reset map config teď mění
jen lokální pohled, nemaže sdílenou server konfiguraci (vědomé
rozhodnutí). openSetupScreen() rozdělen na novou showSetupScreenOnly()
(jen přepnutí obrazovky) + zbytek s reloadem dat - připraveno pro
Task 6, který potřebuje přepnout obrazovku BEZ async reloadu (ten by
přepsal čerstvě vyplněné souřadnice zpátky na starou hodnotu).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Frontend "Vybrat na mapě" - klikací nastavení souřadnice

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/setup-admin.js`
- Modify: `frontend/js/app.js`

**Interfaces:**
- Consumes: `window.MapModule.map` (Leaflet instance), `app.initializeMapModule()`
  (upravováno v tomto tasku, aby vracelo Promise), `this.openDashboardScreen(app)`
  (existující) a `this.showSetupScreenOnly(app)` z Task 5.
- Produces: `SetupAdminModule.pickSelectedSetupStationCoordinateOnMap(app)`,
  tlačítko `#btn-map-station-pick`.

- [ ] **Step 1: Přidat tlačítko do `frontend/index.html`**

Najít:

```html
                    <div class="station-admin-actions">
                        <button type="button" id="btn-map-station-load" class="btn btn-secondary">Načíst souřadnice pozice</button>
                        <button type="button" id="btn-map-station-save" class="btn btn-primary">Uložit souřadnice pozice</button>
                        <button type="button" id="btn-map-config-reset" class="btn btn-alert">Reset map config</button>
                    </div>
```

Nahradit za:

```html
                    <div class="station-admin-actions">
                        <button type="button" id="btn-map-station-load" class="btn btn-secondary">Načíst souřadnice pozice</button>
                        <button type="button" id="btn-map-station-pick" class="btn btn-secondary">Vybrat na mapě</button>
                        <button type="button" id="btn-map-station-save" class="btn btn-primary">Uložit souřadnice pozice</button>
                        <button type="button" id="btn-map-config-reset" class="btn btn-alert">Reset map config</button>
                    </div>
```

- [ ] **Step 2: Nechat `initializeMapModule()` v `app.js` vracet Promise**

Najít:

```js
    initializeMapModule() {
        if (!window.MapModule || typeof window.MapModule.init !== 'function') {
            return;
        }

        requestAnimationFrame(() => {
            window.MapModule.init()
                .then(() => {
                    if (!window.MapModule.isInitialized) {
                        return window.MapModule.init();
                    }
                    return null;
                })
                .catch((error) => {
                    console.error('Map initialization failed:', error);
                });
        });
    },
```

Nahradit za:

```js
    initializeMapModule() {
        if (!window.MapModule || typeof window.MapModule.init !== 'function') {
            return Promise.resolve();
        }

        return new Promise((resolve) => {
            requestAnimationFrame(() => {
                window.MapModule.init()
                    .then(() => {
                        if (!window.MapModule.isInitialized) {
                            return window.MapModule.init();
                        }
                        return null;
                    })
                    .catch((error) => {
                        console.error('Map initialization failed:', error);
                    })
                    .finally(resolve);
            });
        });
    },
```

(Oba stávající volající - `App.init()` a `openDashboardScreen()` - Promise
ignorují stejně jako dřív, chování se pro ně nemění.)

- [ ] **Step 3: Přidat `pickSelectedSetupStationCoordinateOnMap` do `setup-admin.js`**

Vložit hned za metodu `saveSelectedSetupStationCoordinate` (z Task 5):

```js
    /**
     * Switch to the live dashboard and arm a one-shot map click listener
     * that fills the selected station's lat/lon fields with the clicked
     * point, then returns to Setup. Saving still requires the explicit
     * "Uložit souřadnice pozice" button - clicking the map never saves
     * silently.
     *
     * Setup obrazovka a dashboard (kde jediný žije Leaflet `#map`) jsou
     * dvě vzájemně skryté obrazovky - proto je nutné dočasně přepnout na
     * dashboard, počkat na inicializaci mapy a po kliku se vrátit zpět.
     * Návrat používá `showSetupScreenOnly()` (ne plný `openSetupScreen()`)
     * záměrně - `openSetupScreen()` by asynchronně přenačetl seznam pozic
     * a jeho render by o chvíli později přepsal právě vyplněné pole zpátky
     * na dřív uloženou hodnotu.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async pickSelectedSetupStationCoordinateOnMap(app) {
        if (!app.selectedAdminStationId) {
            app.showToast('Nejprve vyber pozici ze seznamu', 'info');
            return;
        }

        const stationId = app.selectedAdminStationId;
        this.openDashboardScreen(app);

        if (!window.MapModule?.isInitialized) {
            await app.initializeMapModule();
        }
        if (!window.MapModule?.map) {
            app.showToast('Mapu se nepodařilo načíst', 'error');
            return;
        }

        app.showToast(`Klikni do mapy pro umístění pozice ${stationId}`, 'info');
        window.MapModule.map.once('click', (event) => {
            if (app.selectedAdminStationId !== stationId) {
                return;
            }

            this.showSetupScreenOnly(app);

            const latInput = document.getElementById('map-station-lat');
            const lonInput = document.getElementById('map-station-lon');
            if (latInput) {
                latInput.value = event.latlng.lat.toFixed(6);
            }
            if (lonInput) {
                lonInput.value = event.latlng.lng.toFixed(6);
            }

            app.showToast('Souřadnice vyplněny - ulož je tlačítkem "Uložit souřadnice pozice"', 'success');
        });
    },
```

- [ ] **Step 4: Zapojit tlačítko v `app.js`**

Najít v `bindSetupAdminEventListeners()`:

```js
        const loadCoordsBtn = document.getElementById('btn-map-station-load');
        if (loadCoordsBtn) {
            loadCoordsBtn.addEventListener('click', () => {
                window.SetupAdminModule.loadSelectedSetupStationCoordinate(this);
            });
        }
```

Přidat hned za tenhle blok:

```js

        const pickCoordsBtn = document.getElementById('btn-map-station-pick');
        if (pickCoordsBtn) {
            pickCoordsBtn.addEventListener('click', () => {
                window.SetupAdminModule.pickSelectedSetupStationCoordinateOnMap(this).catch((error) => {
                    console.error('Map coordinate picker failed:', error);
                    this.showToast('Výběr na mapě selhal', 'error');
                });
            });
        }
```

- [ ] **Step 5: Syntax check**

Run: `node --check frontend/js/setup-admin.js && node --check frontend/js/app.js`
Expected: bez výstupu (žádná chyba)

- [ ] **Step 6: Manuální ověření v prohlížeči**

Přihlásit se jako `admin`, na Setup obrazovce vybrat pozici, kliknout
"Vybrat na mapě" - ověřit, že appka přepne na dashboard, po kliku do
mapy se vrátí zpět na Setup a pole lat/lon jsou vyplněná. Zkontrolovat
konzoli bez nových chyb.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/js/setup-admin.js frontend/js/app.js
git commit -m "Přidej klikací nastavení souřadnice pozice na mapě

Nové tlačítko 'Vybrat na mapě' - přepne na dashboard (tam jediný žije
Leaflet #map), po kliku do mapy vyplní lat/lon pole a vrátí se na
Setup. Uložení zůstává na existujícím tlačítku, klik na mapu nic tiše
neukládá. initializeMapModule() teď vrací Promise, aby šlo počkat na
dokončení inicializace mapy před registrací click listeneru.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Frontend live sync přes WebSocket

**Files:**
- Modify: `frontend/js/app-messaging.js`

**Interfaces:**
- Consumes: `window.MapModule.mapConfigVersion` a `window.MapModule.loadServerMapConfig({redraw})`
  z Task 4, `map_config_version` pole broadcastované z Task 3.

- [ ] **Step 1: Přidat zpracování `map_config_version` do `handleMessage`**

Najít v `frontend/js/app-messaging.js`:

```js
        if (normalized.communication_reset_version !== undefined) {
            app.applyCommunicationResetVersion(normalized.communication_reset_version, true);
        }
        app.registerSenderForTagging(normalized);
```

Nahradit za:

```js
        if (normalized.communication_reset_version !== undefined) {
            app.applyCommunicationResetVersion(normalized.communication_reset_version, true);
        }
        if (normalized.map_config_version !== undefined && window.MapModule) {
            const currentVersion = window.MapModule.mapConfigVersion || 0;
            if (Number(normalized.map_config_version) > currentVersion) {
                window.MapModule.loadServerMapConfig({ redraw: true }).catch((error) => {
                    console.error('Map config live refresh failed:', error);
                });
            }
        }
        app.registerSenderForTagging(normalized);
```

- [ ] **Step 2: Syntax check**

Run: `node --check frontend/js/app-messaging.js`
Expected: bez výstupu (žádná chyba)

- [ ] **Step 3: Manuální ověření živě ve dvou session (klíčový test celého plánu)**

Spustit backend + frontend. Otevřít dvě okna prohlížeče:
- Okno A: přihlásit se jako `admin`/`demo123`, otevřít Setup, vybrat
  libovolnou pozici.
- Okno B: přihlásit se jako `VRZ`/`demo123` (nebo libovolný komisařský
  PIN z `data/pins.json`), zůstat na dashboardu s otevřenou mapou.

V okně A uložit novou souřadnici vybrané pozice tlačítkem "Uložit
souřadnice pozice". Bez jakéhokoliv refreshe v okně B ověřit, že se
marker dané pozice na mapě posune sám (do pár set ms) a v chatu/info
panelu přibyde systémová zpráva o aktualizaci. Zkontrolovat konzoli v
obou oknech bez nových chyb. Servery pak ukončit.

- [ ] **Step 4: Commit**

```bash
git add frontend/js/app-messaging.js
git commit -m "Zapoj live sync mapové konfigurace přes WebSocket

handleMessage reaguje na map_config_version stejně jako už dřív na
communication_reset_version - při vyšší verzi než aktuální
MapModule.mapConfigVersion okamžitě refetchne config a překreslí mapu,
bez čekání na 15s polling nebo reload.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `.gitignore`, example soubor, dokumentace

**Files:**
- Modify: `.gitignore`
- Create: `data/map_config.example.json`
- Modify: `STATUS.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Žádné nové - jen data/dokumentační uzavření tasku.

- [ ] **Step 1: Přidat `data/map_config.json` do `.gitignore`**

Najít v `.gitignore`:

```
data/rz_context.json
```

Nahradit za:

```
data/rz_context.json
data/map_config.json
```

- [ ] **Step 2: Vytvořit `data/map_config.example.json`**

```json
{
  "track_geojson_url": "",
  "station_coordinates": {},
  "version": 0,
  "updated_at": null
}
```

- [ ] **Step 3: Aktualizovat STATUS.md**

Do sekce "Recent Changes" (nahoru, nad poslední záznam) přidat nový
odstavec popisující tuto změnu (perzistentní mapová konfigurace +
live sync + klikací editace souřadnic), do "Next Actions" doplnit
navazující krok "Přidávání/mazání pozic z mapy" (odloženo v rámci
tohoto designu, viz spec).

- [ ] **Step 4: Aktualizovat ROADMAP.md**

Ve Fázi 4 (Mapa) doplnit hotový bod o perzistentní konfiguraci +
live sync a poznámku, že přidávání/mazání pozic z mapy je navazující
krok mimo tento plán.

- [ ] **Step 5: Spustit celou sadu naposledy**

Run: `uv run pytest -q && uv run ruff check .`
Expected: všechny testy PASSED, `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add .gitignore data/map_config.example.json STATUS.md ROADMAP.md
git commit -m "Ukonči perzistentní mapovou konfiguraci - gitignore, šablona, docs

data/map_config.json je per-event data jako pins.json - do gitu jen
example šablona. STATUS.md/ROADMAP.md aktualizovány, navazující krok
(přidávání/mazání pozic z mapy) zapsán jako Next Action.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
