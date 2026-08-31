# Design: Perzistentní mapová konfigurace + live sync

**Datum:** 31.8.2026
**Stav:** Návrh ke schválení uživatelem

## Kontext

Uživatel chce před nadcházející RZ (RZ Hošťálková) upravovat pozice na
mapě pro lepší přehlednost - měnit souřadnice existujících stanic,
ideálně kliknutím do mapy, a mít to hned vidět u všech připojených, ne
až po restartu/reloadu.

Zjištění při průzkumu kódu: dnešní "Uložit souřadnice pozice" a "Použít
podklad trati" na Setup obrazovce (`setup-admin.js`) ukládají **jen do
`localStorage` prohlížeče admina** (`storeMapConfig()`/
`readStoredMapConfig()`). Žádný backend endpoint pro zápis mapové
konfigurace neexistuje - `data/station-coordinates.json` je jen
statický soubor, který `station_registry.py` čte jako šablonu a
frontend fetchuje jako jeden z fallback zdrojů. Změna souřadnic dnes
tedy:
- není vidět nikomu jinému (komisaři, ostatní vedení, jiný prohlížeč
  téhož admina),
- nepřežije vyčištění dat prohlížeče.

To je v rozporu s tím, co uživatel od funkce očekává, takže je součástí
tohoto designu přesunout zápis na server - bez toho by "live sync"
neměl co synchronizovat.

## Cíle

- ADMIN může změnit souřadnice existující stanice a zdroj GeoJSON trati
  ze Setup obrazovky; změna se uloží na server a je vidět všem
  klientům (komisaři na mapě, vedení na dashboardu), ne jen jemu.
- Nová souřadnice se dá zadat kliknutím do mapy (vedle dnešního ručního
  zadání lat/lon), bez nutnosti počítat souřadnice ručně.
- Změna se u připojených klientů projeví okamžitě (WebSocket), bez
  15s pollingu nebo manuálního refreshe - i v době, kdy RZ běží.
- Stanice, které nikdo neupravil, fungují úplně stejně jako dnes
  (fallback na statické šablony/výchozí souřadnice) - žádná migrace
  existujících dat není potřeba.

## Mimo scope (vědomě odloženo)

- **Přidávání/mazání pozic z mapy** - backend (`create-pin`/`delete
  pin`) existuje, UI ne. Navazující krok po tomto designu, ne součást.
- **Import konkrétní trati z KML** pro RZ Hošťálková - jednorázová
  datová úloha (stažení Google My Maps KML, převod na GeoJSON), řeší
  se mimo tento spec přímo použitím hotového mechanismu (`POST
  /api/admin/map-config` + existující pole "GeoJSON trať").
- **Multi-RZ/SUPERADMIN** (víc souběžných RZ, každá s vlastním
  adminem) - uživatel to výslovně odložil na později, viz paměťový
  záznam `multi-rz-superadmin-idea`.
- **Live sync pro assign/release/move stanice** - dnešní 15s polling +
  lokální `admin:station-directory-updated` event tam zůstávají beze
  změny. Týkalo by se to jiné datové vrstvy (obsazení, ne souřadnice) a
  není to, co uživatel žádal - nerozšiřovat bez důvodu.

## Architektura

### 1. Backend: `backend/core/map_config.py` (nový modul)

Stejný vzor jako `rz_context.py` - Pydantic model + manager singleton
nad atomicky zapisovaným JSON souborem.

```python
class MapConfig(BaseModel):
    track_geojson_url: str = ""
    station_coordinates: dict[str, tuple[float, float]] = {}
    version: int = 0
    updated_at: str | None = None
```

`MapConfigManager(storage_file="data/map_config.json")`:
- `get_config() -> MapConfig`
- `set_track_source(url: str) -> MapConfig` - inkrementuje `version`
- `set_station_coordinate(station_id: str, lat: float, lon: float) -> MapConfig` -
  validuje rozsah (-90..90 / -180..180, stejně jako dnešní frontend
  kontrola v `saveSelectedSetupStationCoordinate`), merguje do
  `station_coordinates`, inkrementuje `version`

Chybějící/prázdný `data/map_config.json` = výchozí `MapConfig()` -
žádná migrace, appka funguje jako dnes, dokud admin něco neuloží.
`data/map_config.json` přibude do `.gitignore` (per-event data, stejně
jako `pins.json`) + `data/map_config.example.json` šablona do repa.

### 2. API endpointy

`GET /api/stations/map-config` (`backend/api/status.py`) - veřejné,
bez autentizace (souřadnice a URL trati nejsou PII, stejná úroveň jako
`/rz-context`). Volají ho všichni klienti při startu mapy.

`POST /api/admin/map-config` (`backend/api/admin.py`, `require_admin`) -
částečná aktualizace, tělo obsahuje buď `track_geojson_url`, nebo
`station_coordinate: {station_id, latitude, longitude}` (přesně jedno
z obou na request, podobně jako existující jednoúčelové admin
endpointy). Po úspěchu broadcast na všechny klienty (viz níže) a
`event_logger.log_event("admin_action", ...)` stejně jako ostatní admin
mutace.

### 3. Live sync přes WebSocket

Recyklace mechanismu `communication_reset_version` (`rz_context.py` +
`app.js::applyCommunicationResetVersion`), který appka už má a osvědčil
se:

- Broadcast po uložení: `connection_manager.broadcast_to_all()` se
  `system` zprávou obsahující navíc `map_config_version: <nová verze>`
  (stejný tvar payloadu jako u `rz-config`/reset historie).
- `AppMessagingModule.handleMessage` (`app-messaging.js`) - nová
  podmínka vedle stávající `communication_reset_version`: při
  `normalized.map_config_version !== undefined` a vyšší než
  `app.mapConfigVersion` zavolá `window.MapModule.loadServerMapConfig({redraw: true})`.
- `MapModule.init()` - stejná metoda `loadServerMapConfig()` se zavolá
  i při prvním načtení mapy (`redraw: false`, protože `init()` hned po
  ní kreslí trať i markery sám), aby existoval jeden kód pro načtení a
  aplikaci configu, ne dvě kopie.

### 4. Frontend: priorita zdrojů souřadnic

`MapModule.loadServerMapConfig()` fetchne `/api/stations/map-config` a
aplikuje ho **jako první, nejvyšší prioritní vrstvu**, než se spustí
dnešní `loadStationCoordinates()` (statické šablony + commissioner body
z GeoJSON). Aby server konfigurace zůstala prioritní i po doplnění
šablon, merge v `loadStationCoordinates()` se změní z "přepiš vždy" na
"doplň jen chybějící klíče" (stejný princip, jaký už dnes používá vrstva
commissioner-coordinates o pár řádků níž - `if (!this.stationCoordinates[key])`).
Výsledné pořadí priority: server config > statická šablona/URL > commissioner
body z GeoJSON > hardcoded `DEFAULT_STATION_COORDINATES`.

`MapModule.config.trackGeoJsonUrl` se ze server configu nastaví (pokud
je vyplněný) před voláním `loadTrackGeoJson()` v `init()`.

### 5. Frontend: editace na Setup obrazovce

- `saveSelectedSetupStationCoordinate()` (`setup-admin.js`) - místo
  `storeMapConfig()` do localStorage zavolá `POST
  /api/admin/map-config` s `station_coordinate`. Validace rozsahu
  zůstává na frontendu jako dnes (rychlá zpětná vazba), server ji
  opakuje jako hranici systému.
- `applySetupTrackSource()` - stejně, `POST /api/admin/map-config`
  s `track_geojson_url` místo localStorage.
- Nové tlačítko "Vybrat na mapě" vedle polí lat/lon - po zapnutí se
  zaregistruje jednorázový Leaflet `map.once('click', ...)` handler,
  který vyplní `map-station-lat`/`map-station-lon` souřadnicemi
  kliknutého bodu. Uložení zůstává na existujícím tlačítku "Uložit
  souřadnice pozice" - klik na mapu nic tiše neukládá, jen předvyplní
  formulář (konzistentní s tím, že žádná jiná akce v appce se
  neprovádí bez explicitního potvrzení).
- `readStoredMapConfig`/`storeMapConfig`/`getMapConfigStorageKey`
  (localStorage) se ruší - nahrazuje je server. `applyStoredMapConfig()`
  na startu Setup obrazovky se nahrazuje voláním `loadServerMapConfig()`.

## Testování

- `backend/tests/test_map_config_api.py` (nový): `GET` vrací výchozí
  prázdný config; `POST` bez admin session → 401; `POST` s neplatnými
  souřadnicemi (mimo rozsah) → 422/409; `POST` uloží souřadnici a
  inkrementuje `version`; `GET` po `POST` vrací aktualizovaná data;
  broadcast - `connection_manager` nahrazen testovacím dvojníkem
  (stejný vzor jako `test_admin_notifications.py`), ověří se
  `map_config_version` v odeslané zprávě.
- Manuální průchod v prohlížeči: uložení souřadnice na Setup obrazovce
  se projeví na mapě bez reloadu (otevřít dvě session - admin a
  komisař ve druhém okně - ověřit, že se marker u komisaře posune sám,
  bez jeho zásahu); klik do mapy při zapnutém "Vybrat na mapě" vyplní
  lat/lon pole; uložení souřadnice pro neznámé `station_id` (mimo
  aktuální stanice) proběhne bez chyby - souřadnice je čistě mapová
  vrstva nezávislá na existenci PINu.
