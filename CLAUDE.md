# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Rally Safety App — real-time koordinace traťových komisařů a vedení během
rally (Rychlostní zkoušky). FastAPI + WebSocket backend, vanilla-JS PWA
frontend, žádná databáze (JSON soubory na disku), cílem je zvládnout 160+
současně připojených uživatelů. Detailní stav a plán jsou v `STATUS.md` a
`ROADMAP.md` — než začneš netriviální práci, přečti si je.

## Commands

Správa závislostí přes **uv** (ne pip/venv přímo):

```powershell
uv sync                                              # instalace dle pyproject.toml
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # backend
uv run python scripts/serve_frontend.py --host 127.0.0.1 --port 8080  # frontend (statický server)
uv run pytest                                        # celá testovací sada
uv run pytest backend/tests/test_auth_manager.py -v  # jeden test soubor
uv run pytest backend/tests/test_auth_manager.py::test_name -v  # jeden test
uv run ruff check .                                  # lint (dev dependency, konfigurace v pyproject.toml)
```

VS Code: task `UV: Start App` spustí backend i frontend najednou (Command
Palette → Tasks: Run Task).

API dokumentace (živá, vždy aktuální) běží na `http://localhost:8000/docs`
(Swagger UI) po startu backendu — needuplikuj ji ručně v `.md` souborech.

## Architecture

### Backend — vrstvy a routery

`backend/main.py` jen skládá aplikaci (CORS, lifespan, routery). Skutečná
logika je rozdělená takto:

- `backend/api/` — FastAPI routery: `auth.py` (login), `admin.py` (správa
  stanic/PINů/katalogu lidí, chráněno `X-Session-Token` hlavičkou),
  `status.py` (veřejný stav stanic/RZ kontextu), `audit.py` (frontend audit
  log), `websocket.py` (jediný WS endpoint `/ws/{auth_identifier}`).
- `backend/core/` — stavové manažery jako moduly-singletony (viz níže):
  `auth.py` (AuthManager), `connection_manager.py` (ConnectionManager),
  `station_registry.py`, `people_catalog.py`, `rz_context.py`,
  `event_logger.py`, `config.py` (Settings/`.env`), `atomic_write.py`.
- `backend/models/` — Pydantic modely (validace na hranici API).
- `backend/services/` — `vitality.py` (background task, heartbeat timeout →
  offline stanice) a `operations_state.py` (readiness gate pro RZ
  stop/hold/resume).

**Singleton moduly, ne dependency injection:** `auth_manager`,
`connection_manager`, `station_registry`, `people_catalog`, `rz_context_manager`,
`event_logger` jsou instance vytvořené na úrovni modulu (`xxx = XxxManager()`
na konci souboru) a importované přímo, kde je potřeba — žádné FastAPI
`Depends()`. Testy proti nim monkeypatchují storage cestu / interní stav.

### PIN je vázaný na stanici, ne na člověka

Klíčové architektonické rozhodnutí (viz `ROADMAP.md` Fáze 5): PIN patří
stanici (`data/pins.json`, `KomisarAccess` model), na stanici se
přiřazuje/mění osoba přes `AuthManager.assign_user_to_station()` a historie
přiřazení se drží v `assignment_history`. Výměna člověka NIKDY negeneruje
nový PIN. `station_registry.py` je station-first pohled nad stejnými daty
(pro `/api/stations`), `auth.py` je pohled pro login/PIN validaci — obojí
čte/píše do `data/pins.json`.

### Perzistence bez databáze

Veškerý stav (`data/pins.json`, `data/people_catalog.json`,
`data/rz_context.json`) jsou JSON soubory, zapisují se **atomicky** přes
`backend/core/atomic_write.py` (temp soubor + `os.replace`) — pád procesu
uprostřed zápisu soubor nepoškodí. Tyto soubory jsou v `.gitignore`
(obsahují reálná jména/telefony) — v repu jsou jen `*.example.json` vzory.
WebSocket spojení a session tokeny jsou čistě in-memory (restart = odhlásí
všechny vedení, komisaři se znovu přihlásí PINem).

### Auth — dva tiery

1. **Vedení RZ** (VRZ/ZVRZ/VBRZ/ZVBRZ) — username+heslo (bcrypt),
   `POST /api/auth/login-vedeni` → session token, posílá se v hlavičce
   `X-Session-Token` (ne cookie — proto má CORS `allow_credentials=False`).
2. **Komisaři** — PIN kód vázaný na stanici, `POST /api/auth/login-komisar`.

Obojí se pak připojuje na stejný WebSocket endpoint
`/ws/{pin_code_nebo_session_token}`.

### WebSocket broadcast

`ConnectionManager` (in-memory `pin_code -> WebSocket`) má selective
broadcast: `broadcast_to_all`, `broadcast_to_roles`, `broadcast_critical`.
`send_personal_message`/`broadcast_to_station` existují, ale zatím nemají
volajícího — jsou připravené pro ROADMAP.md Fázi 5 §7 (notifikace
komisaři při přiřazení), nemaž je bez rozmyslu.

### Frontend — pořadí načítání scriptů je závazné

`frontend/index.html` načítá JS moduly jako globální `<script>` tagy (žádný
bundler, žádné ES modules) — `auth.js` musí být první, protože definuje
`API_BASE_URL`/pozdější moduly na něj spoléhají jako na globální konstantu.
Podobně `websocket.js` definuje `WS_BASE_URL`. Nikdy nepiš nový hardcoded
`http://localhost:...` — vždy použij `API_BASE_URL`/`WS_BASE_URL`.

Moduly podle zodpovědnosti: `map.js` + `map-track.js` + `map-elements.js` +
`map-stations.js` (Leaflet), `app.js` je koordinátor + `app-operations-rz.js`
(RZ stav/gate), `app-operations-incidents.js` (incidenty), `app-tagging.js`
(`@jméno`/`#stanice` v chatu), `app-messaging.js`, `setup-admin.js` (celá
setup obrazovka pro správu stanic — oddělená od live dashboardu).

CSS je rozdělené tematicky: `base.css`, `app-shell.css`, `communication.css`,
`responsive.css` (`styles.css` je jen historický zbytek).

## Project rules (z .github/copilot-instructions.md)

- **KISS/YAGNI/DRY** — neimplementuj nic nad rámec aktuální fáze v
  `ROADMAP.md`; žádné abstraktní vrstvy/design patterny "pro budoucnost".
- Po dokončení úkolu aktualizuj `STATUS.md` (a `ROADMAP.md`, pokud se mění
  stav fáze) — ne zvlášť nový `SUMMARY.md`/`CHANGES.md` soubor.
- Bez databáze, bez frameworků na frontendu (žádné React/Vue/TypeScript) —
  dokud to explicitně nepřibude do roadmapy.
- Když najdeš nepoužívaný kód, buď ho smaž, nebo do docstringu jasně napiš
  proč tam zůstává (viz `send_personal_message` výše jako vzor).
