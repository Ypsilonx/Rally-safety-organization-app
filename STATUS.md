# Project Status & Progress Tracking

**Last Updated:** 14. února 2026  
**Current Phase:** Fáze 0 ✅ DOKONČENO  
**Next Phase:** Fáze 1 - Backend MVP

---

## 📊 Overall Progress

```
█████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5% (1/10 phases complete)
```

**Completed Phases:** 1/10  
**Time Invested:** ~2 hours  
**Estimated Remaining:** 41-54 hours

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

## 🔄 Fáze 1: Backend MVP - WebSocket Server (DALŠÍ)

**Status:** 🔄 Ready to start  
**Estimated Time:** 4-5 hours (rozšířeno o auth + logging)

### Checklist:
- [ ] Vytvořit `backend/main.py` - FastAPI aplikace
- [ ] Implementovat health check endpoint `GET /health`
- [ ] Implementovat WebSocket endpoint `/ws/{pin_code}`
- [ ] Vytvořit `backend/core/config.py` - konfigurace z .env
- [ ] Vytvořit `backend/core/connection_manager.py` - WebSocket pool + selective broadcast
- [ ] Vytvořit `backend/core/event_logger.py` - JSONL event logging
- [ ] Vytvořit `backend/models/message.py` - Message Pydantic modely
- [ ] Vytvořit `backend/models/user.py` - User, UserRole (9 rolí), KomisarAccess
- [ ] Vytvořit `backend/models/station.py` - Station, StationType, capacity system
- [ ] Vytvořit `backend/models/auth.py` - Login request/response modely
- [ ] Vytvořit `backend/core/auth.py` - Password hashing (bcrypt), PIN generation
- [ ] Implementovat `/api/auth/login-vedeni` - username + password
- [ ] Implementovat `/api/auth/login-komisar` - PIN kód
- [ ] Test: 2-tier login funguje
- [ ] Test: Event logging zapisuje do JSONL
- [ ] Test: Selective broadcast (jen určitým rolím)
- [ ] Git commit + tag `v0.1`

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

### Success Criteria:
✅ Server startuje bez errorů  
✅ Health endpoint vrací 200 OK  
✅ Vedení může login (username+password)  
✅ Komisař může login (PIN kód)  
✅ WebSocket přijímá zprávy podle role  
✅ Selective broadcast funguje (jen určité role)  
✅ Events se logují do `logs/rz_session_*.jsonl`  
✅ Support pro 160+ současných spojení  

---

## ⏳ Fáze 2: Frontend MVP - Login + Chat UI

**Status:** ⏳ Waiting  
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

### 2026-02-14
- ✅ Fáze 0 dokončena
- ✅ Vyřešen problém s pydantic-core instalací (upgrade na 2.11+)
- ✅ Vytvořena kompletní dokumentace
- ✅ Git repository inicializován
- 📝 Připraveno na Fázi 1

---

## 🎯 Next Actions

1. **Okamžitě:** Začít Fázi 1 - vytvořit `backend/main.py`
2. Implementovat ConnectionManager
3. Vytvořit Pydantic modely
4. Testovat WebSocket komunikaci

---

## 📊 Time Tracking

| Phase | Estimated | Actual | Variance |
|-------|-----------|--------|----------|
| Fáze 0 | 1-2h | ~2h | On track ✅ |
| Fáze 1 | 3-4h | - | - |
| Fáze 2 | 3-4h | - | - |

**Total:** 2h / ~50h estimated

---

**Legend:**
- ✅ Complete
- 🔄 In Progress
- ⏳ Waiting
- ⚠️ Blocked
- 🐛 Issue
