# Project Status & Progress Tracking

**Last Updated:** 15. července 2026  
**Current Phase:** Fáze 4 + Fáze 5 backend slice 🔄 IN PROGRESS  
**Next Phase:** Dokončení station-first backend API + napojení admin UI

> Tento soubor je hlavní zdroj pravdy pro aktuální stav implementace.

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

## ✅ Fáze 0: Příprava projektu (DOKONČENO)

**Status:** ✅ Complete  
**Completed:** 14. února 2026  
**Time:** ~2 hours

### Checklist:
- [x] Vytvořit project_plan.md
- [x] Vytvořit adresářovou strukturu projektu
- [x] Nastavit Git repository (.gitignore, první commit)
- [x] Připravit Python virtual environment
- [x] Vytvořit `requirements.txt` 
- [x] Instalace dependencies (FastAPI, Pydantic, Uvicorn)
- [x] Vytvořit `.env.example`
- [x] Vytvořit dokumentaci (README, DEVELOPMENT, ROADMAP, SETUP)
- [x] Git tag `v0.0`

### Deliverables:
✅ Kompletní adresářová struktura  
✅ Git repository inicializován  
✅ Virtual environment s dependencies  
✅ Development guidelines & roadmap  

### Issues:
- ⚠️ Python 3.13 kompatibilita s pydantic-core (vyřešeno aktualizací na pydantic 2.11+)

---

## ✅ Fáze 1: Backend MVP - WebSocket Server (DOKONČENO)

**Status:** ✅ Complete  
**Completed:** 15. února 2026  
**Time:** ~4.5 hours

### Checklist:
- [x] Vytvořit `backend/main.py` - FastAPI aplikace
- [x] Implementovat health check endpoint `GET /health`
- [x] Implementovat WebSocket endpoint `/ws/{pin_code}`
- [x] Vytvořit `backend/core/config.py` - konfigurace z .env
- [x] Vytvořit `backend/core/connection_manager.py` - WebSocket pool + selective broadcast
- [x] Vytvořit `backend/core/event_logger.py` - JSONL event logging
- [x] Vytvořit `backend/models/message.py` - Message Pydantic modely
- [x] Vytvořit `backend/models/user.py` - User, UserRole (9 rolí), KomisarAccess
- [x] Vytvořit `backend/models/station.py` - Station, StationType, capacity system
- [x] Vytvořit `backend/models/auth.py` - Login request/response modely
- [x] Vytvořit `backend/core/auth.py` - Password hashing (bcrypt), PIN generation
- [x] Implementovat `/api/auth/login-vedeni` - username + password
- [x] Implementovat `/api/auth/login-komisar` - PIN kód
- [x] Test: 2-tier login funguje
- [x] Test: Event logging zapisuje do JSONL
- [x] Test: Selective broadcast (jen určitým rolím)
- [x] Git commit + tag `v0.1`

### Files to Create:
```
backend/
├── main.py                      (NEW)
├── api/
│   └── auth.py                  (NEW)
├── core/
│   ├── config.py                (NEW)
│   ├── connection_manager.py    (NEW - s selective broadcast)
│   ├── event_logger.py          (NEW)
│   └── auth.py                  (NEW - bcrypt, sessions)
├── models/
│   ├── message.py               (NEW)
│   ├── user.py                  (NEW - 9 roles)
│   ├── station.py               (NEW)
│   └── auth.py                  (NEW)
└── logs/                        (NEW - auto-created)
```

### Deliverables:
✅ FastAPI server s WebSocket podporou  
✅ 2-tier autentizace (vedení + komisaři)  
✅ Event logger do JSONL formátu  
✅ Selective broadcast (role, station, critical)  
✅ **Perzistentní PINy** (data/pins.json) - přežijí restart serveru  
✅ Testovací helper scripty  
✅ Debug API endpoint pro PIN management  

### Important Notes:
⚠️ **Architektonické rozhodnutí pro Fázi 5:**
- PINy budou vázané na **STANICE**, ne na lidi
- Umožní snadnou výměnu lidí bez resetování PINů
- Perzistence již implementována (data/pins.json)
- Detail v [ROADMAP.md Fáze 5](ROADMAP.md#-fáze-5-admin-panel--stanice-na-mapě)

### Issues:
- ✅ test_pins.py správně přepsán na API-based místo instance confusion  

---

## ✅ Fáze 2: Frontend MVP - Login + Chat UI (DOKONČENO)

**Status:** ✅ Complete  
**Completed:** 21. února 2026  
**Time:** ~4 hours

### Checklist:
- [x] Vytvořit `frontend/index.html` - login screen + main app
- [x] Vytvořit `frontend/js/auth.js` - 2-tier login logic
- [x] Vytvořit `frontend/js/websocket.js` - WS client
- [x] Vytvořit `frontend/js/app.js` - app logic + role-based UI
- [x] Vytvořit `frontend/css/styles.css` - mobile-first CSS
- [x] Test: Vedení login (username+password) funguje
- [x] Test: Komisař login (PIN) funguje
- [x] Test: Role-based UI (vedení vidí admin panel)
- [x] Test: Chat funguje mezi browsery
- [x] Backend: Podpora session tokenů na WebSocket endpointu
- [x] Frontend: Optimistic update pro vlastní zprávy
- [x] Frontend: Hromadná zpráva s count online stanic
- [x] Git commit + tag `v0.2`

### Deliverables:
✅ Kompletní frontend aplikace (HTML/CSS/JS)  
✅ 2-tier login system (vedení + komisaři)  
✅ WebSocket real-time komunikace  
✅ Role-based UI (admin panel vs quick actions)  
✅ Mobile-first responsive design  
✅ Optimistic updates pro vlastní zprávy  
✅ Broadcast s count online stanic  
✅ Session persistence (localStorage)  
✅ Auto-reconnect při výpadku spojení

### Files Created:
```
frontend/
├── index.html           ✅
├── js/
│   ├── auth.js         ✅
│   ├── websocket.js    ✅
│   └── app.js          ✅
└── css/
    └── styles.css      ✅
```

### Backend Updates:
- ✅ WebSocket endpoint podporuje PIN i session token
- ✅ `broadcast_critical()` s exclude_pin parametrem
- ✅ Správné sender info v broadcast zprávách

---

## ✅ Fáze 3: Heartbeat & Connection Monitoring (DOKONČENO)

**Status:** ✅ Complete  
**Completed:** 12. července 2026

### Deliverables:
✅ Backend vitality service + timeout kontrola  
✅ `GET /api/stations/status` endpoint  
✅ Frontend heartbeat každých 30s  
✅ Unit testy vitality (passing)

---

## ⏳ Fáze 4-10: Pending / In Progress

_Details in [ROADMAP.md](ROADMAP.md)_

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

---

## 📝 Recent Changes

### 2026-07-15 (Fáze 5 - frontend iterace 2)
- ✅ Frontend: setup formulář má dropdown `Katalog osob` napojený na `GET /api/admin/people`
- ✅ Frontend: výběr osoby předvyplní jméno, roli a telefon pro přiřazení na pozici
- ✅ Frontend: přidáno ruční obnovení people katalogu přímo na setup obrazovce
- ✅ Validace: frontend syntax check + editor diagnostika bez chyb

### 2026-07-15 (Fáze 5 - backend iterace 2)
- ✅ Backend: přidán perzistentní people katalog (`data/people_catalog.json`)
- ✅ Backend: nový endpoint `POST /api/admin/people/import-csv` pro import osob z CSV textu
- ✅ Backend: nový endpoint `GET /api/admin/people` pro setup dropdown data
- ✅ Validace: nový test set pro katalog + admin API, backend suite 14/14 passing

### 2026-07-15 (Fáze 4 - frontend modularizace iterace 2)
- ✅ Frontend: `app-operations.js` rozdělen na `app-operations-rz.js` a `app-operations-incidents.js`
- ✅ Frontend: `map.js` rozdělen na `map-track.js` a `map-stations.js`
- ✅ Frontend: `index.html` načítá nové moduly ve stabilním pořadí
- ✅ Validace: `node --check` + browser smoke (login vedení, dashboard/setup přepínání, mapa)

### 2026-07-15 (Fáze 5 - backend iterace 1)
- 🔄 Zahájen station-first backend slice nad perzistentními PINy
- ✅ Backend: `KomisarAccess` rozšířen o historii přiřazení a metadata stanice
- ✅ Backend: přidán `backend/core/station_registry.py`
- ✅ Backend: nový endpoint `GET /api/stations` pro station directory
- ✅ Backend: nový endpoint `GET /api/stations/{station_id}` pro detail stanice
- ✅ Backend: nový endpoint `GET /api/stations/{station_id}/users` pro seznam aktuálních i historických přiřazení
- ✅ Backend: nový endpoint `GET /api/admin/stations` s auth přes `X-Session-Token`
- ✅ Backend: nový endpoint `POST /api/admin/station/create-pin`
- ✅ Backend: nové endpointy `POST /api/admin/station/{station_id}/assign-user` a `/reassign-user`
- ✅ Backend: nový endpoint `GET /api/admin/station/{station_id}/history`
- ✅ Backend: nový endpoint `POST /api/admin/station/{station_id}/release-user`
- ✅ Backend: nový endpoint `DELETE /api/admin/station/{station_id}/pin`
- ✅ Login: released stanice dočasně odmítá PIN login, dokud nepřijde nové přiřazení
- ✅ Testy: přidány persist testy pro assign/reassign, release a create/delete historii v `backend/tests/test_auth_manager.py`
- ✅ Validace: backend test suite 9/9 passing
- ✅ Smoke: create-pin -> login -> delete-pin ověřeno nad běžícím serverem

### 2026-07-15 (Fáze 5 - frontend iterace 1)
- ✅ Frontend: správa pozic přesunuta z live dashboardu do samostatné setup obrazovky
- ✅ Frontend: setup obrazovka načítá seznam pozic z `GET /api/admin/stations`
- ✅ Frontend: detail vybrané pozice zobrazuje PIN, typ, kapacitu a aktuálně přiřazenou osobu
- ✅ Frontend: historie pozice se renderuje na setup obrazovce
- ✅ Frontend: formulář umí přiřadit nebo přepsat osobu na vybrané pozici
- ✅ Frontend: akce `Uvolnit pozici` volá release endpoint a obnoví stav setup obrazovky
- ✅ Frontend: připraven samostatný prostor pro budoucí konfiguraci mapy a pozic
- ✅ Smoke: přihlášení vedení + čistý dashboard + přechod na setup obrazovku ověřeny v browseru

### 2026-07-12 (Fáze 4 - iterace 1)
- 🔄 Zahájena Fáze 4: Leaflet mapa integrovaná do hlavního UI
- ✅ Frontend: přidán `frontend/js/map.js` (inicializace mapy + načtení trati)
- ✅ Frontend: layout upraven na map-first (mapa + chat)
- ✅ Data: přidán `data/example-track.geojson` se vzorovou tratí
- ✅ Frontend: mapa se inicializuje po loginu a reaguje na změnu layoutu
- ✅ Frontend: markery stanic s online/offline barvou a popup detailem
- ✅ Frontend: mapa napojena na `/api/stations/status` s auto-refresh
- ✅ Frontend: komunikační panel přeuspořádán (desktop sidebar + mobilní slide panel)
- ✅ Frontend: obnoven oddělený info kanál pro systémové/problémové zprávy
- ✅ Dashboard: odstraněn počet zpráv, metrika stanic je online/total
- ✅ Dashboard vedení: přidána předdefinovaná krizová tlačítka pro RZ stav
- ✅ Incident flow: komisař zadává detail problému, vedení dostává varování + kontakt
- ✅ Kontakty: komisař vidí telefon na vedoucího, vedení vidí telefon odesílatele incidentu
- ✅ Chat: přidán tagging `@jmeno` a `#stanice` s našeptávačem a zvýrazněním tagů
- ✅ Chat refinement: validní zvýraznění jen pro existující tagy + klik na `#stanice` fokusuje mapu
- ✅ Mapa: marker ikony podle role/type (S/F/T/C/P/B/Z/V/+)
- ✅ Mapa: popup obsahuje i absolutní timestamp poslední aktivity
- ✅ Dokumentace: dopsán manuální map checklist pro Fázi 4
- ✅ Incident gate: backend readiness state + blokace `RZ resume` bez READY potvrzení
- ✅ Dashboard vedení: zobrazení stavu gate (`otevřeno` / `čeká READY X/Y`)
- ✅ Dashboard vedení: seznam konkrétních stanic, kterým chybí READY
- ✅ Desktop UX: komunikační panel je fixně vpravo přes celou výšku, admin panel má menší footprint
- ✅ Hotfix: obnovena viditelnost admin panelu pro vedoucí role po desktop layout změně
- ✅ Vedeni desktop: admin panel převeden na 3 sloupce (status, akce, varování)
- ✅ Hotfix 2: admin panel opět renderuje sloupce vedle sebe (odstraněn inline display override)
- ✅ Komisař: spodní quick panel je fixní a nepřekrývá ho chat panel
- ✅ Hotfix 2: komisař quick panel stabilizován (bez pravého zarovnání a bez překrytí mapy)
- ✅ Komisař: přidáno `🆘 Akutní` tlačítko bez potřeby textového vstupu
- ✅ UX: odstraněny prázdné systémové zprávy v chatu
- ✅ UX: horní lišta zobrazuje živý stav RZ + mapa mění warning border dle stavu
- ✅ UX hotfix: warning border mapy je overlay nad Leafletem (už se neschová pod mapu)
- ✅ Mapa: incident stanice aktivuje alert marker (červený pulz + vlaječka `!`)
- ✅ UX: toast notifikace přesunuty doprostřed nad mapu
- ✅ Incident feed: nejnovější varování je připnuté nahoře, historie je scroll pod ním
- ✅ Perzistence UI: chat/info/varování se obnoví po odhlášení a znovupřihlášení

## 💡 Backlog nápadů

1. Ready gate pro restart RZ: po incidentu automaticky přepnout stanice na `not_ready`.
2. RZ lze obnovit až po potvrzení `ready` ze všech klíčových pozic.
3. Dashboard vedení: samostatný seznam pozic, které nepotvrdily připravenost.
4. Dashboard vedení: rozšířené workflow pro incident -> potvrzení řešení -> návrat do provozu.

### 2026-07-12
- 🔄 **Fáze 3 zahájena** - Heartbeat & vitality monitoring implementován
- ✅ Backend: nový vitality service `backend/services/vitality.py`
- ✅ Backend: nový endpoint `GET /api/stations/status`
- ✅ Backend: WebSocket zpracování `message_type=heartbeat` bez broadcastu
- ✅ Frontend: automatický heartbeat každých 30s ve WebSocket klientovi
- ✅ Testy: přidány unit testy vitality monitoru (`backend/tests/test_vitality.py`)
- ✅ Testy: celkem 4/4 passing (`pytest backend/tests -v`)

### 2026-02-21
- ✅ **Fáze 2 dokončena** - Frontend MVP plně funkční!
- ✅ Login UI s role selection (vedení vs komisař)
- ✅ WebSocket real-time chat mezi browsery
- ✅ Role-based UI (admin panel pro vedení, quick actions pro komisaře)
- ✅ Mobile-first responsive design
- ✅ Backend: Session token support na WebSocket (/ws/{auth_identifier})
- ✅ Frontend: Optimistic update - vlastní zprávy viditelné okamžitě
- ✅ Broadcast zprávy s count online stanic
- ✅ Auto-reconnect při výpadku spojení
- ✅ Testováno: Chat funguje mezi incognito a normálním tabem
- 🎯 **Milestone 1 dosažen:** Working real-time chat!

### 2026-02-15
- ✅ Fáze 1 dokončena
- ✅ FastAPI server s WebSocket + 2-tier auth
- ✅ Event logging do JSONL
- ✅ Selective broadcasting implementována
- ✅ **Perzistentní PINy** - implementováno ukládání do data/pins.json
- ✅ Všechny testy úspěšné (login, WebSocket, logging)
- 🏗️ **Architektonické rozhodnutí:** PINy budou vázané na STANICE (ne lidi) - implementace v Fázi 5
- 📝 Aktualizován ROADMAP.md - Fáze 5 rozšířena o PIN-per-station koncept
- 📝 Připraveno na Fázi 2

### 2026-02-14
- ✅ Fáze 0 dokončena
- ✅ Vyřešen problém s pydantic-core instalací (upgrade na 2.11+)
- ✅ Vytvořena kompletní dokumentace
- ✅ Git repository inicializován

---

## 🎯 Next Actions

1. Doplnit na setup obrazovce create/delete pozice a pohodlnější přesun osoby mezi dvěma pozicemi
2. Navrhnout a implementovat konfiguraci mapy a předdefinovaných pozic na stejné setup obrazovce
3. Rozhodnout, zda držet plně dynamický station registry v `pins.json`, nebo zavést samostatný katalog stanic
4. Vrátit se k formálnímu desktop/mobile průchodu Fáze 4 před širším field testem

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
