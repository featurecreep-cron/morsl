import json
import logging
import os
import re
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import cachetools
import cachetools.keys
from tzlocal import get_localzone

from constants import API_CACHE_MAXSIZE, API_CACHE_TTL_MINUTES

# Global API cache: default 512 entries, 240-minute TTL
_api_cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=API_CACHE_MAXSIZE, ttl=API_CACHE_TTL_MINUTES * 60)
_api_cache_lock = threading.Lock()


def atomic_write_json(path: str, data: Any) -> None:
    """Write JSON to file atomically via temp file + os.replace()."""
    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class InfoFilter(logging.Filter):
    def filter(self, rec: logging.LogRecord) -> bool:
        return rec.levelno in (logging.DEBUG, logging.INFO)


FuncType = Callable[..., Any]


# logging methods
def setup_logging(log: Union[str, int] = "INFO", *, log_to_stdout: bool = False) -> logging.Logger:
    log_levels: Dict[str, int] = {"CRITICAL": logging.CRITICAL, "ERROR": logging.ERROR, "WARNING": logging.WARNING, "INFO": logging.INFO, "DEBUG": logging.DEBUG}
    logger: logging.Logger = logging.getLogger("morsl")
    if logger.handlers:
        # Handlers configured by first call; log_to_stdout only takes effect
        # on initial setup (singleton pattern — all callers share one Settings).
        # Update stdout handler level on subsequent calls
        level = -1
        if isinstance(log, str):
            try:
                level = log_levels[log.upper()]
            except KeyError:
                pass
        elif isinstance(log, int):
            if 0 <= log <= 50:
                level = log
        if level >= 0:
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout:
                    h.setLevel(level)
                    break
            logger.loglevel = level
        return logger
    logger.setLevel(logging.DEBUG)

    # Set up the two formatters
    formatter_brief: logging.Formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    formatter_explicit: logging.Formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s", datefmt="%H:%M:%S")

    # Set up the file logger (skip in stdout-only mode, e.g. Docker)
    if not log_to_stdout:
        fh: logging.FileHandler = logging.FileHandler(filename="morsl.log", encoding="utf-8", mode="w")
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
    level: int = -1
    if isinstance(log, str):
        try:
            level = log_levels[log.upper()]
        except KeyError:
            pass
    elif isinstance(log, int):
        if 0 <= log <= 50:
            level = log

    if level < 0:
        print("Valid logging levels specified by either key or value:{}".format("\n\t".join("{}: {}".format(key, value) for key, value in log_levels.items())))
        raise RuntimeError("Invalid logging level selected: {}".format(level))
    else:
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
            return datetime.strptime(date_str[1:], "%Y-%m-%d").replace(tzinfo=get_localzone()), False
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
        after: bool = not match.group(1) == "-"
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
    """Cache method results in the global API TTL cache (thread-safe)."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        ttl: Optional[int] = kwargs.pop("ttl", None)
        if ttl is None:
            try:
                ttl = self.ttl
            except (NameError, AttributeError):
                ttl = API_CACHE_TTL_MINUTES
        if not ttl or ttl <= 0:
            return func(self, *args, **kwargs)
        # Stringify args to handle unhashable types (dicts, lists)
        key_str = f"{func.__qualname__}|" + "|".join(str(x) for x in args)
        if kwargs:
            key_str += "|" + str(sorted(kwargs.items()))
        key = cachetools.keys.hashkey(key_str)
        with _api_cache_lock:
            try:
                return _api_cache[key]
            except KeyError:
                pass
        result = func(self, *args, **kwargs)
        with _api_cache_lock:
            try:
                _api_cache[key] = result
            except ValueError:
                pass  # Value too large for cache
        return result

    return wrapper
