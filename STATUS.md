# Project Status & Progress Tracking

**Last Updated:** 21. února 2026  
**Current Phase:** Fáze 2 ✅ DOKONČENO  
**Next Phase:** Fáze 3 - Heartbeat & Connection Monitoring

---

## 📊 Overall Progress

```
███████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░ 30% (3/10 phases complete)
```

**Completed Phases:** 3/10  
**Time Invested:** ~10.5 hours  
**Estimated Remaining:** 34-46 hours

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

## ⏳ Fáze 3-10: Pending

_Details in [ROADMAP.md](ROADMAP.md)_

---

## 📈 Milestones

| Milestone | Phase | Target | Status |
|-----------|-------|--------|--------|
| **M1: Working Chat** | Po Fázi 2 | 21.2.2026 | ✅ Complete |
| **M2: Incident System** | Po Fázi 6 | TBD | ⏳ Pending |
| **M3: PWA Ready** | Po Fázi 7 | TBD | ⏳ Pending |
| **M4: Production** | Po Fázi 10 | TBD | ⏳ Pending |

---

## 🐛 Active Issues

_Žádné aktivní issues_

---

## 📝 Recent Changes

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

1. **Okamžitě:** Začít Fázi 3 - Heartbeat monitoring
2. Implementovat vitality tracking na backendu
3. Frontend: Automatický heartbeat každých 30s
4. Status endpoint pro offline detection

---

## 📊 Time Tracking

| Phase | Estimated | Actual | Variance |
|-------|-----------|--------|----------|
| Fáze 0 | 1-2h | ~2h | On track ✅ |
| Fáze 1 | 4-5h | ~4.5h | On track ✅ |
| Fáze 2 | 3-4h | ~4h | On track ✅ |
| Fáze 3 | 4-5h | - | - |

**Total:** 10.5h / ~50h estimated

---

**Legend:**
- ✅ Complete
- 🔄 In Progress
- ⏳ Waiting
- ⚠️ Blocked
- 🐛 Issue
