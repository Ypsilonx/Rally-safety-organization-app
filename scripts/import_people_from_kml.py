"""Import real people records from the Google My Maps KML export into the local catalog.

The source KML contains both people and map elements. This script keeps only
person-like placemarks and writes them into `data/people_catalog.json` so the
setup dropdown can use real historical rally data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

KML_URL = "https://www.google.com/maps/d/kml?forcekml=1&mid=15D0UVrvdZUOqNkA1rCilK7sM8FAYlLWz"
OUTPUT_PATH = Path("data/people_catalog.json")
NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


def _clean_text(value: str | None) -> str:
    """Normalize text extracted from KML for stable catalog storage.

    Args:
        value: Raw text value from the source XML.

    Returns:
        Trimmed text with collapsed whitespace.
    """
    if not value:
        return ""
    return " ".join(str(value).split())


def _clean_phone(value: str | None) -> str | None:
    """Normalize the phone number formatting used in the source KML.

    Args:
        value: Raw phone text from the source XML.

    Returns:
        Normalized phone number or None when empty.
    """
    cleaned = _clean_text(value).replace(",", "")
    return cleaned or None


def _extended_data(placemark: ET.Element) -> dict[str, str]:
    """Collect KML ExtendedData entries for one placemark.

    Args:
        placemark: KML placemark element.

    Returns:
        Mapping of data field names to cleaned values.
    """
    data: dict[str, str] = {}
    for item in placemark.findall(".//kml:ExtendedData/kml:Data", NAMESPACE):
        key = _clean_text(item.attrib.get("name"))
        value = _clean_text(item.findtext("kml:value", default="", namespaces=NAMESPACE))
        if key:
            data[key] = value
    return data


def _is_person_record(data: dict[str, str]) -> bool:
    """Decide whether a placemark represents a person record.

    Args:
        data: ExtendedData payload from one placemark.

    Returns:
        True when the placemark has a real person name.
    """
    first_name = _clean_text(data.get("Jméno"))
    last_name = _clean_text(data.get("Příjmení"))
    if first_name in {"", "---"} and last_name in {"", "---"}:
        return False
    return True


def _person_key(person: dict[str, str | None]) -> str:
    """Create a stable matching key for one imported person.

    Args:
        person: Normalized person record.

    Returns:
        Lowercase deduplication key.
    """
    first_name = _clean_text(person.get("first_name"))
    last_name = _clean_text(person.get("last_name"))
    return f"{first_name} {last_name}".strip().lower()


def _extract_people(placemarks: Iterable[ET.Element]) -> list[dict[str, str | None]]:
    """Convert person placemarks into catalog rows.

    Args:
        placemarks: KML placemark elements.

    Returns:
        Normalized people records ready for JSON storage.
    """
    people: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for placemark in placemarks:
        data = _extended_data(placemark)
        if not _is_person_record(data):
            continue

        person = {
            "first_name": _clean_text(data.get("Jméno")) or "---",
            "last_name": _clean_text(data.get("Příjmení")) or "",
            "phone": _clean_phone(data.get("Telefón")),
            "email": _clean_text(data.get("E-mail")) or None,
            "address": _clean_text(data.get("Bydliště")) or None,
            "group": _clean_text(data.get("Vedoucí sk.(dohodil)")) or None,
        }

        key = _person_key(person)
        if key in seen:
            continue

        seen.add(key)
        if person["first_name"] == "---" and not person["last_name"]:
            continue
        people.append(person)

    people.sort(key=lambda item: f"{item['last_name'] or ''} {item['first_name'] or ''}".strip().lower())
    return people


def main() -> None:
    """Download the source KML and update the local people catalog."""
    xml_text = urlopen(KML_URL, timeout=30).read().decode("utf-8", errors="replace")
    root = ET.fromstring(xml_text)
    placemarks = root.findall(".//kml:Placemark", NAMESPACE)
    people = _extract_people(placemarks)

    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "people": people,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(people)} people records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()