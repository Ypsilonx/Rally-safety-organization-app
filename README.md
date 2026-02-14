# Rally Safety App

> Progresivní webová aplikace pro koordinaci traťových komisařů během rally soutěží

## 📊 Current Status

**Aktuální fáze:** ✅ Fáze 0 - DOKONČENO  
**Další fáze:** Fáze 1 - Backend MVP (WebSocket Server)  
**Celkový pokrok:** 5% (1/10 fází)

---

## 🎯 O projektu

Rally Safety App zajišťuje real-time přehled o situaci na trati, poloze a stavu jednotlivých stanovišť traťových komisařů během rally soutěží. Aplikace funguje i offline díky PWA technologii.

### Klíčové funkce:
- 🗺️ **Live mapa** s pozicemi všech stanovišť
- 📡 **Real-time komunikace** přes WebSockets
- 🔴 **Rychlé incident reporting** (nehoda, diváci v nebezpečí)
- 📴 **Offline mode** s automatickou synchronizací
- ⏱️ **Heartbeat monitoring** (detekce offline stanic)
- 📍 **GPS tracking** komisařů v reálném čase

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (aktuálně testováno s 3.13)
- Git
- Moderní browser (Chrome/Edge/Firefox)

### Backend Setup
```powershell
# 1. Aktivuj virtual environment
.\venv\Scripts\activate

# 2. (První setup) Instaluj dependencies
pip install -r backend/requirements.txt

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
| 1 | Backend MVP (WebSocket) | 🔄 Další | 3-4h |
| 2 | Frontend MVP (Chat) | ⏳ Čeká | 3-4h |
| 3 | Heartbeat monitoring | ⏳ Čeká | 4-5h |
| 4 | Mapa s Leaflet | ⏳ Čeká | 3-4h |
| 5 | Stanice na mapě | ⏳ Čeká | 4-5h |
| 6 | Incident reporting | ⏳ Čeká | 4-5h |
| 7 | PWA & Offline mode | ⏳ Čeká | 6-8h |
| 8 | Latency detection | ⏳ Čeká | 3-4h |
| 9 | GPS tracking | ⏳ Čeká | 4-5h |
| 10 | Production polish | ⏳ Čeká | 6-8h |

**Celkový odhad:** 41-54 hodin čistého kódování

---

## 🧪 Testing

### Backend Testing
```powershell
# Spusť pytest
pytest backend/tests/ -v
```

### Frontend Testing
- Chrome DevTools → Device Emulation
- Network tab → Offline mode testing
- Real device testing (Android/iOS)

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.116+ - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** 2.11+ - Data validation
- **WebSockets** - Real-time communication

### Frontend
- **Vanilla JavaScript** (ES6+) - No frameworks
- **Leaflet.js** - Interactive maps
- **Service Workers** - Offline support
- **IndexedDB** - Local data persistence

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

_(Prázdné - projekt v počáteční fázi)_

---

## 📄 License

This project is for internal use.

---

**Poslední aktualizace:** 14. února 2026  
**Verze:** v0.0 (Setup complete)
