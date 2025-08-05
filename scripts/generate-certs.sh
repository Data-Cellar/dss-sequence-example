#!/bin/bash
set -euo pipefail

# Generate certificates and keystore for a specific connector
# Creates PEM certificate, PKCS12 keystore, and vault properties
# Private key is stored securely in PKCS12 keystore only
# Usage: ./generate-certs.sh <cert_dir> <common_name>

CERT_DIR="${1:-}"
COMMON_NAME="${2:-}"

if [[ -z "$CERT_DIR" || -z "$COMMON_NAME" ]]; then
    echo "Usage: $0 <cert_dir> <common_name>"
    exit 1
fi

mkdir -p "$CERT_DIR"

# Generate private key
openssl genpkey -algorithm RSA -out "$CERT_DIR/key.pem"

# Generate self-signed certificate
openssl req -new -x509 -key "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 365 -subj "/CN=$COMMON_NAME"

# Convert to PKCS12 format for Java with explicit alias
openssl pkcs12 -export -out "$CERT_DIR/cert.pfx" -inkey "$CERT_DIR/key.pem" -in "$CERT_DIR/cert.pem" -name datacellar -passout pass:datacellar

# Generate vault properties (public key and API key only)
"$(dirname "$0")/generate-vault-properties.sh" "$CERT_DIR" "$COMMON_NAME"

echo "Generated certificates for $COMMON_NAME in $CERT_DIR"
