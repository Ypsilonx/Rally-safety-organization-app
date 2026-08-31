"""Persistentní konfigurace mapy (podklad trati + souřadnice pozic)
sdílená mezi backend API, frontendem a WebSocket live sync."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.core.atomic_write import atomic_write_text


class MapConfig(BaseModel):
    """Perzistentní mapová konfigurace sdílená všemi klienty.

    Attributes:
        track_geojson_url: Volitelná cesta/URL na GeoJSON podklad trati.
        station_coordinates: Souřadnice stanic přepsané adminem,
            station_id -> (lat, lon).
        version: Monotónní verze inkrementovaná při každé změně (pohání
            live sync přes WebSocket).
        updated_at: Časové razítko poslední změny.
    """

    track_geojson_url: str = ""
    station_coordinates: dict[str, tuple[float, float]] = Field(default_factory=dict)
    version: int = Field(default=0, ge=0)
    updated_at: str | None = None


class MapConfigManager:
    """Načítá, ukládá a mutuje mapovou konfiguraci v lokálním JSON úložišti.

    Validace vstupu (rozsah souřadnic apod.) je záměrně mimo tuto třídu -
    patří na hranici systému (Pydantic request model v `backend/api/admin.py`),
    stejně jako u `AuthManager`/`StationRegistry`.
    """

    def __init__(self, storage_file: str = "data/map_config.json") -> None:
        """Inicializuje manager a načte aktuální konfiguraci.

        Args:
            storage_file: Cesta k JSON souboru pro perzistenci.
        """
        self.storage_path = Path(storage_file)
        self.storage_path.parent.mkdir(exist_ok=True)
        self._config = self._load()

    def _load(self) -> MapConfig:
        """Načte konfiguraci ze souboru, nebo vytvoří výchozí.

        Returns:
            Načtená konfigurace, nebo výchozí prázdná při chybějícím/
            poškozeném souboru.
        """
        if not self.storage_path.exists():
            config = MapConfig(updated_at=datetime.now(UTC).isoformat())
            self._save(config)
            return config

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return MapConfig.model_validate(payload)
        except Exception:
            config = MapConfig(updated_at=datetime.now(UTC).isoformat())
            self._save(config)
            return config

    def _save(self, config: MapConfig) -> None:
        """Zapíše konfiguraci atomicky na disk.

        Args:
            config: Konfigurace k zápisu.
        """
        atomic_write_text(
            self.storage_path,
            json.dumps(config.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )

    def get_config(self) -> MapConfig:
        """Vrátí aktuální konfiguraci z paměti.

        Returns:
            Aktuální mapová konfigurace.
        """
        return self._config

    def set_track_source(self, url: str) -> MapConfig:
        """Nastaví URL/cestu GeoJSON podkladu trati.

        Args:
            url: Nová cesta/URL k podkladu trati (prázdný řetězec =
                návrat na výchozí zabudovaný podklad).

        Returns:
            Aktualizovaná konfigurace.
        """
        self._config.track_geojson_url = str(url or "").strip()
        self._config.version += 1
        self._config.updated_at = datetime.now(UTC).isoformat()
        self._save(self._config)
        return self._config

    def set_station_coordinate(self, station_id: str, latitude: float, longitude: float) -> MapConfig:
        """Nastaví/přepíše souřadnici jedné stanice.

        Args:
            station_id: Identifikátor stanice - nemusí existovat v
                station_registry, souřadnice je čistě mapová vrstva.
            latitude: Zeměpisná šířka.
            longitude: Zeměpisná délka.

        Returns:
            Aktualizovaná konfigurace.
        """
        self._config.station_coordinates[station_id] = (latitude, longitude)
        self._config.version += 1
        self._config.updated_at = datetime.now(UTC).isoformat()
        self._save(self._config)
        return self._config


map_config_manager = MapConfigManager()
