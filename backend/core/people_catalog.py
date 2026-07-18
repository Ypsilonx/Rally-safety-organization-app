"""People catalog service for setup imports and assignment prefill."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.models.people import CatalogPerson, CsvImportError, PeopleImportResult


class PeopleCatalog:
    """Persistent people directory used by setup/admin workflows."""

    def __init__(self, storage_file: str = "data/people_catalog.json") -> None:
        """Initialize catalog storage.

        Args:
            storage_file: JSON file path for catalog persistence.
        """
        self.storage_path = Path(storage_file)
        self.storage_path.parent.mkdir(exist_ok=True)
        self._people: list[CatalogPerson] = self._load()

    def _load(self) -> list[CatalogPerson]:
        """Load catalog from JSON storage.

        Returns:
            List of catalog people.
        """
        if not self.storage_path.exists():
            return []

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            records = payload.get("people", []) if isinstance(payload, dict) else []
            return [CatalogPerson.model_validate(item) for item in records]
        except Exception:
            return []

    def _save(self) -> None:
        """Persist current in-memory catalog to JSON file."""
        payload = {
            "updated_at": datetime.now(UTC).isoformat(),
            "people": [person.model_dump(mode="json") for person in self._people],
        }
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_people(self) -> list[CatalogPerson]:
        """Return people sorted by name.

        Returns:
            Sorted people list.
        """
        return sorted(self._people, key=lambda item: item.display_name.lower())

    def _normalize_name_key(self, value: str) -> str:
        """Normalize person name for stable matching.

        Args:
            value: Raw name value.

        Returns:
            Lowercase trimmed key.
        """
        return " ".join(value.strip().split()).lower()

    def _person_key(self, person: CatalogPerson) -> str:
        """Build stable matching key for one person entry.

        Args:
            person: Catalog person entry.

        Returns:
            Normalized display-name key.
        """
        return self._normalize_name_key(person.display_name)

    def _detect_delimiter(self, csv_content: str) -> str:
        """Detect CSV delimiter from sample.

        Args:
            csv_content: Raw CSV text.

        Returns:
            Detected delimiter or a safe fallback.
        """
        sample = csv_content[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            return dialect.delimiter
        except csv.Error:
            return ";" if sample.count(";") > sample.count(",") else ","

    def _column_value(self, row: dict[str, str], keys: tuple[str, ...]) -> str | None:
        """Return first non-empty value by known header aliases.

        Args:
            row: Parsed CSV row.
            keys: Supported header aliases.

        Returns:
            Trimmed value or None.
        """
        lowered = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
        for key in keys:
            value = lowered.get(key)
            if value is None:
                continue
            cleaned = str(value).strip()
            if cleaned:
                return cleaned
        return None

    def import_csv(self, csv_content: str, replace_existing: bool = False) -> PeopleImportResult:
        """Import people from CSV text.

        Supported headers include both Czech and English aliases:
        - first_name / jmeno / name
        - last_name / prijmeni / surname
        - phone / telefon
        - email / e-mail
        - address / bydliste / bydliště
        - group / skupina

        Args:
            csv_content: CSV text including header.
            replace_existing: Replace existing record matched by normalized name.

        Returns:
            Import result with counters and row-level errors.
        """
        result = PeopleImportResult()
        delimiter = self._detect_delimiter(csv_content)
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)

        existing_by_key = {
            self._person_key(person): index
            for index, person in enumerate(self._people)
        }

        for index, row in enumerate(reader, start=2):
            try:
                first_name = self._column_value(row, ("first_name", "jmeno"))
                last_name = self._column_value(row, ("last_name", "prijmeni", "surname"))
                full_name = self._column_value(row, ("name",))

                if full_name and not first_name:
                    parts = " ".join(full_name.split()).split(" ", 1)
                    first_name = parts[0]
                    if len(parts) > 1 and not last_name:
                        last_name = parts[1]

                if first_name and not last_name and " " in first_name:
                    parts = " ".join(first_name.split()).split(" ", 1)
                    first_name = parts[0]
                    if len(parts) > 1:
                        last_name = parts[1]

                if not first_name:
                    raise ValueError("Chybí sloupec first_name/jmeno/name nebo je prázdný")

                phone = self._column_value(row, ("phone", "telefon"))
                email = self._column_value(row, ("email", "e-mail", "mail"))
                address = self._column_value(row, ("address", "bydliste", "bydliště"))
                group = self._column_value(row, ("group", "skupina"))

                person = CatalogPerson(
                    first_name=" ".join(first_name.split()),
                    last_name=" ".join(last_name.split()) if last_name else "",
                    phone=phone,
                    email=email,
                    address=address,
                    group=group,
                )
                key = self._person_key(person)

                existing_index = existing_by_key.get(key)
                if existing_index is not None:
                    if replace_existing:
                        self._people[existing_index] = person
                        result.updated += 1
                    else:
                        result.skipped += 1
                    continue

                self._people.append(person)
                existing_by_key[key] = len(self._people) - 1
                result.imported += 1
            except ValueError as error:
                result.errors.append(CsvImportError(row=index, reason=str(error)))

        if result.imported > 0 or result.updated > 0:
            self._save()

        result.total_people = len(self._people)
        return result


people_catalog = PeopleCatalog()
