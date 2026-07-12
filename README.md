# Rally Safety App

> Progresivní webová aplikace pro koordinaci traťových komisařů během rally soutěží

## 📊 Current Status

**Aktuální fáze:** 🔄 Fáze 4 - IN PROGRESS (UX stabilizace + manuální testy)  
**Další fáze:** Uzavření Fáze 4 + upřesnění MVP řezu Fáze 5 (admin panel, map podklady, seznam komisařů)  
**Celkový pokrok:** 50% (5/10 fází dokončeno)

### Stav implementace k 12.7.2026

- ✅ Hotovo: Fáze 0, 1, 2, 3
- 🔄 Rozpracováno: Fáze 4 (mapa + desktop/mobile UX refinements)
- 🔄 Částečně dodáno z Fáze 6: incident quick actions + gate READY/NOT_READY
- ⏳ Čeká: Fáze 5, 7, 8, 9, 10

---

## 🎯 O projektu

Rally Safety App zajišťuje real-time přehled o situaci na trati a stavu jednotlivých stanovišť traťových komisařů během rally soutěží.

### Klíčové funkce:
- ✅ **2-tier authentication** (vedení: heslo, komisaři: PIN kód)
- 👥 **Správa 160+ komisařů** s různými rolemi
- ✅ **Live mapa** s tratí + stavem stanic
- ✅ **Real-time komunikace** přes WebSockets (selective broadcast)
- ✅ **Incident gate** (`RZ resume` až po READY potvrzeních)
- ✅ **Heartbeat monitoring** (detekce offline stanic)
- ✅ **Event logging** pro post-race analýzu
- ⏳ **Offline mode (PWA queue + sync)**
- ⏳ **GPS tracking** komisařů v reálném čase
- ⏳ **Plná správa stanic a přiřazení osob** (Fáze 5)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- [UV](https://docs.astral.sh/uv/getting-started/installation/) (doporučeno) nebo pip
- Git
- Moderní browser (Chrome/Edge/Firefox)

### Backend Setup – UV (doporučeno)
```powershell
# 1. Nainstaluj UV (pokud ještě nemáš)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Vytvoř prostředí a instaluj závislosti
uv sync

# 3. Spusť server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Backend Setup – pip (alternativa)
```powershell
# 1. Vytvoř a aktivuj virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Instaluj závislosti
pip install -r requirements.txt

# 3. Spusť server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Server běží na: `http://localhost:8000`

### Frontend Setup
```powershell
# Spusť simple HTTP server
python -m http.server 8080 --directory frontend
```

Frontend běží na: `http://localhost:8080`

Poznámka: při tomto režimu může log frontendu obsahovat 404 pro `/data/example-track.geojson`.
Je to neblokující fallback (mapa použije interní vzorovou trať). Pokud chceš čistý log bez 404,
spouštěj server z kořene repozitáře a frontend otevři přes `/frontend/index.html`.

### VS Code - One Click Start (UV)
Pro rychlé spuštění bez ručního otevírání více terminálů použij tasky ve VS Code:

1. Otevři Command Palette (`Ctrl+Shift+P`)
2. Zvol `Tasks: Run Task`
3. Spusť `UV: Start App`

To současně spustí:
- backend na `http://127.0.0.1:8000`
- frontend na `http://127.0.0.1:8080`

Další tasky:
- `UV: Backend` (jen backend)
- `UV: Frontend` (jen frontend)
- `UV: Tests` (backend testy)

Stop: `Ctrl+Shift+P` → `Tasks: Terminate Task` (nebo `Terminate All Tasks`).

---

## 📁 Struktura projektu

```
rally-safety-app/
├── backend/              # FastAPI WebSocket server
│   ├── main.py          # (připraveno v Fázi 1)
│   ├── api/             # REST & WebSocket endpoints
│   ├── core/            # Config, Connection Manager
│   ├── models/          # Pydantic data models
│   └── services/        # Business logic
├── frontend/            # PWA aplikace
│   ├── index.html       # (připraveno v Fázi 2)
│   ├── js/              # Client-side logika
│   └── css/             # Mobile-first styly
├── data/                # Sample GeoJSON tratě
└── docs/                # Dokumentace
```

---

## 📚 Dokumentace

### Pro vývojáře:
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Coding standards a best practices
- **[ROADMAP.md](ROADMAP.md)** - Fázovaný development plán (10 fází)
- **[SETUP.md](SETUP.md)** - Detailní setup guide
- **[STATUS.md](STATUS.md)** - Aktuální pokrok a checklist

### Koncept a specifikace:
- **[project_plan.md](project_plan.md)** - Product specification a architektura

---

## 🎯 Development Roadmap

| Fáze | Popis | Status | Čas |
|------|-------|--------|-----|
| 0 | Příprava projektu | ✅ Hotovo | 1-2h |
| 1 | Backend MVP (WS + Auth + Logging) | ✅ Hotovo | 4-5h |
| 2 | Frontend (2-tier Login + Chat) | ✅ Hotovo | 4-5h |
| 3 | Heartbeat monitoring | ✅ Hotovo | 4-5h |
| 4 | Mapa s Leaflet | 🔄 Probíhá | 3-4h |
| 5 | Admin Panel + Stanice | ⏳ Čeká | 8-10h |
| 6 | Incident reporting | 🔄 Částečně hotovo | 4-5h |
| 7 | PWA & Offline mode | ⏳ Čeká | 6-8h |
| 8 | Latency detection + GPS batching | ⏳ Čeká | 4-5h |
| 9 | GPS tracking | ⏳ Čeká | 4-5h |
| 10 | Production polish | ⏳ Čeká | 6-8h |

**Celkový odhad:** 45-59 hodin čistého kódování

---

## 🧪 Testing

### Backend Testing
```powershell
# UV (doporučeno)
uv run pytest

# pip alternativa
pytest backend/tests/ -v
```

### Station Status API (heartbeat monitoring)
```powershell
# Přehled online/offline stavů stanic
Invoke-RestMethod http://localhost:8000/api/stations/status

# Incident gate readiness snapshot
Invoke-RestMethod http://localhost:8000/api/stations/readiness
```

### Frontend Testing
- Chrome DevTools → Device Emulation
- Network tab → Offline mode testing
- Real device testing (Android/iOS)
- Ověř mapu: po loginu se zobrazí Leaflet mapa s červeně vykreslenou tratí
- Ověř markery: mapa načte stav ze `/api/stations/status` a markery mění barvu online/offline
- Incident na stanici: marker přepne do alert režimu (červený pulz + vlaječka `!`)
- Klik na marker zobrazí detail stanice (ID, role, počet připojení, poslední aktivita)
- Desktop: komunikační panel je stabilně vpravo vedle mapy
- Desktop: komunikační panel je po celé výšce od hlavičky dolů, admin/map část je zúžená
- Desktop vedeni: admin panel je kompaktní 3-sloupcový layout (status | akce | varování)
- Mobil: komunikační panel se otevírá tlačítkem 💬 jako vysouvací panel z pravé strany
- Info kanál: systémové/problémové zprávy jsou oddělené od běžného chatu v záložce "Info kanál"
- Dashboard vedení: metrika je online/total stanic (např. 12/18), ne počet zpráv
- Dashboard vedení: předdefinované krizové akce (`RZ zastavena`, `Pozor problém`, `RZ pozastavena`, `RZ opět v provozu`)
- `RZ opět v provozu` je blokováno, pokud incident gate nemá READY potvrzení ze stanic
- Dashboard vedení: incident gate ukazuje i konkrétní seznam stanic, kterým chybí READY
- Horní lišta aplikace zobrazuje stav RZ (`V provozu`, `Pozastavena`, `Zastavena`)
- Při stavu `Pozastavena`/`Zastavena` má mapa červený warning border
- Warning border mapy je renderovaný jako overlay nad Leafletem (nesmí se schovat pod mapové vrstvy)
- Komisař: při hlášení problému musí doplnit detail incidentu
- Komisař: má i tlačítko `🆘 Akutní` (odeslání kritického incidentu bez vstupu)
- Komisař: na dashboardu má kontakt na vedoucího RZ (tel link)
- Chat tagging: napiš `@Jmeno` nebo `#Stanice` a použij našeptávač pro rychlé označení
- Tagy se zvýrazní jen pokud odpovídají známému uživateli/stanici; klik na `#Stanice` vycentruje mapu na marker
- Chat, info kanál a varování vedení se ukládají lokálně pro přihlášeného uživatele a po odhlášení/znovupřihlášení se obnoví
- Toast notifikace se zobrazují na středu nad mapou (ne v pravém horním rohu)

### Map Module - Manual Checklist (Fáze 4)
- Na mapě jsou vidět markery stanic se symbolem role (S/F/T/C/P/B/Z/V/+)
- Markery mění barvu podle stavu (online zelená, offline červená)
- Popup stanice obsahuje relativní i absolutní čas poslední aktivity
- Klik na `#Stanice` v chatu otevře popup příslušného markeru
- Mobilní zobrazení: mapa + vysouvací komunikace bez posunu mimo viewport

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.116+ - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** 2.11+ - Data validation
- **WebSockets** - Real-time communication (selective broadcast)
- **bcrypt** - Password hashing for vedení
- **JSONL** - Structured event logging

### Frontend
- **Vanilla JavaScript** (ES6+) - No frameworks
- **Leaflet.js** - Interactive maps
- **Service Workers** - Offline support
- **IndexedDB** - Local data persistence

### Architecture
- **Auth:** 2-tier (password hash + PIN codes)
- **Scalability:** 160+ concurrent connections
- **Storage:** In-memory (MVP phase)
- **No database** until production phase

---

## 📝 Git Workflow

### Conventional Commits
```bash
feat: add WebSocket connection manager
fix: resolve heartbeat timeout issue
docs: update API documentation
test: add message validation tests
```

### Tagging
Každá dokončená fáze = nový tag:
```bash
git tag v0.1  # Po Fázi 1
git tag v0.2  # Po Fázi 2
# atd.
```

---

## 🤝 Coding Principles

- ✅ **KISS** - Keep It Simple, Stupid
- ✅ **YAGNI** - You Aren't Gonna Need It
- ✅ **DRY** - Don't Repeat Yourself
- ✅ Dělej pouze to, co je **TEĎ** potřeba
- ✅ Testuj každou změnu před commitem

Detaily v [DEVELOPMENT.md](DEVELOPMENT.md)

---

## ⚠️ Known Issues

- Desktop/mobile layout je aktivně dolaďován podle field feedbacku (Fáze 4).
- PWA offline queue a background sync zatím nejsou implementované.
- Pokud frontend server běží jen nad složkou `frontend`, může se v logu objevit 404 pro `/data/example-track.geojson` (neblokující fallback).

---

## 🤝 Contributing & Issues

Projekt je připravený na externí příspěvky přes GitHub Pull Request workflow.

### Jak přispět

1. Přečti si [CONTRIBUTING.md](CONTRIBUTING.md)
2. Vytvoř issue (bug/feature/question) přes připravené šablony
3. Otevři PR podle [PR šablony](.github/pull_request_template.md)

### Community Health soubory

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [Issue templates](.github/ISSUE_TEMPLATE)

Poznámka: před plně veřejným open-source režimem doporučujeme finálně potvrdit licenci projektu.

---

## 📄 License

MIT License. Viz [LICENSE](LICENSE).

---

**Poslední aktualizace:** 12. července 2026  
**Verze dokumentace:** v0.5-dev (Fáze 4 in progress)
