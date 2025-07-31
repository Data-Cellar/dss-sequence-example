import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dashboard Backend API",
    description="Dashboard backend that orchestrates DSS F1 (Energy Optimization) tool access via connectors",
    version="1.0.0",
)

# Configuration
DASHBOARD_CONNECTOR_URL = "http://dashboard_connector:29193"  # Management API
DSS_CONNECTOR_URL = "http://dss_connector:19194"  # Protocol API for DSP communication
DASHBOARD_BACKEND_URL = "http://dashboard_backend:28000"
DSS_API_URL = "http://dss_mock_api:8000"

# API Keys
DASHBOARD_API_KEY = "dashboard-api-key"
DSS_API_KEY = "dss-api-key"


class F1ToolRequest(BaseModel):
    building_id: str = "building_001"
    optimization_type: str = "energy_efficiency"
    user_id: str
    callback_url: Optional[str] = None


class F1ToolResponse(BaseModel):
    request_id: str
    status: str
    message: str
    dss_job_id: Optional[str] = None


# In-memory storage for tracking requests
requests_storage: Dict[str, Dict[str, Any]] = {}


async def negotiate_contract(asset_id: str, provider_url: str) -> str:
    """Negotiate contract with DSS connector for F1 service access"""

    try:
        # Contract negotiation request
        contract_request = {
            "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "@type": "ContractRequest",
            "counterPartyAddress": provider_url,
            "protocol": "dataspace-protocol-http",
            "policy": {
                "@type": "Policy",
                "permission": [{"action": "use", "target": asset_id}],
            },
        }

        headers = {"x-api-key": DASHBOARD_API_KEY, "Content-Type": "application/json"}

        response = requests.post(
            f"{DASHBOARD_CONNECTOR_URL}/management/contractnegotiations",
            json=contract_request,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        negotiation_id = response.json()["@id"]
        logger.info(f"Started contract negotiation: {negotiation_id}")

        # Poll for contract agreement (simplified for demo)
        for _ in range(10):  # Wait up to 50 seconds
            await asyncio.sleep(5)

            status_response = requests.get(
                f"{DASHBOARD_CONNECTOR_URL}/management/contractnegotiations/{negotiation_id}",
                headers=headers,
                timeout=10,
            )

            if status_response.status_code == 200:
                negotiation = status_response.json()
                if negotiation["state"] == "FINALIZED":
                    agreement_id = negotiation["contractAgreementId"]
                    logger.info(f"Contract negotiation completed: {agreement_id}")
                    return agreement_id

        raise Exception("Contract negotiation timed out")

    except Exception as e:
        logger.error(f"Contract negotiation failed: {e}")
        raise


async def initiate_transfer(agreement_id: str, asset_id: str, provider_url: str) -> str:
    """Initiate transfer process for data access"""

    try:
        transfer_request = {
            "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "@type": "TransferRequest",
            "counterPartyAddress": provider_url,
            "protocol": "dataspace-protocol-http",
            "contractId": agreement_id,
            "assetId": asset_id,
            "dataDestination": {"type": "HttpPull"},
        }

        headers = {"x-api-key": DASHBOARD_API_KEY, "Content-Type": "application/json"}

        response = requests.post(
            f"{DASHBOARD_CONNECTOR_URL}/management/transferprocesses",
            json=transfer_request,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        transfer_id = response.json()["@id"]
        logger.info(f"Started transfer process: {transfer_id}")

        # Poll for transfer completion (simplified for demo)
        for _ in range(10):  # Wait up to 50 seconds
            await asyncio.sleep(5)

            status_response = requests.get(
                f"{DASHBOARD_CONNECTOR_URL}/management/transferprocesses/{transfer_id}",
                headers=headers,
                timeout=10,
            )

            if status_response.status_code == 200:
                transfer = status_response.json()
                if transfer["state"] == "STARTED":
                    logger.info(f"Transfer process started: {transfer_id}")
                    return transfer_id

        raise Exception("Transfer process timed out")

    except Exception as e:
        logger.error(f"Transfer process failed: {e}")
        raise


async def wait_for_access_token(transfer_id: str) -> str:
    """Wait for access token via SSE endpoint"""

    try:
        # In a real scenario, this would listen to the SSE endpoint
        # For this demo, we'll simulate receiving the token
        await asyncio.sleep(3)  # Simulate SSE wait time

        # Simulate access token (in real scenario, comes from SSE)
        access_token = f"simulated-token-{transfer_id}"
        logger.info(f"Received access token for transfer {transfer_id}")
        return access_token

    except Exception as e:
        logger.error(f"Failed to get access token: {e}")
        raise


async def call_dss_f1_service(access_token: str, f1_request: F1ToolRequest) -> str:
    """Call the DSS F1 (Energy Optimization) service using the access token"""

    try:
        # Prepare the F1 job request
        job_request = {
            "building_id": f1_request.building_id,
            "optimization_type": f1_request.optimization_type,
            "parameters": {},
        }

        # Call DSS connector's public API (which proxies to DSS service)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # For demo purposes, call DSS API directly (in real scenario via connector)
        dss_headers = {
            "X-API-Key": "dss-backend-key",
            "Content-Type": "application/json",
        }

        callback_url = (
            f"http://dashboard_api:8000/webhooks/dss-callback/{f1_request.user_id}"
        )

        response = requests.post(
            f"{DSS_API_URL}/f1/jobs",
            json=job_request,
            headers=dss_headers,
            params={"callback_url": callback_url},
            timeout=30,
        )
        response.raise_for_status()

        job_data = response.json()
        dss_job_id = job_data["job_id"]
        logger.info(f"Created DSS F1 job: {dss_job_id}")

        return dss_job_id

    except Exception as e:
        logger.error(f"Failed to call DSS F1 service: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint"""

    return {
        "status": "healthy",
        "service": "Dashboard Backend API (DSS F1 Energy Optimization)",
    }


@app.post("/f1/request-tool", response_model=F1ToolResponse)
async def request_f1_tool(f1_request: F1ToolRequest, background_tasks: BackgroundTasks):
    """Request to use DSS F1 (Energy Optimization) tool through data space connectors"""

    request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f1_request.user_id}"

    # Store request
    requests_storage[request_id] = {
        "request_id": request_id,
        "user_id": f1_request.user_id,
        "building_id": f1_request.building_id,
        "optimization_type": f1_request.optimization_type,
        "status": "initiated",
        "created_at": datetime.now().isoformat(),
    }

    # Start background processing
    background_tasks.add_task(process_f1_request, request_id, f1_request)

    logger.info(f"Initiated DSS F1 tool request: {request_id}")

    return F1ToolResponse(
        request_id=request_id,
        status="initiated",
        message=f"DSS F1 energy optimization request initiated for building {f1_request.building_id} ({f1_request.optimization_type})",
    )


async def process_f1_request(request_id: str, f1_request: F1ToolRequest):
    """Background task to process DSS F1 (Energy Optimization) tool request through connectors"""

    try:
        requests_storage[request_id]["status"] = "negotiating_contract"

        # Step 1: Contract Negotiation
        asset_id = "dss-f1-service"  # Predefined in DSS connector
        agreement_id = await negotiate_contract(asset_id, DSS_CONNECTOR_URL)

        requests_storage[request_id]["contract_agreement_id"] = agreement_id
        requests_storage[request_id]["status"] = "initiating_transfer"

        # Step 2: Transfer Process
        transfer_id = await initiate_transfer(agreement_id, asset_id, DSS_CONNECTOR_URL)

        requests_storage[request_id]["transfer_process_id"] = transfer_id
        requests_storage[request_id]["status"] = "waiting_access_token"

        # Step 3: Wait for Access Token
        access_token = await wait_for_access_token(transfer_id)

        requests_storage[request_id]["status"] = "calling_dss_service"

        # Step 4: Call DSS F1 Service
        dss_job_id = await call_dss_f1_service(access_token, f1_request)

        requests_storage[request_id]["dss_job_id"] = dss_job_id
        requests_storage[request_id]["status"] = "dss_job_running"

        logger.info(
            f"DSS F1 request {request_id} processed successfully, DSS job: {dss_job_id}"
        )

    except Exception as e:
        logger.error(f"Failed to process DSS F1 request {request_id}: {e}")
        requests_storage[request_id]["status"] = "failed"
        requests_storage[request_id]["error"] = str(e)


@app.get("/f1/requests/{request_id}")
async def get_request_status(request_id: str):
    """Get the status of a DSS F1 energy optimization tool request"""

    if request_id not in requests_storage:
        raise HTTPException(status_code=404, detail="Request not found")

    return requests_storage[request_id]


@app.get("/f1/requests")
async def list_requests():
    """List all DSS F1 energy optimization tool requests"""

    return {"requests": list(requests_storage.values())}


@app.post("/webhooks/dss-callback/{user_id}")
async def dss_webhook_callback(user_id: str, callback_data: Dict[str, Any]):
    """Webhook endpoint for DSS job completion callbacks"""

    logger.info(f"Received DSS callback for user {user_id}: {callback_data}")

    # Find the corresponding request
    for request_id, request_data in requests_storage.items():
        if request_data["user_id"] == user_id and request_data.get(
            "dss_job_id"
        ) == callback_data.get("job_id"):

            request_data["status"] = "completed"
            request_data["dss_result"] = callback_data.get("result", {})
            request_data["completed_at"] = datetime.now().isoformat()

            logger.info(f"Updated request {request_id} with DSS results")
            break

    return {"status": "callback_received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
