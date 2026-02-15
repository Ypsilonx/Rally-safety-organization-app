# Rally Safety App - Development Roadmap

## 🎯 Cíl: Postupný vývoj od MVP k plné funkcionalitě

**Pravidlo:** Dokončit a otestovat každou fázi před přechodem na další.

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

## 📍 Fáze 1: Backend MVP - WebSocket + Auth + Logging

**Cíl:** WebSocket server s 2-tier autentizací, event loggingem a podporou 160+ uživatelů

### Co se implementuje:

1. **FastAPI základy** (`backend/main.py`)
   - Základní FastAPI aplikace
   - Health check endpoint: `GET /health`
   - WebSocket endpoint: `/ws/{pin_code}` (autentizovaný)

2. **Authentication System** (`backend/core/auth.py`, `backend/api/auth.py`)
   - **Tier 1 (Vedení RZ):** Username + Password (bcrypt hashed)
   - **Tier 2 (Komisaři):** PIN kódy (4místné, generované vedoucím)
   - Session management pro vedení
   - PIN validation pro komisaře
   - Endpoints: `/api/auth/login-vedeni`, `/api/auth/login-komisar`

3. **User & Role Models** (`backend/models/user.py`)
   - `UserRole` enum: 9 rolí (vedouci, zastupce, komisar_trat, casomer, parkovani, atd.)
   - `User` model: user_id, name, role, station_id
   - `KomisarAccess` model: PIN, name, phone, station assignment
   - Hardcoded vedení credentials (pro MVP)
   - In-memory PIN storage

4. **Station Models** (`backend/models/station.py`)
   - `StationType` enum: track_point, corner, timing, parking, medical, atd.
   - `Station` model: station_id, name, type, lat, lon, capacity
   - Support pro více lidí na jedné stanici (capacity system)

5. **Connection Manager** (`backend/core/connection_manager.py`)
   - Správa WebSocket spojení (160+ connections)
   - **Selective Broadcasting:**
     - `broadcast_to_role()` - jen určité role
     - `broadcast_to_area()` - jen určitá oblast
     - `broadcast_critical()` - STOP RZ všem
   - PIN → WebSocket mapping
   - Role tracking

6. **Event Logger** (`backend/core/event_logger.py`)
   - JSONL logging všech events
   - Log file per RZ session: `logs/rz_session_YYYYMMDD_HHMMSS.jsonl`
   - Events: login, station_assigned, incident, broadcast, atd.
   - Structured JSON format pro post-race analýzu

7. **Message Models** (`backend/models/message.py`)
   - `StationMessage`: message_id, created_at, message_type, content
   - `MessagePriority`: critical, high, normal, low

### Co se NEIMPLEMENTUJE:
- ❌ Database persistence (in-memory pro MVP)
- ❌ Heartbeat monitoring (Fáze 3)
- ❌ GPS tracking (Fáze 9)
- ❌ Admin panel UI (Fáze 5)
- ❌ SMS integrace (Fáze 6+)
- ❌ Password reset/recovery

### Testování:
```bash
# Spustit server
uvicorn backend.main:app --reload

# Test WebSocket (můžeš použít REST client nebo browser console)
# Pošle zprávu a měl by dostat echo
```

### Výstup:
- Fungující WebSocket server na `ws://localhost:8000/ws/TEST-01`
- Schopnost přijmout JSON zprávu a broadcastnout ji všem klientům

**Trvání:** 3-4 hodiny  
**Kritérium úspěchu:** Dva browsery mohou spolu komunikovat přes server

---

## 📍 Fáze 2: Frontend MVP - 2-Tier Login + Chat UI

**Cíl:** Login system s rolemi + základní komunikační UI

### Co se implementuje:

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

### Co se NEIMPLEMENTUJE:
- ❌ Mapa (Leaflet)
- ❌ Service Worker
- ❌ Offline mode
- ❌ GPS tracking
- ❌ Admin panel pro správu komisařů (Fáze 5)
- ❌ PIN generování UI (Fáze 5)

### Testování:
```bash
# Spustit simple HTTP server
python -m http.server 8080 --directory frontend

# Otevřít http://localhost:8080 ve dvou tabech
# Zpráva z jednoho tabu by měla dojít do druhého
```

### Výstup:
- Jednoduchá chat aplikace mezi station a HQ
- Real-time komunikace funguje

**Trvání:** 3-4 hodiny  
**Kritérium úspěchu:** Chat funguje mezi více browsery v reálném čase

---

## 📍 Fáze 3: Heartbeat & Connection Monitoring

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

## 📍 Fáze 4: Základní mapa s Leaflet

**Cíl:** Zobrazit mapu a vykreslit jednoduchou trať

### Co se implementuje:
1. **Leaflet integrace** (`frontend/js/map.js`)
   - Inicializace Leaflet mapy
   - Použití OpenStreetMap tiles (online)
   - Vykreslení sample GeoJSON tratě

2. **Sample data** (`data/example-track.geojson`)
   - Jednoduchá GeoJSON linestring trať (fiktivní nebo reálná)
   - 5-10 bodů, aby to vypadalo jako trať

3. **UI adjustments** (`frontend/index.html`, `frontend/css/styles.css`)
   - Mapa zabírá 80% výšky obrazovky
   - Chat/controls v dolní části (20%)

### Co se NEIMPLEMENTUJE:
- ❌ Offline map tiles
- ❌ Geolokace uživatele
- ❌ Markery pro stanice
- ❌ Interakce s mapou (kromě zoom/pan)

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

**Cíl:** Vedoucí může spravovat 160+ komisařů a vidět je na mapě

### Co se implementuje:

1. **Admin API Endpoints** (`backend/api/admin.py`)
   - `POST /api/admin/generate-pin` - generovat PIN pro komisaře
   - `POST /api/admin/assign-station` - přiřadit stanici komisaři
   - `POST /api/admin/reassign-station` - změnit přiřazení (s důvodem)
   - `GET /api/admin/commissioners` - seznam všech komisařů
   - `DELETE /api/admin/revoke-pin` - deaktivovat PIN
   - Všechny vyžadují vedení role (auth check)

2. **Station Registry** (`backend/core/station_registry.py`)
   - Hardcoded definice stanic (různé typy)
   - Track points, timing, parking, medical, atd.
   - Capacity management (více lidí na jednu stanici)
   - Assignment tracking

3. **Station API** (`backend/api/stations.py`)
   - `GET /api/stations` → všechny stanice + obsazenost
   - `GET /api/stations/{station_id}/users` → kdo je přiřazen

4. **Frontend: Admin Dashboard** (`frontend/js/admin.js`)
   - **Commissioner Management:**
     - Tabulka všech komisařů (virtual scrolling pro 160+)
     - Filtry: role, status (online/offline), přiřazení
     - Search by name
     - Hromadné akce (bulk reassign)
   - **PIN Generation:**
     - Přidat komisaře: jméno + telefon → vygeneruje PIN
     - Zobrazit PIN (pro SMS nebo QR kód)
   - **Station Assignment:**
     - Drag & drop komisařů na stanice
     - Capacity warnings (stanice plná)
     - Real-time reassignment s notifikací

5. **Frontend: Station markers** (`frontend/js/map.js`)
   - Různé ikony podle typu (track, timing, parking)
   - Marker tooltip: obsazenost, jména komisařů
   - Barva podle statusu: online/offline
   - Click → detail stanice

6. **WebSocket Notifications**
   - Komisař dostane notifikaci při přiřazení/změně
   - Auto-update mapy při změně
   - Potvrzení od komisaře (optional)

7. **Optimizations**
   - Virtual scrolling v admin tabulce (jen 20 řádků renderováno)
   - Debounced search
   - Lazy loading markers (jen viditelné)

### Testování:
```bash
# Vygenerovat 50+ PIN kódů
# Přiřadit komisaře na různé stanice
# Změnit přiřazení během "závodu"
# Ověřit notifikace komisařům
# Test capacity limits
```

### Výstup:
- Funkční admin panel pro správu velkého počtu komisařů
- Dynamická mapa s různými typy stanic
- Real-time updates při změnách

**Trvání:** 6-8 hodin (rozšířeno o admin funkcionalitu)  
**Kritérium úspěchu:** Vedoucí může spravovat 160 komisařů efektivně

---

## 📍 Fáze 6: Incident Reporting (Quick Actions)

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
| 5 | Stanice na mapě | 4-5h |
| 6 | Incident reporting | 4-5h |
| 7 | PWA & Offline | 6-8h |
| 8 | Latency detection | 3-4h |
| 9 | GPS tracking | 4-5h |
| 10 | Production polish | 6-8h |
| **CELKEM** | | **41-54 hodin** |

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

**Začínáme od Fáze 0. Ready?**
