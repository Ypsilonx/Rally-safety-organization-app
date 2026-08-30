# Design: Oddělení role ADMIN od vedení RZ + READY gate pro vedení

**Datum:** 30.8.2026
**Stav:** Návrh ke schválení uživatelem

## Kontext

Aktuální stav (před touto změnou) má tři problémy zjištěné při testování:

1. **Oprávnění nejsou oddělená.** `require_vedeni` v `backend/api/admin.py`
   pouští role `vedouci`, `zastupce` i `admin` na úplně stejná práva —
   přiřazování osob na pozice, mazání/regenerace PINů, změna názvu RZ,
   reset historie komunikace, import katalogu lidí. Neexistuje způsob, jak
   dát tyhle pravomoci výhradně ADMINovi.
2. **Vedení (VRZ/ZVRZ/VBRZ/ZVBRZ) nemá jak potvrdit READY.** Po opravě
   vitality trackingu (viz `STATUS.md`, commit `97c71c9`) se vedení nově
   zapojuje do `operations_state` readiness gate stejně jako komisaři na
   trati — ale frontend jim nedává žádné tlačítko k potvrzení, takže po
   libovolném incidentu by `rz_resume` byl natrvalo blokovaný bez
   `force_resume`.
3. **PIN u pozic vedení je matoucí mrtvá váha.** `VRZ`/`ZVRZ`/`VBRZ`/`ZVBRZ`
   mají v `pins.json` PIN záznam, ačkoliv se přes něj nikdy nedá přihlásit
   (`auth.py::verify_pin` je pro tyto 4 station_id blokuje). Setup
   obrazovka i mapový popup ho přesto ukazují a nabízí "Regenerovat PIN".

## Cíle

- ADMIN = jediná role, která smí přiřazovat/přeřazovat osoby na jakoukoliv
  pozici (běžnou i vedení), spravovat katalog lidí, měnit název RZ, mazat
  historii komunikace a konfigurovat mapu. Nemá vlastní pozici na mapě.
- VRZ/ZVRZ/VBRZ/ZVBRZ mají operační dashboard (chat, incident handling,
  RZ stop/hold/resume) a nově i vlastní potvrzení READY - ale ztrácí
  přístup na Setup obrazovku a admin API.
- PIN zmizí z UI pro pozice vedení (zůstává jako neviditelný interní detail
  úložiště - žádná migrace dat).

## Mimo scope (vědomě odloženo)

- Zásah do datového modelu `pins.json`/`StationAccess.pin_code` (varianta
  B z brainstormingu) - PIN zůstává interně beze změny, jen se přestane
  zobrazovat a nabízet.
- Konfigurovatelný počet pozic vedení / více ADMIN účtů - uživatel to
  zmínil jako možnou budoucí potřebu, ne aktuální požadavek. Řešení níže
  na to nezavírá dveře (permission check je podle role, ne podle
  hardcoded seznamu usernames), ale nic navíc se nestaví teď.
- Úklid testovacích dat smíchaných v `data/` - uživatel to výslovně odložil
  na později.

## Architektura

### 1. Backend: `require_admin` místo `require_vedeni`

`backend/api/admin.py` - funkce `require_vedeni` (dnes řádek 49) se
přejmenuje na `require_admin` a zúží allowlist rolí z
`{"vedouci", "zastupce", "admin"}` na `{"admin"}`. Všech 11 endpointů v
routeru (`Depends(require_vedeni)` → `Depends(require_admin)`) tím
automaticky zpřísní bez nutnosti měnit každý zvlášť.

Dopad na testy: `backend/tests/test_admin_people_api.py::_admin_headers()`
dnes vytváří session s `UserRole.VEDOUCI` a nazývá to "admin headers" -
po změně musí použít `UserRole.ADMIN`, jinak testy začnou padat na 401.

### 2. Frontend: nová `isAdminUser()` vedle `isVedeniUser()`

`frontend/js/app-operations-rz.js` dostane novou funkci vedle stávající
`isVedeniUser()`:

```js
isAdminUser(app) {
    return app.user?.role === 'admin';
},
```

`App.isAdminUser()` (v `app.js`, analogicky ke stávající
`App.isVedeniUser()`) deleguje na ni.

`frontend/js/setup-admin.js` - všech 7 dnešních `if (!app.isVedeniUser())`
guard (řádky 311, 347, 380, 420, 460, 634, 1066) se přepne na
`!app.isAdminUser()`. Tlačítko `#open-setup-btn` (viditelnost řízená v
`app.js::setupUI()`) se řídí `isAdminUser()` místo `isVedeniUser()`.

`isVedeniUser()` (vedouci/zastupce/admin) zůstává beze změny všude jinde -
řídí viditelnost `#admin-panel` (live dashboard), incident gate UI a
resume/stop/hold ovládání, které má ADMIN nadále vidět stejně jako vedení.

### 3. Výchozí obrazovka podle role

`App.init()` po `setupUI()` (frontend/js/app.js) - pokud
`this.isAdminUser()`, zavolá rovnou
`window.SetupAdminModule.openSetupScreen(this)` místo ponechání uživatele
na `app-screen`. Existující tlačítka `#back-to-dashboard-btn` (v hlavičce
Setupu) a `#open-setup-btn` (na dashboardu) fungují beze změny oběma
směry, takže ADMIN se může kdykoliv přepnout na živou mapu zkontrolovat
konfiguraci.

### 4. READY potvrzení pro vedení

Nové tlačítko "Připraveno" v `#admin-panel` (frontend/index.html, sekce
`.admin-actions` vedle stávajícího `#btn-broadcast`), viditelné jen pro
`isVedeniUser() && !isAdminUser()` (tj. vedouci/zastupce, ne admin - ten
nemá `station_id`, takže ho `operations_state` vůbec neeviduje).

Handler v novém `bindLeadershipReadyButton()` (`app-operations-rz.js`)
odešle stejnou zprávu jako dnešní komisařská quick-action:

```js
window.wsClient.sendMessage({
    message_type: 'status_update',
    readiness_state: 'ready',
    content: '✅ Vedení připraveno',
    created_at: new Date().toISOString(),
});
```

Žádná změna na backendu není potřeba - `_process_message` v
`websocket.py` už `readiness_state` zpracovává univerzálně pro
jakéhokoliv odesílatele se `station_id` (což vedení má od včerejší
opravy).

### 5. PIN zmizí z UI pro pozice vedení

`frontend/js/setup-admin.js::renderSelectedAdminStation()` a
`renderAdminStationList()` - podmíněně skryjí `station-pin-badge` a
tlačítko "Regenerovat PIN" (`regenerateSelectedStationPin`), když
`isVedeniStation(station.station_id)` (helper už existuje, řádek 14-16).
Totéž pro mapový popup v `map-stations.js::buildStationPopup()`.

Datový model (`pins.json`, `StationAccess.pin_code`) se nemění - žádná
migrace, žádné riziko pro existující reálná data.

## Testování

- `backend/tests/test_admin_people_api.py` - přepnout `_admin_headers()`
  na `UserRole.ADMIN`, přidat test, že session s `UserRole.VEDOUCI` dostane
  na admin endpoint 403 (dnes by prošla).
- Manuální průchod v prohlížeči (jako u předchozích oprav, na fiktivních
  datech): admin vidí Setup a nevidí ho vedouci/zastupce; vedouci/zastupce
  vidí a mohou odeslat tlačítko Připraveno; PIN badge/tlačítko zmizí u
  VRZ/ZVRZ/VBRZ/ZVBRZ v setup listu i mapovém popupu, u běžných stanic
  zůstává.
- End-to-end ověření readiness gate: aktivovat incident mode (poslat
  `message_type: incident`), ověřit že `can_resume()` vrátí VRZ v
  `missing_stations`, poslat READY za VRZ, ověřit že zmizí ze seznamu.
