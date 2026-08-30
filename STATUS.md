# Project Status & Progress Tracking

**Last Updated:** 30. srpna 2026
**Current Phase:** Fáze 4 + Fáze 5 backend slice 🔄 IN PROGRESS
**Next Phase:** Dokončení station-first backend API + napojení admin UI

> Tento soubor je hlavní zdroj pravdy pro aktuální stav implementace.
> Detailní plán a checklisty jednotlivých fází jsou v `ROADMAP.md` - sem
> patří jen průběžný stav, ne znovu celý plán.

## 📌 Executive Summary

- ✅ Dokončeno: Fáze 0-3
- 🔄 Aktivně rozpracováno: Fáze 4 (UI/UX stabilizace desktop + mobil)
- 🔄 Zahájeno z Fáze 5: backend station registry + assign/reassign API
- 🔄 Částečně dodáno z Fáze 6: incident reporting + readiness gate
- ⏳ Další priorita: doplnit zbývající Fázi 5 endpointy a napojit admin dashboard

---

## 📊 Overall Progress

```
████████████████████████░░░░░░░░░░░░░░░░░░ 50% (5/10 phases complete)
```

**Completed Phases:** 5/10
**Time Invested:** ~14.5 hours
**Estimated Remaining:** 31-45 hours

---

## 📍 Stav fází

Plný plán a checklisty jednotlivých fází jsou v [ROADMAP.md](ROADMAP.md).

| Fáze | Popis | Status | Dokončeno |
|------|-------|--------|-----------|
| 0 | Příprava projektu | ✅ | 14.2.2026 |
| 1 | Backend MVP (WS + Auth + Logging) | ✅ | 15.2.2026 |
| 2 | Frontend (2-tier Login + Chat) | ✅ | 21.2.2026 |
| 3 | Heartbeat monitoring | ✅ | 12.7.2026 |
| 4 | Mapa s Leaflet | 🔄 funkční, finální průchod odložen | - |
| 5 | Admin Panel + Stanice | 🔄 backend hotový, frontend v minimálním řezu | - |
| 6 | Incident reporting | 🔄 částečně dodáno | - |
| 7-10 | PWA, latency, GPS, production polish | ⏳ Čeká | - |

---

## 📈 Milestones

| Milestone | Phase | Target | Status |
|-----------|-------|--------|--------|
| **M1: Working Chat** | Po Fázi 2 | 21.2.2026 | ✅ Complete |
| **M1.5: Heartbeat Online/Offline** | Po Fázi 3 | 12.7.2026 | ✅ Complete |
| **M2: Incident System** | Po Fázi 6 | TBD | ⏳ Pending |
| **M3: PWA Ready** | Po Fázi 7 | TBD | ⏳ Pending |
| **M4: Production** | Po Fázi 10 | TBD | ⏳ Pending |

---

## 🐛 Active Issues

- ℹ️ Neurgentní: při frontend serveru nad `frontend/` se může objevit 404 pro `/data/example-track.geojson`.
    Aplikace používá fallback trať, funkčnost mapy tím není blokovaná.
- ⚠️ Architektonické: pozice VRZ/ZVRZ/VBRZ/ZVBRZ mají zároveň PIN-station
  záznam v `station_registry` (jméno lze "přeřadit" ze setup obrazovky) i
  natvrdo dané přihlašovací jméno ve `VEDENI_CREDENTIALS`
  (`backend/models/user.py`) — ty dva zdroje pravdy se můžou rozejít
  (mapa ukáže jiné jméno, než jaké se reálně přihlásí a píše v chatu).
  Řešení čeká na návrh (mění vztah auth/station_registry/vitality).
- 🔒 Bezpečnostní dluh: `GET /api/stations/status` a `/api/stations/{id}/users`
  (`backend/api/status.py`) nemají žádnou autentizaci — kdokoliv s přístupem
  na server vidí jméno, telefon, e-mail, adresu a skupinu ke každé pozici
  bez přihlášení (PIN mezi nimi není — ten po opravě 30.8. už žádná veřejná
  route nevrací). Vědomě odloženo — řešit jako samostatný úkol (Fáze 10
  "Security Basics" v ROADMAP.md).

---

## 📝 Recent Changes

> Starší průběžný vývoj (14.2. - 15.7.2026, Fáze 0-6 založení) je shrnutý
> níže v jednom odstavci na fázi. Detail commit po commitu je v `git log
> --oneline`, milníky fází mají git tagy `v0.1`-`v0.4`.

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
- 🔒 Backend: doplněn nálezem ze závěrečného review - `GET /api/stations` a
  `/api/stations/{id}` vracely PIN kód úplně bez autentizace (sourozenecké
  routy k nově postavenému `/pins`) - zagateováno stejnou
  `require_vedeni_or_admin` závislostí, doplněny regresní testy
- 🐛 Frontend: oprava vedlejšího efektu nového landing screenu - ADMIN po
  přistání na Setup dostával rozbitý zoom mapy při návratu na dashboard
  (mapa se inicializovala, dokud byla skrytá); inicializace mapy je pro
  admina teď odložená až na první otevření dashboardu
- 📝 Oprava README smoke testu - přihlášení na `/api/admin/stations` už
  musí být jako `admin`, ne `VRZ` (ten na tuhle routu po zpřísnění nemá přístup)
- 📄 Detail viz `docs/superpowers/specs/2026-08-30-rz-admin-permissions-design.md`

### 2026-08-30 (opravy: admin gate, vitality vedení, popup poznámka)
- ✅ Frontend: uživatel s rolí `admin` teď vidí Setup obrazovku a admin panel
  — `isVedeniUser()` (`app-operations-rz.js`) a `setupUI()` (`app.js`)
  kontrolovaly jen `vedouci`/`zastupce`, ačkoliv backend `admin` roli pro
  admin endpointy už povoloval
- ✅ Backend: vedení (VRZ/ZVRZ/VBRZ/ZVBRZ) se po přihlášení konečně
  zapisuje do vitality trackingu a svítí online/offline stejně jako
  komisaři — `websocket.py::_resolve_user` posílal pro session login
  natvrdo `station_id: None` místo skutečné hodnoty ze session dat, takže
  `vitality_monitor.mark_seen()` je vždy ignoroval
- ✅ Frontend: popup mapového prvku correctně renderuje `<br>` v poznámce
  jako řádkování místo doslovného textu `&lt;br&gt;` — nová
  `escapeHtmlWithLineBreaks()` v `map-elements.js` escapuje vše kromě
  úzké výjimky pro `<br>`/`<br/>` (ověřeno, že `<script>`/`<img onerror>`
  zůstávají escapované)

### 2026-08-30 (Fáze 5 - filtry a search na setup obrazovce)
- ✅ Frontend: setup obrazovka pro správu pozic má search (podle ID/názvu) a
  filtry typ/stav (obsazená/volná/offline)/role nad seznamem pozic —
  `frontend/js/setup-admin.js` (`getFilteredAdminStations`,
  `populateStationAdminFilterOptions`), ovládací prvky v `index.html`
- ℹ️ Vědomě bez virtual scrollingu: pro 160 pozic je vykreslení zanedbatelné,
  virtualizace by přidala komplexitu bez reálného přínosu (YAGNI)
- ℹ️ Stav "offline" ve filtru čte existující `MapModule.stationStatusCache`
  (polling z `/api/stations/status`), žádný nový backend endpoint

### 2026-08-30 (údržba + zpevnění pro produkci)
- ✅ Frontend: sjednoceny hardcoded `http://localhost:8000` volání na centrální konstantu `API_BASE_URL` (14 míst v `app.js`, `map.js`, `setup-admin.js`, `app-operations-*.js`) — appka teď jde nasadit na jiný host/port bez zásahu do kódu
- ✅ Git: odstraněny z trackování testovací session logy (`logs/rz_session_202602*.jsonl`), které se do repa dostaly ještě před přidáním `.gitignore` pravidla; obsahovaly jen fiktivní jména z vývojového testování
- ✅ Backend: nová sdílená utilita `backend/core/atomic_write.py` — `pins.json`, `people_catalog.json` a `rz_context.json` se teď zapisují atomicky (temp soubor + `os.replace`), pád procesu uprostřed zápisu už soubor nepoškodí
- ✅ Backend: `DEBUG` má bezpečný default `False` (dřív `True`) — chybějící/nezměněný `.env` už neriskuje veřejné `/api/debug/pins`; startup navíc vypíše varování, když běží `DEBUG=True` na jiném hostu než localhost
- ✅ Backend: CORS čte originy z nové `ALLOWED_ORIGINS` (`.env`), `allow_credentials` vypnuto (appka posílá token v hlavičce, ne cookie, takže wildcard + credentials nedávalo smysl)
- ✅ Backend: odstraněn nepoužívaný `SESSION_SECRET` z configu (sessions jsou náhodné opaké tokeny v serverové paměti, podpis nic nepřidával)
- ✅ Backend: `main.py` přepíná stdout/stderr na UTF-8 při startu — dřív mohl `print()` s emoji shodit server s `UnicodeEncodeError`, když výstup neběžel v UTF-8 konzoli/byl přesměrovaný do souboru
- ✅ Backend: odstraněn mrtvý kód (`AuthManager.remove_pin`, `ConnectionManager.get_users_by_role`/`get_users_at_station`) a doplněny 2 chybějící docstringy; `send_personal_message`/`broadcast_to_station` zůstávají nezapojené, ale jasně okomentované jako čekající na ROADMAP.md Fázi 5 §7
- 📝 Dokumentace (README/STATUS/ROADMAP/DEVELOPMENT) výrazně zkrácena a zarovnána se skutečným stavem kódu - detail viz níže i v jednotlivých souborech

### 2026-07-18 (Fáze 4/5 - backend + frontend refaktor)
- ✅ Backend: `api/` rozdělené na samostatné routery (`admin.py`, `audit.py`, `auth.py`, `status.py`, `websocket.py`); `main.py` zeštíhlen na inicializaci a lifespan
- ✅ Backend: nový `backend/core/rz_context.py` pro správu názvu RZ a resetu historie komunikace
- ✅ Frontend: `styles.css` rozdělen na `base.css`, `app-shell.css`, `communication.css`, `responsive.css` (`styles.css` zůstává jen jako zbytkový soubor)
- ✅ Frontend: `app-operations.js` úplně zrušen, logika je jen v `app-operations-rz.js` a `app-operations-incidents.js`
- ✅ Validace: backend test suite 17/17 passing, `data/pins.json`/`people_catalog.json`/`rz_context.json` zůstávají mimo git

### Shrnutí staršího vývoje (14.2. - 15.7.2026)
- **Fáze 0-3** (14.2.-12.7.): projekt založen, backend MVP (WebSocket + 2-tier auth + JSONL logging + perzistentní PINy), frontend MVP (login, real-time chat, role-based UI), heartbeat monitoring online/offline stanic. Detail v [ROADMAP.md](ROADMAP.md).
- **Fáze 4** (od 12.7.): Leaflet mapa nad OpenStreetMap integrovaná do map-first layoutu, typové ikony markerů podle role, GeoJSON vrstva mapových prvků (start/cíl, zdravotníci, uzavírky...), desktop/mobil iterace komunikačního panelu, chat tagging `@jméno`/`#stanice`, audit log klíčových UI akcí.
- **Fáze 5** (od 15.7.): navržen a implementován station-first PIN model (PIN vázaný na stanici, ne na člověka), station registry s historií přiřazení, samostatná setup obrazovka oddělená od live dashboardu, people katalog s CSV importem.
- **Fáze 6** (od 12.7.): incident quick action tlačítka včetně akutního režimu, readiness gate blokující `RZ resume` bez READY potvrzení všech stanic, dashboard vedení se stavem gate.

---

## 🎯 Next Actions

1. Export stanic + PINů do CSV/Excel ze setup obrazovky
2. Doplnit na setup obrazovce pohodlnější přesun osoby mezi dvěma pozicemi (dnes jen reassign na jedné)
3. Zapojit WS notifikace komisařům při přiřazení/změně stanice (primitivy v `connection_manager.py` už existují)
4. Rozhodnout, zda držet plně dynamický station registry v `pins.json`, nebo zavést samostatný katalog stanic
5. Formální desktop/mobile průchod Fáze 4 (checklist + E2E gate) odložit na závěrečnou validační iteraci

---

## 🚦 Go-Live Minimum Checklist

1. Dokumentace konzistentní: ROADMAP, STATUS, README mají stejný stav fází.
2. Mapa: role/type ikony, absolutní poslední aktivita, otestováno desktop + mobil.
3. Incident workflow: definovaný postup `incident -> not_ready -> ready potvrzení -> resume`.
4. Reconnect/auth: ověřen scénář restartu backendu a nuceného reloginu.
5. Security baseline: CORS, rate limit zpráv, vstupní sanitizace.
6. Testy: unit + základní integrační scénáře před každou rally.

---

## 📊 Time Tracking

| Phase | Estimated | Actual | Variance |
|-------|-----------|--------|----------|
| Fáze 0 | 1-2h | ~2h | On track ✅ |
| Fáze 1 | 4-5h | ~4.5h | On track ✅ |
| Fáze 2 | 3-4h | ~4h | On track ✅ |
| Fáze 3 | 4-5h | ~4h | On track ✅ |

**Total:** 14.5h / ~50h estimated

---

**Legend:**
- ✅ Complete
- 🔄 In Progress
- ⏳ Waiting
- ⚠️ Blocked
- 🐛 Issue
