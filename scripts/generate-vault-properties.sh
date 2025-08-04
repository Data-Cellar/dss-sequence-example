#!/bin/bash
set -euo pipefail

# Generate vault properties file with public key and API key only
# Private key remains securely in PKCS12 keystore
# Usage: ./generate-vault-properties.sh <cert_dir> <connector_name>

CERT_DIR="${1:-}"
CONNECTOR_NAME="${2:-}"

if [[ -z "$CERT_DIR" || -z "$CONNECTOR_NAME" ]]; then
    echo "Usage: $0 <cert_dir> <connector_name>"
    exit 1
fi

if [[ ! -f "$CERT_DIR/cert.pem" ]]; then
    echo "Error: Certificate file not found in $CERT_DIR"
    exit 1
fi

# Extract certificate and format with escaped newlines
PUBLIC_KEY_PEM=$(tr '\n' '\r' <"$CERT_DIR/cert.pem" | sed 's/\r/\\r\\n/g')

# Set API key based on connector name
if [[ "$CONNECTOR_NAME" == "dashboard_connector" ]]; then
    API_KEY="dashboard-api-key"
else
    API_KEY="dss-api-key"
fi

# Generate vault.properties file
cat >"$CERT_DIR/vault.properties" <<EOF
# $CONNECTOR_NAME Connector Vault Configuration
# Certificate for token verification (PEM format with escaped newlines)
publickey=$PUBLIC_KEY_PEM

# API key for management API authentication
apikey=$API_KEY

# Note: Private key is stored securely in the PKCS12 keystore (cert.pfx)
# and accessed via KEYSTORE_PATH environment variable
EOF

echo "Generated vault.properties for $CONNECTOR_NAME"
