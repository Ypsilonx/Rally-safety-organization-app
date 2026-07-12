# Rally Safety App - Technická Specifikace

**Verze:** 0.5.1-dev  
**Datum:** 12. července 2026  
**Status:** Technická specifikace produktu a cílové architektury

---

Tento dokument neudržuje průběžný stav implementace. Aktuální dodané části sleduj v `STATUS.md`, fázování v `ROADMAP.md`.

---

## 📋 Obsah

1. [Přehled projektu](#-přehled-projektu)
2. [Klíčové role a funkce](#-klíčové-role-a-funkce)
3. [Technický stack](#️-technický-stack)
4. [Architektura systému](#-architektura-systému)
5. [Autentizace a bezpečnost](#-autentizace-a-bezpečnost)
6. [Vitality monitoring](#-vitality-monitoring)
7. [UI/UX koncept](#-uiux-koncept)
8. [Budoucí rozšíření](#-budoucí-rozšíření)

---

## 🎯 Přehled projektu

Rally Safety App je **progresivní webová aplikace (PWA)** pro koordinaci traťových komisařů a vedení Rychlostní zkoušky (RZ) během rally soutěží.

### Hlavní cíl
Zajistit **v reálném čase** přehled o situaci na trati, poloze a stavu jednotlivých stanovišť a umožnit **okamžitou komunikaci** mezi komisaři a vedením (Start/Cíl) s důrazem na:
- ✅ **Bezpečnost** - kritické zprávy mají prioritu
- ✅ **Přehlednost** - vizuální zpětná vazba o stavu RZ
- ✅ **Odolnost** - funguje i při výpadku signálu

### Klíčové vlastnosti
- 📱 **Mobile-first** design pro práci v terénu
- 🌐 **Offline-first** - funguje bez internetu
- ⚡ **Real-time** komunikace přes WebSockets
- 🗺️ **Interaktivní mapa** s trasou a stanovišti
- 🚨 **Rychlá hlášení** - velká tlačítka pro okamžitou reakci
- 👥 **Škálování** - podpora pro 160+ komisařů současně

---

## 👥 Klíčové role a funkce

### 🎖️ Vedení RZ (Start & Cíl)

**Role:** Vedoucí rallye (Start) + Zástupce (Cíl)

**Funkce:**
- 🗺️ **Globální přehled**
  - Interaktivní mapa s trasou RZ
  - Vytyčená stanoviště a divácké zóny
  - Real-time pozice všech komisařů
  
- 💚 **Monitoring konektivity (Vitality)**
  - Vizualizace stáří dat z každého stanoviště
  - Detekce offline stavu v reálném čase
  - Varování při dlouhé latenci zpráv
  
- 📢 **Broadcast messaging**
  - Urgentní hlášení všem stanovištím najednou
  - Kritická zpráva: "STOP RZ - Nebezpečí"
  - Selective broadcast (jen určité role/oblasti)
  
- 👨‍💼 **Administrace**
  - Správa komisařů a přiřazování stanic
  - Generování PIN kódů pro stanice
  - Textová komunikace Start ↔ Cíl
  - Historie všech událostí

### 🚩 Traťový komisař (Stanoviště)

**Role:** Komisař tratě, zatáčky, časoměřič, parking, zdravotník, atd.

**Funkce:**
- 📍 **Lokalizace**
  - Zobrazení vlastní pozice na mapě
  - Vzdálenost k trase a sousedním stanovištím
  - Přehled o okolí
  
- 🚨 **Rychlá hlášení** (FAB - Floating Action Button)
  - ⛑️ **NEHODA** - kritické hlášení
  - ⚠️ **DIVÁCI V NEBEZPEČÍ** - vysoká priorita
  - ✅ **STANOVIŠTĚ PŘIPRAVENO** - potvrzení ready
  - 💬 **Volný text** - doplňující informace
  
- 🎨 **Vizuální zpětná vazba**
  - 🟢 **Zelená** - RZ běží normálně
  - 🟡 **Žlutá** - Varování na trati
  - 🔴 **Červená** - STOP RZ (okamžitá akce)
  - ⚪ **Šedá** - Ztráta spojení

---

## 🛠️ Technický stack

### Frontend (PWA)

| Kategorie | Technologie | Důvod výběru |
|-----------|-------------|--------------|
| **Core** | HTML5, CSS3, Vanilla JavaScript | Rychlost, bez závislostí |
| **Mapa** | Leaflet.js / MapLibre | Efektivní práce s vektorovými daty, offline tiles |
| **Offline** | Service Workers | Cache strategie pro offline režim |
| **Storage** | IndexedDB | Fronta zpráv pro offline messaging |
| **Sync** | Background Sync API | Automatické odeslání dat při obnovení signálu |

**Offline resilience (plán):**
- ⏳ Service Workers pro dostupnost mapy i bez internetu
- ⏳ IndexedDB (Outbox) pro frontu zpráv při výpadku
- ⏳ Background Sync pro automatické odeslání po obnovení signálu

### Backend (Python)

| Kategorie | Technologie | Důvod výběru |
|-----------|-------------|--------------|
| **Framework** | FastAPI | Asynchronní, vysoký výkon, moderní Python |
| **WebSockets** | Uvicorn + FastAPI WebSocket | Real-time obousměrná komunikace |
| **Validace** | Pydantic v2 | Striktní typování, validace dat |
| **Auth** | Bcrypt + Sessions | Bezpečné hashing hesel |
| **Logging** | JSONL + Python logging | Strukturované logy pro analýzu |

---

## 🏗️ Architektura systému

### Komunikační model

```
┌─────────────────┐                 ┌─────────────────┐
│  Komisař (PWA)  │◄───WebSocket───►│  FastAPI Server │
│                 │                 │                 │
│  - Leaflet Map  │                 │  - Connection   │
│  - Offline DB   │                 │    Manager      │
│  - Service      │                 │  - Event Logger │
│    Worker       │                 │  - Auth         │
└─────────────────┘                 └─────────────────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │  data/        │
                                    │  - pins.json  │
                                    │  - logs/*.jsonl│
                                    └───────────────┘
```

### Message Flow

```
1. Komisař klikne "NEHODA" →
2. WebSocket odešle JSON zprávu →
3. Server validuje (Pydantic) →
4. Event logger zaznamená do JSONL →
5. ConnectionManager broadcastuje:
   - Critical → VŠEM
   - Normal → jen vedení
6. Vedení obdrží notifikaci + UI se zbarví červeně
```

---

## 🔐 Autentizace a bezpečnost

### 2-Tier systém

| Role | Metoda | Implementace |
|------|--------|--------------|
| **Vedení RZ** | Username + Password | Bcrypt hash, session token (8h) |
| **Komisaři** | PIN kód (4 číslice) | Vázaný na STANICI, ne člověka |

### 🔑 PIN per Station (Klíčový koncept)

**Architektonické rozhodnutí:**
> **PIN je vázaný na STANICI, ne na člověka!**

#### Příklad workflow:

**1. Před rally (Příprava):**
```
Vedoucí vytvoří stanici TK-01 "Zatáčka u lesa"
→ Systém auto-generuje PIN: 1234
→ Vedoucí přiřadí: Jan Novák → TK-01
→ SMS na Jana: "Váš PIN pro TK-01: 1234"
```

**2. Den rally (Změna obsazení):**
```
Jan onemocní v 12:00
→ Vedoucí v admin panelu: Změnit obsazení TK-01
→ Nový člověk: Petr Nový
→ PIN zůstává STEJNÝ: 1234 ✅
→ Petr používá PIN 1234 pro stanici TK-01
```

**3. Historie:**
```
Stanice TK-01 (PIN: 1234):
├─ Jan Novák    (08:00 - 12:00)
└─ Petr Nový    (12:00 - 16:00)
```

#### ✅ Výhody tohoto přístupu:

- 🔒 **Stabilní PINy** - TK-01 má vždy PIN 1234 (i přes roky)
- 🔄 **Snadná výměna** - Změna člověka bez resetování PINu
- 📱 **Předem rozeslat SMS** - Už víš čísla stanic před rally
- 📊 **Centrální správa** - "Stanice obsazená/volná/offline"
- ⏱️ **Vícedenní rally** - Den 1: Jan, Den 2: Petr (stejný PIN)

### Bezpečnostní opatření

- ✅ Bcrypt hashing pro hesla vedení (12 rounds)
- ✅ Session tokeny s expirací (8 hodin)
- ✅ PIN validace při každém WebSocket připojení
- ✅ Perzistence PINů v `data/pins.json` (přežije restart)
- ✅ Event logging všech autentizačních pokusů

---

## 💚 Vitality monitoring

### Parametry sledování

| Parametr | Význam | Akce |
|----------|--------|------|
| `created_at` | Čas vzniku události v mobilu komisaře | Zdroj pravdy pro bezpečnost |
| `received_at` | Čas doručení na server | Výpočet latence |
| `heartbeat` | Ping každých 30 sekund | Detekce offline stavu |
| `latency` | `received_at - created_at` | Varování při > 60s |

### Logika detekce stavu

```python
# Heartbeat timeout
if (now - last_heartbeat) > 120s:
    status = "OFFLINE"  # Ikona na mapě zešedne

# Latence varování
if (received_at - created_at) > 60s:
    alert = f"⚠️ ZPRÁVA ZPOŽDĚNA O {latency} MIN"
```

### Vizualizace na mapě

| Barva | Stav | Popis |
|-------|------|-------|
| 🟢 Zelená | Online + OK | Heartbeat < 2 min, RZ běží |
| 🟡 Žlutá | Online + Varování | Latence > 60s nebo incident |
| 🔴 Červená | Critical incident | STOP RZ aktivní |
| ⚪ Šedá | Offline | Bez heartbeatu > 2 min |

---

## 🎨 UI/UX koncept

### Mobile-First design

**Principy:**
- 📱 **Dotykové ovládání** - velká tlačítka (min 44x44px)
- 🗺️ **Dominance mapy** - Mapa zabírá 80-100% plochy
- 🎯 **FAB pattern** - Jediné plovoucí tlačítko pro hlavní akce
- ⚡ **Okamžitá zpětná vazba** - Vizuální potvrzení každé akce
- 🌐 **Offline indikátor** - Jasný status spojení

### Barvy stavů RZ

| Barva | Hex | Použití | UI změna |
|-------|-----|---------|----------|
| 🟢 **Zelená** | `#22C55E` | RZ běží normálně | Standardní header |
| 🟡 **Žlutá** | `#EAB308` | Varování na trati | Žluté záhlaví |
| 🔴 **Červená** | `#EF4444` | STOP RZ / Nehoda | Celá app červená, vibrace |
| ⚪ **Šedá** | `#9CA3AF` | Offline / Nedostupné | Šedá ikona na mapě |

### FAB (Floating Action Button)

```
┌────────────────────────────────┐
│         🗺️ MAPA                │
│                                │
│    [Marker]    [Marker]        │
│                                │
│         [Marker]               │
│                        ┌─────┐ │
│                        │ 🚨  │ │ ← FAB
│                        │     │ │   (60x60px)
└────────────────────────┴─────┴─┘
```

**Klik na FAB → Modal s velkými tlačítky:**
```
┌──────────────────────────────┐
│  Nahlásit událost            │
├──────────────────────────────┤
│  ⛑️  NEHODA (Critical)       │
├──────────────────────────────┤
│  ⚠️  DIVÁCI V NEBEZPEČÍ      │
├──────────────────────────────┤
│  ✅  STANOVIŠTĚ OK           │
├──────────────────────────────┤
│  💬  Jiné (text)             │
└──────────────────────────────┘
```

---

## 🚀 Budoucí rozšíření

### Fáze 8-10 (Plánované)

- 📡 **Telemetry integrace**
  - Napojení na GPS trackery ve vozech
  - Automatická detekce zastavení vozu
  - Real-time tracking posádek

- 📸 **Multimedia podpora**
  - Focení incidentu (async upload)
  - Video záznam z kritických situací
  - Offline fronta pro média

- 📄 **Reporting & Export**
  - Auto-generování PDF reportu po RZ
  - Export událostí pro bezpečnostního delegáta
  - Statistiky a analýzy (časové rozložení, heatmapy)

- 🔔 **Push notifikace**
  - Native push i při zavřené app
  - Kritické zprávy s prioritou
  
- 🌍 **Multi-rally podpora**
  - Správa více závodů najednou
  - Šablony tras a stanic
  - Import/export konfigurace

---

## 📚 Související dokumenty

- [ROADMAP.md](ROADMAP.md) - Detailní plán vývoje (10 fází)
- [STATUS.md](STATUS.md) - Aktuální stav projektu
- [DEVELOPMENT.md](DEVELOPMENT.md) - Coding standards
- [README.md](README.md) - Úvodní dokumentace
- [SETUP.md](SETUP.md) - Návod na instalaci

---

**Verze dokumentu:** 1.1  
**Poslední aktualizace:** 12. července 2026