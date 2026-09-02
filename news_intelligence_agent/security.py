"""Input validation and in-memory abuse/cost guards (shared across agents).

Lightweight (no external store) so each demo stays a single container. For a
production, multi-instance deployment, replace RateLimiter with a shared store.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from datetime import date

from .config import CONFIG

_ALLOWED_WHITESPACE = {"\n", "\t"}


class ValidationError(ValueError):
    """Raised when user input fails validation (shown to the user verbatim)."""


class RateLimitError(RuntimeError):
    """Raised when a caller exceeds the per-minute or global daily budget."""


def sanitize_text(raw: str, *, field: str = "input", min_chars: int | None = None,
                  max_chars: int | None = None) -> str:
    """Validate/normalize free text (length + control-char strip).

    NOT an injection filter — injection is mitigated in each agent's system prompt,
    which treats user/tool/document content as untrusted data.
    """
    lo = CONFIG.min_input_chars if min_chars is None else min_chars
    hi = CONFIG.max_input_chars if max_chars is None else max_chars
    if raw is None:
        raise ValidationError(f"Please provide {field}.")
    text = "".join(c for c in raw if c in _ALLOWED_WHITESPACE or c.isprintable()).strip()
    if len(text) < lo:
        raise ValidationError(f"Please enter at least {lo} characters of {field}.")
    if len(text) > hi:
        raise ValidationError(f"{field.capitalize()} is too long (max {hi} characters).")
    return text


def validate_upload(file_path: str, allowed_exts: set[str]) -> None:
    """Reject wrong-type or oversized files before reading them."""
    if not file_path:
        raise ValidationError("Please upload a file first.")
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in allowed_exts:
        allowed = ", ".join(sorted(e.lstrip(".").upper() for e in allowed_exts))
        raise ValidationError(f"Unsupported file type. Allowed: {allowed}.")
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        raise ValidationError("Could not read the uploaded file.")
    if size_mb > CONFIG.max_file_mb:
        raise ValidationError(f"File is too large (max {CONFIG.max_file_mb} MB).")


class RateLimiter:
    """Sliding-window per-caller limit plus a global daily cap. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque] = defaultdict(deque)
        self._day: date = date.today()
        self._day_count = 0

    def check(self, caller_id: str) -> None:
        now = time.monotonic()
        with self._lock:
            today = date.today()
            if today != self._day:
                self._day = today
                self._day_count = 0
            if self._day_count >= CONFIG.daily_call_cap:
                raise RateLimitError(
                    "The demo has reached its daily usage limit. Please try again "
                    "tomorrow, or view the source on GitHub."
                )
            window = self._hits[caller_id]
            cutoff = now - 60.0
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= CONFIG.rate_limit_per_min:
                raise RateLimitError(
                    "You're sending requests too quickly. Please wait a minute and try again."
                )
            window.append(now)
            self._day_count += 1
