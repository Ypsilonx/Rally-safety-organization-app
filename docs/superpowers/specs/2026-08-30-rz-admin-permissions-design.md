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
3. **Vedení nemá kde vidět PIN, jakmile ztratí Setup obrazovku.** PIN se
   dnes zobrazuje jen na Setup obrazovce (ADMIN-only po této změně) -
   vedení ho ale potřebuje znát i operativně (např. nadiktovat komisaři
   po telefonu), takže potřebuje nové, čistě informativní místo.

## Cíle

- ADMIN = jediná role, která smí přiřazovat/přeřazovat osoby na jakoukoliv
  pozici (běžnou i vedení), spravovat katalog lidí, měnit název RZ, mazat
  historii komunikace a konfigurovat mapu. Nemá vlastní pozici na mapě.
- VRZ/ZVRZ/VBRZ/ZVBRZ mají operační dashboard (chat, incident handling,
  RZ stop/hold/resume) a nově i vlastní potvrzení READY - ale ztrácí
  přístup na Setup obrazovku a admin API.
- PIN zůstává čitelný pro ADMINa i vedení (mapový popup), měnit ho ale
  smí jen ADMIN ze Setup obrazovky (regenerace je vázaná na přiřazení
  osoby, což je mutační ADMIN-only akce).

## Mimo scope (vědomě odloženo)

- Konfigurovatelný počet pozic vedení / více ADMIN účtů - uživatel to
  zmínil jako možnou budoucí potřebu, ne aktuální požadavek. Řešení níže
  na to nezavírá dveře (permission check je podle role, ne podle
  hardcoded seznamu usernames), ale nic navíc se nestaví teď.
- Úklid testovacích dat smíchaných v `data/` - uživatel to výslovně odložil
  na později.

## Navazující kola (samostatné brainstormingy, mimo tento dokument)

Při zpětné vazbě k tomuto návrhu vyplynuly další 3 nezávislé kusy práce,
které se **nebudují v rámci tohoto designu** - dostanou vlastní
brainstorming/spec, až na ně dojde řada:

- **B) Kompletní správa pozic v UI** - `create-pin`/`delete pin` endpointy
  na backendu existují, ale Setup obrazovka k nim nemá formulář/tlačítko;
  chybí i endpoint pro editaci metadat existující pozice (název, typ,
  kapacita) bez zásahu do přiřazení osoby.
- **C) Upload mapových podkladů přes web** - dnes se cesta k
  track/elements/station-template souborům jen ručně vypisuje do textového
  pole a soubor musí už ležet na serveru; chybí skutečný upload + validace
  formátu.
- **D) Návody** - co má obsahovat mapový podklad a odkud ho vzít, jak
  připravit CSV se seznamem osob.

Pořadí po dokončení tohoto designu: B → C → D.

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

### 5. PIN je vidět v mapovém popupu pro ADMIN i vedení

Revize po zpětné vazbě: PIN nemá z UI zmizet, ale vedení ztrácí Setup
obrazovku (jediné dnešní místo, kde PIN vidí) - potřebuje tedy nové místo.

**Bezpečnostní zjištění při návrhu:** `/api/stations/status` (odkud
`map-stations.js` bere data pro popup) nemá žádnou autentizaci - je to
existující stav (`backend/api/status.py` nemá na žádném route
`Depends()`), ne něco, co zavádí tento design. Nejde do něj proto přidat
`pin_code` - zpřístupnilo by to PIN kterékoliv stanice komukoliv bez
přihlášení. Ostatní pole, co tam dnes jsou (telefon/e-mail/adresa),
zůstávají veřejná jako dnes - to je samostatný bezpečnostní dluh mimo
scope tohoto designu (zapsat do `STATUS.md`, neřešit teď).

Řešení: nový endpoint `GET /api/stations/pins` v `status.py`, gated novou
funkcí `require_vedeni_or_admin` (role `vedouci`/`zastupce`/`admin`,
stejný `X-Session-Token` mechanismus jako `require_admin`), vrací
`{station_id: pin_code}` pro všechny stanice. Komisaři (auth přes PIN, ne
session token) touto branou neprojdou.

`map-stations.js::refreshStationMarkers()` - pro `isVedeniUser()` (admin i
vedení) doplní druhý fetch na `/api/stations/pins` vedle stávajícího
`/api/stations/status`, výsledek domerguje do dat před stavbou popupu.
Komisaři tento druhý fetch vůbec nevolají. `buildStationPopup()` dostane
navíc řádek s PIN kódem, jen když je v datech přítomný.

`map-stations.js` dnes nemá referenci na `App`/session token (na rozdíl
od `setup-admin.js`, který dostává `app` jako parametr) - bude muset číst
`window.App.user?.role` a `window.App.user?.session_token` přímo, stejně
jako jiné standalone moduly přistupují k `window.SetupAdminModule` apod.

Setup obrazovka (ADMIN-only) PIN zobrazuje beze změny jako dosud, včetně
tlačítka "Regenerovat PIN" - to zůstává výhradně u ADMINa, protože je to
mutační akce svázaná s přiřazením osoby.

## Testování

- `backend/tests/test_admin_people_api.py` - přepnout `_admin_headers()`
  na `UserRole.ADMIN`, přidat test, že session s `UserRole.VEDOUCI` dostane
  na admin endpoint 403 (dnes by prošla).
- `GET /api/stations/pins` - test bez tokenu vrátí 401, s PIN komisaře
  místo session tokenu vrátí 401 (`verify_session` PIN neuzná), s vedeni/
  admin session tokenem vrátí `{station_id: pin_code}` mapu.
- Manuální průchod v prohlížeči (jako u předchozích oprav, na fiktivních
  datech): admin vidí Setup a nevidí ho vedouci/zastupce; vedouci/zastupce
  vidí a mohou odeslat tlačítko Připraveno; mapový popup u libovolné
  stanice (včetně VRZ/ZVRZ/VBRZ/ZVBRZ) ukazuje PIN jen přihlášenému
  admin/vedení uživateli, ne komisaři.
- End-to-end ověření readiness gate: aktivovat incident mode (poslat
  `message_type: incident`), ověřit že `can_resume()` vrátí VRZ v
  `missing_stations`, poslat READY za VRZ, ověřit že zmizí ze seznamu.
