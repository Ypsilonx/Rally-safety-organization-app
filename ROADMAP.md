# Rally Safety App - Development Roadmap

## 🎯 Cíl: Postupný vývoj od MVP k plné funkcionalitě

**Pravidlo:** Dokončit a otestovat každou fázi před přechodem na další.

Aktuální průběžný stav drž v `STATUS.md`. Tento dokument je plán a backlog po fázích.

---

## 📍 Fáze 0: Příprava projektu ✅

**Cíl:** Nastavit vývojové prostředí a základní strukturu

### Úkoly:
- [x] Vytvořit project_plan.md
- [x] Vytvořit adresářovou strukturu projektu
- [x] Nastavit Git repository
- [x] Připravit Python virtual environment
- [x] Vytvořit `.gitignore`
- [x] Vytvořit `requirements.txt`

### Výstup:
- Prázdná, ale kompletní struktura projektu
- Git inicializovaný s prvním commitem
- Virtual environment aktivní

**Trvání:** 1-2 hodiny  
**Kritérium úspěchu:** Můžeš spustit `python --version` a `git status` bez chyb

---

## 📍 Fáze 1: Backend MVP - WebSocket + Auth + Logging ✅

**Cíl:** WebSocket server s 2-tier autentizací, event loggingem a podporou 160+ uživatelů  
**Status:** ✅ DOKONČENO (15. února 2026)  
**Čas:** ~4.5 hodin

### Co bylo implementováno:

1. **FastAPI základy** (`backend/main.py`) ✅
   - [x] Základní FastAPI aplikace
   - [x] Health check endpoint: `GET /health`
   - [x] WebSocket endpoint: `/ws/{pin_code}` (autentizovaný)
   - [x] Stats endpoint: `GET /api/stats`
   - [x] Debug PIN endpoint: `GET /api/debug/pins`

2. **Authentication System** (`backend/core/auth.py`, `backend/api/auth.py`) ✅
   - [x] **Tier 1 (Vedení RZ):** Username + Password (bcrypt hashed)
   - [x] **Tier 2 (Komisaři):** PIN kódy (4místné, generované vedoucím)
   - [x] Session management pro vedení
   - [x] PIN validation pro komisaře
   - [x] Endpoints: `/api/auth/login-vedeni`, `/api/auth/login-komisar`

3. **User & Role Models** (`backend/models/user.py`) ✅
   - [x] `UserRole` enum: 9 rolí (vedouci, zastupce, komisar_trat, casomer, parkovani, atd.)
   - [x] `User` model: user_id, name, role, station_id
   - [x] `KomisarAccess` model: PIN, name, phone, station assignment
   - [x] Hardcoded vedení credentials (admin/demo123)
   - [x] In-memory PIN storage

4. **Station Models** (`backend/models/station.py`) ✅
   - [x] `StationType` enum: track_point, corner, timing, parking, medical, atd.
   - [x] `Station` model: station_id, name, type, lat, lon, capacity
   - [x] Support pro více lidí na jedné stanici (capacity system)

5. **Connection Manager** (`backend/core/connection_manager.py`) ✅
   - [x] Správa WebSocket spojení (200 max connections)
   - [x] **Selective Broadcasting:**
     - `broadcast_to_roles()` - jen určité role
     - `broadcast_to_station()` - jen určitá stanice
     - `broadcast_critical()` - STOP RZ všem
   - [x] PIN → WebSocket mapping
   - [x] Role tracking

6. **Event Logger** (`backend/core/event_logger.py`) ✅
   - [x] JSONL logging všech events
   - [x] Log file per RZ session: `logs/rz_session_YYYYMMDD_HHMMSS.jsonl`
   - [x] Events: login, connection, message, broadcast, error
   - [x] Structured JSON format pro post-race analýzu

7. **Message Models** (`backend/models/message.py`) ✅
   - [x] `StationMessage`: message_id, created_at, message_type, content
   - [x] `MessagePriority`: critical, high, normal, low
   - [x] `MessageType`: chat, incident, status_update, broadcast, system

8. **Testování** ✅
   - [x] Test script pro zobrazení PINů (`backend/tests/test_pins.py`)
   - [x] WebSocket test client (`backend/tests/test_websocket_client.py`)
   - [x] Všechny testy úspěšné (login vedení, login komisař, WebSocket, logging)

### Co se NEIMPLEMENTOVALO (dle plánu):
- ❌ Database persistence (in-memory pro MVP)
- ❌ Heartbeat monitoring (Fáze 3)
- ❌ GPS tracking (Fáze 9)
- ❌ Admin panel UI (Fáze 5)
- ❌ SMS integrace (Fáze 6+)
- ❌ Password reset/recovery

### Výsledek:
✅ Fungující WebSocket server na `ws://localhost:8000/ws/{PIN}`  
✅ 2-tier autentizace plně funkční  
✅ Event logging do JSONL  
✅ Selective broadcast podle rolí/stanic  
✅ Support pro 200 současných spojení

**Trvání:** 3-4 hodiny  
**Kritérium úspěchu:** Dva browsery mohou spolu komunikovat přes server

---

## 📍 Fáze 2: Frontend MVP - 2-Tier Login + Chat UI ✅

**Cíl:** Login system s rolemi + základní komunikační UI  
**Status:** ✅ DOKONČENO (21. února 2026)  
**Čas:** ~4 hodiny

### Co bylo implementováno:

1. **HTML struktura** (`frontend/index.html`)
   - **Login Screen:**
     - Role selection: "Jsem vedení RZ" / "Jsem komisař"
     - Vedení: username + password input
     - Komisař: PIN input (4 číslice)
   - **Main App:** (po loginu)
     - Chat interface
     - Role-based UI (vedení vidí více)
     - Logout button

2. **Authentication Logic** (`frontend/js/auth.js`)
   - `loginVedeni(username, password)` → `/api/auth/login-vedeni`
   - `loginKomisar(pin)` → `/api/auth/login-komisar`
   - Store user data v localStorage
   - Session persistence
   - Auto-logout při 401

3. **WebSocket klient** (`frontend/js/websocket.js`)
   - Připojení na `ws://localhost:8000/ws/{pin_code}`
   - Authentication v URL (PIN for komisař, session token for vedení)
   - Odeslání zprávy jako JSON
   - Příjem a zobrazení zpráv
   - Reconnect logika s re-auth

4. **App logika** (`frontend/js/app.js`)
   - Role-based UI rendering:
     - Vedení: admin controls visible
     - Komisař: simple quick actions
   - Event listeners
   - Message handling podle role
   - Notifikace systém

5. **Základní CSS** (`frontend/css/styles.css`)
   - Mobile-first responsive design
   - Login screen styling
   - Role-specific UI elements
   - Velká tlačítka (min 44x44px)
   - Čitelné písmo (min 16px)

### Co se NEIMPLEMENTOVALO (dle plánu):
- ❌ Mapa (Leaflet) - Fáze 4
- ❌ Service Worker - Fáze 7
- ❌ Offline mode - Fáze 7
- ❌ GPS tracking - Fáze 9
- ❌ Admin panel pro správu komisařů - Fáze 5
- ❌ PIN generování UI - Fáze 5

### Testování:
✅ Manuálně testováno:
- ✅ Login vedení (admin/demo123) funguje
- ✅ Login komisař (PIN 1234, 5678) funguje  
- ✅ Role-based UI (vedení vidí admin panel, komisaři quick actions)
- ✅ Chat mezi browsery funguje (incognito + normální tab)
- ✅ Vlastní zprávy viditelné okamžitě (optimistic update)
- ✅ Hromadná zpráva s count online stanic
- ✅ Auto-reconnect při výpadku spojení
- ✅ WebSocket podporuje PIN i session tokeny

### Výsledek:
✅ Plně funkční real-time chat aplikace  
✅ 2-tier autentizace funguje bezproblémově  
✅ Mobile-first responsive design  
✅ Role-based UI pro různé typy uživatelů  
✅ Optimistic updates zajišťují instant feedback  
✅ **Milestone 1 dosažen:** Working real-time chat!

**Trvání:** 4 hodiny  
**Kritérium úspěchu:** ✅ Chat funguje mezi více browsery v reálném čase

---

## 📍 Fáze 3: Heartbeat & Connection Monitoring ✅

**Status:** ✅ DOKONČENO (12. července 2026)

**Cíl:** Server detekuje offline stanice pomocí heartbeat mechanismu

### Co se implementuje:
1. **Backend: Heartbeat tracking** (`backend/services/vitality.py`)
   - Ukládání `last_seen` timestamp pro každé station
   - Background task (AsyncIO), který každých 10s kontroluje timeouty
   - Pokud `now - last_seen > 120s` → station = OFFLINE

2. **Extend Message Model** (`backend/models/message.py`)
   - Nový `message_type`: `"heartbeat"`
   - Heartbeat zprávy nemusí mít `content`

3. **Frontend: Automatický heartbeat** (`frontend/js/websocket.js`)
   - `setInterval` každých 30s odešle heartbeat zprávu
   - Pokud WebSocket disconnected → pokus o reconnect

4. **Status endpoint** (`backend/api/status.py`)
   - `GET /api/stations/status` → vrátí seznam stanic + jejich status (online/offline)

### Testování:
```bash
# Připoj klienta, počkej 3 minuty bez heartbeatu
# Station by měla být označena jako OFFLINE
```

### Výstup:
- Server ví, které stanice jsou online/offline
- Status API endpoint funguje

**Trvání:** 4-5 hodin  
**Kritérium úspěchu:** Server detekuje a reportuje offline stanice

---

## 📍 Fáze 4: Základní mapa s Leaflet 🔄

**Status:** 🔄 IN PROGRESS (iterace 1 hotová)

**Cíl:** Zobrazit mapu a vykreslit jednoduchou trať

### Co se implementuje:
1. **Leaflet integrace** (`frontend/js/map.js`)
   - [x] Inicializace Leaflet mapy
   - [x] Použití OpenStreetMap tiles (online)
   - [x] Vykreslení sample GeoJSON tratě

2. **Sample data** (`data/example-track.geojson`)
   - [x] Jednoduchá GeoJSON linestring trať (fiktivní nebo reálná)
   - [x] 5-10 bodů, aby to vypadalo jako trať

3. **UI adjustments** (`frontend/index.html`, `frontend/css/styles.css`)
   - [x] Mapa-first layout pro desktop i mobil
   - [x] Chat/controls jako desktop sidebar + mobilní vysouvací panel

4. **Status napojení mapy** (`frontend/js/map.js`)
   - [x] Načítání `/api/stations/status`
   - [x] Auto-refresh markerů online/offline
   - [x] Tooltip a popup detail stanice

### Co se NEIMPLEMENTUJE:
- ❌ Offline map tiles
- ❌ Geolokace uživatele
- ❌ Interakce s mapou (kromě zoom/pan)

### Otevřené body do dokončení Fáze 4:
- ✅ Typové ikony markerů podle role/type
- ✅ Absolutní timestamp poslední aktivity v popupu
- ✅ Modularizace frontend logiky: operations/map rozděleny do menších modulů
- ✅ Manuální test checklist pro mapový modul
- ⏳ Finální manuální průchod desktop + mobil a zápis výsledků (odloženo na finální validační průchod)

### Testování:
```bash
# Otevřít frontend, měla by se zobrazit mapa s tratí
```

### Výstup:
- Viditelná mapa s vykreslené tratí

**Trvání:** 3-4 hodiny  
**Kritérium úspěchu:** Mapa se načte a zobrazí trať

---

## 📍 Fáze 5: Admin Panel + Stanice na mapě

**Status:** 🔄 IN PROGRESS (backend iterace 1 hotová)

**Cíl:** Vedoucí může spravovat 160+ komisařů a vidět je na mapě

### ⚠️ KLÍČOVÝ KONCEPT - PIN per Station (ne per Person):

**Důležitá změna designu:**
- ✅ **PIN je vázaný na STANICI**, ne na člověka
- ✅ Na stanici se PŘIŘADÍ člověk (lze kdykoliv změnit)
- ✅ PINy jsou **perzistentní** (přežijí restart serveru) - uloženo v `data/pins.json`
- ✅ Změna člověka na stanici → PIN zůstává STEJNÝ

**Příklad:**
```
PIN 1234 → Stanice TK-01 "Zatáčka u lesa"
           ├─ Aktuálně obsazeno: Jan Novák (+420...)
           ├─ Lze změnit na: Petr Nový (stejný PIN 1234!)
           └─ Historie: Jan (8:00-12:00), Petr (12:00-16:00)
```

**Výhody:**
- 🔒 Stabilní PINy (TK-01 má vždy PIN 1234, i přes roky)
- 🔄 Snadná výměna lidí (onemocnění, střídání směn)
- 📱 Rozeslat SMS s PINem PŘED rally (už víš číslo stanice)
- 📊 Centrální správa "Stanice obsazená/volná"

### Co se implementuje:

1. **Přepracování PIN systému** (`backend/models/station.py`, `backend/core/auth.py`)
   - 🔄 Refaktor probíhá neinvazivně: `KomisarAccess` zůstává pro login, přibyl station-first view `StationAccess`
   - Model:
     ```python
     StationAccess:
       pin_code: str              # 1234
       station_id: str            # TK-01
       station_name: str          # "Zatáčka u lesa"
       station_type: StationType  # corner, timing, etc.
       capacity: int              # 1-3 lidé
       assigned_users: list[AssignedUser]  # historie + aktuální
       created_at: datetime
     
     AssignedUser:
       name: str
       phone: str
       role: UserRole
       assigned_at: datetime
       assigned_until: datetime | None
       is_active: bool
     ```
   - [x] Migrace z legacy `data/pins.json` do station-first historie při loadu
   - [x] Perzistence historie při assign/reassign zachována v `data/pins.json`

2. **Admin API Endpoints** (`backend/api/admin.py`)
   - [x] `POST /api/admin/station/create-pin` - vytvořit PIN pro novou stanici
   - [x] `POST /api/admin/station/{station_id}/assign-user` - přiřadit člověka na stanici (PIN zůstává)
   - [x] `POST /api/admin/station/{station_id}/reassign-user` - změnit člověka (s důvodem)
   - [x] `POST /api/admin/station/{station_id}/release-user` - uvolnit stanici
   - [x] `GET /api/admin/stations` - seznam všech stanic + obsazenost
   - [x] `GET /api/admin/station/{station_id}/history` - historie změn obsazení
   - [x] `DELETE /api/admin/station/{station_id}/pin` - smazat PIN stanice (admin only)
   - Všechny vyžadují vedení role (auth check)

3. **Station Registry** (`backend/core/station_registry.py`)
   - [x] Assignment tracking s historií nad perzistentními PINy
   - [x] Best-effort infer typů stanice z ID prefixu
   - [ ] Hardcoded nebo importovaný katalog stanic
   - [ ] Capacity management pro více lidí na jednu stanici

4. **Station API** (`backend/api/stations.py`)
   - [x] `GET /api/stations` → všechny stanice + obsazenost + current user
   - [x] `GET /api/stations/{station_id}` → detail stanice + historie
   - [x] `GET /api/stations/{station_id}/users` → kdo je/byl přiřazen

5. **Frontend: Admin Dashboard** (`frontend/js/admin.js`)
   - **Station Management:**
   - [x] Samostatná setup obrazovka oddělená od live dashboardu
   - [x] Základní seznam všech stanic na setup obrazovce
   - [x] Detail vybrané stanice + historie obsazení
   - [x] Přiřadit/přepsat osobu na vybrané pozici
   - [x] Uvolnit pozici
   - [ ] Tabulka / virtual scrolling pro 160+
   - [ ] Filtry: typ, status (obsazená/volná/offline), role
   - [ ] Search by station ID nebo název
   - **PIN Generation:**
     - Vytvořit novou stanici → auto-generuje PIN
     - Zobrazit PIN (pro SMS nebo QR kód)
     - Export do CSV/Excel (stanice + PIN + aktuální obsazení)
   - **User Assignment:**
       - [x] Import lidí do katalogu z CSV (Excel-friendly) přes admin API
       - [x] Endpoint pro seznam katalogu lidí pro setup dropdown
       - [x] Přiřadit člověka na stanici: výběr z katalogu + jméno/telefon/role
     - Změnit člověka (modal s potvrzením)
     - Uvolnit stanici
     - Důvod změny (optional, pro historii)
   - **History View:**
     - Kdo byl na stanici kdy
     - Důvody změn obsazení
   - **Real-time updates:**
     - Notifikace komisaři při přiřazení/změně
     - Auto-update v admin panelu

6. **Frontend: Station markers** (`frontend/js/map.js`)
   - Různé ikony podle typu (track, timing, parking)
   - Marker tooltip: ID stanice, obsazenost, jména aktuálně přiřazených lidí
   - Barva podle statusu: zelená (online + obsazená), žlutá (volná), červená (offline)
   - Click → detail stanice (historie obsazení)

7. **WebSocket Notifications**
   - Komisař dostane notifikaci při přiřazení/změně stanice
   - Zpráva: "Byl jste přiřazen na stanici TK-01 (Zatáčka u lesa)"
   - Auto-update mapy při změně obsazení
   - Potvrzení od komisaře (optional)

8. **Optimizations**
   - Virtual scrolling v admin tabulce (jen 20 řádků renderováno)
   - Debounced search
   - Lazy loading markers (jen viditelné)

### Testování:
```bash
# 1. Vytvořit 50+ stanic s PINy
# 2. Přiřadit lidi na stanice (různé konfigurace)
# 3. Změnit člověka na stanici během "závodu" (PIN zůstává stejný)
# 4. Test: Restart serveru → PINy stále platné
# 5. Test: Změna Jana na Petra na TK-01 → PIN 1234 funguje pro Petra
# 6. Ověřit notifikace komisařům při změně
# 7. Test capacity limits (3 lidé na jednu stanici)
# 8. Historie obsazení stanice
```

### Výstup:
- Funkční admin panel pro správu **STANIC** (ne jednotlivých lidí)
- **Perzistentní PINy** vázané na stanice (data/pins.json)
- Snadná změna obsazení bez nutnosti generovat nové PINy
- Dynamická mapa s různými typy stanic + obsazenost
- Real-time updates při změnách
- Historie všech změn obsazení

**Trvání:** 8-10 hodin (rozšířeno o redesign PIN systému + historii)  
**Kritérium úspěchu:** 
- ✅ PIN je vázaný na stanici, ne na člověka
- ✅ Změna člověka na stanici neresetuje PIN
- ✅ Vedoucí může spravovat 160 stanic efektivně
- ✅ PINy přežijí restart serveru

---

## 📍 Fáze 6: Incident Reporting (Quick Actions)

**Status:** 🔄 ČÁSTEČNĚ DODÁNO (12. července 2026)

Již implementováno mimo plný scope fáze:
- ✅ Quick action incident tlačítka (včetně akutního režimu)
- ✅ Readiness gate: `RZ resume` je blokováno bez READY potvrzení
- ✅ Dashboard vedení: stav gate + seznam chybějících READY stanic

**Cíl:** Komisař může rychle nahlásit incident pomocí velkých tlačítek

### Co se implementuje:
1. **Incident Message Types**
   - `message_type`: `"incident"`
   - `severity`: `"low"`, `"medium"`, `"high"`, `"critical"`
   - Předdefinované typy: NEHODA, DIVÁCI_V_NEBEZPEČÍ, PŘIPRAVEN

2. **Frontend: FAB (Floating Action Button)** (`frontend/index.html`, `frontend/css/styles.css`)
   - Velké plovoucí tlačítko v rohu (min 60x60px)
   - Klik → otevře modal s 3-5 velkými tlačítky pro typy incidentů
   - Každé tlačítko pošle instant zprávu na server

3. **Incident Display** (`frontend/js/app.js`)
   - Incidents se zobrazí jako notifikace
   - Critical incidents → celá app změní barvu (červené záhlaví)

4. **Backend: Broadcast logic** (`backend/core/connection_manager.py`)
   - Critical incidents → broadcast VŠEM stanicím
   - Normal incidents → pouze HQ (Start/Cíl)

### Testování:
```bash
# Komisař: klikni FAB → vyber "NEHODA"
# HQ browser: měl by dostat instant notifikaci
# Všichni klienti: červené záhlaví při critical incident
```

### Výstup:
- Funkční incident reporting
- Visual feedback podle severity

**Trvání:** 4-5 hodin  
**Kritérium úspěchu:** Critical incident změní barvu UI všem klientům do 2 sekund

---

## 📍 Fáze 7: PWA - Service Worker & Offline Mode

**Cíl:** Aplikace funguje offline, zprávy se ukládají do fronty

### Co se implementuje:
1. **Service Worker** (`frontend/service-worker.js`)
   - Cache static assets (HTML, CSS, JS)
   - Cache strategie: Cache-First pro assets, Network-First pro API
   - Offline page fallback

2. **Manifest.json** (`frontend/manifest.json`)
   - PWA metadata (name, icons, start_url, display: standalone)
   - Icons (512x512, 192x192)

3. **Offline Queue** (`frontend/js/offline.js`)
   - IndexedDB pro ukládání zpráv, když není internet
   - Automatické odeslání při obnovení konektivity
   - UI indikátor: "X zpráv čeká na odeslání"

4. **Background Sync** (`frontend/service-worker.js`)
   - Registrace background sync tagu
   - Při obnovení internetu → automaticky odešli frontu

### Testování:
```bash
# Chrome DevTools → Application → Service Workers → Register
# Network tab → Offline mode
# Pošli zprávu → měla by jít do fronty
# Online mode → zpráva by se měla automaticky odeslat
```

### Výstup:
- PWA instalovatelná na mobil
- Offline mode funguje s frontou

**Trvání:** 6-8 hodin  
**Kritérium úspěchu:** Aplikace funguje offline a sync funguje po reconnectu

---

## 📍 Fáze 8: Latency Detection & Warnings

**Cíl:** Server detekuje zpoždění zpráv a varuje HQ

### Co se implementuje:
1. **Extended Message Model** (`backend/models/message.py`)
   - `created_at`: čas vytvoření zprávy v klientovi
   - `received_at`: čas příjmu na serveru
   - `latency_ms`: rozdíl v milisekundách

2. **Latency Service** (`backend/services/latency.py`)
   - Výpočet `latency = received_at - created_at`
   - Pokud `latency > 60s` → přidej warning flag

3. **Frontend: Warning Display** (`frontend/js/app.js`)
   - Pokud zpráva má `latency_warning: true` → zobrazit žlutý banner
   - Text: "⚠️ ZPRÁVA ZPOŽDĚNA O X MINUT"

4. **HQ Dashboard Enhancement**
   - Přidat info panel s latency metrikami
   - Zobrazit průměrnou/max latency pro každou stanici

### Testování:
```bash
# Manuálně změnit `created_at` na starší čas
# Server by měl detekovat zpoždění a přidat warning
```

### Výstup:
- HQ vidí zpožděné zprávy
- Vizuální warning pro critical delayed messages

**Trvání:** 3-4 hodiny  
**Kritérium úspěchu:** Zpožděná zpráva (>60s) zobrazí warning v HQ

---

## 📍 Fáze 9: Geolokace a Live Tracking

**Cíl:** Komisař sdílí svou GPS pozici, HQ vidí live pozice

### Co se implementuje:
1. **Frontend: Geolocation API** (`frontend/js/app.js`)
   - Při startu: žádost o GPS permissions
   - Watch position: kontinuální tracking
   - Každých 10s poslat pozici na server

2. **Position Update Handling** (`backend/api/websocket.py`)
   - Příjem position updates
   - Broadcast pozice do HQ (ne všem stanicím)

3. **Live Marker Updates** (`frontend/js/map.js`)
   - HQ mapa: real-time aktualizace pozic stanic
   - Smooth marker transitions (ne "skákání")
   - Zobrazit trail (poslední 5 pozic) jako čáru

### Co se NEIMPLEMENTUJE:
- ❌ GPS tracking v backgroundu (když je app minimizovaná)
- ❌ Historické GPS logy

### Testování:
```bash
# Použít Chrome DevTools → Sensors → Geolocation override
# Změnit pozici → marker by se měl pohybovat v HQ mapě
```

### Výstup:
- HQ vidí live pozice všech komisařů na mapě

**Trvání:** 4-5 hodin  
**Kritérium úspěchu:** Live GPS tracking funguje s max 10s delay

---

## 📍 Fáze 10: Polish & Production Ready

**Cíl:** Připravit aplikaci na produkci

### Co se implementuje:
1. **Environment Configuration**
   - Produkční vs. development config
   - WebSocket URL z environment variable
   - HTTPS/WSS pro produkci

2. **Error Handling & User Feedback**
   - Toast notifikace pro úspěšné akce
   - Error stavy s retry tlačítky
   - Loading states (spinnery)

3. **Security Basics**
   - CORS správně nastaveno
   - Input sanitization
   - Rate limiting pro WebSocket zprávy

4. **Documentation**
   - API.md: popis všech endpointů
   - DEPLOYMENT.md: jak nasadit na server
   - USER_MANUAL.md: návod pro komisaře

5. **Performance Optimization**
   - Minifikace JS/CSS
   - Gzip compression
   - Lazy loading pro neesenciální komponenty

### Testování:
```bash
# Penetration testing základní (SQL injection, XSS)
# Load testing: 50 současných WebSocket spojení
# Mobile testing: real device (Android/iOS)
```

### Výstup:
- Production-ready aplikace
- Dokumentace pro deployment a uživatele

**Trvání:** 6-8 hodin  
**Kritérium úspěchu:** Aplikace běží stabilně s 50 současnými uživateli

---

## 📊 Celkový Časový Odhad

| Fáze | Popis | Čas |
|------|-------|-----|
| 0 | Příprava projektu | 1-2h |
| 1 | Backend MVP | 3-4h |
| 2 | Frontend MVP | 3-4h |
| 3 | Heartbeat monitoring | 4-5h |
| 4 | Mapa s tratí | 3-4h |
| 5 | Admin panel + stanice | 8-10h |
| 6 | Incident reporting | 4-5h |
| 7 | PWA & Offline | 6-8h |
| 8 | Latency detection | 3-4h |
| 9 | GPS tracking | 4-5h |
| 10 | Production polish | 6-8h |
| **CELKEM** | | **45-59 hodin** |

## 🎯 Milestones

**Milestone 1 (po Fázi 2):** Working real-time chat  
**Milestone 2 (po Fázi 6):** Functional incident reporting system  
**Milestone 3 (po Fázi 7):** PWA ready for field testing  
**Milestone 4 (po Fázi 10):** Production deployment

---

## ⚠️ DŮLEŽITÁ PRAVIDLA

1. **Nedělej skip** - Každá fáze musí být kompletní a otestovaná
2. **Commituj často** - Každá fáze = nový git tag (`v0.1`, `v0.2`, etc.)
3. **Testuj na mobilu** - Od Fáze 2 testuj i na skutečném mobilu
4. **Dokumentuj problémy** - Když něco nefunguje, zapiš do ISSUES.md

**Aktuální priorita:** rozjet Fázi 5 v minimálním řezu
(správa mapových podkladů + seznam komisařů);
formální finální průchod Fáze 4 (manuální checklist + E2E gate scénář) je odložen
na závěrečnou validační iteraci před širším field testem.
