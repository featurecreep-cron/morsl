from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import cachetools
import cachetools.keys
from tzlocal import get_localzone

from morsl.constants import API_CACHE_MAXSIZE, API_CACHE_TTL_MINUTES

# Global API cache: LRU with manual per-entry TTL (respects operator config)
_api_cache: cachetools.LRUCache = cachetools.LRUCache(maxsize=API_CACHE_MAXSIZE)
_api_cache_timestamps: dict = {}  # key → (timestamp, ttl_seconds)
_api_cache_lock = threading.Lock()


def safe_path(base_dir: str, *parts: str) -> str:
    """Join path components and verify the result stays within base_dir.

    Prevents path traversal by resolving symlinks and checking containment.
    """
    joined = os.path.join(base_dir, *parts)
    resolved = os.path.realpath(joined)
    base_resolved = os.path.realpath(base_dir)
    if not (resolved == base_resolved or resolved.startswith(base_resolved + os.sep)):
        raise ValueError(f"Path escapes base directory: {joined}")
    return resolved


_PIN_HASH_PREFIX = "scrypt$"


def hash_pin(pin: str) -> str:
    """Hash a PIN using scrypt. Returns 'scrypt$salt_hex$hash_hex'."""
    if not pin:
        return ""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"{_PIN_HASH_PREFIX}{salt.hex()}${derived.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    """Verify a PIN against a stored hash or plaintext (migration).

    Returns (valid, needs_rehash) — needs_rehash is True when the stored
    value was plaintext and should be replaced with a hash.
    """
    if not stored:
        return False
    if stored.startswith(_PIN_HASH_PREFIX):
        parts = stored.split("$")
        if len(parts) != 3:
            return False
        salt = bytes.fromhex(parts[1])
        expected = bytes.fromhex(parts[2])
        derived = hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
        return secrets.compare_digest(derived, expected)
    # Legacy plaintext — constant-time compare
    import hmac

    return hmac.compare_digest(pin, stored)


def is_pin_hashed(stored: str) -> bool:
    """Check if a stored PIN value is already hashed."""
    return stored.startswith(_PIN_HASH_PREFIX) if stored else True


def atomic_write_json(path: str, data: Any) -> None:
    """Write JSON to file atomically via temp file + os.replace()."""
    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except (OSError, TypeError, ValueError):
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class InfoFilter(logging.Filter):
    def filter(self, rec: logging.LogRecord) -> bool:
        return rec.levelno in (logging.DEBUG, logging.INFO)


FuncType = Callable[..., Any]


_LOG_LEVELS: Dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _resolve_log_level(log: Union[str, int]) -> int:
    """Convert a string or int log level to a numeric level. Returns -1 if invalid."""
    if isinstance(log, str):
        return _LOG_LEVELS.get(log.upper(), -1)
    if isinstance(log, int) and 0 <= log <= 50:
        return log
    return -1


# logging methods
def setup_logging(log: Union[str, int] = "INFO", *, log_to_stdout: bool = False) -> logging.Logger:
    logger: logging.Logger = logging.getLogger("morsl")
    if logger.handlers:
        level = _resolve_log_level(log)
        if level >= 0:
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout:
                    h.setLevel(level)
                    break
            logger.loglevel = level
        return logger
    logger.setLevel(logging.DEBUG)

    # Set up the two formatters
    formatter_brief: logging.Formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
    )
    formatter_explicit: logging.Formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Set up the file logger (skip in stdout-only mode, e.g. Docker)
    if not log_to_stdout:
        fh: logging.FileHandler = logging.FileHandler(
            filename="morsl.log", encoding="utf-8", mode="w"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter_explicit)
        logger.addHandler(fh)

    # Set up the error / warning command line logger
    ch_err: logging.StreamHandler = logging.StreamHandler(stream=sys.stderr)
    ch_err.setFormatter(formatter_explicit)
    ch_err.setLevel(logging.WARNING)
    logger.addHandler(ch_err)

    # Set up the verbose info / debug command line logger
    ch_std: logging.StreamHandler = logging.StreamHandler(stream=sys.stdout)
    ch_std.setFormatter(formatter_brief)
    ch_std.addFilter(InfoFilter())
    level = _resolve_log_level(log)

    if level < 0:
        valid = "\n\t".join(f"{k}: {v}" for k, v in _LOG_LEVELS.items())
        raise RuntimeError(f"Invalid logging level selected: {log}\nValid levels:\n\t{valid}")

    ch_std.setLevel(level)
    logger.addHandler(ch_std)
    logger.loglevel = level
    return logger


def now() -> datetime:
    """Return the current timezone-aware datetime."""
    return datetime.now(get_localzone())


# date methods
def string_to_date(date_str: str) -> tuple[Union[datetime, bool], bool]:
    # Define the regex pattern
    pattern: str = r"^-?\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"

    # Use re.match to check if the string matches the pattern
    if re.match(pattern, date_str):
        if date_str[:1] == "-":
            return datetime.strptime(date_str[1:], "%Y-%m-%d").replace(
                tzinfo=get_localzone()
            ), False
        else:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=get_localzone()), True
    else:
        return False, False


def split_offset(s: str) -> tuple[bool, int, str]:
    # Define the regex pattern to match the desired format
    pattern: str = r"^(-?)(\d+)([dD]?[aA]?[yY]?[sS]?)$"

    # Use re.match to extract the parts of the string
    match = re.match(pattern, s)

    if match:
        # Extract and assign values to variables
        after: bool = match.group(1) != "-"
        offset: int = int(match.group(2))
        interval: str = match.group(3).lower()  # Convert to lowercase for case-insensitivity
        return after, offset, interval

    else:
        # Return None or raise an exception for invalid input
        raise ValueError(f"Invalid time offset format: {s}.  Value must be in form of '-XXdays'")


def format_date(string: str, future: bool = False) -> tuple[datetime, bool]:
    date, after = string_to_date(string)
    if date:
        return date, after

    after, offset, _interval = split_offset(string)
    # TODO support more time intervals than days
    delta: timedelta = timedelta(days=offset)
    if future:
        return now() + delta, after
    return now() - delta, after


def cached(func: FuncType) -> FuncType:
    """Cache method results in the global API cache (thread-safe).

    Respects per-instance TTL via ``self.ttl`` (minutes) — the operator-configured
    ``api_cache_minutes`` setting flows through here correctly.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        import time as _time

        ttl: Optional[int] = kwargs.pop("ttl", None)
        if ttl is None:
            try:
                ttl = self.ttl
            except (NameError, AttributeError):
                ttl = API_CACHE_TTL_MINUTES
        if not ttl or ttl <= 0:
            return func(self, *args, **kwargs)
        ttl_seconds = ttl * 60
        # Stringify args to handle unhashable types (dicts, lists)
        # Include instance id to prevent cache cross-contamination between instances
        key_str = f"{func.__qualname__}|{id(self)}|" + "|".join(str(x) for x in args)
        if kwargs:
            key_str += "|" + str(sorted(kwargs.items()))
        key = cachetools.keys.hashkey(key_str)
        with _api_cache_lock:
            try:
                ts, stored_ttl = _api_cache_timestamps.get(key, (0, 0))
                if _time.monotonic() - ts < stored_ttl:
                    return _api_cache[key]
                # Expired — remove stale entry
                _api_cache.pop(key, None)
                _api_cache_timestamps.pop(key, None)
            except KeyError:
                pass
        result = func(self, *args, **kwargs)
        with _api_cache_lock:
            try:
                _api_cache[key] = result
                _api_cache_timestamps[key] = (_time.monotonic(), ttl_seconds)
            except ValueError:
                pass
        return result

    return wrapper
