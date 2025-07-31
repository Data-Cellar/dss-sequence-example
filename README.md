# Dashboard-DSS Integration Example

Proof-of-concept implementation demonstrating Dashboard interaction with the DSS F1 (Energy Optimization) tool via data space connectors.

This example uses the pre-built `agmangas/edc-connector` Docker image and demonstrates the complete flow from the sequence diagram below.

```mermaid
sequenceDiagram
    actor USER as End user
    participant CONSBACK as Dashboard<br/>Consumer Backend
    participant BROKER as Dashboard<br/>Message Broker
    participant BACK as Dashboard<br/>Backend
    participant CONNBACK as Dashboard<br/>Connector
    participant CONNDSS as DSS Connector
    participant DSS as DSS Server

    note over CONSBACK: The Consumer Backend is an off-the-shelf component<br/>deployed with the connector via the participant template.<br/>It is separate from the actual Dashboard Backend<br/>(the API behind the Dashboard web app).
    USER-->>BACK: Request to use DSS F1 tool
    note over BACK: Knows DSS F1 Service / Dataset ID<br/>as defined in the DSS Connector
    note over BACK: The following are predefined HTTP calls per the<br/>Dataspace Protocol to prepare for access token retrieval
    BACK<<-->>CONNBACK: Implement<br/>Contract Negotiation
    CONNBACK<<-->>CONNDSS: Connector communication
    CONNBACK-->>BACK: Return Contract Agreement ID
    BACK<<-->>CONNBACK: Implement<br/>Transfer Process
    CONNBACK<<-->>CONNDSS: Connector communication
    CONNBACK-->>BACK: Return Transfer Process ID
    BACK-->>CONSBACK: Listen to the HTTP SSE endpoint for a Pull transfer<br/>with the given Transfer Process ID
    CONSBACK-->>BROKER: Subscribe to messages
    CONNDSS-->>CONSBACK: Send access token
    CONSBACK-->>BROKER: Publish access token<br/>to the exchange
    BROKER-->>CONSBACK: The message is delivered<br/>via the previously established<br/>HTTP SSE connection
    note over BROKER: We use the message broker for<br/>back-and-forth communication to support other<br/>decoupled consumers that may also be listening
    CONSBACK-->>BACK: Deliver access token event
    BACK-->>CONNDSS: Use the access token to call the DSS connector<br/>Public API and trigger the F1 job
    CONNDSS-->>DSS: Proxy request
    DSS-->>BACK: Return DSS internal job ID
    note over BACK: ~10 minutes later…<br/>Connectors no longer involved
    DSS-->>BACK: Final callback (webhook)
```

## Architecture

This proof of concept implements the complete data space integration flow using:

- **Dashboard Connector** (Consumer) - Handles contract negotiation and transfer processes
- **Dashboard Backend** - Consumer backend with message broker integration for access tokens
- **Dashboard API** - Main orchestration API that coordinates the DSS F1 tool requests
- **DSS Connector** (Provider) - Exposes DSS services to the data space using OpenAPI extension
- **DSS Mock API** - Simulates the actual DSS F1 (Energy Optimization) service
- **Message Broker** - RabbitMQ for decoupled communication between components

## Quick Start

### Prerequisites

- Docker and Docker Compose
- [Taskfile](https://taskfile.dev/) (`brew install go-task/tap/go-task` on macOS)

### Running the Environment

```bash
# Start the complete environment
task up

# Test the integration flow
task test-f1-request

# View logs
task logs

# Check container status  
task status

# Stop the environment
task down
```

### Available Endpoints

- **Dashboard API**: http://localhost:38000 (Main integration API)
- **Dashboard API Docs**: http://localhost:38000/docs
- **DSS Mock API**: http://localhost:18000 (Energy optimization service)
- **DSS Mock API Docs**: http://localhost:18000/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### Testing Energy Optimization

The system simulates a realistic energy optimization workflow:

```bash
# Request energy optimization for a building
curl -X POST "http://localhost:38000/f1/request-tool" \
  -H "Content-Type: application/json" \
  -d '{
    "building_id": "building_001",
    "optimization_type": "energy_efficiency", 
    "user_id": "test-user-001"
  }'
```

Results include:
- Energy savings (kWh)
- Cost reduction (EUR)
- CO2 reduction (kg)
- Optimization score
- Recommended efficiency actions

## Implementation Notes

- Uses `agmangas/edc-connector` Docker image (no local building required)
- Self-signed certificates generated automatically
- Simplified authentication (no Verifiable Credentials)
- Mock services provide realistic energy optimization data
- Complete connector-to-connector communication via Dataspace Protocol