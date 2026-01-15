import asyncio
import httpx
import json
import zipstream

from edcpy.edc_api import ConnectorController
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import HTTPException
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
    query_params: dict
) -> JSONResponse:
    request_args = await negotiate_and_get_request_args(
        asset_id,
        provider_connector_protocol_url,
        provider_connector_id,
        provider_host
    )

    return await execute_json_request(
        request_args,
        query_params
    )

async def run_edcpy_negotiation_and_transfer_streaming(
    asset_id: str,
    provider_connector_protocol_url: str,
    provider_connector_id: str,
    provider_host: str,
    query_params: dict
) -> StreamingResponse:
    request_args = await negotiate_and_get_request_args(
        asset_id,
        provider_connector_protocol_url,
        provider_connector_id,
        provider_host,
    )

    return await execute_streaming_request(
        request_args,
        query_params,
        filename=f"{asset_id}.json"
    )

async def negotiate_and_get_request_args(
        asset_id: str,
        provider_connector_protocol_url: str,
        provider_connector_id: str,
        provider_host: str
) -> dict:
        edc_config = create_edc_config()
        controller = ConnectorController(config=edc_config)

        sse_receiver = SSEPullCredentialsReceiver(
            DASHBOARD_CONSUMER_BACKEND_URL, DASHBOARD_API_KEY
        )

        listen_task = asyncio.create_task(sse_receiver.start_listening(provider_host))
        try:
            logger.info(f"Starting negotiation for asset {asset_id}")

            transfer_details = await controller.run_negotiation_flow(
                counter_party_protocol_url=provider_connector_protocol_url,
                counter_party_connector_id=provider_connector_id,
                asset_query=asset_id,
            )

            logger.info("Starting transfer process")
            transfer_id = await controller.run_transfer_flow(
                transfer_details=transfer_details, is_provider_push=False
            )

            logger.info(f"Transfer process initiated: {transfer_id}")
            logger.info("Awaiting transfer credentials via SSE")
            pull_message = await sse_receiver.get_credentials(transfer_id)
            
            return pull_message["request_args"]
        finally:
            await sse_receiver.stop_listening()
            listen_task.cancel()

            try:
                await listen_task
            except asyncio.CancelledError:
                pass

async def execute_json_request(
        request_args: dict,
        query_params: dict
) -> JSONResponse:
    logger.info("Executing authenticated data request")

    request_args = {**request_args}
    request_args["url"] = ensure_url_ends_with_slash(request_args["url"])
    request_args["params"] = query_params

    timeout = httpx.Timeout(
        connect=10.0,
        read=120.0,
        write=10.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(**request_args)

        try:
            payload = response.json()
            while isinstance(payload, str):
                payload = json.loads(payload)
        except Exception as exc:
            logger.error("Invalid JSON from provider: %s", response.text[:500])
            raise HTTPException(
                status_code=502,
                detail="Provider returned invalid JSON"
            ) from exc

        return JSONResponse(content=payload)
    
async def execute_streaming_request(
    request_args: dict,
    query_params: dict,
    *,
    filename: str,
) -> StreamingResponse:
    logger.info("Executing authenticated ZIP STREAMING request")

    request_args = {**request_args}
    request_args["url"] = ensure_url_ends_with_slash(request_args["url"])
    request_args["params"] = query_params

    timeout = httpx.Timeout(
        connect=10.0,
        read=None,
        write=10.0,
        pool=10.0,
    )

    z = zipstream.ZipStream()

    def provider_stream():
        """
        Synchronous byte generator required by zipstream-ng
        """
        with httpx.Client(timeout=timeout) as client:
            with client.stream(**request_args) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    if chunk:
                        yield chunk

    z.add(provider_stream(), arcname=filename)

    zip_name = filename.rsplit(".", 1)[0] + ".zip"

    return StreamingResponse(
        z,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_name}"'
        },
    )