import asyncio
from logger_config import logger
from edc_connector.edc_config import create_edc_config
from edc_connector.sse_receiver import SSEPullCredentialsReceiver
from edcpy.edc_api import ConnectorController
from config import DASHBOARD_BACKEND_URL, DASHBOARD_API_KEY


async def run_edcpy_negotiation_and_transfer(
        asset_id: str,
        provider_connector_protocol_url: str,
        provider_connector_id: str,
        provider_host: str) -> dict:
    """Use edcpy to handle contract negotiation and transfer process"""
    try:
        # Initialize EDC controller with custom config
        edc_config = create_edc_config()
        controller = ConnectorController(config=edc_config)

        # Start SSE listener for credentials
        sse_receiver = SSEPullCredentialsReceiver(
            DASHBOARD_BACKEND_URL, DASHBOARD_API_KEY)

        # Start listening in the background
        listen_task = asyncio.create_task(
            sse_receiver.start_listening(provider_host))

        try:
            # Run negotiation flow
            logger.info(f"Starting negotiation for asset {asset_id}")

            transfer_details = await controller.run_negotiation_flow(
                counter_party_protocol_url=provider_connector_protocol_url,
                counter_party_connector_id=provider_connector_id,
                asset_query=asset_id
            )

            # Run transfer flow
            logger.info("Starting transfer process")
            transfer_id = await controller.run_transfer_flow(
                transfer_details=transfer_details, is_provider_push=False
            )

            logger.info(f"Transfer process initiated: {transfer_id}")

            # Wait for credentials via SSE
            credentials = await sse_receiver.get_credentials(transfer_id)

            # Extract access token from credentials
            # The SSE message contains auth_code field with the JWT token
            bearer_token = credentials.get("auth_code")

            # Also get the endpoint URL from the credentials
            endpoint_url = credentials.get("endpoint")

            if not bearer_token:
                logger.error(
                    f"No access token in received credentials for transfer {transfer_id}")
                raise Exception(
                    "No auth_code (access token) in received credentials")

            if not endpoint_url:
                logger.error(
                    f"No endpoint URL in received credentials for transfer {transfer_id}")
                raise Exception("No endpoint in received credentials")

            return {"bearer_token": bearer_token, "endpoint_url": endpoint_url}

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
