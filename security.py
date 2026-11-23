from __future__ import annotations

import base64
import hashlib
import hmac
import itertools
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 310_000
SECRET_PREFIX = "pbkdf2_sha256"


def hash_secret(secret: str, *, iterations: int = PBKDF2_ITERATIONS, salt: bytes | None = None) -> str:
    """Return a versioned PBKDF2-HMAC-SHA256 representation of a secret."""
    import secrets

    value = str(secret or "")
    if not value:
        raise ValueError("Segredo vazio não pode ser protegido.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(PBKDF2_ALGORITHM, value.encode("utf-8"), salt, int(iterations))
    return "$".join([
        SECRET_PREFIX,
        str(int(iterations)),
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    ])


def is_hashed_secret(value: str | None) -> bool:
    return str(value or "").startswith(SECRET_PREFIX + "$")


def _b64decode(value: str) -> bytes:
    value = str(value or "")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_secret(candidate: str, stored: str | None) -> bool:
    """Verify PBKDF2 secrets and keep a narrow compatibility path for legacy plaintext."""
    stored = str(stored or "")
    candidate = str(candidate or "")
    if not stored:
        return False
    if not is_hashed_secret(stored):
        return hmac.compare_digest(candidate, stored)
    try:
        prefix, iterations, salt64, digest64 = stored.split("$", 3)
        if prefix != SECRET_PREFIX:
            return False
        salt = _b64decode(salt64)
        expected = _b64decode(digest64)
        actual = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            candidate.encode("utf-8"),
            salt,
            int(iterations),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def verify_pin_pairs(pair_choices: list[tuple[str, str]], stored: str | None, expected_length: int) -> bool:
    """Validate the randomized pair keyboard without storing the PIN in plaintext.

    Each click identifies a pair containing the expected digit. With 6-8 digits this
    produces at most 256 candidates, each verified against the PBKDF2 hash.
    """
    if expected_length < 1 or len(pair_choices) != expected_length:
        return False
    for candidate_tuple in itertools.product(*pair_choices):
        if verify_secret("".join(candidate_tuple), stored):
            return True
    return False


@dataclass
class AttemptState:
    failures: int = 0
    locked_until: datetime | None = None
    # Prazo em time.monotonic(); usado quando o chamador não informa `now`,
    # para que ajustes do relógio de parede não encurtem nem alonguem o bloqueio.
    locked_until_mono: float | None = None


class AuthAttemptLimiter:
    """Thread-safe in-memory limiter for PIN and recovery attempts."""

    def __init__(self, max_attempts: int = 5, lock_minutes: int = 15):
        self.max_attempts = max(1, int(max_attempts))
        self.lock_minutes = max(1, int(lock_minutes))
        self._states: dict[str, AttemptState] = {}
        self._lock = RLock()

    @staticmethod
    def _key(user_id, chat_id=None, purpose: str = "pin") -> str:
        return f"{purpose}:{user_id if user_id is not None else 'unknown'}:{chat_id if chat_id is not None else 'unknown'}"

    @staticmethod
    def _seconds_left(state: AttemptState, now: datetime | None, wall_now: datetime) -> float | None:
        """Segundos restantes de bloqueio, ou None quando não há bloqueio."""
        if not state.locked_until:
            return None
        if now is None and state.locked_until_mono is not None:
            return state.locked_until_mono - time.monotonic()
        return (state.locked_until - wall_now).total_seconds()

    def status(self, user_id, chat_id=None, purpose: str = "pin", now: datetime | None = None):
        wall_now = now or datetime.now()
        key = self._key(user_id, chat_id, purpose)
        with self._lock:
            state = self._states.get(key, AttemptState())
            left = self._seconds_left(state, now, wall_now)
            if left is not None and left <= 0:
                self._states.pop(key, None)
                return False, 0
            if left is not None:
                remaining = max(1, int(left // 60) + 1)
                return True, remaining
            return False, 0

    def register_failure(self, user_id, chat_id=None, purpose: str = "pin", now: datetime | None = None):
        wall_now = now or datetime.now()
        key = self._key(user_id, chat_id, purpose)
        with self._lock:
            state = self._states.get(key, AttemptState())
            left = self._seconds_left(state, now, wall_now)
            if left is not None and left <= 0:
                state = AttemptState()
                left = None
            if left is not None:
                remaining = max(1, int(left // 60) + 1)
                return True, remaining, state.failures
            state.failures += 1
            if state.failures >= self.max_attempts:
                state.locked_until = wall_now + timedelta(minutes=self.lock_minutes)
                state.locked_until_mono = time.monotonic() + self.lock_minutes * 60 if now is None else None
            self._states[key] = state
            locked = state.locked_until is not None
            remaining = self.lock_minutes if locked else 0
            return locked, remaining, state.failures

    def register_success(self, user_id, chat_id=None, purpose: str = "pin"):
        key = self._key(user_id, chat_id, purpose)
        with self._lock:
            self._states.pop(key, None)

    def clear(self):
        with self._lock:
            self._states.clear()


def chat_is_private(update) -> bool:
    chat = getattr(update, "effective_chat", None)
    if chat is None:
        return False
    return str(getattr(chat, "type", "")).lower() == "private"


def chat_is_allowed(update, allow_groups: bool = False, allowed_chat_id: int | None = None) -> bool:
    """Fail closed: when an allowed chat is supplied it must match exactly."""
    chat = getattr(update, "effective_chat", None)
    if chat is None:
        return False
    try:
        chat_id = int(getattr(chat, "id", 0))
    except (TypeError, ValueError):
        return False
    if chat_is_private(update):
        return allowed_chat_id is not None and chat_id == int(allowed_chat_id)
    if not allow_groups or allowed_chat_id is None:
        return False
    try:
        return chat_id == int(allowed_chat_id)
    except (TypeError, ValueError):
        return False
