# Rally Safety App - Development Roadmap

## 🎯 Cíl: Postupný vývoj od MVP k plné funkcionalitě

**Pravidlo:** Dokončit a otestovat každou fázi před přechodem na další.

Aktuální průběžný stav drž v `STATUS.md`. Tento dokument je plán a backlog po fázích.

> Dokončené fáze (0-3) jsou tu jen jako stručné shrnutí - detail implementace
> ověříš přímo v kódu (docstringy) a testech, ne tady. Rozpracované a
> neotevřené fáze (4-10) mají plný plán, protože jinde zatím neexistuje.

---

## 📍 Fáze 0: Příprava projektu ✅

Git repo, adresářová struktura, venv/uv, `.gitignore`, `requirements.txt`, základní dokumentace.
**Trvání:** ~2h

---

## 📍 Fáze 1: Backend MVP - WebSocket + Auth + Logging ✅

**Dokončeno:** 15.2.2026, ~4.5h

FastAPI server, 2-tier autentizace (vedení: heslo, komisaři: PIN), WebSocket
connection manager se selective broadcast, JSONL event logging, perzistentní
PINy. Kód: `backend/main.py`, `backend/core/auth.py`,
`backend/core/connection_manager.py`, `backend/core/event_logger.py`.

Vědomě neimplementováno v této fázi: DB persistence, heartbeat (→ Fáze 3),
GPS tracking (→ Fáze 9), admin panel (→ Fáze 5), SMS integrace.

---

## 📍 Fáze 2: Frontend MVP - 2-Tier Login + Chat UI ✅

**Dokončeno:** 21.2.2026, ~4h

Login screen s volbou role, WebSocket klient s reconnect logikou,
role-based UI, mobile-first CSS. Kód: `frontend/index.html`,
`frontend/js/auth.js`, `websocket.js`, `app.js`.

---

## 📍 Fáze 3: Heartbeat & Connection Monitoring ✅

**Dokončeno:** 12.7.2026

Backend vitality service (timeout detekce offline stanic), `GET
/api/stations/status`, frontend heartbeat každých 30s. Kód:
`backend/services/vitality.py`, `backend/api/status.py`.

---

## 📍 Fáze 4: Základní mapa s Leaflet 🔄

**Status:** funkční, formální finální průchod odložen

Leaflet mapa nad OpenStreetMap, GeoJSON trať i další mapové prvky,
map-first layout pro desktop i mobil, typové ikony markerů podle role,
auto-refresh stavu ze `/api/stations/status`. Kód: `frontend/js/map.js`,
`map-track.js`, `map-elements.js`, `map-stations.js`.

### Zbývá:
- ⏳ Finální manuální průchod desktop + mobil a zápis výsledků do
  checklistu v README.md (odloženo na závěrečnou validační iteraci
  před širším field testem)

**Kritérium úspěchu:** Mapa se načte a zobrazí trať ✅

---

## 📍 Fáze 5: Admin Panel + Stanice na mapě 🔄

**Status:** backend hotový, frontend setup obrazovka funkční v minimálním řezu

### ⚠️ Klíčový koncept - PIN per Station (ne per Person)

**PIN je vázaný na STANICI, ne na člověka.** Na stanici se přiřadí člověk
(lze kdykoliv změnit), PIN zůstává stejný a je perzistentní
(`data/pins.json`, přežije restart serveru).

```
PIN 1234 → Stanice TK-01 "Zatáčka u lesa"
           ├─ Aktuálně obsazeno: Jan Novák (+420...)
           ├─ Lze změnit na: Petr Nový (stejný PIN 1234!)
           └─ Historie: Jan (8:00-12:00), Petr (12:00-16:00)
```

Výhody: stabilní PINy nezávislé na výměně lidí, možnost rozeslat SMS s
PINem před rally, centrální přehled obsazenosti.

### Co je hotové
Station-first backend (`backend/core/station_registry.py`,
`backend/core/auth.py`, `backend/api/admin.py`, `backend/api/status.py`):
create/assign/reassign/release/regenerate/delete PIN, historie obsazení,
people katalog s CSV importem, station directory API. Frontend: samostatná
setup obrazovka (seznam pozic, detail, historie, assign/reassign/release,
dropdown z katalogu lidí, bulk-generate PINů z mapových pozic).

Detail endpointů viz `/docs` (živá Swagger dokumentace) na běžícím serveru,
detail modelů viz docstringy v `backend/models/station.py` a
`backend/core/station_registry.py`.

### Zbývá:
- [ ] Tabulka / virtual scrolling pro 160+ pozic na setup obrazovce
- [ ] Filtry: typ, status (obsazená/volná/offline), role
- [ ] Search by station ID nebo název
- [ ] Export stanic + PINů do CSV/Excel
- [ ] Pohodlnější přesun osoby mezi dvěma pozicemi (dnes jen reassign na jedné)
- [ ] WebSocket notifikace komisaři při přiřazení/změně stanice (primitivy
      `send_personal_message`/`broadcast_to_station` v
      `backend/core/connection_manager.py` už existují, jen nejsou zapojené)
- [ ] Potvrzení přiřazení od komisaře (optional)

**Kritérium úspěchu:** PIN vázaný na stanici, změna člověka PIN neresetuje,
PINy přežijí restart serveru ✅ - zbývá jen škálovací/UX dolaďování výše.

---

## 📍 Fáze 6: Incident Reporting (Quick Actions) 🔄

**Status:** částečně dodáno mimo plný scope fáze (12.7.2026)

Hotovo: quick action incident tlačítka včetně akutního režimu bez textového
vstupu, readiness gate (`RZ resume` blokován bez READY potvrzení ze všech
stanic), dashboard vedení se stavem gate. Kód:
`frontend/js/app-operations-incidents.js`,
`backend/services/operations_state.py`.

### Zbývá dle původního scope:
- [ ] Formalizovat `severity` na typované úrovně (low/medium/high/critical)
      a předdefinované typy (NEHODA, DIVÁCI_V_NEBEZPEČÍ, PŘIPRAVEN) - dnes
      je to volný text
- [ ] Ověřit/doladit routing broadcastu: critical → všem stanicím, normal →
      jen HQ (Start/Cíl)

**Kritérium úspěchu:** Critical incident změní barvu UI všem klientům do 2
sekund - k formálnímu ověření v závěrečné validační iteraci.

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
   - ✅ CORS přes `ALLOWED_ORIGINS` (hotovo, viz `.env.example`)
   - ✅ `DEBUG` bezpečný default False (hotovo)
   - [ ] Input sanitization (XSS na chat obsahu)
   - [ ] Rate limiting pro WebSocket zprávy

4. **Documentation**
   - [ ] DEPLOYMENT.md: jak nasadit na server
   - [ ] USER_MANUAL.md: návod pro komisaře
   - API endpointy jsou už zdokumentované živě na `/docs` (FastAPI Swagger)

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

**Milestone 1 (po Fázi 2):** Working real-time chat ✅
**Milestone 1.5 (po Fázi 3):** Heartbeat online/offline ✅
**Milestone 2 (po Fázi 6):** Functional incident reporting system
**Milestone 3 (po Fázi 7):** PWA ready for field testing
**Milestone 4 (po Fázi 10):** Production deployment

---

## ⚠️ DŮLEŽITÁ PRAVIDLA

1. **Nedělej skip** - Každá fáze musí být kompletní a otestovaná
2. **Commituj často** - Malé logické celky, ne jeden velký commit na fázi
3. **Testuj na mobilu** - Od Fáze 2 testuj i na skutečném mobilu
4. **Dokumentuj problémy** - Neobvyklé chování patří do STATUS.md, ne jen do hlavy

**Aktuální priorita:** dotáhnout zbývající body Fáze 5 (škálovací/UX
dolaďování setup obrazovky), pak formální finální průchod Fáze 4 a 6 před
širším field testem.
