# Development Guidelines - Rally Safety App

Tento dokument popisuje vývojářské standardy specifické pro tenhle projekt.
Aktuální stav projektu sleduj v `STATUS.md`, rozsah fází v `ROADMAP.md`.

Obecné konvence (PEP 8, JSDoc, type hints, pydantic modely...) tu záměrně
nejsou vypsané znovu - jsou to standardní zvyklosti daného jazyka a
existující kód je už konzistentně dodržuje. Když si nejsi jistý stylem,
podívej se na hotový kód, např. `backend/core/auth.py` (Python) nebo
`frontend/js/websocket.js` (JS) - obojí má důsledné docstringy/JSDoc a
type hints.

## 🧭 Pravidlo dokumentace

Po každé změně chování aplikace aktualizuj minimálně:
- `README.md` (uživatelské a provozní chování)
- `STATUS.md` (co je hotovo / co je další krok)
- `ROADMAP.md` (stav fází a částečně dodané položky)

Detailní API dokumentace se negeneruje ručně - běžící server ji má vždy
aktuální na `http://localhost:8000/docs` (Swagger UI).

## 🧪 Testování

```bash
uv run pytest                  # celá sada
pytest backend/tests/ -v       # pip alternativa
```

Testy používají `httpx.AsyncClient` s `ASGITransport` (ne `TestClient`) a
`asyncio_mode = "auto"` (viz `pyproject.toml`) - fixture s `async def` bez
dalšího boilerplate. Příklad viz `backend/tests/test_admin_people_api.py`.

Frontend nemá automatizované testy - manuální checklist je v `README.md`
(sekce Testing).

## 🔀 Git Workflow

Vývoj probíhá přímo na `master` (žádné `develop`/`feature` větve pro
interní práci). Pro externí příspěvky přes PR viz `CONTRIBUTING.md`.

### Commit zprávy
Krátký český imperativ popisující *co* se změnilo, ne "fix"/"update"/"wip":
```
Refaktoruj backend API a rozložení frontendu
Oprav gate sync a odstraň deprecation warningy
Přidej anonymní example data a ignoruj citlivé soubory
```

### Pravidla
- Commit často, malé logické celky
- NIKDY necommituj nefunkční kód
- Testuj (`uv run pytest`) před commitem
- `.env` a citlivá data → `.gitignore` (viz README sekci o `data/*.json`)
- Force push / přepis historie jen po výslovném souhlasu

## 📦 Dependencies Management

```bash
uv sync                        # instalace podle pyproject.toml
uv add package-name            # přidání závislosti
uv export --format requirements-txt --no-hashes --no-dev -o requirements.txt
```

Aktuální seznam závislostí je v `pyproject.toml` (autoritativní) a
odvozeném `requirements.txt` pro pip uživatele - nekopíruj verze sem,
ať se nerozejdou.

## 🌐 Environment Variables

Nastavení je v `.env` (nikdy necommituj), šablona v `.env.example`.
Definice a bezpečné výchozí hodnoty viz `backend/core/config.py`
(`Settings` třída má docstring u každého pole).

## 🚫 Co NEDĚLAT

- Komplexní architektury od začátku
- Optimalizace předčasně ("premature optimization")
- Features, které nikdo nepožadoval
- Kopírování kódu místo vytvoření funkce
- Ignorování errorů (prázdné catch bloky)
- Commity typu "fix", "update", "changes"
- Hard-coded hodnoty (URLs, credentials) - viz `API_BASE_URL`/`WS_BASE_URL`
  v `frontend/js/auth.js`/`websocket.js` a `ALLOWED_ORIGINS` v configu jako
  správný vzor centrální konfigurace

## ✅ Co dělat

- Testuj každou změnu lokálně
- Piš čitelný kód (ne chytrý kód)
- Komentuj PROČ, ne CO (kód ukazuje CO)
- Když najdeš nepoužívaný kód, buď ho smaž, nebo jasně okomentuj proč tam
  zůstává (viz `send_personal_message`/`broadcast_to_station` v
  `backend/core/connection_manager.py` jako příklad zdůvodněné výjimky)
- Refactoruj průběžně (malé iterace)
- Ptej se, když nejsi jistý

## 🎨 Code Review Checklist

Before každého commitu se zeptej:
- [ ] Funguje to lokálně?
- [ ] Je kód čitelný pro druhého člověka?
- [ ] Mají funkce jasné názvy?
- [ ] Jsou error stavy ošetřené?
- [ ] Přidal jsem něco, co **teď** není potřeba?
- [ ] Smažu všechny `console.log` / `print` debug výpisy?
- [ ] Jsou citlivá data v `.gitignore`?
- [ ] Aktualizoval jsem README/STATUS/ROADMAP, pokud jsem změnil chování?

## 🚀 Performance Guidelines

- Frontend: Bundle size < 500 KB (gzipped)
- Backend: Response time < 200ms (except WebSocket streaming)
- WebSocket: Heartbeat každých 30s
- Offline queue: Max 100 zpráv v IndexedDB (Fáze 7, zatím neimplementováno)
- Map tiles: Cache max 50 MB

---

**Pamatuj:** Jednoduchý fungující kód > Komplexní "chytrý" kód
