Technická specifikace projektu: RALLY Safety App

Tento dokument shrnuje koncept a architekturu progresivní webové aplikace (PWA) pro koordinaci traťových komisařů a vedení RZ (Rychlostní zkoušky) během rally soutěží.

1. Cíl aplikace

Zajistit v reálném čase přehled o situaci na trati, poloze a stavu jednotlivých stanovišť a umožnit okamžitou komunikaci mezi komisaři a vedením (Start/Cíl) s důrazem na bezpečnost, přehlednost a odolnost vůči výpadkům signálu.

2. Klíčové role a funkce

A. Vedení RZ (Start & Cíl)

Globální přehled: Interaktivní mapa s trasou RZ, vytyčenými stanovišti a diváckými zónami.

Monitoring konektivity (Vitality): Vizualizace stáří dat z každého stanoviště. Detekce offline stavu v reálném čase.

Broadcast: Možnost odeslat urgentní hlášení všem stanovištím najednou (např. "STOP RZ - Nebezpečí").

Administrace: Textová komunikace mezi vedoucím (Start) a zástupcem (Cíl) pro potvrzování stavu trati.

B. Traťový komisař (Stanoviště)

Lokalizace: Zobrazení vlastní polohy vůči trase RZ a sousedním stanovištím (přehled o okolí).

Rychlá hlášení: Systém velkých, snadno ovladatelných tlačítek pro okamžité hlášení stavu (Nehoda, Diváci v nebezpečí, Stanoviště připraveno).

Vizuální zpětná vazba: Celá aplikace mění barvu záhlaví podle globálního stavu RZ (zelená = OK, červená = STOP).

3. Technické řešení

Frontend (PWA - Mobile First)

Technologie: HTML5, CSS3, Moderní JavaScript.

Mapové jádro: Leaflet.js / MapLibre (zvoleno pro efektivní práci s vektorovými daty a offline dlaždicemi).

Offline Resilience:

Service Workers: Zajišťují chod aplikace a dostupnost mapových podkladů i bez internetu.

IndexedDB (Outbox): Lokální fronta zpráv. Pokud není signál, hlášení se uloží a čeká na konektivitu.

Background Sync: Automatické odeslání dat na pozadí, jakmile telefon detekuje signál.

Backend (Python)

Framework: FastAPI (vybráno pro asynchronní povahu a vysoký výkon).

Komunikace: WebSockets pro okamžitý obousměrný přenos dat mezi všemi uzly.

Validace: Pydantic modely pro striktní definici datových struktur (zprávy, incidenty, poloha).

4. Logika hlídání času a validity (Vitality)

Parametr

Popis

created_at

Čas vzniku incidentu v mobilu komisaře (zdroj pravdy pro bezpečnost).

received_at

Čas, kdy zpráva skutečně dorazila na server.

Heartbeat

Každých 30s posílá mobil "ping". Pokud chybí > 2 minuty, ikona na mapě zešedne (Offline).

Latence

Pokud received_at - created_at > 60s, vedení uvidí varování: "ZPRÁVA ZPOŽDĚNA O X MIN".

5. Navržená struktura projektu (Modulární)

rally-safety-app/
├── backend/                # FastAPI aplikace
│   ├── main.py             # Vstupní bod
│   ├── api/                # REST a WebSocket endpointy
│   ├── core/               # Konfigurace, Auth, WebSocket Manager
│   ├── models/             # Pydantic schémata (datové struktury)
│   └── services/           # Logika synchronizace a výpočty latence
├── frontend/               # PWA (Static files)
│   ├── index.html          # Hlavní mapové rozhraní
│   ├── js/                 # Logika mapy, API klient, Offline manager
│   ├── css/                # Responzivní design pro mobilní zařízení
│   └── service-worker.js   # Strategie pro offline cache a sync
└── data/                   # Definice tratí (GPX / GeoJSON)


6. UI/UX Koncept

Dominance mapy: Mapa zabírá 100 % plochy, ovládací prvky jsou průhledné nebo vysouvací.

FAB (Floating Action Button): Jediné výrazné tlačítko v rohu pro vyvolání menu hlášení. Minimalizuje nechtěné kliknutí a šetří místo.

Barvy stavů:

Zelená: Závod probíhá (standardní stav).

Žlutá: Varování na trati (zpomalení).

Červená: RZ zastavena (okamžitá akce).

Šedá: Stanoviště nedostupné (ztráta signálu).

7. Budoucí rozšiřitelnost

Telemetry Integration: Napojení na GPS trackery přímo ve vozech pro automatickou detekci zastavení vozu.

Multimedia: Možnost pořídit a odeslat fotografii incidentu (asynchronně, až signál dovolí).

Reporting: Automatické generování PDF reportu o průběhu RZ pro bezpečnostního delegáta po skončení závodu.