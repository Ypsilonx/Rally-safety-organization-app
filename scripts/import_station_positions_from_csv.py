"""Import station positions and suggested station mapping from CSV export.

The source CSV may contain unescaped commas in phone/address fields. This
script reads the stable columns (`WKT`, `P.č.`) and exports two outputs:
- coordinate aliases for frontend marker placement
- normalized station list with suggested role and station type
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

INPUT_PATH = Path("data/RZ Hošťálková FINAL- 1_Tabulka pozic se jmény a tel.xlsx.csv")
OUTPUT_PATH = Path("data/station-coordinates.json")

POINT_RE = re.compile(r'^"POINT \((?P<lon>-?\d+(?:\.\d+)?) (?P<lat>-?\d+(?:\.\d+)?)\)"')


@dataclass(frozen=True)
class StationMapping:
    """Normalized station mapping derived from one CSV position row.

    Attributes:
        csv_code: Original value from `P.č.` column.
        station_id: Canonical station identifier for backend usage.
        station_name: Human-readable default station label.
        suggested_role: Suggested user role for assignment.
        suggested_station_type: Suggested station type for station create API.
        latitude: Station latitude.
        longitude: Station longitude.
    """

    csv_code: str
    station_id: str
    station_name: str
    suggested_role: str
    suggested_station_type: str
    latitude: float
    longitude: float


def _clean_text(value: str | None) -> str:
    """Normalize one raw text value.

    Args:
        value: Raw text.

    Returns:
        Trimmed and whitespace-collapsed text.
    """
    if not value:
        return ""
    return " ".join(str(value).split())


def _aliases_for_code(code: str) -> list[str]:
    """Build station-id aliases for one CSV position code.

    Args:
        code: Raw `P.č.` value from CSV.

    Returns:
        List of station-id aliases that may be used in the app.
    """
    normalized = _clean_text(code)
    aliases = [normalized]

    digits_only = normalized.replace("*", "")
    if digits_only.isdigit():
        aliases.append(f"TK-{int(digits_only):02d}")

    upper = normalized.upper()
    if upper.startswith("RB-"):
        aliases.append(upper)
    if upper in {"VRZ", "VBRZ", "ZVBRZ", "ZVRZ", "RF1", "RF2"}:
        aliases.append(upper)

    # Deduplicate while preserving order.
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _canonical_station_id(code: str) -> str:
    """Build canonical station identifier from CSV position code.

    Args:
        code: Raw `P.č.` value.

    Returns:
        Canonical station ID suitable for backend station registry.
    """
    normalized = _clean_text(code)
    digits_only = normalized.replace("*", "")
    if digits_only.isdigit():
        suffix = "A" if normalized.endswith("*") else ""
        return f"TK-{int(digits_only):02d}{suffix}"
    return normalized.upper()


def _station_profile(code: str) -> tuple[str, str, str]:
    """Resolve default station profile from CSV position code.

    Args:
        code: Raw `P.č.` value.

    Returns:
        Tuple (station_name, suggested_role, suggested_station_type).
    """
    station_id = _canonical_station_id(code)

    if station_id == "VRZ":
        return "Vedoucí RZ", "vedouci", "start_finish"

    if station_id in {"VBRZ", "ZVBRZ", "ZVRZ"}:
        return "Zástupce vedoucího RZ", "zastupce", "start_finish"

    if station_id.startswith("RF"):
        return f"Rozhodčí faktu {station_id}", "casomer", "timing"

    if station_id.startswith("RB-"):
        return f"Radiobod {station_id}", "technik", "technical"

    if station_id.startswith("TK-"):
        return f"Traťový bod {station_id}", "komisar_trat", "track_point"

    return f"Pozice {station_id}", "komisar_trat", "other"


def _mapping_from_code(code: str, lat: float, lon: float) -> StationMapping:
    """Create normalized station mapping from parsed CSV row.

    Args:
        code: Raw `P.č.` value.
        lat: Latitude.
        lon: Longitude.

    Returns:
        Structured station mapping.
    """
    station_id = _canonical_station_id(code)
    station_name, suggested_role, suggested_station_type = _station_profile(code)
    return StationMapping(
        csv_code=_clean_text(code),
        station_id=station_id,
        station_name=station_name,
        suggested_role=suggested_role,
        suggested_station_type=suggested_station_type,
        latitude=lat,
        longitude=lon,
    )


def _parse_line(line: str) -> tuple[str, float, float] | None:
    """Extract one position code with coordinates from a CSV row.

    Args:
        line: Raw CSV line.

    Returns:
        Tuple (`code`, `lat`, `lon`) or None for unsupported rows.
    """
    text = line.strip()
    if not text or text.startswith("WKT,"):
        return None

    match = POINT_RE.match(text)
    if not match:
        return None

    lon = float(match.group("lon"))
    lat = float(match.group("lat"))

    parts = text.split(",", 4)
    if len(parts) < 4:
        return None

    code = _clean_text(parts[3])
    if not code:
        return None

    return code, lat, lon


def main() -> None:
    """Read the CSV export and write station coordinate aliases."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_PATH}")

    coordinates: dict[str, list[float]] = {}
    stations: list[dict[str, object]] = []
    processed_rows = 0

    for raw_line in INPUT_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_line(raw_line)
        if parsed is None:
            continue

        code, lat, lon = parsed
        processed_rows += 1
        for alias in _aliases_for_code(code):
            coordinates[alias] = [lat, lon]

        mapping = _mapping_from_code(code, lat, lon)
        stations.append(
            {
                "csv_code": mapping.csv_code,
                "station_id": mapping.station_id,
                "station_name": mapping.station_name,
                "suggested_role": mapping.suggested_role,
                "suggested_station_type": mapping.suggested_station_type,
                "latitude": mapping.latitude,
                "longitude": mapping.longitude,
            }
        )

    stations.sort(key=lambda item: item["station_id"])

    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "source_file": str(INPUT_PATH).replace("\\", "/"),
        "processed_rows": processed_rows,
        "coordinates": coordinates,
        "stations": stations,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(coordinates)} station coordinate aliases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()