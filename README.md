[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=for-the-badge&logo=javascript&logoColor=F7DF1E)
![Vibecoding](https://img.shields.io/badge/Vibecoding-8A2BE2?style=for-the-badge&logo=githubcopilot&logoColor=white)
![AI Powered](https://img.shields.io/badge/AI_Powered-412991?style=for-the-badge&logo=openai&logoColor=white)

# Rally Safety App

🔶 **Celá aplikace a kód jsou vyvinuta pomocí AI pod přísným dohledem člověka, veškerá architektura je vymyšlená autorem a AI vyplnilo pouze kódem a dokumentací.** 🔶

> Progresivní webová aplikace pro koordinaci traťových komisařů během rally soutěží

## 📊 Current Status

**Aktuální fáze:** 🔄 Fáze 4 + Fáze 5 backend slice - IN PROGRESS  
**Další fáze:** Dokončení backendového station-first API a napojení admin UI  
**Celkový pokrok:** 50% (5/10 fází dokončeno)

### Stav implementace k 15.7.2026

- ✅ Hotovo: Fáze 0, 1, 2, 3
- 🔄 Rozpracováno: Fáze 4 (mapa + desktop/mobile UX refinements)
- 🔄 Zahájeno z Fáze 5: station-first backend API a historie přiřazení na stanici
- 🔄 Částečně dodáno z Fáze 6: incident quick actions + gate READY/NOT_READY
- ⏳ Čeká: zbytek Fáze 5, 7, 8, 9, 10

---

## 🎯 O projektu

Rally Safety App zajišťuje real-time přehled o situaci na trati a stavu jednotlivých stanovišť traťových komisařů během rally soutěží.

### Klíčové funkce:
- ✅ **2-tier authentication** (vedení: heslo, komisaři: PIN kód)
- 👥 **Správa 160+ komisařů** s různými rolemi
- ✅ **Live mapa** s tratí + stavem stanic
- ✅ **Real-time komunikace** přes WebSockets (selective broadcast)
- ✅ **Incident gate** (`RZ resume` až po READY potvrzeních)
- ✅ **Heartbeat monitoring** (detekce offline stanic)
- ✅ **Event logging** pro post-race analýzu
- ⏳ **Offline mode (PWA queue + sync)**
- ⏳ **GPS tracking** komisařů v reálném čase
- ✅ **Station-first backend API** (`/api/stations`, `/api/admin/stations`, create/delete, history, release, assign/reassign)
- 🔄 **Samostatná setup obrazovka pro správu pozic** (seznam, detail, historie, release, assign/reassign)
- ✅ **Setup map config (minimum)**: vlastní cesta k GeoJSON trati + ruční souřadnice vybrané pozice
- ✅ **Map data model**: trať jako `LineString`, ostatní prvky jako `Point`/`LineString` s `properties.kind` a `requires_commissioner`
- ✅ **Map podklad**: viditelný badge v hlavičce mapy ukazuje `OpenStreetMap + vlastní vrstva`
- ✅ **Offline kontakt**: každá pozice v pop-upu ukazuje jméno, název pozice, telefonní číslo a email
- ✅ **Frontend modularizace (iterace 2)**: rozdělení operations/map logiky do menších JS modulů
- ✅ **Setup assignment dropdown**: výběr osoby z people katalogu s předvyplněním role/telefonu
- ⏳ **Rozšířená setup obrazovka** (create/delete pozice, pohodlnější přesun osoby, nastavení mapy a podkladů)

## 🖼️ Ukázky rozhraní

### Přihlášení podle role
Úvodní obrazovka nabízí rychlou volbu režimu přihlášení pro vedení RZ nebo traťového komisaře.

![Přihlašovací obrazovka](media/login%20screen.png)

### Marker stanice na mapě
Každá stanice je na mapě reprezentována markerem se symbolem role; barva markeru odpovídá aktuálnímu stavu připojení.

![Marker stanice na mapě](media/mapovy%20marker%20pozice%20komisare.png)

### Detail stanice a varování
Po kliknutí na marker se otevře detail stanice s identifikací, rolí a časem poslední aktivity. Při incidentu se marker zvýrazní v alert režimu.

![Detail markeru stanice](media/marker%20s%20varovanim.png)

### Dashboard vedoucího RZ
Pohled pro vedení kombinuje admin panel, mapu trati a komunikační panel s odděleným info kanálem.

![Dashboard vedoucího RZ](media/vedouci%20RZ%20dashboard.png)

### Dashboard traťového komisaře
Pohled komisaře je zjednodušený na mapu, chat/info kanál a rychlé akce (Připraven, Problém, Akutní).

![Dashboard traťového komisaře](media/tratovy%20komisar%20dashboard.png)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- [UV](https://docs.astral.sh/uv/getting-started/installation/) (doporučeno) nebo pip
- Git
- Moderní browser (Chrome/Edge/Firefox)

### Backend Setup – UV (doporučeno)
```powershell
# 1. Nainstaluj UV (pokud ještě nemáš)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Vytvoř prostředí a instaluj závislosti
uv sync

# 3. Spusť server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Backend Setup – pip (alternativa)
```powershell
# 1. Vytvoř a aktivuj virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Instaluj závislosti
pip install -r requirements.txt

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

Poznámka: při tomto režimu může log frontendu obsahovat 404 pro `/data/example-track.geojson`.
Je to neblokující fallback (mapa použije interní vzorovou trať). Pokud chceš čistý log bez 404,
spouštěj server z kořene repozitáře a frontend otevři přes `/frontend/index.html`.

### VS Code - One Click Start (UV)
Pro rychlé spuštění bez ručního otevírání více terminálů použij tasky ve VS Code:

1. Otevři Command Palette (`Ctrl+Shift+P`)
2. Zvol `Tasks: Run Task`
3. Spusť `UV: Start App`

To současně spustí:
- backend na `http://127.0.0.1:8000`
- frontend na `http://127.0.0.1:8080`

Další tasky:
- `UV: Backend` (jen backend)
- `UV: Frontend` (jen frontend)
- `UV: Tests` (backend testy)

Stop: `Ctrl+Shift+P` → `Tasks: Terminate Task` (nebo `Terminate All Tasks`).

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
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - PR workflow, commity a checklist pro příspěvky
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
| 1 | Backend MVP (WS + Auth + Logging) | ✅ Hotovo | 4-5h |
| 2 | Frontend (2-tier Login + Chat) | ✅ Hotovo | 4-5h |
| 3 | Heartbeat monitoring | ✅ Hotovo | 4-5h |
| 4 | Mapa s Leaflet | 🔄 Probíhá | 3-4h |
| 5 | Admin Panel + Stanice | ⏳ Čeká | 8-10h |
| 6 | Incident reporting | 🔄 Částečně hotovo | 4-5h |
| 7 | PWA & Offline mode | ⏳ Čeká | 6-8h |
| 8 | Latency detection + GPS batching | ⏳ Čeká | 4-5h |
| 9 | GPS tracking | ⏳ Čeká | 4-5h |
| 10 | Production polish | ⏳ Čeká | 6-8h |

**Celkový odhad:** 45-59 hodin čistého kódování

---

## 🧪 Testing

### Backend Testing
```powershell
# UV (doporučeno)
uv run pytest

# pip alternativa
pytest backend/tests/ -v
```

### Station Status API (heartbeat monitoring)
```powershell
# Přehled online/offline stavů stanic
Invoke-RestMethod http://localhost:8000/api/stations/status

# Incident gate readiness snapshot
Invoke-RestMethod http://localhost:8000/api/stations/readiness

# Station-first directory z perzistentních PINů
Invoke-RestMethod http://localhost:8000/api/stations
```

### Admin Station API
```powershell
# Přihlášení vedení a získání session tokenu
$login = Invoke-RestMethod -Method Post http://localhost:8000/api/auth/login-vedeni `
	-ContentType 'application/json' `
	-Body '{"username":"admin","password":"demo123"}'

# Seznam stanic pro admin správu
Invoke-RestMethod http://localhost:8000/api/admin/stations `
	-Headers @{ 'X-Session-Token' = $login.session_token }

# Hromadné vygenerování PINů podle mapových pozic (PIN je vázaný na pozici, ne na jméno)
Invoke-RestMethod -Method Post http://localhost:8000/api/admin/station/bulk-generate-pins `
	-Headers @{ 'X-Session-Token' = $login.session_token } `
	-ContentType 'application/json' `
	-Body '{"regenerate_existing":false}'

# Vytvoření nové stanice s PINem a počátečním osazením
Invoke-RestMethod -Method Post http://localhost:8000/api/admin/station/create-pin `
	-Headers @{ 'X-Session-Token' = $login.session_token } `
	-ContentType 'application/json' `
	-Body '{"station_id":"PK-10","station_name":"Parkoviště 10","station_type":"parking","capacity":2,"description":"Příjezdové parkoviště","name":"Alena Testovací","role":"parkovani","phone":"+420555444333","note":"První osazení"}'

# Regenerace PINu konkrétní pozice (starý PIN se okamžitě zneplatní)
Invoke-RestMethod -Method Post http://localhost:8000/api/admin/station/TK-01/regenerate-pin `
	-Headers @{ 'X-Session-Token' = $login.session_token }

# Historie obsazení stanice
Invoke-RestMethod http://localhost:8000/api/admin/station/TK-01/history `
	-Headers @{ 'X-Session-Token' = $login.session_token }

# Uvolnění stanice zneplatní PIN pro login, dokud nepřijde nové přiřazení
Invoke-RestMethod -Method Post http://localhost:8000/api/admin/station/TK-01/release-user `
	-Headers @{ 'X-Session-Token' = $login.session_token } `
	-ContentType 'application/json' `
	-Body '{"note":"Konec směny"}'

# Přeřazení osoby na stanici se zachováním PINu
Invoke-RestMethod -Method Post http://localhost:8000/api/admin/station/TK-01/reassign-user `
	-Headers @{ 'X-Session-Token' = $login.session_token } `
	-ContentType 'application/json' `
	-Body '{"name":"Petr Nový","role":"komisar_trat","phone":"+420111222333","note":"Střídání směny"}'

# Smazání PINu stanice
Invoke-RestMethod -Method Delete http://localhost:8000/api/admin/station/PK-10/pin `
	-Headers @{ 'X-Session-Token' = $login.session_token }

# Import katalogu lidí z CSV textu (first_name/jmeno, last_name/prijmeni, phone/telefon, email/mail, address/bydliště, group/skupina)
$csv = @"
jmeno;prijmeni;telefon;mail;bydliště;skupina
Jan;Novák;+420111222333;jan.novak@example.com;Praha;RZ
Eva;Testovací;+420444555666;eva@example.com;Brno;TZ
"@

Invoke-RestMethod -Method Post http://localhost:8000/api/admin/people/import-csv `
	-Headers @{ 'X-Session-Token' = $login.session_token } `
	-ContentType 'application/json' `
	-Body (@{ csv_content = $csv; replace_existing = $false } | ConvertTo-Json)

# Seznam katalogu lidí pro setup dropdown
Invoke-RestMethod http://localhost:8000/api/admin/people `
	-Headers @{ 'X-Session-Token' = $login.session_token }
```

Pokud chceš naplnit `data/people_catalog.json` reálnými historickými daty z Google My Maps KML, spusť:

```powershell
uv run python scripts/import_people_from_kml.py
```

Bezpečnostní poznámka: `data/people_catalog.json` a `data/pins.json` jsou lokální soubory s citlivými údaji.
Jsou nastavené v `.gitignore`, takže je aplikace používá lokálně, ale do repozitáře se necommitují.
V repozitáři jsou pouze anonymní vzory `data/people_catalog.example.json` a `data/pins.example.json`.

První inicializace lokálních dat ze vzorů:

```powershell
Copy-Item data/people_catalog.example.json data/people_catalog.json
Copy-Item data/pins.example.json data/pins.json
```

Pro mapové podklady z téhož KML spusť:

```powershell
uv run python scripts/import_map_elements_from_kml.py
```

Pro souřadnice traťových pozic ze speciální CSV tabulky spusť:

```powershell
uv run python scripts/import_station_positions_from_csv.py
```

Tím se vygeneruje `data/station-coordinates.json`, který frontend mapy načítá automaticky při startu.
Soubor zároveň obsahuje i `stations` se `station_id`, `suggested_role` a `suggested_station_type`
pro přesnější seed/admin create workflow.

### Frontend Testing
- Chrome DevTools → Device Emulation
- Network tab → Offline mode testing
- Real device testing (Android/iOS)
- Ověř mapu: po loginu se zobrazí Leaflet mapa s červeně vykreslenou tratí
- Ověř markery: mapa načte stav ze `/api/stations/status` a barvy jsou: offline červená, online + not ready žlutá, online + ready zelená
- Pokud stanice během `RZ: V provozu` přejde do offline, vedení dostane varování v chatu/info s ID pozice a telefonem (bez automatického zastavení RZ)
- Incident na stanici: marker přepne do alert režimu (červený pulz + vlaječka `!`)
- Klik na marker zobrazí detail stanice (ID, role, počet připojení, poslední aktivita)
- Desktop: komunikační panel je stabilně vpravo vedle mapy
- Desktop: komunikační panel je po celé výšce od hlavičky dolů, admin/map část je zúžená
- Desktop vedeni: admin panel je kompaktní 3-sloupcový layout (status | akce | varování)
- Mobil: komunikační panel se otevírá tlačítkem 💬 jako vysouvací panel z pravé strany
- Info kanál: systémové/problémové zprávy jsou oddělené od běžného chatu v záložce "Info kanál"
- Dashboard vedení: metrika je online/total stanic (např. 12/18), ne počet zpráv
- Dashboard vedení: předdefinované krizové akce (`RZ zastavena`, `Pozor problém`, `RZ pozastavena`, `RZ opět v provozu`)
- `RZ opět v provozu` je blokováno, pokud incident gate nemá READY potvrzení ze stanic
- Vedoucí může potvrdit `Spustit i přes warning` a vynutit `RZ opět v provozu` i s chybějícími READY stanicemi
- Potvrzení obsahuje explicitní seznam žlutých/červených pozic; lze jen potvrdit zprovoznění nebo zrušit a vrátit se k řešení situace
- Dashboard vedení: incident gate ukazuje i konkrétní seznam stanic, kterým chybí READY
- Setup obrazovka: změna GeoJSON cesty se po tlačítku "Použít podklad trati" projeví okamžitě na mapě
- Setup obrazovka: u vybrané pozice lze uložit souřadnice (lat/lon) a marker se hned přesune
- Mapové prvky: divácká místa, uzavírky, retardéry, zdravotníci, hasiči, start/cíl a časomíra jsou načtené z GeoJSON a zobrazí se v mapě
- Komisařské pozice mají v datech flag `requires_commissioner` a jejich popisek popisuje, zda podléhají pravidlům READY/online
- V hlavičce mapy je viditelný štítek s podkladem `OpenStreetMap + vlastní vrstva`
- Každá pozice v mapové vrstvě zobrazuje jméno, název pozice a telefonní číslo, aby šlo volat i v offline režimu
- Horní lišta aplikace zobrazuje stav RZ (`V provozu`, `Pozastavena`, `Zastavena`)
- Při stavu `Pozastavena`/`Zastavena` má mapa červený warning border
- Warning border mapy je renderovaný jako overlay nad Leafletem (nesmí se schovat pod mapové vrstvy)
- Komisař: při hlášení problému musí doplnit detail incidentu
- Komisař: má i tlačítko `🆘 Akutní` (odeslání kritického incidentu bez vstupu)
- Komisař: na dashboardu má kontakt na vedoucího RZ (tel link)
- Chat tagging: napiš `@Jmeno` nebo `#Stanice` a použij našeptávač pro rychlé označení
- Tagy se zvýrazní jen pokud odpovídají známému uživateli/stanici; klik na `#Stanice` vycentruje mapu na marker
- Chat, info kanál a varování vedení se ukládají lokálně pro přihlášeného uživatele a po odhlášení/znovupřihlášení se obnoví
- Toast notifikace se zobrazují na středu nad mapou (ne v pravém horním rohu)
- Audit log obsahuje nejen komunikaci, ale i klíčové UI kroky (potvrzení/zrušení warningů, změny RZ stavu, setup změny lidí a map config)

### Map Module - Manual Checklist (Fáze 4)
- Na mapě jsou vidět markery stanic se symbolem role (S/F/T/C/P/B/Z/V/+)
- Markery mění barvu podle stavu (online zelená, offline červená)
- Popup stanice obsahuje relativní i absolutní čas poslední aktivity
- Klik na `#Stanice` v chatu otevře popup příslušného markeru
- Mobilní zobrazení: mapa + vysouvací komunikace bez posunu mimo viewport

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.116+ - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** 2.11+ - Data validation
- **WebSockets** - Real-time communication (selective broadcast)
- **bcrypt** - Password hashing for vedení
- **JSONL** - Structured event logging

### Frontend
- **Vanilla JavaScript** (ES6+) - No frameworks
- **Leaflet.js** - Interactive maps
- **Service Workers** - Offline support
- **IndexedDB** - Local data persistence

### Architecture
- **Auth:** 2-tier (password hash + PIN codes; nové PINy mají 8 číslic, legacy 4místné jsou podporované)
- **Scalability:** 160+ concurrent connections
- **Storage:** In-memory (MVP phase)
- **No database** until production phase

---

Vývojové zásady, pravidla pro commity a contributor workflow jsou v [DEVELOPMENT.md](DEVELOPMENT.md) a [CONTRIBUTING.md](CONTRIBUTING.md).

---

## ⚠️ Known Issues

- Desktop/mobile layout je aktivně dolaďován podle field feedbacku (Fáze 4).
- PWA offline queue a background sync zatím nejsou implementované.
- Pokud frontend server běží jen nad složkou `frontend`, může se v logu objevit 404 pro `/data/example-track.geojson` (neblokující fallback).

---

## 🤝 Contributing & Issues

Projekt je připravený na externí příspěvky přes GitHub Pull Request workflow.

### Jak přispět

1. Přečti si [CONTRIBUTING.md](CONTRIBUTING.md)
2. Vytvoř issue (bug/feature/question) přes připravené šablony
3. Otevři PR podle [PR šablony](.github/pull_request_template.md)

### Community Health soubory

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md)
- [Issue templates](.github/ISSUE_TEMPLATE)

Poznámka: před plně veřejným open-source režimem doporučujeme finálně potvrdit licenci projektu.

---

## 📄 License

MIT License. Viz [LICENSE](LICENSE).

---

**Poslední aktualizace:** 12. července 2026  
**Verze dokumentace:** v0.5-dev (Fáze 4 in progress)
