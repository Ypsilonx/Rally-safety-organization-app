"""In-memory rate limiter proti brute-force útoku na login endpointy."""

import time
from collections import defaultdict
from typing import Callable


class LoginRateLimiter:
    """Sleduje neúspěšné pokusy o přihlášení podle klíče (typicky IP adresa).

    Po dosažení `max_attempts` neúspěšných pokusů v posledních
    `window_seconds` sekundách je klíč na `lockout_seconds` zamčený -
    `is_locked` vrací True bez ohledu na to, jestli mezitím přijde platný
    pokus. Bez databáze jde záměrně jen o limiter v paměti jednoho procesu,
    stejně jako ostatní stavové manažery v `backend/core/`.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: float = 60.0,
        lockout_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Inicializuje limiter s prázdnou historií pokusů.

        Args:
            max_attempts: Počet neúspěchů v okně, po kterém se klíč zamkne.
            window_seconds: Délka klouzavého okna pro počítání neúspěchů.
            lockout_seconds: Délka zamčení po překročení limitu.
            clock: Zdroj času (výchozí `time.monotonic`; testy si mohou
                dosadit vlastní pro deterministické posouvání času).
        """
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._lockout_seconds = lockout_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._locked_until: dict[str, float] = {}

    def is_locked(self, key: str) -> bool:
        """Zjistí, jestli je klíč aktuálně v lockoutu.

        Args:
            key: Identifikátor pokusů o přihlášení (např. IP adresa).

        Returns:
            True, pokud je klíč zamčený.
        """
        locked_until = self._locked_until.get(key)
        if locked_until is None:
            return False
        if self._clock() >= locked_until:
            del self._locked_until[key]
            self._failures.pop(key, None)
            return False
        return True

    def record_failure(self, key: str) -> None:
        """Zaznamená neúspěšný pokus a případně klíč zamkne.

        Args:
            key: Identifikátor pokusů o přihlášení.
        """
        now = self._clock()
        window_start = now - self._window_seconds
        recent = [ts for ts in self._failures[key] if ts >= window_start]
        recent.append(now)
        self._failures[key] = recent
        if len(recent) >= self._max_attempts:
            self._locked_until[key] = now + self._lockout_seconds

    def record_success(self, key: str) -> None:
        """Vymaže historii neúspěchů daného klíče po úspěšném přihlášení.

        Args:
            key: Identifikátor pokusů o přihlášení.
        """
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)


# Globální instance pro login endpointy - viz backend/api/auth.py.
login_rate_limiter = LoginRateLimiter()
