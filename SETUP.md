# Rally Safety App - Setup Guide

> ⚠️ Poznámka k 12.7.2026:
> Tento dokument obsahuje i historické kroky z Fáze 0 (zakládání projektu od nuly).
> Pro běžnou práci na existujícím repozitáři používej primárně README (Quick Start) + STATUS + ROADMAP.

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

## 🏗️ Fáze 0: Inicializace projektu

### Krok 1: Vytvoř adresářovou strukturu

```powershell
# Jsi ve složce: d:\61_Programing\Rally safety organization app

# Vytvoř backend strukturu
New-Item -ItemType Directory -Force backend
New-Item -ItemType Directory -Force backend/api
New-Item -ItemType Directory -Force backend/core
New-Item -ItemType Directory -Force backend/models
New-Item -ItemType Directory -Force backend/services
New-Item -ItemType Directory -Force backend/tests

# Vytvoř frontend strukturu
New-Item -ItemType Directory -Force frontend
New-Item -ItemType Directory -Force frontend/css
New-Item -ItemType Directory -Force frontend/js

# Vytvoř data a docs složky
New-Item -ItemType Directory -Force data
New-Item -ItemType Directory -Force docs

# Vytvoř __init__.py soubory (aby Python rozpoznal jako packages)
New-Item -ItemType File -Force backend/__init__.py
New-Item -ItemType File -Force backend/api/__init__.py
New-Item -ItemType File -Force backend/core/__init__.py
New-Item -ItemType File -Force backend/models/__init__.py
New-Item -ItemType File -Force backend/services/__init__.py
New-Item -ItemType File -Force backend/tests/__init__.py
```

### Krok 2: Iniciuj Git repository

```powershell
# Inicializuj Git
git init

# Vytvoř .gitignore
@"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv/

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log

# Frontend
node_modules/
dist/
.parcel-cache/
"@ | Out-File -FilePath .gitignore -Encoding utf8

# První commit
git add .
git commit -m "chore: initial project structure"
```

### Krok 3: Setup Python prostředí

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

### Krok 4: Závislosti

Závislosti projektu jsou definovány v `pyproject.toml` a uzamčeny v `uv.lock`.
Soubor `requirements.txt` v kořeni projektu je exportovaný artefakt pro pip uživatele – **neupravuj ho ručně**.

Po každé změně závislostí (UV workflow):
```powershell
# Přidej závislost
uv add nazev-balicku

# Exportuj aktualizovaný requirements.txt
uv export --format requirements-txt --no-hashes --no-dev -o requirements.txt
```

### Krok 5: Vytvoř .env.example

```powershell
@"
# Server Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000

# CORS - Allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:8080,http://127.0.0.1:8000,http://127.0.0.1:8080

# Heartbeat Settings
HEARTBEAT_INTERVAL_SECONDS=30
HEARTBEAT_TIMEOUT_SECONDS=120

# Logging
LOG_LEVEL=INFO
"@ | Out-File -FilePath backend/.env.example -Encoding utf8

# Zkopíruj do .env pro local development
Copy-Item backend/.env.example backend/.env
```

### Krok 6: Vytvoř README.md

```powershell
@"
# Rally Safety App

Progresivní webová aplikace pro koordinaci traťových komisařů během rally soutěží.

## 🚀 Quick Start

### Backend
\`\`\`bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
python -m http.server 8080
\`\`\`

Otevři: http://localhost:8080

## 📚 Documentation

- [Development Guidelines](DEVELOPMENT.md)
- [Development Roadmap](ROADMAP.md)
- [Setup Guide](SETUP.md)
- [Project Plan](project_plan.md)

## 🏗️ Current Status

**Current Phase:** Fáze 0 - Project Setup  
**Next Milestone:** Fáze 1 - Backend MVP

## 🤝 Contributing

1. Přečti [DEVELOPMENT.md](DEVELOPMENT.md) pro coding standards
2. Následuj [ROADMAP.md](ROADMAP.md) pro postupný vývoj
3. Každý commit musí být tested lokálně

## 📄 License

This project is for internal use.
"@ | Out-File -FilePath README.md -Encoding utf8
```

### Krok 7: Commit setup

```powershell
git add .
git commit -m "chore: add project setup (requirements, gitignore, env)"
git tag v0.0
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

# 4. Struktura adresářů
tree /F
# Nebo
Get-ChildItem -Recurse -Directory
```

Očekávaná struktura:
```
rally-safety-app/
├── .git/
├── .gitignore
├── README.md
├── project_plan.md
├── DEVELOPMENT.md
├── ROADMAP.md
├── SETUP.md
├── venv/
├── backend/
│   ├── __init__.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env
│   ├── api/
│   │   └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── tests/
│       └── __init__.py
├── frontend/
│   ├── css/
│   └── js/
├── data/
└── docs/
```

---

## 🎯 Co dál?

✅ **Fáze 0 je hotová!**

Pokračuj na **Fáze 1: Backend MVP**

### Další kroky:
1. Otevři [ROADMAP.md](ROADMAP.md) a přečti si Fázi 1
2. Začni tvořit `backend/main.py` podle specifikace
3. Testuj každou změnu lokálně před commitem

### Spuštění development serveru (až budeš mít main.py):
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
