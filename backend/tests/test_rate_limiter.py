"""Unit testy pro in-memory rate limiter proti brute-force loginu."""

from backend.core.rate_limiter import LoginRateLimiter


class FakeClock:
    """Ovladatelné hodiny pro deterministické testování časových oken."""

    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        """Vrátí aktuální (testovací) čas."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Posune testovací čas o zadaný počet sekund."""
        self._now += seconds


def test_allows_attempts_under_threshold() -> None:
    """Pod hranicí max_attempts by klíč neměl být zamčený."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, lockout_seconds=60)

    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")

    assert not limiter.is_locked("1.2.3.4")


def test_locks_after_reaching_max_attempts() -> None:
    """Po dosažení max_attempts neúspěchů je klíč zamčený."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, lockout_seconds=60)

    for _ in range(3):
        limiter.record_failure("1.2.3.4")

    assert limiter.is_locked("1.2.3.4")


def test_lock_expires_after_lockout_window() -> None:
    """Po uplynutí lockout_seconds se klíč odemkne."""
    clock = FakeClock()
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60, lockout_seconds=30, clock=clock.now)

    limiter.record_failure("1.2.3.4")
    assert limiter.is_locked("1.2.3.4")

    clock.advance(31)
    assert not limiter.is_locked("1.2.3.4")


def test_old_failures_outside_window_do_not_count() -> None:
    """Neúspěchy starší než window_seconds se do limitu nepočítají."""
    clock = FakeClock()
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=10, lockout_seconds=60, clock=clock.now)

    limiter.record_failure("1.2.3.4")
    clock.advance(11)
    limiter.record_failure("1.2.3.4")

    assert not limiter.is_locked("1.2.3.4")


def test_successful_login_clears_failure_count() -> None:
    """Úspěšné přihlášení vynuluje historii neúspěchů daného klíče."""
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60, lockout_seconds=60)

    limiter.record_failure("1.2.3.4")
    limiter.record_success("1.2.3.4")
    limiter.record_failure("1.2.3.4")

    assert not limiter.is_locked("1.2.3.4")


def test_different_keys_are_independent() -> None:
    """Zamčení jednoho klíče (IP) neovlivní ostatní klíče."""
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60, lockout_seconds=60)

    limiter.record_failure("1.2.3.4")

    assert limiter.is_locked("1.2.3.4")
    assert not limiter.is_locked("5.6.7.8")
