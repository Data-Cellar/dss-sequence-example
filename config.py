"""
Application configuration (env-driven).

This module defines configuration values as **module-level constants** so they can be imported
from anywhere without initialization. Values are read from environment variables with
developer-friendly defaults for local/dev usage.
"""

from __future__ import annotations

import os
from typing import Final

# ---------------------------------------------------------------------------
# HTTP protocol constants (stable surface)
# ---------------------------------------------------------------------------

# Standard HTTP header keys used in requests.
API_KEY_HEADER: Final[str] = "X-API-Key"
AUTHORIZATION_HEADER: Final[str] = "Authorization"
CONTENT_TYPE_HEADER: Final[str] = "Content-Type"
ACCEPT_HEADER: Final[str] = "Accept"

# Standard HTTP content type values.
JSON_CONTENT_TYPE: Final[str] = "application/json"
SSE_CONTENT_TYPE: Final[str] = "text/event-stream"

# Standard HTTP status codes.
HTTP_NOT_FOUND: Final[int] = 404


# ---------------------------------------------------------------------------
# Dashboard consumer backend (SSE credentials stream)
# ---------------------------------------------------------------------------

# Env: DASHBOARD_CONSUMER_BACKEND_URL
#
# Base URL of the Dashboard Consumer Backend service that provides the SSE stream for credentials.
# Example (docker): http://dashboard_backend:28000
DASHBOARD_CONSUMER_BACKEND_URL: Final[str] = (
    os.environ.get("DASHBOARD_CONSUMER_BACKEND_URL", "http://dashboard_backend:28000")
    .strip()
    .rstrip("/")
)

# Env: DASHBOARD_API_KEY
#
# Token/API key used to authenticate requests to the Dashboard Consumer Backend (SSE connection).
# Note: the same value is also used as the EDC connector API key in `edc_connector/edc_config.py`.
DASHBOARD_API_KEY: Final[str] = os.environ.get("DASHBOARD_API_KEY", "dashboard-api-key")


# ---------------------------------------------------------------------------
# EDC connector location & identity
# ---------------------------------------------------------------------------

# Env: CONNECTOR_SCHEME
#
# Protocol scheme used for connector URLs.
CONNECTOR_SCHEME: Final[str] = (
    os.environ.get("CONNECTOR_SCHEME", "https").strip().lower()
)

# Env: DASHBOARD_CONNECTOR_HOST
#
# Hostname where the dashboard connector is reachable.
DASHBOARD_CONNECTOR_HOST: Final[str] = os.environ.get(
    "DASHBOARD_CONNECTOR_HOST", "certh.dashboard.datacellar.iti.gr"
).strip()

# Env: DASHBOARD_PARTICIPANT_ID
#
# Unique participant identifier for this EDC connector instance (also used as connector id).
DASHBOARD_PARTICIPANT_ID: Final[str] = os.environ.get(
    "DASHBOARD_PARTICIPANT_ID", "certh"
).strip()


# ---------------------------------------------------------------------------
# EDC connector ports
# ---------------------------------------------------------------------------

_management_port_raw = os.environ.get("DASHBOARD_CONNECTOR_MANAGEMENT_PORT")
try:
    DASHBOARD_CONNECTOR_MANAGEMENT_PORT: Final[int] = (
        29193 if _management_port_raw is None else int(_management_port_raw)
    )
except ValueError as exc:
    raise ValueError(
        f"Invalid integer for env var 'DASHBOARD_CONNECTOR_MANAGEMENT_PORT': {_management_port_raw!r}"
    ) from exc

_control_port_raw = os.environ.get("DASHBOARD_CONNECTOR_CONTROL_PORT")
try:
    DASHBOARD_CONNECTOR_CONTROL_PORT: Final[int] = (
        29192 if _control_port_raw is None else int(_control_port_raw)
    )
except ValueError as exc:
    raise ValueError(
        f"Invalid integer for env var 'DASHBOARD_CONNECTOR_CONTROL_PORT': {_control_port_raw!r}"
    ) from exc

_public_port_raw = os.environ.get("DASHBOARD_CONNECTOR_PUBLIC_PORT")
try:
    DASHBOARD_CONNECTOR_PUBLIC_PORT: Final[int] = (
        29291 if _public_port_raw is None else int(_public_port_raw)
    )
except ValueError as exc:
    raise ValueError(
        f"Invalid integer for env var 'DASHBOARD_CONNECTOR_PUBLIC_PORT': {_public_port_raw!r}"
    ) from exc

_protocol_port_raw = os.environ.get("DASHBOARD_CONNECTOR_PROTOCOL_PORT")
try:
    DASHBOARD_CONNECTOR_PROTOCOL_PORT: Final[int] = (
        29194 if _protocol_port_raw is None else int(_protocol_port_raw)
    )
except ValueError as exc:
    raise ValueError(
        f"Invalid integer for env var 'DASHBOARD_CONNECTOR_PROTOCOL_PORT': {_protocol_port_raw!r}"
    ) from exc


# ---------------------------------------------------------------------------
# Derived/handy connector URLs (constants; safe to import)
# ---------------------------------------------------------------------------

DASHBOARD_CONNECTOR_PROTOCOL_URL: Final[str] = (
    f"{CONNECTOR_SCHEME}://{DASHBOARD_CONNECTOR_HOST}:{DASHBOARD_CONNECTOR_PROTOCOL_PORT}/protocol"
)

DASHBOARD_CONNECTOR_MANAGEMENT_URL: Final[str] = (
    f"{CONNECTOR_SCHEME}://{DASHBOARD_CONNECTOR_HOST}:{DASHBOARD_CONNECTOR_MANAGEMENT_PORT}"
)

DASHBOARD_CONNECTOR_CONTROL_URL: Final[str] = (
    f"{CONNECTOR_SCHEME}://{DASHBOARD_CONNECTOR_HOST}:{DASHBOARD_CONNECTOR_CONTROL_PORT}"
)

DASHBOARD_CONNECTOR_PUBLIC_URL: Final[str] = (
    f"{CONNECTOR_SCHEME}://{DASHBOARD_CONNECTOR_HOST}:{DASHBOARD_CONNECTOR_PUBLIC_PORT}"
)


# ---------------------------------------------------------------------------
# SSE parsing & timeouts
# ---------------------------------------------------------------------------

# Used to strip the SSE "data: " prefix during parsing.
SSE_DATA_PREFIX_LENGTH: Final[int] = len("data: ")

# The maximum duration (in seconds) to wait for credentials to arrive via the SSE stream.
CREDENTIALS_TIMEOUT_SECONDS: Final[int] = 60

# The interval (in seconds) at which to poll for received credentials while waiting.
SSE_POLL_INTERVAL_SECONDS: Final[int] = 1
