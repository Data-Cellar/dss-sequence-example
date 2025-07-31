import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import uvicorn
from edcpy.edc_api import ConnectorController
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

# EDC Configuration
DSS_CONNECTOR_PROTOCOL_URL = "http://dss_connector:19194"
DSS_CONNECTOR_ID = "dss-connector"


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


class SSEPullCredentialsReceiver:
    """Handles SSE-based access token reception from consumer backend"""

    def __init__(self, consumer_backend_url: str, api_key: str):
        self.consumer_backend_url = consumer_backend_url
        self.api_key = api_key
        self.credentials = {}
        self._listening = False
        self._client = None

    async def start_listening(self, provider_host: str):
        """Start listening for SSE messages from consumer backend"""
        sse_url = f"{self.consumer_backend_url}/pull/stream/provider/{provider_host}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }

        self._client = httpx.AsyncClient()
        self._listening = True

        try:
            async with self._client.stream("GET", sse_url, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not self._listening:
                        break
                    await self._process_sse_line(line)
        except Exception as e:
            logger.error(f"SSE connection failed: {e}")
            raise

    async def _process_sse_line(self, line: str):
        """Process individual SSE message lines"""
        if line.startswith("data: "):
            try:
                import json

                data = json.loads(line[6:])  # Remove 'data: ' prefix
                transfer_id = data.get("transfer_process_id")
                if transfer_id:
                    self.credentials[transfer_id] = data
                    logger.info(f"Received credentials for transfer {transfer_id}")
            except json.JSONDecodeError:
                pass

    async def get_credentials(
        self, transfer_id: str, timeout: int = 60
    ) -> Dict[str, Any]:
        """Wait for and retrieve credentials for a specific transfer"""
        for _ in range(timeout):
            if transfer_id in self.credentials:
                return self.credentials[transfer_id]
            await asyncio.sleep(1)
        raise TimeoutError(f"Credentials not received for transfer {transfer_id}")

    async def stop_listening(self):
        """Stop listening for SSE messages"""
        self._listening = False
        if self._client:
            await self._client.aclose()


async def run_edcpy_negotiation_and_transfer(
    asset_id: str, f1_request: F1ToolRequest
) -> str:
    """Use edcpy to handle contract negotiation and transfer process"""

    try:
        # Initialize EDC controller
        controller = ConnectorController(
            management_url=DASHBOARD_CONNECTOR_URL, api_key=DASHBOARD_API_KEY
        )

        # Start SSE listener for credentials
        sse_receiver = SSEPullCredentialsReceiver(
            DASHBOARD_BACKEND_URL, DASHBOARD_API_KEY
        )

        # Start listening in background
        provider_host = "dss_connector:19194"
        listen_task = asyncio.create_task(sse_receiver.start_listening(provider_host))

        try:
            # Run negotiation flow
            logger.info(f"Starting negotiation for asset {asset_id}")
            transfer_details = await controller.run_negotiation_flow(
                counter_party_protocol_url=DSS_CONNECTOR_PROTOCOL_URL,
                counter_party_connector_id=DSS_CONNECTOR_ID,
                asset_query=asset_id,
            )

            # Run transfer flow
            logger.info("Starting transfer process")
            transfer_process = await controller.run_transfer_flow(
                transfer_details=transfer_details, is_provider_push=False
            )

            transfer_id = transfer_process.transfer_process_id
            logger.info(f"Transfer process initiated: {transfer_id}")

            # Wait for credentials via SSE
            credentials = await sse_receiver.get_credentials(transfer_id)

            # Extract access token from credentials
            access_token = credentials.get("authKey") or credentials.get("token")
            if not access_token:
                raise Exception("No access token in received credentials")

            logger.info(f"Received access token for transfer {transfer_id}")

            # Call DSS service with the access token
            dss_job_id = await call_dss_f1_service_with_token(access_token, f1_request)

            return dss_job_id

        finally:
            # Stop SSE listener
            await sse_receiver.stop_listening()
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"EDC negotiation and transfer failed: {e}")
        raise


async def call_dss_f1_service_with_token(
    access_token: str, f1_request: F1ToolRequest
) -> str:
    """Call DSS F1 service using the received access token"""

    try:
        # Prepare the F1 job request
        job_request = {
            "building_id": f1_request.building_id,
            "optimization_type": f1_request.optimization_type,
            "parameters": {},
        }

        # Call DSS connector's public API using the access token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        callback_url = (
            f"http://dashboard_api:8000/webhooks/dss-callback/{f1_request.user_id}"
        )

        # Use the DSS connector's public API endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://dss_connector:19291/api/f1/jobs",  # DSS Connector Public API
                json=job_request,
                headers=headers,
                params={"callback_url": callback_url},
                timeout=30,
            )
            response.raise_for_status()

            job_data = response.json()
            dss_job_id = job_data["job_id"]
            logger.info(f"Created DSS F1 job via connector: {dss_job_id}")

            return dss_job_id

    except Exception as e:
        logger.error(f"Failed to call DSS F1 service via connector: {e}")
        # Fallback to direct API call for demo purposes
        return await call_dss_f1_service_direct(f1_request)


async def call_dss_f1_service_direct(f1_request: F1ToolRequest) -> str:
    """Fallback: Call DSS F1 service directly (for demo purposes)"""

    try:
        job_request = {
            "building_id": f1_request.building_id,
            "optimization_type": f1_request.optimization_type,
            "parameters": {},
        }

        headers = {
            "X-API-Key": "dss-backend-key",
            "Content-Type": "application/json",
        }

        callback_url = (
            f"http://dashboard_api:8000/webhooks/dss-callback/{f1_request.user_id}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DSS_API_URL}/f1/jobs",
                json=job_request,
                headers=headers,
                params={"callback_url": callback_url},
                timeout=30,
            )
            response.raise_for_status()

            job_data = response.json()
            dss_job_id = job_data["job_id"]
            logger.info(f"Created DSS F1 job (direct): {dss_job_id}")

            return dss_job_id

    except Exception as e:
        logger.error(f"Failed to call DSS F1 service directly: {e}")
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
    """Background task to process DSS F1 tool request using edcpy"""

    try:
        requests_storage[request_id]["status"] = "processing_via_edcpy"

        # Use edcpy for complete negotiation and transfer flow
        asset_id = "dss-f1-service"  # Predefined in DSS connector
        dss_job_id = await run_edcpy_negotiation_and_transfer(asset_id, f1_request)

        requests_storage[request_id]["dss_job_id"] = dss_job_id
        requests_storage[request_id]["status"] = "dss_job_running"

        logger.info(
            f"DSS F1 request {request_id} processed successfully via edcpy, DSS job: {dss_job_id}"
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
