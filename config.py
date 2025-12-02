import os

# Configuration
DASHBOARD_BACKEND_URL = os.environ.get(
    "DASHBOARD_BACKEND_URL",
    "http://dashboard_backend:28000")

# API Keys
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY", "dashboard-api-key")

# Connector Ports
DASHBOARD_CONNECTOR_MANAGEMENT_PORT = int(
    os.environ.get("DASHBOARD_CONNECTOR_MANAGEMENT_PORT", 29193))
DASHBOARD_CONNECTOR_CONTROL_PORT = int(
    os.environ.get("DASHBOARD_CONNECTOR_CONTROL_PORT", 29192))
DASHBOARD_CONNECTOR_PUBLIC_PORT = int(
    os.environ.get("DASHBOARD_CONNECTOR_PUBLIC_PORT", 29291))
DASHBOARD_CONNECTOR_PROTOCOL_PORT = int(
    os.environ.get("DASHBOARD_CONNECTOR_PROTOCOL_PORT", 29194))


# SSE Data Prefix Length
SSE_DATA_PREFIX_LENGTH = 6

# Timeout Constants (seconds)
CREDENTIALS_TIMEOUT_SECONDS = 60
SSE_POLL_INTERVAL_SECONDS = 1

# API Headers
API_KEY_HEADER = "X-API-Key"
AUTHORIZATION_HEADER = "Authorization"
CONTENT_TYPE_HEADER = "Content-Type"
ACCEPT_HEADER = "Accept"

# Content Types
JSON_CONTENT_TYPE = "application/json"
SSE_CONTENT_TYPE = "text/event-stream"

# EDC Connector Configuration
CONNECTOR_SCHEME = "http"
DASHBOARD_CONNECTOR_HOST = "dashboard_connector"
DASHBOARD_PARTICIPANT_ID = "dashboard-participant"

# HTTP Status Codes
HTTP_NOT_FOUND = 404
