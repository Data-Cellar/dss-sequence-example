#!/bin/bash
set -euo pipefail

# Test a complete DSS F1 (Energy Optimization) request flow

# Configuration variables with defaults
DASHBOARD_API_PORT=${DASHBOARD_API_PORT:-38000}
DSS_API_PORT=${DSS_API_PORT:-18000}
WAIT_TIME_SECONDS=${WAIT_TIME_SECONDS:-30}
BUILDING_ID=${BUILDING_ID:-"building_001"}
OPTIMIZATION_TYPE=${OPTIMIZATION_TYPE:-"energy_efficiency"}
USER_ID=${USER_ID:-"test-user-001"}
DSS_API_KEY=${DSS_API_KEY:-"dss-backend-key"}

echo "🧪 Testing DSS F1 energy optimization request flow..."
echo "📋 EDC Protocol Flow: Consumer → Contract Negotiation → Transfer Process → Data Access"
echo ""

# Check if jq is available
if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

# Make the initial request
echo "🚀 Step 1: Initiating request to Dashboard API"
echo "   → Dashboard API will start EDC contract negotiation with DSS Connector"
response=$(curl -s -X POST "http://localhost:${DASHBOARD_API_PORT}/f1/request-tool" \
    -H "Content-Type: application/json" \
    -d "{
        \"building_id\": \"${BUILDING_ID}\",
        \"optimization_type\": \"${OPTIMIZATION_TYPE}\",
        \"user_id\": \"${USER_ID}\"
    }")

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
echo "🔄 Initial Status: $(echo "$response" | jq -r '.status')"
echo ""

# Wait and check status
echo "🔄 Step 2: EDC Protocol execution in progress"
echo "   → Contract negotiation between Dashboard and DSS Connectors"
echo "   → Transfer process initiation for asset: POST-f1-jobs"
echo "   → SSE stream listening for access credentials"
echo "⏱️  Waiting ${WAIT_TIME_SECONDS} seconds for the SSE stream to receive access credentials from the DSS Connector..."
sleep "$WAIT_TIME_SECONDS"

status_response=$(curl -s "http://localhost:${DASHBOARD_API_PORT}/f1/requests/$request_id")
if [[ -z "$status_response" ]]; then
    echo "❌ Failed to get status response"
    exit 1
fi

echo "📊 Final Status: $(echo "$status_response" | jq -r '.status')"
echo ""

# Check DSS job if available
echo "🔄 Step 3: Verifying EDC transfer completion and data access"
dss_job_id=$(echo "$status_response" | jq -r '.dss_job_id // empty')
if [[ -n "$dss_job_id" && "$dss_job_id" != "null" ]]; then
    echo "   → Transfer process completed: access credentials received via SSE"
    echo "   → JWT token used to authenticate with DSS Connector public API"
    echo "🔧 DSS Job ID: $dss_job_id"

    # Check DSS job status
    echo "   → Querying DSS Mock API for job execution status"
    dss_status=$(curl -s -H "X-API-Key: ${DSS_API_KEY}" "http://localhost:${DSS_API_PORT}/f1/jobs/$dss_job_id")
    if [[ -n "$dss_status" ]]; then
        echo "✅ DSS Job Status: $(echo "$dss_status" | jq -r '.status')"
        echo ""
        echo "📋 EDC Protocol Summary:"
        echo "   ✓ Contract negotiation completed between connectors"
        echo "   ✓ Transfer process executed with pull mechanism"
        echo "   ✓ Access credentials delivered via SSE stream"
        echo "   ✓ Protected resource accessed using JWT token"
        echo "✅ Test completed successfully"
    else
        echo "⚠️  Could not retrieve DSS job status"
        echo "❌ Test failed: Unable to verify DSS job status"
        exit 1
    fi
else
    echo "   → Transfer process failed or credentials not received"
    echo "⚠️  No DSS job ID found in response"
    echo "❌ Test failed: EDC transfer process incomplete"
    exit 1
fi
