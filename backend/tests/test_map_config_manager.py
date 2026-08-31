"""Unit tests for MapConfigManager persistence and mutation logic."""

from pathlib import Path

from backend.core.map_config import MapConfigManager


def test_default_config_is_empty(tmp_path: Path) -> None:
    """A fresh manager with no existing file should start with empty config."""
    manager = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))

    config = manager.get_config()

    assert config.track_geojson_url == ""
    assert config.station_coordinates == {}
    assert config.version == 0


def test_set_track_source_persists_and_increments_version(tmp_path: Path) -> None:
    """Setting the track source should persist across manager restarts."""
    storage_file = str(tmp_path / "map_config.json")
    manager = MapConfigManager(storage_file=storage_file)

    updated = manager.set_track_source("/data/rz-hostalkova-track.geojson")

    assert updated.track_geojson_url == "/data/rz-hostalkova-track.geojson"
    assert updated.version == 1

    reloaded = MapConfigManager(storage_file=storage_file)
    assert reloaded.get_config().track_geojson_url == "/data/rz-hostalkova-track.geojson"
    assert reloaded.get_config().version == 1


def test_set_station_coordinate_persists_and_increments_version(tmp_path: Path) -> None:
    """Setting a station coordinate should persist and bump version."""
    storage_file = str(tmp_path / "map_config.json")
    manager = MapConfigManager(storage_file=storage_file)

    updated = manager.set_station_coordinate("TK-01", 49.2088, 16.5792)

    assert updated.station_coordinates["TK-01"] == (49.2088, 16.5792)
    assert updated.version == 1

    reloaded = MapConfigManager(storage_file=storage_file)
    assert reloaded.get_config().station_coordinates["TK-01"] == (49.2088, 16.5792)


def test_multiple_station_coordinates_accumulate(tmp_path: Path) -> None:
    """Setting coordinates for different stations should not overwrite each other."""
    manager = MapConfigManager(storage_file=str(tmp_path / "map_config.json"))

    manager.set_station_coordinate("TK-01", 49.2088, 16.5792)
    updated = manager.set_station_coordinate("TK-02", 49.1936, 16.6241)

    assert updated.station_coordinates["TK-01"] == (49.2088, 16.5792)
    assert updated.station_coordinates["TK-02"] == (49.1936, 16.6241)
    assert updated.version == 2
