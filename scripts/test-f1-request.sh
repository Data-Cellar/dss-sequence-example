#!/bin/bash
set -euo pipefail

# Test a complete DSS F1 (Energy Optimization) request flow

echo "🧪 Testing DSS F1 energy optimization request flow..."

# Check if jq is available
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

# Make the initial request
response=$(curl -s -X POST "http://localhost:38000/f1/request-tool" \
    -H "Content-Type: application/json" \
    -d '{
        "building_id": "building_001",
        "optimization_type": "energy_efficiency",
        "user_id": "test-user-001"
    }')

if [[ -z "$response" ]]; then
    echo "❌ Failed to get response from Dashboard API"
    exit 1
fi

request_id=$(echo "$response" | jq -r '.request_id')
if [[ "$request_id" == "null" || -z "$request_id" ]]; then
    echo "❌ No request ID received"
    echo "Response: $response"
    exit 1
fi

echo "📝 Request ID: $request_id"
echo "🔄 Status: $(echo "$response" | jq -r '.status')"

# Wait and check status
echo "⏳ Waiting 30 seconds for processing..."
sleep 30

status_response=$(curl -s "http://localhost:38000/f1/requests/$request_id")
if [[ -z "$status_response" ]]; then
    echo "❌ Failed to get status response"
    exit 1
fi

echo "📊 Final Status: $(echo "$status_response" | jq -r '.status')"

# Check DSS job if available
dss_job_id=$(echo "$status_response" | jq -r '.dss_job_id // empty')
if [[ -n "$dss_job_id" && "$dss_job_id" != "null" ]]; then
    echo "🏎️  DSS Job ID: $dss_job_id"

    # Check DSS job status
    dss_status=$(curl -s -H "X-API-Key: dss-backend-key" "http://localhost:18000/f1/jobs/$dss_job_id")
    if [[ -n "$dss_status" ]]; then
        echo "🏁 DSS Job Status: $(echo "$dss_status" | jq -r '.status')"
    else
        echo "⚠️  Could not retrieve DSS job status"
    fi
else
    echo "⚠️  No DSS job ID found in response"
fi

echo "✅ Test completed successfully"
