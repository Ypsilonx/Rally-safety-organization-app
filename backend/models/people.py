"""People catalog models used by setup import and assignment flows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CatalogPerson(BaseModel):
    """One reusable person entry for pre-race assignment.

    Attributes:
        name: Person display name.
        phone: Optional phone number.
    """

    name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)


class CsvImportError(BaseModel):
    """Validation error for one CSV row.

    Attributes:
        row: 1-based CSV row index including header line.
        reason: Validation error description.
    """

    row: int = Field(..., ge=2)
    reason: str


class PeopleImportResult(BaseModel):
    """Summary of one CSV import run.

    Attributes:
        imported: Number of newly created people records.
        updated: Number of updated records (replace mode).
        skipped: Number of skipped rows (typically duplicates).
        total_people: Catalog size after import.
        errors: Row-level validation errors.
    """

    imported: int = 0
    updated: int = 0
    skipped: int = 0
    total_people: int = 0
    errors: list[CsvImportError] = Field(default_factory=list)


class PeopleCsvImportRequest(BaseModel):
    """Request payload for CSV text import endpoint.

    Attributes:
        csv_content: Raw CSV data including header.
        replace_existing: When true, rows matching by person name overwrite existing entries.
    """

    csv_content: str = Field(..., min_length=1)
    replace_existing: bool = False
