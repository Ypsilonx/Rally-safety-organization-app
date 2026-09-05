"""Integrační testy pro rate limiting na loginových endpointech."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import auth as auth_module
from backend.core.auth import AuthManager
from backend.core.rate_limiter import LoginRateLimiter
from backend.main import app
from backend.models.user import UserRole


def _isolated_auth_manager(tmp_path: Path) -> AuthManager:
    """Vytvoří izolovaný AuthManager, který se nedotkne data/pins.json.

    Args:
        tmp_path: Pytest dočasný adresář.

    Returns:
        Čerstvý AuthManager s jednou testovací stanicí.
    """
    manager = AuthManager(pins_file=str(tmp_path / "pins.json"))
    manager.generate_pin(name="Test Komisar", role=UserRole.KOMISAR_TRAT, station_id="TK-01")
    return manager


def _patch_rate_limiter(monkeypatch, **kwargs) -> LoginRateLimiter:
    """Nahradí sdílený rate limiter čerstvou instancí s danými parametry.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        kwargs: Parametry předané konstruktoru LoginRateLimiter.

    Returns:
        Nově nasazená instance limiteru.
    """
    limiter = LoginRateLimiter(**kwargs)
    monkeypatch.setattr(auth_module, "login_rate_limiter", limiter)
    return limiter


@pytest.mark.asyncio
async def test_login_komisar_locks_after_repeated_failures(monkeypatch, tmp_path: Path) -> None:
    """Opakované neplatné PINy ze stejné IP vedou k 429 po překročení limitu."""
    monkeypatch.setattr(auth_module, "auth_manager", _isolated_auth_manager(tmp_path))
    _patch_rate_limiter(monkeypatch, max_attempts=3, window_seconds=60, lockout_seconds=60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for _ in range(3):
            response = await client.post("/api/auth/login-komisar", json={"pin_code": "00000000"})
            assert response.status_code == 401

        locked_response = await client.post("/api/auth/login-komisar", json={"pin_code": "00000000"})

    assert locked_response.status_code == 429


@pytest.mark.asyncio
async def test_login_komisar_success_is_not_blocked_and_resets_counter(monkeypatch, tmp_path: Path) -> None:
    """Platný PIN projde i po pár předchozích neúspěších a vynuluje počítadlo."""
    manager = _isolated_auth_manager(tmp_path)
    pin_code = next(iter(manager.komisar_pins))
    monkeypatch.setattr(auth_module, "auth_manager", manager)
    _patch_rate_limiter(monkeypatch, max_attempts=3, window_seconds=60, lockout_seconds=60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        await client.post("/api/auth/login-komisar", json={"pin_code": "00000000"})
        success = await client.post("/api/auth/login-komisar", json={"pin_code": pin_code})

    assert success.status_code == 200


@pytest.mark.asyncio
async def test_login_vedeni_locks_after_repeated_failures(monkeypatch, tmp_path: Path) -> None:
    """Opakovaně špatné heslo pro vedení vede k 429 po překročení limitu."""
    monkeypatch.setattr(auth_module, "auth_manager", _isolated_auth_manager(tmp_path))
    _patch_rate_limiter(monkeypatch, max_attempts=3, window_seconds=60, lockout_seconds=60)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for _ in range(3):
            response = await client.post(
                "/api/auth/login-vedeni", json={"username": "VRZ", "password": "wrong-pass"}
            )
            assert response.status_code == 401

        locked_response = await client.post(
            "/api/auth/login-vedeni", json={"username": "VRZ", "password": "wrong-pass"}
        )

    assert locked_response.status_code == 429
