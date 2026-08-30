# Oddělení ADMIN role od vedení RZ + READY gate - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Oddělit ADMIN roli (výhradní správa pozic/lidí/mapy) od vedení RZ
(VRZ/ZVRZ/VBRZ/ZVBRZ - operační dashboard s vlastním READY potvrzením), a
zpřístupnit PIN kódy stanic admin/vedení bezpečnou cestou (mapový popup),
bez veřejné expozice.

**Architecture:** Backend zpřísní `/api/admin/*` na roli `admin` jedinou
funkcí (`require_admin`), přidá nový autentizovaný endpoint
`/api/stations/pins` pro vedení+admin. Frontend přidá přísnou
`isAdminUser()` vedle stávající `isVedeniUser()`, přesměruje ADMINa po
loginu rovnou na Setup obrazovku, přidá READY tlačítko pro vedení a domerguje
PIN do mapového popupu jen pro přihlášené admin/vedení uživatele.

**Tech Stack:** FastAPI (Pydantic modely, `Depends()`), pytest +
pytest-asyncio + httpx `AsyncClient`/`ASGITransport` pro backend testy;
vanilla JS (žádný bundler/framework) + Playwright MCP pro manuální
ověření frontendu (v repu není JS test runner).

**Spec:** `docs/superpowers/specs/2026-08-30-rz-admin-permissions-design.md`

## Global Constraints

- Nikdy nezapisovat testovací data do reálného `data/pins.json` - všechny
  backend testy musí použít `tmp_path`-backed `AuthManager`/`PeopleCatalog`
  instance (monkeypatch), stejně jako `backend/tests/test_admin_people_api.py`.
- Frontend nemá test runner - "test" krok u frontend tasků je manuální
  ověření v prohlížeči přes Playwright MCP na fiktivních datech, nikdy
  proti reálné `data/pins.json`.
- Nikdy neprintovat/nezobrazovat reálná osobní data (jména/telefony/e-maily)
  z produkční `data/pins.json` při manuálním ověřování - použít vždy
  fiktivní fixture data vložená přímo do `App`/DOM.
- `/api/stations/pins` musí být registrovaný v `status.py` PŘED
  `/{station_id}` route (FastAPI matchuje v pořadí registrace - jinak by
  `/pins` spadl do dynamického `{station_id}` parametru a nikdy se
  nezavolal).
- Existující veřejná expozice telefonu/e-mailu/adresy přes
  `/api/stations/status` zůstává mimo scope (viz `STATUS.md`) - neopravovat
  v rámci tohoto plánu.

---

## Task 1: Backend - `require_admin` místo `require_vedeni`

**Files:**
- Modify: `backend/api/admin.py:49-81` (definice funkce), `:85,104,154,203,219,252,268,302,348,398,430,477,517` (`Depends(require_vedeni)` volání)
- Modify: `backend/tests/test_admin_people_api.py`

**Interfaces:**
- Produces: `require_admin(session_token: str | None) -> dict[str, Any]` - FastAPI dependency, nahrazuje `require_vedeni`, allowlist rolí zúžen na `{"admin"}`.

- [ ] **Step 1: Přejmenuj definici funkce a zúž allowlist**

V `backend/api/admin.py` nahraď:

```python
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
```

za:

```python
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
```

- [ ] **Step 2: Přepni všechna volání na novou funkci**

V `backend/api/admin.py` nahraď VŠECH 13 výskytů `Depends(require_vedeni)`
za `Depends(require_admin)` (najdi/nahraď v celém souboru - je to
identická podřetězcová shoda na každém výskytu).

- [ ] **Step 3: Uprav existující test, který dnes spoléhá na vedouci roli**

V `backend/tests/test_admin_people_api.py` nahraď:

```python
def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(
        username="admin",
        name="Vedouci RZ",
        role=UserRole.VEDOUCI,
    )
    return {"X-Session-Token": token}
```

za:

```python
def _admin_headers() -> dict[str, str]:
    """Create valid admin headers for test requests."""
    token = auth_manager.create_session(
        username="admin",
        name="Admin RZ",
        role=UserRole.ADMIN,
    )
    return {"X-Session-Token": token}
```

- [ ] **Step 4: Napiš nový test, že vedouci role dostane 403**

Přidej do `backend/tests/test_admin_people_api.py`:

```python
@pytest.mark.asyncio
async def test_admin_people_rejects_vedouci_role() -> None:
    """Vedení role should be rejected - only ADMIN may manage people."""
    token = auth_manager.create_session(
        username="VRZ",
        name="Vedouci RZ",
        role=UserRole.VEDOUCI,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/admin/people", headers={"X-Session-Token": token})

    assert response.status_code == 403
```

- [ ] **Step 5: Spusť testy a ověř, že projdou**

Run: `uv run pytest backend/tests/test_admin_people_api.py -v`
Expected: 3 testy PASS (`test_admin_people_requires_auth`,
`test_admin_people_import_and_list`, `test_admin_people_rejects_vedouci_role`)

- [ ] **Step 6: Spusť celou sadu a lint**

Run: `uv run pytest -q && uv run ruff check backend/api/admin.py backend/tests/test_admin_people_api.py`
Expected: všechny testy PASS, ruff bez nálezů

- [ ] **Step 7: Commit**

```bash
git add backend/api/admin.py backend/tests/test_admin_people_api.py
git commit -m "Zpřísni /api/admin/* jen na roli admin (require_admin místo require_vedeni)"
```

---

## Task 2: Backend - `GET /api/stations/pins` (PIN mapa pro vedení+admin)

**Files:**
- Modify: `backend/api/status.py`
- Create: `backend/tests/test_stations_pins_api.py`

**Interfaces:**
- Consumes: `auth_manager.verify_session(token)` (z `backend.core.auth`), `station_registry.list_stations() -> list[StationAccess]` (`StationAccess.station_id: str`, `.pin_code: str`)
- Produces: `GET /api/stations/pins -> dict[str, str]` (station_id -> pin_code), gated `require_vedeni_or_admin`.

- [ ] **Step 1: Přidej potřebné importy do status.py**

V `backend/api/status.py` nahraď hlavičku importů:

```python
"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from backend.core.rz_context import rz_context_manager
from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor
from backend.core.station_registry import station_registry

router = APIRouter(prefix="/api/stations", tags=["stations"])
```

za:

```python
"""Station status API endpoints."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.core.auth import auth_manager
from backend.core.rz_context import rz_context_manager
from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor
from backend.core.station_registry import station_registry

router = APIRouter(prefix="/api/stations", tags=["stations"])


def require_vedeni_or_admin(
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> dict[str, Any]:
    """Require valid vedení/admin session (not a komisař PIN) for this router.

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
```

- [ ] **Step 2: Přidej endpoint PŘED `list_station_directory`/`/{station_id}`**

V `backend/api/status.py` nahraď:

```python
@router.get("")
async def list_station_directory() -> dict[str, Any]:
```

za:

```python
@router.get("/pins")
async def get_station_pins(
    _: Annotated[dict[str, Any], Depends(require_vedeni_or_admin)],
) -> dict[str, str]:
    """Return PIN codes for all stations - visible only to vedení/admin.

    Komisaři autentizovaní přes PIN (ne session token) touto branou
    neprojdou - `verify_session` jejich PIN nikdy neuzná jako platný token.

    Returns:
        Mapping station_id -> pin_code.
    """
    return {station.station_id: station.pin_code for station in station_registry.list_stations()}


@router.get("")
async def list_station_directory() -> dict[str, Any]:
```

- [ ] **Step 3: Napiš testy pro nový endpoint**

Vytvoř `backend/tests/test_stations_pins_api.py`:

```python
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
```

- [ ] **Step 4: Spusť nové testy a ověř, že projdou**

Run: `uv run pytest backend/tests/test_stations_pins_api.py -v`
Expected: 4 testy PASS

- [ ] **Step 5: Ověř, že `/pins` nespadl pod `/{station_id}` route**

Run: `uv run pytest backend/tests/test_stations_pins_api.py::test_station_pins_returns_map_for_vedeni_session -v`
Expected: PASS se statusem 200 a klíčem `TK-01` v odpovědi (kdyby `/pins`
omylem spadl do `/{station_id}`, dostali bychom 404 "Station not found",
protože `station_registry.get_station("pins")` neexistuje)

- [ ] **Step 6: Spusť celou sadu a lint**

Run: `uv run pytest -q && uv run ruff check backend/api/status.py backend/tests/test_stations_pins_api.py`
Expected: všechny testy PASS, ruff bez nálezů

- [ ] **Step 7: Commit**

```bash
git add backend/api/status.py backend/tests/test_stations_pins_api.py
git commit -m "Přidej GET /api/stations/pins - autentizovaná PIN mapa pro vedení/admin"
```

---

## Task 3: Frontend - `isAdminUser()` + zpřísnění Setup obrazovky + landing screen

**Files:**
- Modify: `frontend/js/app-operations-rz.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/js/setup-admin.js`

**Interfaces:**
- Consumes: `app.user.role: string`
- Produces: `AppOperationsRzModule.isAdminUser(app) -> boolean`, `App.isAdminUser() -> boolean`

- [ ] **Step 1: Přidej `isAdminUser` vedle `isVedeniUser`**

V `frontend/js/app-operations-rz.js` nahraď:

```js
    isVedeniUser(app) {
        return ['vedouci', 'zastupce', 'admin'].includes(app.user?.role);
    },
};
```

za:

```js
    isVedeniUser(app) {
        return ['vedouci', 'zastupce', 'admin'].includes(app.user?.role);
    },

    /**
     * Return true when current user is strictly the ADMIN role (not
     * vedouci/zastupce) - used to gate Setup obrazovka a station/people
     * administration, odděleně od operačního dashboardu vedení.
     * @param {Object} app
     * @returns {boolean}
     */
    isAdminUser(app) {
        return app.user?.role === 'admin';
    },
};
```

- [ ] **Step 2: Přidej `App.isAdminUser()` delegující metodu**

V `frontend/js/app.js` najdi:

```js
    isVedeniUser() {
        return window.AppOperationsRzModule.isVedeniUser(this);
    },
```

a přidej hned za ni:

```js
    isAdminUser() {
        return window.AppOperationsRzModule.isAdminUser(this);
    },
```

- [ ] **Step 3: Přepni Setup obrazovku na `isAdminUser()`**

V `frontend/js/setup-admin.js` nahraď VŠECH 7 výskytů (jsou identické) `if (!app.isVedeniUser()) {` za `if (!app.isAdminUser()) {` (najdi/nahraď v celém souboru - je to identická podřetězcová shoda na každém výskytu).

- [ ] **Step 4: Uprav `setupUI()` - tlačítko Setup jen pro ADMINa**

V `frontend/js/app.js` nahraď:

```js
        // Show/hide admin panel (only for vedeni roles)
        const isVedeni = this.isVedeniUser();
        const adminPanel = document.getElementById('admin-panel');
        const quickActions = document.getElementById('quick-actions');
        const appScreen = document.getElementById('app-screen');

        if (appScreen) {
            appScreen.classList.remove('role-vedeni', 'role-komisar');
            appScreen.classList.add(isVedeni ? 'role-vedeni' : 'role-komisar');
        }
        
        if (isVedeni) {
            adminPanel.classList.remove('hidden');
            quickActions.classList.add('hidden');
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.remove('hidden');
            }
```

za:

```js
        // Show/hide admin panel (only for vedeni roles)
        const isVedeni = this.isVedeniUser();
        const isAdmin = this.isAdminUser();
        const adminPanel = document.getElementById('admin-panel');
        const quickActions = document.getElementById('quick-actions');
        const appScreen = document.getElementById('app-screen');

        if (appScreen) {
            appScreen.classList.remove('role-vedeni', 'role-komisar');
            appScreen.classList.add(isVedeni ? 'role-vedeni' : 'role-komisar');
        }
        
        if (isVedeni) {
            adminPanel.classList.remove('hidden');
            quickActions.classList.add('hidden');
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.toggle('hidden', !isAdmin);
            }
```

- [ ] **Step 5: Přesměruj ADMINa po loginu rovnou na Setup**

V `frontend/js/app.js` v metodě `init()` nahraď:

```js
        this.initializeMapModule();
        
        console.log('App initialized for user:', this.user.name);
    },
```

za:

```js
        this.initializeMapModule();

        if (this.isAdminUser()) {
            window.SetupAdminModule.openSetupScreen(this);
        }

        console.log('App initialized for user:', this.user.name);
    },
```

- [ ] **Step 6: Ověř syntaxi**

Run: `node --check frontend/js/app-operations-rz.js && node --check frontend/js/app.js && node --check frontend/js/setup-admin.js`
Expected: žádný výstup (syntaxe OK)

- [ ] **Step 7: Manuální ověření v prohlížeči (fiktivní data)**

Spusť backend (`uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000`) a
frontend (`uv run python scripts/serve_frontend.py --host 127.0.0.1 --port 8080`)
na pozadí. Přes Playwright MCP naviguj na `http://127.0.0.1:8080/index.html`,
skryj login-screen, ukaž app-screen, a over dvě role:

```js
// role admin
document.getElementById('login-screen').classList.add('hidden');
document.getElementById('app-screen').classList.remove('hidden');
document.getElementById('app-screen').classList.add('active');
App.user = { name: 'Test Admin', role: 'admin', session_token: 'fake-token' };
App.setupUI();
// očekávej: document.getElementById('open-setup-btn').classList.contains('hidden') === false

// role vedouci
App.user = { name: 'Test Vedouci', role: 'vedouci', session_token: 'fake-token' };
App.setupUI();
// očekávej: document.getElementById('open-setup-btn').classList.contains('hidden') === true
```

Dále ověř, že `setup-admin.js` guardy fungují:

```js
App.user = { name: 'Test Vedouci', role: 'vedouci' };
window.SetupAdminModule.openSetupScreen(App);
// očekávej: document.getElementById('setup-screen').classList.contains('active') === false (guard vrátil early)

App.user = { name: 'Test Admin', role: 'admin' };
App.adminStations = [];
App.adminPeople = [];
window.SetupAdminModule.openSetupScreen(App);
// očekávej: document.getElementById('setup-screen').classList.contains('active') === true
```

Po ověření zavři prohlížeč a ukonči oba servery (stejný postup jako u
předchozích commitů v tomto projektu - `Get-NetTCPConnection -LocalPort
8000,8080 | Stop-Process`).

- [ ] **Step 8: Commit**

```bash
git add frontend/js/app-operations-rz.js frontend/js/app.js frontend/js/setup-admin.js
git commit -m "Přidej isAdminUser() a zpřísni Setup obrazovku jen na ADMINa"
```

---

## Task 4: Frontend - READY tlačítko pro vedení

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/js/app-operations-rz.js`
- Modify: `frontend/js/app.js`

**Interfaces:**
- Consumes: `window.wsClient.sendMessage(payload: object)`, `app.logUiAction(action: string, detail: object)`, `app.requestGateStatusRefresh()`, `app.showToast(message: string, kind: string)`
- Produces: `AppOperationsRzModule.sendLeadershipReady(app)`, `App.sendLeadershipReady()`

- [ ] **Step 1: Přidej tlačítko do admin-panelu**

V `frontend/index.html` nahraď:

```html
                    <div class="admin-actions">
                        <button id="btn-broadcast" class="btn btn-secondary">
                            📢 Hromadná zpráva
                        </button>
                        <button class="btn btn-alert" data-alert="rz_stop">🛑 RZ zastavena</button>
```

za:

```html
                    <div class="admin-actions">
                        <button id="btn-broadcast" class="btn btn-secondary">
                            📢 Hromadná zpráva
                        </button>
                        <button id="btn-leadership-ready" class="btn btn-primary hidden">
                            ✅ Vedení připraveno
                        </button>
                        <button class="btn btn-alert" data-alert="rz_stop">🛑 RZ zastavena</button>
```

- [ ] **Step 2: Přidej `sendLeadershipReady` do app-operations-rz.js**

V `frontend/js/app-operations-rz.js` nahraď:

```js
    /**
     * Return true when current user is strictly the ADMIN role (not
     * vedouci/zastupce) - used to gate Setup obrazovka a station/people
     * administration, odděleně od operačního dashboardu vedení.
     * @param {Object} app
     * @returns {boolean}
     */
    isAdminUser(app) {
        return app.user?.role === 'admin';
    },
};
```

za:

```js
    /**
     * Return true when current user is strictly the ADMIN role (not
     * vedouci/zastupce) - used to gate Setup obrazovka a station/people
     * administration, odděleně od operačního dashboardu vedení.
     * @param {Object} app
     * @returns {boolean}
     */
    isAdminUser(app) {
        return app.user?.role === 'admin';
    },

    /**
     * Odešle READY potvrzení za pozici vedení (VRZ/ZVRZ/VBRZ/ZVBRZ) -
     * obdoba komisařské quick-action "Připraven", ale pro operační
     * dashboard vedení. ADMIN toto tlačítko nevidí (nemá station_id,
     * operations_state ho neeviduje).
     * @param {Object} app
     */
    sendLeadershipReady(app) {
        if (!this.isVedeniUser(app) || this.isAdminUser(app)) {
            return;
        }

        window.wsClient.sendMessage({
            message_type: 'status_update',
            readiness_state: 'ready',
            content: '✅ Vedení připraveno',
            created_at: new Date().toISOString(),
        });
        app.logUiAction('leadership_ready', {
            station_id: app.user.station_id || null,
        });
        app.requestGateStatusRefresh();
        app.showToast('Stav odeslán', 'success');
    },
};
```

- [ ] **Step 3: Přidej `App.sendLeadershipReady()` delegující metodu**

V `frontend/js/app.js` najdi:

```js
    isAdminUser() {
        return window.AppOperationsRzModule.isAdminUser(this);
    },
```

a přidej hned za ni:

```js
    sendLeadershipReady() {
        window.AppOperationsRzModule.sendLeadershipReady(this);
    },
```

- [ ] **Step 4: Nastav viditelnost tlačítka v `setupUI()`**

V `frontend/js/app.js` nahraď:

```js
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.toggle('hidden', !isAdmin);
            }

            const panelHeader = adminPanel.querySelector('.panel-header');
```

za:

```js
            const setupButton = document.getElementById('open-setup-btn');
            if (setupButton) {
                setupButton.classList.toggle('hidden', !isAdmin);
            }

            const leadershipReadyBtn = document.getElementById('btn-leadership-ready');
            if (leadershipReadyBtn) {
                leadershipReadyBtn.classList.toggle('hidden', isAdmin);
            }

            const panelHeader = adminPanel.querySelector('.panel-header');
```

- [ ] **Step 5: Naváž click handler**

V `frontend/js/app.js` v `bindCoreEventListeners()` nahraď:

```js
        // Broadcast button
        const broadcastBtn = document.getElementById('btn-broadcast');
        if (broadcastBtn) {
            broadcastBtn.addEventListener('click', () => {
                this.sendBroadcast();
            });
        }
```

za:

```js
        // Broadcast button
        const broadcastBtn = document.getElementById('btn-broadcast');
        if (broadcastBtn) {
            broadcastBtn.addEventListener('click', () => {
                this.sendBroadcast();
            });
        }

        const leadershipReadyBtn = document.getElementById('btn-leadership-ready');
        if (leadershipReadyBtn) {
            leadershipReadyBtn.addEventListener('click', () => {
                this.sendLeadershipReady();
            });
        }
```

- [ ] **Step 6: Ověř syntaxi**

Run: `node --check frontend/js/app-operations-rz.js && node --check frontend/js/app.js`
Expected: žádný výstup

- [ ] **Step 7: Manuální ověření v prohlížeči**

Se spuštěnými servery (viz Task 3 Step 7) a fiktivním uživatelem:

```js
App.user = { name: 'Test Vedouci', role: 'vedouci', station_id: 'VRZ' };
App.setupUI();
// očekávej: document.getElementById('btn-leadership-ready').classList.contains('hidden') === false

App.user = { name: 'Test Admin', role: 'admin' };
App.setupUI();
// očekávej: document.getElementById('btn-leadership-ready').classList.contains('hidden') === true

// Ověř odeslanou zprávu bez skutečného WS spojení - dočasně nahraď sendMessage
App.user = { name: 'Test Vedouci', role: 'vedouci', station_id: 'VRZ' };
let sentPayload = null;
window.wsClient = { sendMessage: (payload) => { sentPayload = payload; } };
App.sendLeadershipReady();
// očekávej: sentPayload.readiness_state === 'ready' && sentPayload.message_type === 'status_update'
```

- [ ] **Step 8: Commit**

```bash
git add frontend/index.html frontend/js/app-operations-rz.js frontend/js/app.js
git commit -m "Přidej READY tlačítko pro vedení (vedouci/zastupce, ne admin)"
```

---

## Task 5: Frontend - PIN v mapovém popupu pro admin/vedení

**Files:**
- Modify: `frontend/js/map-stations.js`

**Interfaces:**
- Consumes: `window.App.isVedeniUser() -> boolean`, `window.App.user.session_token: string`, `GET /api/stations/pins` (Task 2)
- Produces: `MapStationsModule.fetchStationPins() -> Promise<Object<string, string>>`

- [ ] **Step 1: Přidej `fetchStationPins()`**

V `frontend/js/map-stations.js` nahraď:

```js
const MapStationsModule = {
    /**
     * Fetch status API and render station markers.
     * @param {Object} mapModule
     * @returns {Promise<void>}
     */
    async refreshStationMarkers(mapModule) {
```

za:

```js
const MapStationsModule = {
    /**
     * Fetch PIN codes for all stations - jen pro přihlášené admin/vedení
     * (komisaři nemají session token, dostanou 401 a dostanou prázdnou
     * mapu). Selhání se tiše ignoruje - PIN v popupu je bonus, ne kritická
     * cesta.
     * @returns {Promise<Object<string, string>>}
     */
    async fetchStationPins() {
        const isVedeni = window.App?.isVedeniUser?.();
        const sessionToken = window.App?.user?.session_token;
        if (!isVedeni || !sessionToken) {
            return {};
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/stations/pins`, {
                headers: { 'X-Session-Token': sessionToken },
            });
            if (!response.ok) {
                return {};
            }
            return await response.json();
        } catch (_error) {
            return {};
        }
    },

    /**
     * Fetch status API and render station markers.
     * @param {Object} mapModule
     * @returns {Promise<void>}
     */
    async refreshStationMarkers(mapModule) {
```

- [ ] **Step 2: Domerguj PIN do dat stanic**

V `frontend/js/map-stations.js` nahraď:

```js
        try {
            const response = await fetch(mapModule.config.statusApiUrl);
            if (!response.ok) {
                throw new Error(`Status API ${response.status}`);
            }

            const payload = await response.json();
            const stations = Array.isArray(payload.stations) ? payload.stations : [];
            this.emitOfflineTransitions(mapModule, stations);
```

za:

```js
        try {
            const [response, pinsByStation] = await Promise.all([
                fetch(mapModule.config.statusApiUrl),
                this.fetchStationPins(),
            ]);
            if (!response.ok) {
                throw new Error(`Status API ${response.status}`);
            }

            const payload = await response.json();
            const stations = Array.isArray(payload.stations) ? payload.stations : [];
            stations.forEach((station) => {
                const pinCode = pinsByStation[station.station_id];
                if (pinCode) {
                    station.pin_code = pinCode;
                }
            });
            this.emitOfflineTransitions(mapModule, stations);
```

- [ ] **Step 3: Přidej řádek s PIN do popupu**

V `frontend/js/map-stations.js` nahraď:

```js
        const name = this.escapeHtml(station.name || 'Neznámé jméno');
        const positionName = this.escapeHtml(station.station_name || station.station_id || 'neuvedeno');
        const role = this.escapeHtml(station.role || 'N/A');
```

za:

```js
        const name = this.escapeHtml(station.name || 'Neznámé jméno');
        const positionName = this.escapeHtml(station.station_name || station.station_id || 'neuvedeno');
        const pinLine = station.pin_code
            ? `<p><strong>PIN:</strong> ${this.escapeHtml(station.pin_code)}</p>`
            : '';
        const role = this.escapeHtml(station.role || 'N/A');
```

Následně v témže souboru nahraď:

```js
                <p><strong>Název pozice:</strong> ${positionName}</p>
                <p><strong>Role:</strong> ${role}</p>
```

za:

```js
                <p><strong>Název pozice:</strong> ${positionName}</p>
                ${pinLine}
                <p><strong>Role:</strong> ${role}</p>
```

- [ ] **Step 4: Ověř syntaxi**

Run: `node --check frontend/js/map-stations.js`
Expected: žádný výstup

- [ ] **Step 5: Manuální ověření v prohlížeči**

Se spuštěnými servery (viz Task 3 Step 7):

```js
// Bez přihlášení / komisař - fetchStationPins vrací {}
window.App = { isVedeniUser: () => false, user: {} };
const pinsAsKomisar = await window.MapStationsModule.fetchStationPins();
// očekávej: Object.keys(pinsAsKomisar).length === 0

// Popup obsahuje PIN, jen když je v datech
const popupWithPin = window.MapStationsModule.buildStationPopup({
    station_id: 'TK-01', station_name: 'Test', online: true, pin_code: '12345678',
});
// očekávej: popupWithPin.includes('12345678') === true

const popupWithoutPin = window.MapStationsModule.buildStationPopup({
    station_id: 'TK-02', station_name: 'Test 2', online: true,
});
// očekávej: popupWithoutPin.includes('PIN') === false
```

- [ ] **Step 6: Commit**

```bash
git add frontend/js/map-stations.js
git commit -m "Zobraz PIN v mapovém popupu jen přihlášenému admin/vedení"
```

---

## Task 6: Aktualizuj STATUS.md

**Files:**
- Modify: `STATUS.md`

- [ ] **Step 1: Zapiš dokončenou práci do Recent Changes**

V `STATUS.md` nahraď:

```markdown
### 2026-08-30 (opravy: admin gate, vitality vedení, popup poznámka)
```

za:

```markdown
### 2026-08-30 (oddělení ADMIN role od vedení RZ + READY gate)
- ✅ Backend: `/api/admin/*` je nově výhradně pro roli `admin`
  (`require_admin` nahradilo `require_vedeni`, které dřív pouštělo i
  vedouci/zastupce) - přiřazování osob, PINy, název RZ, reset komunikace
  i mapová konfigurace jsou teď jen v rukou ADMINa
- ✅ Backend: nový autentizovaný `GET /api/stations/pins` (jen
  vedouci/zastupce/admin) vrací PIN mapu stanic - `/api/stations/status`
  (veřejný, bez auth) zůstává beze změny, PIN se do něj záměrně nepřidal
- ✅ Frontend: nová přísná `isAdminUser()` řídí Setup obrazovku a tlačítko
  Setup (dřív ji viděla i vedení); ADMIN po přihlášení přistává rovnou na
  Setup, může se kdykoliv přepnout na live dashboard
- ✅ Frontend: vedení (vedouci/zastupce) má v admin-panelu nové tlačítko
  "Vedení připraveno" - potvrzuje READY stejně jako komisaři na trati
  (nutné od chvíle, co vedení díky opravě vitality trackingu vstupuje do
  readiness gate)
- ✅ Frontend: mapový popup stanice ukazuje PIN, jen když je přihlášený
  uživatel admin/vedení - komisařům se PIN cizí stanice nezobrazí
- 📄 Detail viz `docs/superpowers/specs/2026-08-30-rz-admin-permissions-design.md`

### 2026-08-30 (opravy: admin gate, vitality vedení, popup poznámka)
```

- [ ] **Step 2: Odstraň vyřešený "Active Issue"**

Ponech bezpečnostní dluh (`/api/stations/status` bez auth) v `## 🐛 Active
Issues` - ten zůstává otevřený. Otevřený zápis o VRZ/PIN name-drift
(`VEDENI_CREDENTIALS` vs `station_registry`) rovněž zůstává - tento plán
ho neřeší.

- [ ] **Step 3: Commit**

```bash
git add STATUS.md
git commit -m "Aktualizuj STATUS.md o rozdělení ADMIN/vedení a READY gate"
```
