import asyncio
import json

import httpx
import zipstream
from edcpy.edc_api import ConnectorController
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

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
    query_params: dict,
    catalog_limit: int | None = None,
) -> JSONResponse:
    request_args = await negotiate_and_get_request_args(
        asset_id,
        provider_connector_protocol_url,
        provider_connector_id,
        provider_host,
        catalog_limit=catalog_limit,
    )

    return await execute_json_request(
        request_args,
        query_params,
    )


async def run_edcpy_negotiation_and_transfer_streaming(
    asset_id: str,
    provider_connector_protocol_url: str,
    provider_connector_id: str,
    provider_host: str,
    query_params: dict,
    catalog_limit: int | None = None,
) -> StreamingResponse:
    request_args = await negotiate_and_get_request_args(
        asset_id,
        provider_connector_protocol_url,
        provider_connector_id,
        provider_host,
        catalog_limit=catalog_limit,
    )

    return await execute_streaming_request(
        request_args, query_params, filename=f"{asset_id}.json"
    )


async def negotiate_and_get_request_args(
    asset_id: str,
    provider_connector_protocol_url: str,
    provider_connector_id: str,
    provider_host: str,
    catalog_limit: int | None = None,
) -> dict:
    edc_config = create_edc_config()
    controller = ConnectorController(config=edc_config)

    sse_receiver = SSEPullCredentialsReceiver(
        DASHBOARD_CONSUMER_BACKEND_URL, DASHBOARD_API_KEY
    )

    listen_task = asyncio.create_task(sse_receiver.start_listening(provider_host))
    try:
        logger.info(f"Starting negotiation for asset {asset_id}")
        negotiation_kwargs = {
            "counter_party_protocol_url": provider_connector_protocol_url,
            "counter_party_connector_id": provider_connector_id,
            "asset_query": asset_id,
        }
        if catalog_limit is not None:
            negotiation_kwargs["catalog_limit"] = catalog_limit

        transfer_details = await controller.run_negotiation_flow(
            **negotiation_kwargs,
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


async def execute_json_request(request_args: dict, query_params: dict) -> JSONResponse:
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
                status_code=502, detail="Provider returned invalid JSON"
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
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


async def execute_multipart_request(
    request_args: dict,
    file_path: str,
    file_field_name: str = "file",
    additional_fields: dict | None = None,
    query_params: dict | None = None,
) -> dict:
    """
    Execute a multipart/form-data POST request using EDC-negotiated credentials.

    Args:
        request_args: Dict from negotiate_and_get_request_args() containing:
            - method: str (will be overridden to POST)
            - url: str (provider endpoint)
            - headers: dict (auth headers to preserve)
            - params: dict (contains contractId - will be merged with query_params)
        file_path: Path to the file to upload
        file_field_name: Name of the file field in multipart form (default: "file")
        additional_fields: Optional dict of additional form fields
        query_params: Optional additional query parameters

    Returns:
        dict: Parsed JSON response from the provider (NOT JSONResponse)
    """
    logger.info("Executing authenticated multipart POST request")

    # Build URL (preserve trailing slash pattern from other functions)
    url = ensure_url_ends_with_slash(request_args["url"])

    # Merge query params: request_args["params"] + additional query_params
    merged_params = {**request_args.get("params", {})}
    if query_params:
        merged_params.update(query_params)

    # Preserve auth headers from EDC negotiation
    headers = {**request_args.get("headers", {})}

    timeout = httpx.Timeout(
        connect=10.0,
        read=120.0,
        write=60.0,  # Longer write timeout for file upload
        pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Open file for multipart upload
        with open(file_path, "rb") as f:
            files = {file_field_name: f}

            # Additional form fields if provided
            data = additional_fields if additional_fields else None

            # POST request (explicitly, not from request_args["method"])
            response = await client.post(
                url,
                headers=headers,
                params=merged_params,
                files=files,
                data=data,
            )

        response.raise_for_status()

        try:
            payload = response.json()
            # Handle double-encoded JSON (consistent with execute_json_request)
            while isinstance(payload, str):
                payload = json.loads(payload)
            return payload
        except Exception as exc:
            logger.error("Invalid JSON from provider: %s", response.text[:500])
            raise HTTPException(
                status_code=502, detail="Provider returned invalid JSON"
            ) from exc
