import asyncio
import httpx
import pprint

from edcpy.edc_api import ConnectorController

from config import DASHBOARD_API_KEY, DASHBOARD_CONSUMER_BACKEND_URL
from edc_connector.edc_config import create_edc_config
from edc_connector.sse_receiver import SSEPullCredentialsReceiver
from logger_config import logger
from utils.http import ensure_url_ends_with_slash


"""
EDC Service Wrapper.

This module provides a high-level service to handle the orchestration of EDC contract negotiation
and data transfer, utilizing the `edcpy` library and SSE for credential retrieval.
"""


async def run_edcpy_negotiation_and_transfer(
    asset_id: str,
    provider_connector_protocol_url: str,
    provider_connector_id: str,
    provider_host: str,
) -> dict:
    """
    Use edcpy to handle contract negotiation and transfer process.

    This function initializes the EDC controller, starts an SSE listener for credentials,
    negotiates a contract for the specified asset, and initiates the data transfer.
    It waits for the access token and endpoint URL to be delivered via SSE.

    Args:
        asset_id (str): The unique identifier of the asset to transfer.
        provider_connector_protocol_url (str): The protocol URL of the provider's EDC connector.
        provider_connector_id (str): The identifier of the provider's connector.
        provider_host (str): The hostname of the provider.

    Returns:
        dict: A dictionary containing the access credentials:
            - bearer_token (str): The JWT access token.
            - endpoint_url (str): The URL to access the data.

    Raises:
        Exception: If the negotiation fails, transfer fails, or credentials are invalid/missing.
    """
    try:
        # Initialize EDC controller with custom config
        edc_config = create_edc_config()
        controller = ConnectorController(config=edc_config)

        # Start SSE listener for credentials
        sse_receiver = SSEPullCredentialsReceiver(
            DASHBOARD_CONSUMER_BACKEND_URL, DASHBOARD_API_KEY
        )

        # Step 1: Start listening in the background
        listen_task = asyncio.create_task(sse_receiver.start_listening(provider_host))

        try:
            # Step 2: Negotiate contract
            logger.info(f"Starting negotiation for asset {asset_id}")

            transfer_details = await controller.run_negotiation_flow(
                counter_party_protocol_url=provider_connector_protocol_url,
                counter_party_connector_id=provider_connector_id,
                asset_query=asset_id,
            )

            # Step 3: Start transfer
            logger.info("Starting transfer process")
            transfer_id = await controller.run_transfer_flow(
                transfer_details=transfer_details, is_provider_push=False
            )

            logger.info(f"Transfer process initiated: {transfer_id}")

            # Step 4: Get credentials
            logger.info("Awaiting transfer credentials via SSE")
            pull_message = await sse_receiver.get_credentials(transfer_id)
            
            # Step 5: Execute authenticated request
            return await execute_authenticated_request(pull_message["request_args"])


            # return {"bearer_token": bearer_token, "endpoint_url": endpoint_url}

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

async def execute_authenticated_request(request_args: dict) -> str:
    """
    Execute an authenticated data request using provided credentials.

    Args:
        request_args: Dictionary containing HTTP request arguments (url, method, headers, etc.)

    Returns:
        Response text from the authenticated request
    """

    logger.info("Step 5: Executing authenticated data request")

    # IMPORTANT: Normalize URL to include trailing slash (required by some endpoints)
    request_args = {**request_args}
    request_args["url"] = ensure_url_ends_with_slash(request_args["url"])

    # Configure timeout for data transfer requests (can be long-running)
    timeout = httpx.Timeout(
        connect=10.0,
        read=120.0,
        write=10.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(**request_args)
        data = response.text

        logger.info(
            "Data transfer completed successfully ✅\n--- Response preview ---\n%s\n--- End of preview ---",
            pprint.pformat(data, width=100, compact=True)[
                :1024
            ],
        )

        return data