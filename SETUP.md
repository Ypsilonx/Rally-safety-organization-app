# Rally Safety App - Setup Guide

Tento dokument je pro zprovoznění existujícího repozitáře. Historický bootstrap z Fáze 0 sem už nepatří.

## 🚀 Jak začít - Krok za krokem

Tento dokument tě provede kompletním setupem projektu od nuly.

### Rychlý setup pro současný stav projektu

```powershell
# 1) V kořeni projektu
uv sync

# 2) Spusť backend
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 3) V druhém terminálu spusť frontend
python -m http.server 8080 --directory frontend
```

Poznámka: v tomto režimu může frontend logovat 404 pro `/data/example-track.geojson`.
Jde o neblokující fallback (mapa použije interní vzorovou trať).
Pokud chceš čistý log bez 404, spusť server nad kořenem repozitáře a otevři
`http://127.0.0.1:8080/frontend/index.html`.

Alternativa ve VS Code: `Tasks: Run Task` -> `UV: Start App`.

---

## 📋 Prerequisites (Co potřebuješ mít nainstalované)

### 1. Python 3.13+
```powershell
# Zkontroluj verzi
python --version

# Mělo by být: Python 3.13.x nebo vyšší
```

Pokud nemáš: [Python Download](https://www.python.org/downloads/)

### 2. Git
```powershell
git --version
# Mělo by být: git version 2.x.x
```

Pokud nemáš: [Git Download](https://git-scm.com/downloads)

### 3. VS Code (doporučeno)
- [VS Code Download](https://code.visualstudio.com/)
- Extensions:
  - Python
  - Pylance
  - ESLint
  - Live Server (pro frontend development)

---

## 🧰 Instalace prostředí

#### Varianta A – UV (doporučeno)

```powershell
# Nainstaluj UV (pokud ještě nemáš)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Vytvoř .venv a instaluj všechny závislosti z uv.lock
uv sync

# V VS Code: Ctrl+Shift+P → Python: Select Interpreter → .venv\Scripts\python.exe
```

#### Varianta B – pip (alternativa)

```powershell
# Vytvoř virtual environment
python -m venv .venv

# Aktivuj virtual environment
.\.venv\Scripts\activate

# Měl by se změnit prompt na: (.venv) PS D:\61_Programing\Rally safety organization app>

# Instaluj závislosti
pip install -r requirements.txt
```

## 📦 Závislosti

Závislosti projektu jsou definovány v `pyproject.toml` a uzamčeny v `uv.lock`.
Soubor `requirements.txt` v kořeni projektu je exportovaný artefakt pro pip uživatele – **neupravuj ho ručně**.

Po každé změně závislostí (UV workflow):
```powershell
# Přidej závislost
uv add nazev-balicku

# Exportuj aktualizovaný requirements.txt
uv export --format requirements-txt --no-hashes --no-dev -o requirements.txt
```

---

## ✅ Verifikace setupu

Zkontroluj, že vše funguje:

```powershell
# 1. Virtual environment je aktivní
# Měl bys vidět (venv) v promptu

# 2. Python packages jsou nainstalované
pip list
# Měl by obsahovat fastapi, uvicorn, pydantic, etc.

# 3. Git je inicializovaný
git status
# Mělo by ukázat "On branch main" nebo "master"
```

---

## 🎯 Co dál?

Po zprovoznění prostředí pokračuj podle [README.md](README.md), aktuálního stavu v [STATUS.md](STATUS.md) a plánovaných fází v [ROADMAP.md](ROADMAP.md).

### Spuštění development serveru:
```powershell
# V root složce projektu s aktivním venv
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🆘 Troubleshooting

### Problem: `python` příkaz nefunguje
**Řešení:**
```powershell
# Zkus místo toho:
py --version
# Nebo najdi Python v Path
where.exe python
```

### Problem: `pip install` je pomalý
**Řešení:**
```powershell
# Použij mirror (např. PyPI mirror)
pip install -r requirements.txt --index-url https://pypi.org/simple
```

### Problem: Virtual environment se neaktivuje
**Řešení:**
```powershell
# Možná potřebuješ povolit scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Pak znovu zkus
.\venv\Scripts\activate
```

### Problem: Git commit hlásí CRLF warning
**Řešení:**
```powershell
# Je to normální na Windows, Git to automaticky konvertuje
# Můžeš ignorovat nebo nastavit:
git config core.autocrlf true
```

---

## 📞 Potřebuješ pomoc?

Pokud něco nefunguje:
1. Zkontroluj, že máš všechny prerequisites
2. Zkus restart terminálu
3. Deaktivuj a aktivuj znovu venv
4. V nejhorším případě smaž `venv/` a udělej znovu Krok 3-4

**Ready to code!** 🚀
