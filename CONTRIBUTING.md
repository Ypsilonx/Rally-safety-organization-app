# Contributing Guide

Diky za zajem o prispevky do Rally Safety App.

## Jak zacit

1. Forkni repozitar a vytvor feature branch:
   - `git checkout -b feat/moje-zmena`
2. Nainstaluj zavislosti:
   - `uv sync`
3. Spust testy pred odeslanim PR:
   - `uv run pytest backend/tests -v`
4. Otevri Pull Request podle sablony v `.github/pull_request_template.md`.

## Co ocekavame

- Drz se principu KISS a YAGNI.
- Men pouze to, co je nutne pro dany ukol.
- Zachovej modularni strukturu (`backend/api`, `backend/core`, `backend/models`, `backend/services`).
- Pri zmene chovani aktualizuj odpovidajici dokumentaci (`README.md`, `STATUS.md`, `ROADMAP.md`, pokud je relevantni).

## Styl kodu

### Python

- Pouzivej type hints.
- Piste srozumitelne docstringy u funkci, trid a modulu.
- Preferuj standardni knihovnu pred novymi zavislostmi.

### Frontend

- Vanilla JavaScript bez frameworku.
- Jedna oblast zodpovednosti na soubor (`app.js`, `map.js`, `websocket.js`, `auth.js`).

## Testovani

Minimalni sada pred PR:

- `uv run pytest backend/tests -v`
- Zakladni manualni smoke test:
  - login vedeni
  - login komisar
  - odeslani zpravy
  - overeni mapy po prihlaseni

## Commity

V tomto projektu se pouzivaji Conventional Commits:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `test: ...`
- `refactor: ...`

## Pull Request checklist

- [ ] Kod je funkcni a lokalne otestovany
- [ ] Testy prochazi
- [ ] Dokumentace je aktualizovana (pokud bylo potreba)
- [ ] Scope zmeny odpovida issue
- [ ] PR popisuje rizika a dopad na uzivatele
