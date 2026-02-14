# Rally Safety App - Development Roadmap

## 🎯 Cíl: Postupný vývoj od MVP k plné funkcionalitě

**Pravidlo:** Dokončit a otestovat každou fázi před přechodem na další.

---

## 📍 Fáze 0: Příprava projektu

**Cíl:** Nastavit vývojové prostředí a základní strukturu

### Úkoly:
- [x] Vytvořit project_plan.md
- [ ] Vytvořit adresářovou strukturu projektu
- [ ] Nastavit Git repository
- [ ] Připravit Python virtual environment
- [ ] Vytvořit `.gitignore`
- [ ] Vytvořit `requirements.txt` a `manifest.json`

### Výstup:
- Prázdná, ale kompletní struktura projektu
- Git inicializovaný s prvním commitem
- Virtual environment aktivní

**Trvání:** 1-2 hodiny  
**Kritérium úspěchu:** Můžeš spustit `python --version` a `git status` bez chyb

---

## 📍 Fáze 1: Backend MVP - Basic WebSocket Server

**Cíl:** Jednoduchý WebSocket server, který umí přijímat a broadcastovat zprávy

### Co se implementuje:
1. **FastAPI základy** (`backend/main.py`)
   - Základní FastAPI aplikace
   - Health check endpoint: `GET /health`
   - WebSocket endpoint: `/ws/{station_id}`

2. **Connection Manager** (`backend/core/connection_manager.py`)
   - Správa aktivních WebSocket spojení
   - Broadcast zpráv všem připojeným klientům
   - Ukládání station_id → WebSocket mapping

3. **Základní Message Model** (`backend/models/message.py`)
   - `StationMessage` Pydantic model
   - Pole: `message_id`, `station_id`, `created_at`, `message_type`, `content`

### Co se NEIMPLEMENTUJE:
- ❌ Autentizace/autorizace
- ❌ Database persistence
- ❌ Heartbeat monitoring
- ❌ Latency detection
- ❌ Složité validace

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

## 📍 Fáze 2: Frontend MVP - Připojení k serveru

**Cíl:** Základní HTML stránka, která se připojí k WebSocket serveru a ukáže zprávy

### Co se implementuje:
1. **HTML struktura** (`frontend/index.html`)
   - Základní layout
   - Text input pro zprávy
   - Tlačítko "Odeslat"
   - `<div>` pro zobrazení přijatých zpráv
   - Include CSS a JS souborů

2. **WebSocket klient** (`frontend/js/websocket.js`)
   - Připojení na `ws://localhost:8000/ws/{station_id}`
   - Odeslání zprávy jako JSON
   - Příjem a zobrazení zpráv
   - Základní reconnect logika

3. **App logika** (`frontend/js/app.js`)
   - Event listeners pro formulář
   - Generování `message_id` (UUID nebo timestamp)
   - Zobrazení zpráv v UI

4. **Základní CSS** (`frontend/css/styles.css`)
   - Mobile-first responsive design
   - Velká tlačítka (min 44x44px)
   - Čitelné písmo (min 16px)

### Co se NEIMPLEMENTUJE:
- ❌ Mapa (Leaflet)
- ❌ Service Worker
- ❌ Offline mode
- ❌ Geolokace
- ❌ Fancy UI/animace

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

## 📍 Fáze 5: Stanice na mapě

**Cíl:** Zobrazit pozice stanic na mapě podle jejich stavu (online/offline)

### Co se implementuje:
1. **Station Position Model** (`backend/models/station.py`)
   - `Station` model: `station_id`, `lat`, `lon`, `name`, `status`
   - Storage v paměti (dict) pro rychlý přístup

2. **Position Update Message** (`backend/models/message.py`)
   - Nový `message_type`: `"position_update"`
   - Payload: `{"lat": 50.123, "lon": 14.456}`

3. **Station API** (`backend/api/stations.py`)
   - `GET /api/stations` → vrátí všechny stanice s pozicemi a statusy

4. **Frontend: Station markers** (`frontend/js/map.js`)
   - Fetch seznam stanic z API
   - Vykreslit marker pro každou stanici
   - Barva podle statusu:
     - 🟢 Zelená = online
     - 🔴 Červená = offline

5. **Real-time marker updates** (`frontend/js/app.js`)
   - Když přijde WebSocket zpráva o změně statusu → aktualizuj marker

### Testování:
```bash
# Přidat 3-5 fiktivních stanic
# Připojit/odpojit klienty → markery by měly měnit barvu
```

### Výstup:
- Dynamická mapa se stanicemi, která reaguje na jejich status v reálném čase

**Trvání:** 4-5 hodin  
**Kritérium úspěchu:** Markery správně reagují na online/offline změny

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
