"""Unit tests for people catalog CSV import service."""

from pathlib import Path

from backend.core.people_catalog import PeopleCatalog


def test_import_csv_supports_semicolon_and_basic_aliases(tmp_path: Path) -> None:
    """CSV import should parse semicolon input and alias headers."""
    catalog = PeopleCatalog(storage_file=str(tmp_path / "people.json"))

    result = catalog.import_csv(
        "jmeno;telefon\n"
        "Jan Novák;+420111222333\n"
        "Eva Testovací;+420444555666\n"
    )

    assert result.imported == 2
    assert result.updated == 0
    assert result.skipped == 0
    assert result.total_people == 2
    assert result.errors == []

    people = catalog.list_people()
    assert people[0].name == "Eva Testovací"
    assert people[1].name == "Jan Novák"
    assert people[1].phone == "+420111222333"


def test_import_csv_reports_invalid_rows(tmp_path: Path) -> None:
    """Invalid rows should be skipped with row-level validation errors."""
    catalog = PeopleCatalog(storage_file=str(tmp_path / "people.json"))

    result = catalog.import_csv(
        "name,phone\n"
        ",+420111222333\n"
        "Alena Korektni,+420777888999\n"
    )

    assert result.imported == 1
    assert result.total_people == 1
    assert len(result.errors) == 1
    assert result.errors[0].row == 2
    assert "name/jmeno" in result.errors[0].reason


def test_import_csv_replace_existing_updates_person(tmp_path: Path) -> None:
    """Replace mode should overwrite existing person matched by name."""
    catalog = PeopleCatalog(storage_file=str(tmp_path / "people.json"))
    catalog.import_csv("name,phone\nJan Novak,+420111222333\n")

    result = catalog.import_csv(
        "name,phone\nJan Novak,+420999888777\n",
        replace_existing=True,
    )

    assert result.imported == 0
    assert result.updated == 1
    assert result.skipped == 0
    assert result.total_people == 1

    person = catalog.list_people()[0]
    assert person.phone == "+420999888777"
