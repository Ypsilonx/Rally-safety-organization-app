# Development Guidelines - Rally Safety App

Tento dokument popisuje vývojářské standardy. Aktuální stav projektu sleduj v `STATUS.md`, rozsah fází v `ROADMAP.md`.

## 🧭 Pravidlo dokumentace

Po každé změně chování aplikace aktualizuj minimálně:
- `README.md` (uživatelské a provozní chování)
- `STATUS.md` (co je hotovo / co je další krok)
- `ROADMAP.md` (stav fází a částečně dodané položky)

## 🔧 Coding Standards

### Python (Backend)

#### Naming Conventions
```python
# Classes: PascalCase
class ConnectionManager:
    pass

# Functions/methods: snake_case
def send_broadcast_message():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_HEARTBEAT_INTERVAL = 120

# Private: prefix with underscore
def _internal_helper():
    pass
```

#### Type Hints (POVINNÉ)
```python
from typing import List, Optional
from datetime import datetime

def process_message(
    message_id: str,
    created_at: datetime,
    content: str,
    priority: int = 0
) -> dict:
    """
    Process incoming message from station.
    
    Args:
        message_id: Unique message identifier
        created_at: Client timestamp when message created
        content: Message content
        priority: Message priority (0=normal, 1=urgent)
    
    Returns:
        Processed message dict with server metadata
    """
    pass
```

#### Pydantic Models
```python
from pydantic import BaseModel, Field
from datetime import datetime

class StationMessage(BaseModel):
    """Message from station to server."""
    message_id: str = Field(..., description="Unique message ID")
    station_id: str
    created_at: datetime
    message_type: str  # "incident", "heartbeat", "ready"
    content: str
    location: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "uuid-here",
                "station_id": "ST-01",
                "created_at": "2026-02-14T10:30:00Z",
                "message_type": "incident",
                "content": "Nehoda v zatáčce 3"
            }
        }
```

#### Error Handling
```python
# Specifické exceptions
class StationNotFoundError(Exception):
    """Raised when station ID doesn't exist."""
    pass

# Try-except pouze kde očekáváš chybu
try:
    result = await process_critical_data(data)
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

### JavaScript (Frontend)

#### Naming Conventions
```javascript
// Classes: PascalCase
class WebSocketManager {}

// Functions: camelCase
function sendMessage() {}

// Constants: UPPER_SNAKE_CASE
const MAX_RETRY_ATTEMPTS = 3;

// Private convention: prefix with underscore
function _internalHelper() {}
```

#### Modern ES6+
```javascript
// Prefer const, use let when needed, NEVER var
const config = { url: 'ws://...' };
let retryCount = 0;

// Arrow functions
const handleMessage = (msg) => {
    console.log(msg);
};

// Destructuring
const { message_id, content } = messageData;

// Template literals
const url = `ws://${host}:${port}/ws`;

// Async/await (NO callbacks nebo .then chains)
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch:', error);
        throw error;
    }
}
```

#### JSDoc komentáře
```javascript
/**
 * Send message via WebSocket with offline fallback
 * @param {string} messageType - Type of message
 * @param {Object} payload - Message data
 * @returns {Promise<boolean>} True if sent, false if queued offline
 */
async function sendMessage(messageType, payload) {
    // ...
}
```

## 🧪 Testování

### Backend Testing
```python
# pytest for all tests
# Test file: test_*.py or *_test.py

import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_websocket_connection(client):
    with client.websocket_connect("/ws/ST-01") as websocket:
        websocket.send_json({"type": "heartbeat"})
        data = websocket.receive_json()
        assert data["status"] == "ok"
```

### Frontend Testing
- Manuální testing v prohlížeči (Chrome DevTools)
- Testovat offline mode (DevTools -> Network -> Offline)
- Testovat na mobile (Chrome Device Emulation)

## 🔀 Git Workflow

### Branch Naming
```
main           # Production ready code
develop        # Development branch
feature/xyz    # New features
fix/xyz        # Bug fixes
refactor/xyz   # Code improvements
```

### Commit Messages (Conventional Commits)
```
feat: add heartbeat mechanism
fix: resolve WebSocket reconnection issue
refactor: simplify message validation
docs: update API documentation
test: add WebSocket connection tests
chore: update dependencies
```

### Pravidla
- Commit často, malé logické celky
- NIKDY necommituj nefunkční kód do `main`
- Vždy test před commitem
- `.env` a citlivá data → `.gitignore`

## 📦 Dependencies Management

### Backend (Python)
```bash
# Doporučený workflow (UV)
uv sync

# Přidání závislosti
uv add package-name

# Export requirements.txt pro pip uživatele
uv export --format requirements-txt --no-hashes --no-dev -o requirements.txt
```

### Základní dependencies
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
python-dotenv>=1.0.0
websockets>=12.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

## 🌐 Environment Variables

Vždy používej `.env` file (NIKDY necommituj):

```bash
# .env.example (tento commituj jako template)
DEBUG=true
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = ["http://localhost:8000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 📝 Logging

### Backend
```python
import logging

# Setup in main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Usage
logger.info("WebSocket connection established: {station_id}")
logger.warning("Heartbeat timeout for station: {station_id}")
logger.error("Failed to process message", exc_info=True)
```

### Frontend
```javascript
// Simple console logging with levels
const logger = {
    info: (msg, ...args) => console.log(`[INFO] ${msg}`, ...args),
    warn: (msg, ...args) => console.warn(`[WARN] ${msg}`, ...args),
    error: (msg, ...args) => console.error(`[ERROR] ${msg}`, ...args)
};

logger.info('WebSocket connected');
logger.error('Failed to send message:', error);
```

## 🚫 Co NEDĚLAT

### ❌ Nedělej
- Komplexní architektury od začátku
- Optimalizace předčasně ("premature optimization")
- Features, které nikdo nepožadoval
- Kopírování kódu místo vytvoření funkce
- Ignorování errorů (prázdné catch bloky)
- Commity typu "fix", "update", "changes"
- Hard-coded hodnoty (URLs, credentials)

### ✅ Dělej
- Testuj každou změnu lokálně
- Piš čitelný kód (ne chytrý kód)
- Komentuj PROČ, ne CO (kód ukazuje CO)
- Refactoruj průběžně (malé iterace)
- Ptej se, když nejsi jistý
- Používej version control často

## 🎨 Code Review Checklist

Before každého commitu se zeptej:
- [ ] Funguje to lokálně?
- [ ] Je kód čitelný pro druhého člověka?
- [ ] Mají funkce jasné názvy?
- [ ] Jsou error stavy ošetřené?
- [ ] Přidal jsem něco, co **teď** není potřeba?
- [ ] Smažu všechny `console.log` / `print` debug výpisy?
- [ ] Jsou citlivá data v `.gitignore`?

## 🚀 Performance Guidelines

- Frontend: Bundle size < 500 KB (gzipped)
- Backend: Response time < 200ms (except WebSocket streaming)
- WebSocket: Heartbeat každých 30s
- Offline queue: Max 100 zpráv v IndexedDB
- Map tiles: Cache max 50 MB

---

**Pamatuj:** Jednoduchý fungující kód > Komplexní "chytrý" kód
