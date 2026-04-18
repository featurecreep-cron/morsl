"""Centralised magic numbers and factory defaults for the backend."""

from __future__ import annotations

from pathlib import Path

# Cache (factory defaults — runtime reads from settings where applicable)
API_CACHE_MAXSIZE = 512
API_CACHE_TTL_MINUTES = 240
ADMIN_TOKEN_CACHE_MAXSIZE = 128
PIN_TIMEOUT_OPTIONS = [0, 30, 60, 300]
# Grace period for "immediate" timeout — allows admin page to complete its
# parallel API calls during a single page load before the token expires.
PIN_IMMEDIATE_GRACE_SECONDS = 15

# HTTP client
HTTP_CONNECT_TIMEOUT = 5
HTTP_READ_TIMEOUT = 30
DEFAULT_TIMEOUT = (HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT)
HTTP_MAX_RETRIES = 2
HTTP_BACKOFF_FACTOR = 0.5
HTTP_RETRY_STATUS_CODES = [502, 503, 504]
HTTP_POOL_CONNECTIONS = 5
HTTP_POOL_MAXSIZE = 10
API_PAGE_SIZE = 100

# SSE & shutdown
SSE_QUEUE_TIMEOUT = 30.0
GENERATION_SHUTDOWN_TIMEOUT = 10.0

# Upload limits
CUSTOM_ICON_MAX_SIZE = 512 * 1024
BRANDING_IMAGE_MAX_SIZE = 5 * 1024 * 1024
GZIP_MIN_SIZE = 500

# History
MAX_HISTORY_ENTRIES = 100

# Solver
SOLVER_SLACK_EPSILON = 1e-6
SOLVER_RANDOM_SCALE = 10
DEFAULT_SOFT_WEIGHT = 10

# Paths
UPLOADS_DIR = Path("data/branding")
ICONS_DIR = Path("web/icons")
DEFAULT_FAVICON_PATH = ICONS_DIR / "default-favicon.svg"

# Menu generation
DEFAULT_CHOICES = 5
DEFAULT_PANTRY_WEIGHT = 5

# Settings factory defaults (settings-backed values)
DEFAULT_MENU_POLL_SECONDS = 60
DEFAULT_TOAST_SECONDS = 2
DEFAULT_MAX_DISCOVER_GENS = 10
DEFAULT_MAX_PREVIOUS_RECIPES = 50
