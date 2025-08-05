# Dashboard-DSS Integration Example

This is a proof-of-concept implementation that demonstrates how the Dashboard interacts with the DSS F1 (Energy Optimization) tool using data space connectors. Both the Dashboard and DSS components are mock implementations: they do not contain any real business logic, and all interactions are random and hardcoded. The purpose of this repository is to show how connector-based communication can be set up and tested.

This example uses the pre-built `agmangas/edc-connector` Docker image and demonstrates the complete flow from the sequence diagram below.

## Prerequisites

- **Docker** with Docker Compose v2 support
- **Task** (go-task) - Task runner for executing commands ([installation guide](https://taskfile.dev/installation/))
- **OpenSSL** - For SSL certificate generation (usually pre-installed on Linux/macOS)
- **jq** - JSON processor for parsing API responses
- **curl** - HTTP client for API testing

## Sequence Diagram

### Component Mapping

| Diagram Participant        | Docker Service        | Description                             |
| -------------------------- | --------------------- | --------------------------------------- |
| Dashboard Backend          | `dashboard_api`       | Main orchestration service (FastAPI)    |
| Dashboard Consumer Backend | `dashboard_backend`   | EDC consumer backend for SSE/messaging  |
| Dashboard Message Broker   | `dashboard_broker`    | RabbitMQ message broker                 |
| Dashboard Connector        | `dashboard_connector` | EDC connector (consumer)                |
| DSS Connector              | `dss_connector`       | EDC connector (provider)                |
| DSS Server                 | `dss_mock_api`        | Mock DSS F1 energy optimization service |

```mermaid
sequenceDiagram
    actor USER as End user
    participant CONSBACK as Dashboard<br/>Consumer Backend<br/>(dashboard_backend)
    participant BROKER as Dashboard<br/>Message Broker<br/>(dashboard_broker)
    participant BACK as Dashboard<br/>Backend<br/>(dashboard_api)
    participant CONNBACK as Dashboard<br/>Connector<br/>(dashboard_connector)
    participant CONNDSS as DSS Connector<br/>(dss_connector)
    participant DSS as DSS Server<br/>(dss_mock_api)

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

## Quick Start

You can deploy all the services, which are preconfigured for localhost access, using the `up` task:

```
task up
```

Once the services have stabilized (all services are up and running for about a minute), you can run the script to orchestrate the request from the Dashboard connector to the DSS connector:

```
task test-dss-request
```