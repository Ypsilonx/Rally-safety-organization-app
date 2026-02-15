# Project Status & Progress Tracking

**Last Updated:** 15. února 2026  
**Current Phase:** Fáze 1 ✅ DOKONČENO  
**Next Phase:** Fáze 2 - Frontend MVP

---

## 📊 Overall Progress

```
██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 20% (2/10 phases complete)
```

**Completed Phases:** 2/10  
**Time Invested:** ~6.5 hours  
**Estimated Remaining:** 37-50 hours

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
✅ Testovací helper scripty  
✅ Debug API endpoint pro PIN management  

### Issues:
- ✅ test_pins.py správně přepsán na API-based místo instance confusion  

---

## 🔄 Fáze 2: Frontend MVP - Login + Chat UI (DALŠÍ)

**Status:** 🔄 Ready to start  
**Estimated Time:** 4-5 hours (rozšířeno o 2-tier login)

### Checklist:
- [ ] Vytvořit `frontend/index.html` - login screen + main app
- [ ] Vytvořit `frontend/js/auth.js` - 2-tier login logic
- [ ] Vytvořit `frontend/js/websocket.js` - WS client
- [ ] Vytvořit `frontend/js/app.js` - app logic + role-based UI
- [ ] Vytvořit `frontend/css/styles.css` - mobile-first CSS
- [ ] Test: Vedení login (username+password) funguje
- [ ] Test: Komisař login (PIN) funguje
- [ ] Test: Role-based UI (vedení vidí admin panel)
- [ ] Test: Chat funguje mezi browsery
- [ ] Git commit + tag `v0.2`

### Files to Create:
```
frontend/
├── index.html           (NEW - s login screen)
├── js/
│   ├── auth.js         (NEW)
│   ├── websocket.js    (NEW)
│   └── app.js          (NEW)
└── css/
    └── styles.css      (NEW)
```

---

## ⏳ Fáze 3-10: Pending

_Details in [ROADMAP.md](ROADMAP.md)_

---

## 📈 Milestones

| Milestone | Phase | Target | Status |
|-----------|-------|--------|--------|
| **M1: Working Chat** | Po Fázi 2 | TBD | ⏳ Pending |
| **M2: Incident System** | Po Fázi 6 | TBD | ⏳ Pending |
| **M3: PWA Ready** | Po Fázi 7 | TBD | ⏳ Pending |
| **M4: Production** | Po Fázi 10 | TBD | ⏳ Pending |

---

## 🐛 Active Issues

_Žádné aktivní issues_

---

## 📝 Recent Changes

### 2026-02-15
- ✅ Fáze 1 dokončena
- ✅ FastAPI server s WebSocket + 2-tier auth
- ✅ Event logging do JSONL
- ✅ Selective broadcasting implementována
- ✅ Všechny testy úspěšné (login, WebSocket, logging)
- 📝 Připraveno na Fázi 2

### 2026-02-14
- ✅ Fáze 0 dokončena
- ✅ Vyřešen problém s pydantic-core instalací (upgrade na 2.11+)
- ✅ Vytvořena kompletní dokumentace
- ✅ Git repository inicializován

---

## 🎯 Next Actions

1. **Okamžitě:** Začít Fázi 2 - vytvořit `frontend/index.html`
2. Implementovat 2-tier login UI
3. WebSocket klient v JavaScriptu
4. Testovat chat mezi browsery

---

## 📊 Time Tracking

| Phase | Estimated | Actual | Variance |
|-------|-----------|--------|----------|
| Fáze 0 | 1-2h | ~2h | On track ✅ |
| Fáze 1 | 4-5h | ~4.5h | On track ✅ |
| Fáze 2 | 4-5h | - | - |

**Total:** 6.5h / ~50h estimated

---

**Legend:**
- ✅ Complete
- 🔄 In Progress
- ⏳ Waiting
- ⚠️ Blocked
- 🐛 Issue
