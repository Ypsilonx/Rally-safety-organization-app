"""Unit tests for authentication manager behavior."""

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
