# Dashboard Mediator

A FastAPI-based service that orchestrates Eclipse Dataspace Connector (EDC) contract negotiations and data transfers. The Mediator acts as an intermediary that manages the complex workflow of negotiating data access contracts and coordinating secure data transfers between connectors.

## Overview

The Dashboard Mediator simplifies EDC interactions by:

-   **Automating contract negotiation** with provider connectors
-   **Managing transfer processes** using pull-based data access
-   **Receiving credentials** via Server-Sent Events (SSE) for secure data retrieval
-   **Providing a simple REST API** for initiating EDC workflows

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Client    │─────▶│     Mediator     │─────▶│   Provider   │
│ Application │      │   (This Service) │      │  Connector   │
└─────────────┘      └──────────────────┘      └──────────────┘
                              │
                              │ SSE
                              ▼
                     ┌──────────────────┐
                     │ Consumer Backend │
                     │  (Credentials)   │
                     └──────────────────┘
```

## Features

-   **Contract Negotiation**: Automated negotiation flow with provider connectors
-   **Transfer Management**: Handles transfer process initiation and monitoring
-   **SSE-based Credentials**: Real-time credential reception via Server-Sent Events
-   **Bearer Token Extraction**: Automatic extraction of access tokens for data retrieval
-   **Comprehensive Logging**: Detailed logging with colored output for debugging
-   **Input Validation**: Pydantic-based validation for all API inputs
