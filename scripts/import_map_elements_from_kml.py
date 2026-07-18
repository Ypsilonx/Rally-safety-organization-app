"""Import map elements and track data from the Google My Maps KML export.

The source KML contains both people and map objects. This script keeps only
non-person placemarks for `data/example-map-elements.geojson` and also exports
the main rally route to `data/example-track.geojson`.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

KML_URL = "https://www.google.com/maps/d/kml?forcekml=1&mid=15D0UVrvdZUOqNkA1rCilK7sM8FAYlLWz"
OUTPUT_PATH = Path("data/example-map-elements.geojson")
TRACK_OUTPUT_PATH = Path("data/example-track.geojson")
NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}

LAYER_KIND_ALIASES = {
    "trasa": "track",
    "divaci": "spectator",
    "divacke misto": "spectator",
    "zakazane pruchody": "closure",
    "dulezita mista a funkce": "critical",
    "zakazy lidi a sg3": "marshal_control",
}


def _clean_text(value: str | None) -> str:
    """Normalize text extracted from KML for stable GeoJSON output.

    Args:
        value: Raw text from the source XML.

    Returns:
        Trimmed text with collapsed whitespace.
    """
    if not value:
        return ""
    return " ".join(str(value).split())


def _normalize_key(value: str | None) -> str:
    """Normalize text for stable matching independent of diacritics/case.

    Args:
        value: Raw source text.

    Returns:
        Lowercase ascii-like key with compact whitespace.
    """
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = stripped.lower()
    return " ".join(lowered.split())


def _local_name(element: ET.Element) -> str:
    """Return XML local tag name without namespace prefix.

    Args:
        element: XML element.

    Returns:
        Namespace-free tag name.
    """
    return element.tag.rsplit("}", 1)[-1]


def _extended_data(placemark: ET.Element) -> dict[str, str]:
    """Collect ExtendedData entries for one placemark.

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
    """Return True when the placemark represents a person entry.

    Args:
        data: ExtendedData payload.

    Returns:
        True when the placemark contains person name fields.
    """
    first_name = _clean_text(data.get("Jméno"))
    last_name = _clean_text(data.get("Příjmení"))
    return bool(first_name or last_name)


def _iter_placemarks_with_layers(node: ET.Element, layer_stack: list[str] | None = None) -> list[tuple[ET.Element, list[str]]]:
    """Traverse KML tree and return placemarks with their folder stack.

    Args:
        node: Current XML node.
        layer_stack: Parent folder names.

    Returns:
        List of placemarks paired with folder path.
    """
    stack = list(layer_stack or [])
    result: list[tuple[ET.Element, list[str]]] = []

    for child in list(node):
        tag = _local_name(child)
        if tag == "Folder":
            folder_name = _clean_text(child.findtext("kml:name", default="", namespaces=NAMESPACE))
            result.extend(_iter_placemarks_with_layers(child, [*stack, folder_name]))
        elif tag == "Placemark":
            result.append((child, stack))
        elif tag == "Document":
            result.extend(_iter_placemarks_with_layers(child, stack))

    return result


def _resolve_layer_kind(layer_stack: list[str]) -> str | None:
    """Resolve source layer classification using robust normalized aliases.

    Args:
        layer_stack: Folder hierarchy from KML.

    Returns:
        Internal layer kind or None when no alias matches.
    """
    candidates = [_normalize_key(layer) for layer in layer_stack if layer]
    joined = " / ".join(candidates)

    for alias, kind in LAYER_KIND_ALIASES.items():
        if alias in joined:
            return kind
    return None


def _infer_kind(name: str, description: str, geometry_type: str, layer_kind: str | None) -> str:
    """Infer a frontend-friendly element kind from KML text.

    Args:
        name: Placemark name.
        description: Placemark description or label text.
        geometry_type: KML geometry type.

    Returns:
        Symbolic element kind used by the frontend.
    """
    if layer_kind == "spectator":
        return "spectator"
    if layer_kind == "closure":
        return "closure"
    if layer_kind == "marshal_control":
        return "commissioner"

    text = f"{name} {description}".lower()

    keyword_map = [
        ("start", "start"),
        ("cíl", "finish"),
        ("finish", "finish"),
        ("časom", "timing"),
        ("timing", "timing"),
        ("zdravot", "medical"),
        ("hasič", "fire"),
        ("spectator", "spectator"),
        ("diváck", "spectator"),
        ("divack", "spectator"),
        ("retard", "retarder"),
        ("zpomal", "retarder"),
        ("uzav", "closure"),
        ("zákaz", "closure"),
        ("zakaz", "closure"),
        ("průchod", "closure"),
        ("pruchod", "closure"),
        ("radiobod", "commissioner"),
    ]

    for keyword, kind in keyword_map:
        if keyword in text:
            return kind

    if geometry_type == "LineString":
        return "closure" if any(word in text for word in ("páska", "zábrana", "zakaz", "zákaz")) else "spectator"

    if geometry_type == "Polygon":
        return "closure"

    if layer_kind == "critical":
        return "commissioner"

    return "element"


def _geometry_to_geojson(placemark: ET.Element) -> dict[str, object] | None:
    """Convert one KML geometry to GeoJSON geometry.

    Args:
        placemark: KML placemark element.

    Returns:
        GeoJSON geometry dict or None when the geometry is unsupported.
    """
    point = placemark.find(".//kml:Point", NAMESPACE)
    if point is not None:
        coordinates = _coordinates_to_point(point.findtext("kml:coordinates", default="", namespaces=NAMESPACE))
        if coordinates:
            return {"type": "Point", "coordinates": coordinates}

    line = placemark.find(".//kml:LineString", NAMESPACE)
    if line is not None:
        coordinates = _coordinates_to_line(line.findtext("kml:coordinates", default="", namespaces=NAMESPACE))
        if coordinates:
            return {"type": "LineString", "coordinates": coordinates}

    polygon = placemark.find(".//kml:Polygon", NAMESPACE)
    if polygon is not None:
        coordinates = _coordinates_to_polygon(polygon)
        if coordinates:
            return {"type": "Polygon", "coordinates": coordinates}

    return None


def _coordinates_to_point(raw: str) -> list[float] | None:
    """Convert raw KML point coordinates to GeoJSON order.

    Args:
        raw: KML coordinates string.

    Returns:
        [lon, lat] pair or None.
    """
    text = _clean_text(raw)
    if not text:
        return None

    first = text.split()[0]
    parts = first.split(",")
    if len(parts) < 2:
        return None
    return [float(parts[0]), float(parts[1])]


def _coordinates_to_line(raw: str) -> list[list[float]] | None:
    """Convert raw KML line coordinates to GeoJSON order.

    Args:
        raw: KML coordinates string.

    Returns:
        List of [lon, lat] coordinates or None.
    """
    coordinates: list[list[float]] = []
    for chunk in _clean_text(raw).split():
        parts = chunk.split(",")
        if len(parts) < 2:
            continue
        coordinates.append([float(parts[0]), float(parts[1])])
    return coordinates or None


def _coordinates_to_polygon(polygon: ET.Element) -> list[list[list[float]]] | None:
    """Convert a KML polygon outer boundary to GeoJSON coordinates.

    Args:
        polygon: KML Polygon element.

    Returns:
        GeoJSON polygon coordinate array or None.
    """
    ring = polygon.find(".//kml:outerBoundaryIs/kml:LinearRing", NAMESPACE)
    if ring is None:
        return None

    ring_coordinates = _coordinates_to_line(ring.findtext("kml:coordinates", default="", namespaces=NAMESPACE))
    if not ring_coordinates:
        return None
    return [ring_coordinates]


def _should_require_commissioner(kind: str) -> bool:
    """Return whether one feature type should be commissioner-bound.

    Args:
        kind: Final feature kind.

    Returns:
        True when the kind should be tied to commissioner readiness rules.
    """
    return kind in {"start", "finish", "timing", "medical", "fire", "commissioner", "closure"}


def _extract_features(placemarks: list[tuple[ET.Element, list[str]]]) -> list[dict[str, object]]:
    """Convert non-person placemarks into GeoJSON features.

    Args:
        placemarks: Placemark elements with their KML folder stack.

    Returns:
        GeoJSON feature list.
    """
    features: list[dict[str, object]] = []

    for placemark, layer_stack in placemarks:
        name = _clean_text(placemark.findtext("kml:name", default="", namespaces=NAMESPACE))
        description = _clean_text(placemark.findtext("kml:description", default="", namespaces=NAMESPACE))
        data = _extended_data(placemark)
        if _is_person_record(data):
            continue

        layer_kind = _resolve_layer_kind(layer_stack)
        if layer_kind == "track":
            # Route data is exported separately to example-track.geojson.
            continue

        geometry = _geometry_to_geojson(placemark)
        if geometry is None:
            continue

        kind = _infer_kind(name, description, str(geometry["type"]), layer_kind)
        requires_commissioner = _should_require_commissioner(kind)

        properties = {
            "element_id": name or data.get("id") or "unknown",
            "name": name or data.get("Popis") or "Prvek trati",
            "position_name": name or data.get("Popis") or "neuvedeno",
            "contact_name": None,
            "contact_phone": None,
            "kind": kind,
            "requires_commissioner": requires_commissioner,
            "commissioner_rule": "ready_before_rz" if requires_commissioner else None,
            "note": description or data.get("Popis") or data.get("Poznámky") or None,
            "source_name": name or None,
            "source_style_url": _clean_text(placemark.findtext("kml:styleUrl", default="", namespaces=NAMESPACE)) or None,
            "source_layer": " / ".join(layer_stack) if layer_stack else None,
            "source_layer_kind": layer_kind or "unknown",
        }

        for key, value in data.items():
            if key not in {"Jméno", "Příjmení"} and value:
                safe_key = key.lower().replace(" ", "_").replace(".", "").replace("(", "").replace(")", "")
                properties[f"kml_{safe_key}"] = value

        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": geometry,
        })

    return features


def _export_track(placemarks: list[tuple[ET.Element, list[str]]]) -> dict[str, object]:
    """Export the best candidate track LineString from layer-classified placemarks.

    Args:
        placemarks: Placemark elements with their KML folder stack.

    Returns:
        GeoJSON FeatureCollection containing one route line when available.
    """
    best_line: list[list[float]] | None = None

    for placemark, layer_stack in placemarks:
        layer_kind = _resolve_layer_kind(layer_stack)
        if layer_kind != "track":
            continue

        line = placemark.find(".//kml:LineString", NAMESPACE)
        if line is None:
            continue

        coordinates = _coordinates_to_line(line.findtext("kml:coordinates", default="", namespaces=NAMESPACE))
        if not coordinates:
            continue

        if best_line is None or len(coordinates) > len(best_line):
            best_line = coordinates

    features: list[dict[str, object]] = []
    if best_line:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": "RZ Track from Google My Maps",
                    "source": "kml-layer-trasa",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": best_line,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main() -> None:
    """Download KML and write the GeoJSON map element dataset."""
    root = ET.fromstring(urlopen(KML_URL, timeout=30).read())
    placemarks = _iter_placemarks_with_layers(root)
    features = _extract_features(placemarks)
    track_geojson = _export_track(placemarks)

    payload = {
        "type": "FeatureCollection",
        "features": features,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    TRACK_OUTPUT_PATH.write_text(json.dumps(track_geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(features)} map elements to {OUTPUT_PATH}")
    print(f"Wrote {len(track_geojson['features'])} track features to {TRACK_OUTPUT_PATH}")


if __name__ == '__main__':
    main()