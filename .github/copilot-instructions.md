# GitHub Copilot Instructions - Rally Safety App

## 🎯 Core Principles (ALWAYS FOLLOW)

### 1. Simplicity First
- **KISS** - Keep It Simple, Stupid
- Prefer simple, readable solutions over "clever" code
- If it can be done in 10 lines instead of 50, do it in 10
- Question complexity - ask "is this really needed?"

### 2. YAGNI - You Aren't Gonna Need It
- **DO NOT** implement features ahead of time
- **DO NOT** add "future-proofing" unless explicitly requested
- Build exactly what's needed for current phase, nothing more
- If user doesn't ask for it → don't add it

### 3. Follow the Plan (ROADMAP.md)
- Current phase is defined in STATUS.md
- Complete current phase fully before moving to next
- Do not skip steps or combine phases
- Each phase has specific deliverables - stick to them
- **IMPORTANT:** When completing tasks, update BOTH STATUS.md AND ROADMAP.md
  - Check off completed tasks in ROADMAP.md (add checkmarks)
  - Mark phases as complete with ✅ emoji in ROADMAP.md headings
  - Keep both files synchronized at all times

### 4. Modular Architecture
- Keep modules small and focused (single responsibility)
- One file = one concern
- Clear separation: models, services, API, core
- Follow existing project structure exactly

---

## 📁 Project Structure Rules

### Backend Structure (Python/FastAPI)
```
backend/
├── main.py              # ONLY FastAPI app initialization & routes
├── api/                 # API endpoints (WebSocket, REST)
│   ├── websocket.py    # WebSocket handlers
│   └── health.py       # Health check endpoints
├── core/                # Core functionality (config, managers)
│   ├── config.py       # Configuration from .env
│   └── connection_manager.py  # WebSocket connection pool
├── models/              # Pydantic models (data schemas)
│   ├── message.py      # Message models
│   └── station.py      # Station/User models
├── services/            # Business logic
│   └── vitality.py     # Heartbeat monitoring (Phase 3+)
└── tests/               # Unit & integration tests
```

**Rule:** If creating new functionality, ask yourself: "Which folder does this belong to?" Place it correctly.

### Frontend Structure (JavaScript/PWA)
```
frontend/
├── index.html           # ONLY main HTML structure
├── manifest.json        # PWA manifest
├── css/
│   └── styles.css      # All styles in one file (until it's >500 lines)
├── js/
│   ├── app.js          # Main app initialization & coordination
│   ├── map.js          # Map-related logic ONLY
│   ├── websocket.js    # WebSocket client ONLY
│   └── offline.js      # Offline queue management ONLY
└── service-worker.js    # PWA caching & sync
```

**Rule:** Each JS file handles ONE concern. No mixing map logic with WebSocket logic.

---

## 🚫 What NOT to Do

### 1. NO Extra .md Files
- **FORBIDDEN:** Creating summary .md files after each task
- **FORBIDDEN:** "CHANGES.md", "UPDATES.md", "SUMMARY.md"
- Update existing docs (STATUS.md, README.md) instead
- Only create .md if explicitly requested by user

### 2. NO Premature Features
- Don't add authentication before Phase 10
- Don't add database before it's in roadmap
- Don't add logging frameworks (use Python's built-in logging)
- Don't add TypeScript (stick to vanilla JS)

### 3. NO Over-Engineering
- Don't create abstract base classes "for future extensibility"
- Don't add dependency injection frameworks
- Don't create complex design patterns (Factory, Strategy, etc.) unless needed
- Simple functions > Classes (when appropriate)

### 4. NO Skipping Testing
- Every phase ends with testing
- Test manually before marking phase complete
- Simple tests > no tests

---

## ✅ What TO Do

### 1. Code Quality
- **Type hints** in Python (mandatory)
- **JSDoc** comments for JS functions (parameters, return values)
- Meaningful variable names (`station_id` not `sid`)
- Keep functions under 50 lines (split if longer)

### 2. Error Handling
- Specific exceptions, not generic `Exception`
- Always handle network failures gracefully
- Log errors with context
- User-friendly error messages

### 3. Documentation
- Update STATUS.md after completing tasks
- Update README.md when changing setup/usage
- Inline comments for "why", not "what" (code shows "what")
- API documentation in docstrings

### 4. Git Workflow
- Frequent commits (after each logical change)
- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- Tag at end of each phase: `v0.1`, `v0.2`, etc.

---

## 📝 Code Style Guidelines

### Python
```python
# Good - Simple, clear, typed
def send_message(station_id: str, content: str) -> bool:
    """Send message to station."""
    logger.info(f"Sending to {station_id}")
    return ws_manager.send(station_id, content)

# Bad - Over-engineered
class MessageSenderFactory:
    def create_sender(self) -> IMessageSender:
        return ConcreteMessageSender(
            DependencyContainer.resolve(ILogger)
        )
```

### JavaScript
```javascript
// Good - Simple, modern ES6
async function connectWebSocket(url) {
    try {
        const ws = new WebSocket(url);
        ws.onopen = () => logger.info('Connected');
        return ws;
    } catch (error) {
        logger.error('Connection failed:', error);
        throw error;
    }
}

// Bad - Over-complicated
class WebSocketConnectionFactory {
    constructor(config) {
        this.config = config;
        this.handlers = new Map();
    }
    // ... 200 lines of abstraction
}
```

---

## 🔄 Development Workflow

### When Starting New Phase:
1. Read ROADMAP.md for phase requirements
2. Update STATUS.md: mark phase as "in-progress"
3. Create files listed in phase checklist
4. Implement features ONE BY ONE
5. Test each feature as you go
6. Update STATUS.md: check off completed items
7. Final testing
8. Git commit + tag
9. Update STATUS.md: mark phase "complete"

### When User Asks for Feature:
1. Check: Is it in current phase? → Yes: do it. No: Ask if we should add it to backlog.
2. Ask: Can this be simpler? → Always try simpler first.
3. Check: Where does this code belong? → Put it in correct folder.
4. Implement minimally → Test → Iterate if needed.

---

## 💬 Communication Style

### When Explaining:
- Keep explanations SHORT (2-3 sentences max)
- Don't say "I'll use multi_replace_string_in_file" → Just do it
- Don't ask permission for routine tasks → Just do them
- Focus on WHAT was done and WHY, not HOW

### When Presenting Code:
- No need to show entire file contents after edit
- Just confirm what was changed/created
- Link to files using markdown links: [filename.py](path/filename.py)

### When Something is Unclear:
- ASK instead of guessing
- Present 2-3 options if multiple approaches exist
- Recommend the simplest one

---

## 🎯 Current Project Context

**Technology Stack:**
- Backend: FastAPI + Uvicorn + Pydantic + WebSockets
- Frontend: Vanilla JS (ES6+) + Leaflet.js + PWA
- No frameworks: No React, Vue, Angular, TypeScript
- No database until explicitly added to roadmap

**Current Phase:** Check STATUS.md
**Coding Standards:** See DEVELOPMENT.md
**Architecture:** See project_plan.md

---

## ⚠️ Critical Rules Recap

1. ✅ Follow ROADMAP.md phases strictly
2. ✅ Update **BOTH** STATUS.md AND ROADMAP.md after completing tasks
3. ✅ Keep code modular and simple
4. ✅ Test before marking complete
5. ❌ NO extra .md files (update existing instead)
6. ❌ NO features ahead of time
7. ❌ NO over-engineering
8. ❌ NO skipping project structure

---

**Remember:** Simple working code today > Perfect code tomorrow

**When in doubt:** KISS (Keep It Simple, Stupid)
