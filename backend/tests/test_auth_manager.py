"""Unit tests for authentication manager behavior."""

import json
from pathlib import Path

import bcrypt

from backend.core.auth import AuthManager, hash_password
from backend.models.user import UserRole


def test_generate_pin_is_persistent(tmp_path: Path) -> None:
    """Generated PIN should be valid and survive manager restart."""
    pins_file = tmp_path / "pins.json"
    manager = AuthManager(pins_file=str(pins_file))

    created = manager.generate_pin(
        name="Test Komisar",
        role=UserRole.KOMISAR_TRAT,
        station_id="TK-01",
    )

    verified = manager.verify_pin(created.pin_code)
    assert verified is not None
    assert len(created.pin_code) == 8
    assert created.pin_code.isdigit()
    assert verified.name == "Test Komisar"
    assert verified.station_id == "TK-01"

    reloaded_manager = AuthManager(pins_file=str(pins_file))
    reloaded = reloaded_manager.verify_pin(created.pin_code)
    assert reloaded is not None
    assert reloaded.name == "Test Komisar"
    assert reloaded.role == UserRole.KOMISAR_TRAT


def test_hash_password_returns_bcrypt_hash() -> None:
    """Password hashing should produce value verifiable by bcrypt."""
    plain = "demo-secret-123"

    hashed = hash_password(plain)

    assert hashed != plain
    assert bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def test_assign_user_to_station_updates_history_and_persists(tmp_path: Path) -> None:
    """Reassignment should preserve PIN and append assignment history."""
    pins_file = tmp_path / "pins.json"
    initial_payload = {
        "1234": {
            "name": "Jan Testovací",
            "role": "komisar_trat",
            "phone": "+420123456789",
            "station_id": "TK-01",
            "station_name": "Traťový bod 01",
            "created_at": "2026-02-15T15:00:00+00:00",
        }
    }
    pins_file.write_text(json.dumps(initial_payload, ensure_ascii=False), encoding="utf-8")

    manager = AuthManager(pins_file=str(pins_file))
    updated = manager.assign_user_to_station(
        station_id="TK-01",
        name="Petr Nový",
        role=UserRole.KOMISAR_ZATACKA,
        phone="+420111222333",
        note="Střídání směny",
    )

    assert updated.pin_code == "1234"
    assert updated.name == "Petr Nový"
    assert updated.role == UserRole.KOMISAR_ZATACKA
    assert len(updated.assignment_history) == 2
    assert updated.assignment_history[0].is_active is False
    assert updated.assignment_history[1].is_active is True
    assert updated.assignment_history[1].note == "Střídání směny"

    reloaded = AuthManager(pins_file=str(pins_file)).verify_pin("1234")
    assert reloaded is not None
    assert reloaded.name == "Petr Nový"
    assert len(reloaded.assignment_history) == 2
    assert reloaded.assignment_history[0].assigned_until is not None
    assert reloaded.assignment_history[1].name == "Petr Nový"


def test_release_user_from_station_disables_pin_until_reassigned(tmp_path: Path) -> None:
    """Released station PIN should reject login until a new assignee is added."""
    pins_file = tmp_path / "pins.json"
    initial_payload = {
        "1234": {
            "name": "Jan Testovací",
            "role": "komisar_trat",
            "phone": "+420123456789",
            "station_id": "TK-01",
            "created_at": "2026-02-15T15:00:00+00:00",
        }
    }
    pins_file.write_text(json.dumps(initial_payload, ensure_ascii=False), encoding="utf-8")

    manager = AuthManager(pins_file=str(pins_file))
    released = manager.release_user_from_station("TK-01", note="Konec směny")

    assert all(entry.is_active is False for entry in released.assignment_history)
    assert released.assignment_history[0].assigned_until is not None
    assert released.assignment_history[0].note == "Konec směny"
    assert manager.verify_pin("1234") is None

    reloaded = AuthManager(pins_file=str(pins_file))
    assert reloaded.verify_pin("1234") is None

    reassigned = reloaded.assign_user_to_station(
        station_id="TK-01",
        name="Petr Nový",
        role=UserRole.KOMISAR_TRAT,
        phone="+420111222333",
        note="Nová směna",
    )
    assert reloaded.verify_pin("1234") is not None
    assert reassigned.assignment_history[-1].is_active is True


def test_create_and_delete_station_pin_persists(tmp_path: Path) -> None:
    """Creating and deleting a station PIN should persist by station identifier."""
    pins_file = tmp_path / "pins.json"
    manager = AuthManager(pins_file=str(pins_file))

    created = manager.create_station_pin(
        station_id="PK-10",
        station_name="Parkoviště 10",
        station_type="parking",
        capacity=2,
        description="Příjezdové parkoviště",
        assignee_name="Alena Testovací",
        assignee_role=UserRole.PARKOVANI,
        assignee_phone="+420555444333",
        note="První osazení",
    )

    assert created.station_id == "PK-10"
    assert created.station_name == "Parkoviště 10"
    assert created.station_type == "parking"
    assert created.station_capacity == 2
    assert manager.verify_pin(created.pin_code) is not None

    reloaded = AuthManager(pins_file=str(pins_file))
    assert reloaded.find_pin_by_station_id("PK-10") is not None

    removed = reloaded.remove_station_pin("PK-10")
    assert removed.pin_code == created.pin_code
    assert reloaded.find_pin_by_station_id("PK-10") is None
    assert reloaded.verify_pin(created.pin_code) is None

    final_reload = AuthManager(pins_file=str(pins_file))
    assert final_reload.find_pin_by_station_id("PK-10") is None


def test_create_unassigned_station_pin_requires_assignment_for_login(tmp_path: Path) -> None:
    """Station PIN without assignee should stay inactive until assignment is added."""
    pins_file = tmp_path / "pins.json"
    manager = AuthManager(pins_file=str(pins_file))

    created = manager.create_station_pin_unassigned(
        station_id="TK-01",
        station_name="Traťový bod 01",
        station_type="track_point",
        capacity=1,
        description="Auto-generated",
    )

    assert created.station_id == "TK-01"
    assert created.assignment_history == []
    assert manager.verify_pin(created.pin_code) is None

    assigned = manager.assign_user_to_station(
        station_id="TK-01",
        name="Petr Nový",
        role=UserRole.KOMISAR_TRAT,
        phone="+420111222333",
    )

    assert manager.verify_pin(created.pin_code) is not None
    assert assigned.assignment_history[-1].is_active is True


def test_regenerate_station_pin_keeps_station_binding(tmp_path: Path) -> None:
    """Regenerated station PIN should keep station identity and current assignment."""
    pins_file = tmp_path / "pins.json"
    manager = AuthManager(pins_file=str(pins_file))
    created = manager.create_station_pin(
        station_id="TK-22",
        station_name="Traťový bod 22",
        station_type="track_point",
        capacity=1,
        description="",
        assignee_name="Alena Testovací",
        assignee_role=UserRole.KOMISAR_TRAT,
        assignee_phone="+420555444333",
    )
    original_pin = created.pin_code

    old_pin, updated = manager.regenerate_station_pin("TK-22")

    assert old_pin == original_pin
    assert updated.station_id == "TK-22"
    assert updated.pin_code != old_pin
    assert len(updated.pin_code) == 8
    assert manager.verify_pin(old_pin) is None
    assert manager.verify_pin(updated.pin_code) is not None
