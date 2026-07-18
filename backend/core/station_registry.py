"""Station-centric registry built on top of persistent PIN storage."""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
import unicodedata

from backend.core.auth import auth_manager
from backend.models.station import AssignedUser, StationAccess, StationAssignmentRequest, StationCreateRequest, StationType
from backend.models.user import UserRole


class StationRegistry:
    """Provides station-first access and mutation helpers for admin flows."""

    STATION_TEMPLATE_PATH = Path("data/station-coordinates.json")
    MAP_ELEMENTS_TEMPLATE_PATH = Path("data/example-map-elements.geojson")
    RESERVED_VEDENI_STATION_IDS = {"VRZ", "ZVRZ", "VBRZ", "ZVBRZ"}

    def _is_vedeni_station(self, station_id: str) -> bool:
        """Return true when station is one of reserved leadership positions."""
        return str(station_id or "").strip().upper() in self.RESERVED_VEDENI_STATION_IDS

    def _validate_station_role(self, station_id: str, role: UserRole) -> None:
        """Validate allowed role for station-specific constraints.

        Args:
            station_id: Station identifier being assigned.
            role: Requested assigned role.

        Raises:
            ValueError: If role is not allowed for the station.
        """
        if not self._is_vedeni_station(station_id):
            return

        if role not in {UserRole.VEDOUCI, UserRole.ZASTUPCE}:
            raise ValueError(
                f"Station '{station_id}' je vyhrazena vedení RZ (role vedouci nebo zastupce)."
            )

    def _infer_station_type(self, station_id: str, fallback: str | None) -> StationType:
        """Infer station type from stored value or station identifier prefix.

        Args:
            station_id: Station identifier such as TK-01.
            fallback: Optional stored station type value.

        Returns:
            Best-effort station type.
        """
        if fallback:
            try:
                return StationType(fallback)
            except ValueError:
                pass

        prefix = station_id.split("-", 1)[0].upper()
        mapping = {
            "TK": StationType.TRACK_POINT,
            "ZT": StationType.CORNER,
            "CS": StationType.TIMING,
            "PK": StationType.PARKING,
            "ZD": StationType.MEDICAL,
            "TC": StationType.TECHNICAL,
            "SF": StationType.START_FINISH,
        }
        return mapping.get(prefix, StationType.OTHER)

    def _map_assigned_user(self, history_entry) -> AssignedUser:
        """Convert assignment history entry to station API model.

        Args:
            history_entry: Stored assignment history record.

        Returns:
            Station API assignment record.
        """
        return AssignedUser(
            name=history_entry.name,
            role=history_entry.role,
            phone=history_entry.phone,
            email=history_entry.email,
            address=history_entry.address,
            group=history_entry.group,
            assigned_at=history_entry.assigned_at,
            assigned_until=history_entry.assigned_until,
            is_active=history_entry.is_active,
            note=history_entry.note,
        )

    def _clean_text(self, value: object) -> str:
        """Normalize one text value.

        Args:
            value: Raw source value.

        Returns:
            Trimmed text with collapsed whitespace.
        """
        if value is None:
            return ""
        return " ".join(str(value).split())

    def _slugify(self, value: str) -> str:
        """Convert one label to filesystem-safe uppercase slug.

        Args:
            value: Input label.

        Returns:
            ASCII slug with underscore separators.
        """
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
        slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_only).strip("_")
        return slug.upper() or "MAP_POINT"

    def _strip_html(self, value: str) -> str:
        """Strip basic HTML tags from imported notes.

        Args:
            value: Raw note text that may include HTML tags.

        Returns:
            Plain text without tags.
        """
        text = unescape(value)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        lines = [self._clean_text(line) for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _infer_map_control_type(self, name: str, note: str) -> str:
        """Infer station type for map control points.

        Args:
            name: Map control name.
            note: Plain text note.

        Returns:
            Suggested station type string.
        """
        haystack = f"{name} {note}".lower()
        if "park" in haystack:
            return "parking"
        if "start" in haystack or "cil" in haystack or "cíl" in haystack:
            return "start_finish"
        if "zdrav" in haystack:
            return "medical"
        return "other"

    def _load_map_control_templates(self) -> list[dict[str, str | int | float]]:
        """Load additional station templates from map control points.

        Returns:
            Template records derived from commissioner map elements.
        """
        if not self.MAP_ELEMENTS_TEMPLATE_PATH.exists():
            return []

        payload = json.loads(self.MAP_ELEMENTS_TEMPLATE_PATH.read_text(encoding="utf-8"))
        raw_features = payload.get("features", []) if isinstance(payload, dict) else []
        if not isinstance(raw_features, list):
            return []

        templates: list[dict[str, str | int | float]] = []
        seen_ids: set[str] = set()

        for feature in raw_features:
            if not isinstance(feature, dict):
                continue

            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            if not isinstance(properties, dict) or not isinstance(geometry, dict):
                continue

            geometry_type = str(geometry.get("type", "")).strip()
            if geometry_type != "Point":
                continue

            kind = str(properties.get("kind", "")).strip().lower()
            layer_kind = str(properties.get("source_layer_kind", "")).strip().lower()
            if not (kind == "commissioner" or layer_kind == "marshal_control"):
                continue

            coordinates = geometry.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) < 2:
                continue

            longitude = coordinates[0]
            latitude = coordinates[1]
            if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
                continue

            station_name = self._clean_text(
                properties.get("position_name")
                or properties.get("name")
                or properties.get("element_id")
                or "Map point"
            )

            station_id = station_name[:50]
            if station_id in seen_ids:
                base = station_name[:44]
                suffix = 2
                while f"{base} ({suffix})" in seen_ids:
                    suffix += 1
                station_id = f"{base} ({suffix})"
            seen_ids.add(station_id)

            note = self._strip_html(self._clean_text(properties.get("note")))
            station_type = self._infer_map_control_type(station_name, note)
            description = "Auto-generated from map control points"
            if note:
                description = f"{description}: {note}"

            templates.append(
                {
                    "csv_code": f"MAP:{self._slugify(station_name)}",
                    "station_id": station_id,
                    "station_name": station_name,
                    "suggested_role": "komisar_trat",
                    "suggested_station_type": station_type,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "description": description,
                }
            )

        return templates

    def _to_station_access(self, station_access) -> StationAccess:
        """Convert persisted PIN record to station-centric response model.

        Args:
            station_access: Stored PIN record.

        Returns:
            Station-centric API model.
        """
        history = [self._map_assigned_user(item) for item in station_access.assignment_history]
        current_user = next((item for item in history if item.is_active), None)
        station_id = station_access.station_id or station_access.pin_code
        station_name = station_access.station_name or station_id
        return StationAccess(
            pin_code=station_access.pin_code,
            station_id=station_id,
            station_name=station_name,
            station_type=self._infer_station_type(station_id, station_access.station_type),
            capacity=station_access.station_capacity,
            description=station_access.station_description,
            current_user=current_user,
            assigned_users=history,
            created_at=station_access.created_at,
        )

    def _load_station_templates(self) -> list[dict[str, str | int | float]]:
        """Load predefined station templates generated from map source data.

        Returns:
            Deduplicated station template records keyed by station_id.
        """
        raw_templates: list[dict[str, str | int | float]] = []
        if self.STATION_TEMPLATE_PATH.exists():
            payload = json.loads(self.STATION_TEMPLATE_PATH.read_text(encoding="utf-8"))
            csv_templates = payload.get("stations", [])
            if isinstance(csv_templates, list):
                raw_templates.extend(item for item in csv_templates if isinstance(item, dict))

        raw_templates.extend(self._load_map_control_templates())

        deduplicated: dict[str, dict[str, str | int | float]] = {}
        for item in raw_templates:
            station_id = str(item.get("station_id", "")).strip()
            if not station_id:
                continue
            if station_id not in deduplicated:
                deduplicated[station_id] = item

        return list(deduplicated.values())

    def list_stations(self) -> list[StationAccess]:
        """Return all persisted station PINs as station-centric records.

        Returns:
            Sorted station list.
        """
        stations = [self._to_station_access(item) for item in auth_manager.list_all_pins()]
        return sorted(stations, key=lambda item: item.station_id)

    def get_station(self, station_id: str) -> StationAccess | None:
        """Return one station by identifier.

        Args:
            station_id: Requested station identifier.

        Returns:
            Station record or None if unknown.
        """
        record = auth_manager.find_pin_by_station_id(station_id)
        if record is None:
            return None
        return self._to_station_access(record)

    def assign_user(self, station_id: str, request: StationAssignmentRequest) -> StationAccess:
        """Assign or reassign a person on an existing station PIN.

        Args:
            station_id: Station identifier to update.
            request: Assignment payload.

        Returns:
            Updated station record.

        Raises:
            KeyError: If the station does not exist.
        """
        self._validate_station_role(station_id, request.role)

        record = auth_manager.assign_user_to_station(
            station_id=station_id,
            name=request.name,
            role=request.role,
            phone=request.phone,
            email=request.email,
            address=request.address,
            group=request.group,
            note=request.note,
        )
        return self._to_station_access(record)

    def release_user(self, station_id: str, note: str | None = None) -> StationAccess:
        """Release current assignee from station PIN.

        Args:
            station_id: Station identifier to update.
            note: Optional operator note.

        Returns:
            Updated station record with no active current user.

        Raises:
            KeyError: If the station does not exist.
            ValueError: If no current assignment exists.
        """
        record = auth_manager.release_user_from_station(station_id=station_id, note=note)
        return self._to_station_access(record)

    def get_station_history(self, station_id: str) -> list[AssignedUser]:
        """Return assignment history for one station.

        Args:
            station_id: Requested station identifier.

        Returns:
            Assignment history ordered as stored.

        Raises:
            KeyError: If the station does not exist.
        """
        station = self.get_station(station_id)
        if station is None:
            raise KeyError(f"Unknown station '{station_id}'")
        return station.assigned_users

    def create_station(self, request: StationCreateRequest) -> StationAccess:
        """Create new station-bound PIN with initial assignee.

        Args:
            request: Station creation payload.

        Returns:
            Created station record.

        Raises:
            ValueError: If the station already exists.
        """
        self._validate_station_role(request.station_id, request.role)

        record = auth_manager.create_station_pin(
            station_id=request.station_id,
            station_name=request.station_name,
            station_type=request.station_type.value,
            capacity=request.capacity,
            description=request.description,
            assignee_name=request.name,
            assignee_role=request.role,
            assignee_phone=request.phone,
            assignee_email=request.email,
            assignee_address=request.address,
            assignee_group=request.group,
            note=request.note,
        )
        return self._to_station_access(record)

    def regenerate_station_pin(self, station_id: str) -> tuple[str, StationAccess]:
        """Regenerate PIN code for one existing station.

        Args:
            station_id: Station identifier whose PIN should be rotated.

        Returns:
            Tuple of previous PIN and updated station record.

        Raises:
            KeyError: If the station does not exist.
        """
        old_pin, record = auth_manager.regenerate_station_pin(station_id)
        return old_pin, self._to_station_access(record)

    def bulk_generate_station_pins_from_map(self, regenerate_existing: bool = False) -> dict[str, int]:
        """Create missing station PINs from map templates and optionally rotate existing ones.

        Args:
            regenerate_existing: When True, rotate PIN for already existing stations.

        Returns:
            Summary counters for created/regenerated/skipped stations.
        """
        templates = self._load_station_templates()
        created = 0
        regenerated = 0
        skipped = 0

        for item in templates:
            station_id = str(item.get("station_id", "")).strip()
            if not station_id:
                continue

            existing = auth_manager.find_pin_by_station_id(station_id)
            if existing is not None:
                if regenerate_existing:
                    auth_manager.regenerate_station_pin(station_id)
                    regenerated += 1
                else:
                    skipped += 1
                continue

            station_name = str(item.get("station_name", station_id)).strip() or station_id
            station_type = str(item.get("suggested_station_type", "other")).strip() or "other"
            description = str(
                item.get("description")
                or "Auto-generated from map station templates"
            ).strip()
            auth_manager.create_station_pin_unassigned(
                station_id=station_id,
                station_name=station_name,
                station_type=station_type,
                capacity=1,
                description=description,
            )
            created += 1

        return {
            "templates_total": len(templates),
            "created": created,
            "regenerated": regenerated,
            "skipped": skipped,
        }

    def delete_station(self, station_id: str) -> StationAccess:
        """Delete station-bound PIN.

        Args:
            station_id: Station identifier to delete.

        Returns:
            Removed station record.

        Raises:
            KeyError: If the station does not exist.
        """
        record = auth_manager.remove_station_pin(station_id)
        return self._to_station_access(record)


station_registry = StationRegistry()