"""
Lightweight, dependency-free rate limiting + login lockout.

The production environment is an isolated LAN with no internet access, so this
deliberately avoids pulling in an external package (slowapi, redis, etc.). It
is a per-process, in-memory implementation:

  - throttle(key): sliding-window limit on attempts (anti-automation / anti
    brute-force).
  - record_failure(key) / clear(key): account-style lockout after repeated
    failed logins.

LIMITATION: state lives in this process only. For multi-worker / multi-instance
production, replace the dicts with Redis (same function signatures). This is
called out in the remediation document.
"""
import threading
import time
from collections import defaultdict, deque

from app.core import config

_lock = threading.Lock()
_attempts: dict[str, deque] = defaultdict(deque)     # key -> timestamps (window)
_failures: dict[str, deque] = defaultdict(deque)     # key -> failed-login timestamps
_locked_until: dict[str, float] = {}                 # key -> unix ts


def _prune(dq: deque, horizon: float) -> None:
    while dq and dq[0] < horizon:
        dq.popleft()


def is_locked(key: str) -> int:
    """Return remaining lockout seconds (0 if not locked)."""
    with _lock:
        until = _locked_until.get(key)
        if until is None:
            return 0
        remaining = int(until - time.time())
        if remaining <= 0:
            _locked_until.pop(key, None)
            _failures.pop(key, None)
            return 0
        return remaining


def throttle(key: str) -> int:
    """
    Register one attempt against the sliding window.
    Returns the number of seconds to wait if over the limit, else 0.
    """
    now = time.time()
    window = config.LOGIN_RATE_WINDOW_SECONDS
    with _lock:
        dq = _attempts[key]
        _prune(dq, now - window)
        if len(dq) >= config.LOGIN_RATE_MAX_ATTEMPTS:
            return int(window - (now - dq[0])) or 1
        dq.append(now)
        return 0


def record_failure(key: str) -> None:
    """Record a failed login; lock the key out once the threshold is crossed."""
    now = time.time()
    window = config.LOGIN_RATE_WINDOW_SECONDS
    with _lock:
        dq = _failures[key]
        _prune(dq, now - window)
        dq.append(now)
        if len(dq) >= config.LOGIN_RATE_MAX_ATTEMPTS:
            _locked_until[key] = now + config.LOGIN_LOCKOUT_SECONDS
            dq.clear()


def clear(key: str) -> None:
    """Reset counters on a successful login."""
    with _lock:
        _failures.pop(key, None)
        _locked_until.pop(key, None)
