# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a proof-of-concept demonstrating data space connector interactions between a Dashboard consumer and DSS (Decision Support System) provider. The system implements the complete Eclipse Dataspace Components (EDC) protocol flow for energy optimization services.

### Architecture Components

The system consists of 6 containerized services:

- **Dashboard Connector** (Consumer) - EDC connector handling contract negotiation and transfer processes
- **Dashboard Backend** - Consumer backend with Server-Sent Events (SSE) for access token delivery via message broker
- **Dashboard API** - Main orchestration service that coordinates DSS F1 energy optimization requests
- **DSS Connector** (Provider) - EDC connector exposing DSS services using OpenAPI extension
- **DSS Mock API** - Simulates actual DSS F1 (Energy Optimization) service with realistic energy metrics
- **Message Broker** - RabbitMQ for decoupled communication between consumer backend and Dashboard API

### Key Integration Flow

1. Dashboard API initiates contract negotiation with DSS Connector via Dashboard Connector
2. After successful contract agreement, Dashboard API starts transfer process
3. Dashboard Backend listens for access tokens via SSE and message broker
4. Once access token received, Dashboard API calls DSS Connector Public API to trigger F1 job
5. DSS Mock API processes energy optimization and returns results via webhook

## Essential Commands

### Environment Management
```bash
# Start complete environment (includes certificate generation)
task up

# Stop environment and cleanup
task down

# Clean restart
task restart

# View all service logs
task logs

# Check container status
task status
```

### Certificate Management
```bash
# Generate SSL certificates for connectors (auto-run by task up)
task setup-certs

# Clean certificates only
task clean-certs
```

### Testing
```bash
# Test service health endpoints
task test-health

# Test complete F1 energy optimization flow (30-second process)
task test-dss-request

# Show development endpoints and info
task dev-info
```

## Configuration Details

### Connector Properties
- **Dashboard Connector**: Ports 29191-29194, 29291-29292
- **DSS Connector**: Ports 19191-19194, 19291-19292
- Located in `config/` directory with EDC-specific settings

### Certificate System
- Self-signed certificates auto-generated in `certs/` directory
- Vault properties files contain PEM-formatted keys with escaped newlines
- PKCS12 keystores for Java connector compatibility

### API Authentication
- Dashboard API Key: `dashboard-api-key`
- DSS API Key: `dss-api-key`
- Configured via environment variables in Docker Compose

## Important Implementation Notes

### DSS F1 Context
"DSS F1" refers to "Decision Support System Functionality 1" for energy optimization, not Formula 1 racing. All APIs and test data focus on:
- Energy savings (kWh)
- Cost reduction (EUR) 
- CO2 reduction (kg)
- Building optimization recommendations

### EDC Integration
Uses `agmangas/edc-connector` Docker image without local building. The system implements:
- Dataspace Protocol for connector-to-connector communication
- Contract negotiation and transfer processes
- OpenAPI extension for automatic asset generation
- Consumer backend with SSE for access token handling

### Mock Services
Both Dashboard API and DSS Mock API simulate realistic energy optimization workflows with:
- Background job processing
- Webhook callbacks
- Realistic energy metrics and recommendations
- Proper error handling and status tracking

## File Structure Notes

- `scripts/` - Bash scripts extracted from Taskfile for better maintainability
- `dashboard-api/` - FastAPI service orchestrating connector interactions
- `dss-api/` - FastAPI mock DSS service with energy optimization simulation
- Dockerfiles build separate Python services with specific requirements