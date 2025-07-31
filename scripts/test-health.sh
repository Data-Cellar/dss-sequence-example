#!/bin/bash
set -euo pipefail

# Test health endpoints of all services

echo "Testing service health..."

declare -a services=(
    "http://localhost:38000/health|Dashboard API"
    "http://localhost:18000/health|DSS Mock API"
)

exit_code=0

for service in "${services[@]}"; do
    url=$(echo "$service" | cut -d'|' -f1)
    name=$(echo "$service" | cut -d'|' -f2)

    if curl -sf "$url" >/dev/null 2>&1; then
        echo "✅ $name: OK"
    else
        echo "❌ $name: FAILED"
        exit_code=1
    fi
done

exit $exit_code
