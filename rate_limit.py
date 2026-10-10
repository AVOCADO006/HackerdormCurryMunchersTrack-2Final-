"""In-memory rate limiter for login attempts — per email and per IP.

Tracks timestamps of recent attempts; blocks if count exceeds limit within window.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from app.config import get_settings

_settings = get_settings()
_window = _settings.LOGIN_RATE_WINDOW_MINUTES * 60  # seconds
_limit = _settings.LOGIN_RATE_LIMIT


class LoginRateLimiter:
    def __init__(self):
        self._by_email: dict[str, list[float]] = defaultdict(list)
        self._by_ip: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _prune(self, key: str, store: dict[str, list[float]]) -> list[float]:
        now = time.time()
        cutoff = now - _window
        store[key] = [t for t in store[key] if t > cutoff]
        return store[key]

    def check(self, email: str, ip: str) -> tuple[bool, str]:
        """Returns (allowed, message)."""
        with self._lock:
            email_attempts = self._prune(email, self._by_email)
            ip_attempts = self._prune(ip, self._by_ip)

            if len(email_attempts) >= _limit:
                return False, "Too many login attempts for this email. Please try again later."
            if len(ip_attempts) >= _limit * 2:
                return False, "Too many login attempts from this address. Please try again later."
            return True, ""

    def record(self, email: str, ip: str) -> None:
        with self._lock:
            now = time.time()
            self._by_email[email].append(now)
            self._by_ip[ip].append(now)


rate_limiter = LoginRateLimiter()
