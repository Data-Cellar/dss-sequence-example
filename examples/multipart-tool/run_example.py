"""
Multipart POST Tool Example: Direct vs EDC-mediated calls.
"""

import argparse
import asyncio
import os
import sys

# Add project root to sys.path to allow imports from root modules
sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv(override=True)

import httpx  # noqa: E402

from logger_config import logger  # noqa: E402
from services.edcpy_service import negotiate_and_get_request_args  # noqa: E402
from utils.http import ensure_url_ends_with_slash  # noqa: E402

DEFAULT_DIRECT_URL = (
    "https://loki.linksfoundation.com/datacellar/inference_battery_optimization"
)

DEFAULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "sample_payload.json")

DEFAULT_COUNTERPARTY_PROTOCOL_URL = "https://linksai.linksadsconnector.cloud/protocol"
DEFAULT_COUNTERPARTY_PARTICIPANT_ID = "linksai"
DEFAULT_COUNTERPARTY_HOST = "linksai.linksadsconnector.cloud"


def _build_multipart_file(file_path: str) -> dict:
    return {
        "input_file": (
            os.path.basename(file_path),
            open(file_path, "rb"),
            "application/json",
        )
    }


def _build_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=10.0, read=120.0, write=60.0, pool=10.0)


async def direct_multipart_call(
    url: str,
    file_path: str,
    auth_token: str | None = None,
) -> dict:
    """
    Make direct HTTP POST with multipart payload (no EDC).

    This demonstrates calling an API directly when you have:
    - The endpoint URL
    - Any required auth credentials (out-of-band)

    Args:
        url: Target endpoint URL
        file_path: Path to file to upload
        auth_token: Optional Bearer token for authentication

    Returns:
        dict: Parsed JSON response

    Note:
        Direct calls require out-of-band credential exchange.
        For production use with Data Cellar, prefer EDC-mediated calls
        which provide secure credential negotiation.
    """
    logger.info(f"Making DIRECT multipart POST to: {url}")

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with httpx.AsyncClient(timeout=_build_timeout()) as client:
        files = _build_multipart_file(file_path)
        try:
            response = await client.post(
                url,
                headers=headers,
                files=files,
            )
        finally:
            files["input_file"][1].close()

        response.raise_for_status()
        return response.json()


async def execute_multipart_request(
    request_args: dict,
    file_path: str,
) -> dict:
    """
    Execute multipart POST using EDC-provided credentials.

    Takes the request_args dict from EDC negotiation and:
    1. Overrides method to POST (EDC gives GET by default)
    2. Preserves authentication headers
    3. Makes multipart POST with file upload

    Args:
        request_args: Request configuration from EDC negotiation containing:
            - method: str (we override to POST)
            - url: str (provider endpoint)
            - headers: dict (auth headers to preserve)
            - params: dict (contains contractId)
        file_path: Path to file to upload

    Returns:
        dict: Parsed JSON response from the tool
    """
    logger.info("Executing multipart POST with EDC credentials")

    # Use method from request_args when available (default to POST).
    post_args = {
        "method": request_args.get("method", "POST").upper(),
        "url": ensure_url_ends_with_slash(request_args["url"]),
        "headers": request_args["headers"],
    }

    logger.info(f"EDC multipart POST: {post_args['url']}")

    async with httpx.AsyncClient(timeout=_build_timeout()) as client:
        files = _build_multipart_file(file_path)
        try:
            response = await client.request(
                **post_args,
                files=files,
            )
        finally:
            files["input_file"][1].close()

        logger.info(f"EDC multipart response status: {response.status_code}")
        response.raise_for_status()
        return response.json()


async def edc_multipart_call(
    asset_id: str,
    provider_url: str,
    provider_id: str,
    provider_host: str,
    file_path: str,
    catalog_limit: int | None = None,
) -> dict:
    """
    Negotiate via EDC, then make multipart POST with credentials.

    This demonstrates the EDC flow:
    1. Negotiate contract with provider connector
    2. Initiate transfer and receive credentials via SSE
    3. Use received credentials to make authenticated multipart POST

    The request_args from EDC negotiation contains:
    - method: str (typically "GET" - we override to POST)
    - url: str (provider endpoint)
    - headers: dict (auth headers to preserve)
    - params: dict (contains contractId)

    Args:
        asset_id: EDC asset identifier
        provider_url: Provider connector protocol URL
        provider_id: Provider connector ID
        provider_host: Provider host for SSE credentials
        file_path: Path to file to upload
        catalog_limit: Optional catalog query limit

    Returns:
        dict: Parsed JSON response from the tool
    """
    logger.info(f"Starting EDC negotiation for asset: {asset_id}")

    # Step 1 & 2: Negotiate and get credentials
    request_args = await negotiate_and_get_request_args(
        asset_id=asset_id,
        provider_connector_protocol_url=provider_url,
        provider_connector_id=provider_id,
        provider_host=provider_host,
        catalog_limit=catalog_limit,
    )

    logger.info("EDC negotiation complete, received credentials")
    logger.debug(f"request_args keys: {list(request_args.keys())}")

    # Step 3: Make multipart POST with EDC credentials
    # Note: execute_multipart_request overrides method to POST
    return await execute_multipart_request(
        request_args=request_args,
        file_path=file_path,
    )


async def main():
    parser = argparse.ArgumentParser(
        description="Multipart POST Example: Direct vs EDC-mediated calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct call only
  python run_example.py --mode direct --direct-url https://api.example.com/tool

  # EDC-mediated call only
  python run_example.py --mode edc --asset-id my-tool-asset

  # Both modes (default)
  python run_example.py --asset-id my-tool-asset --direct-url https://api.example.com/tool
        """,
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["direct", "edc", "both"],
        default="both",
        help="Execution mode: direct, edc, or both (default: both)",
    )

    # Direct call arguments
    parser.add_argument(
        "--direct-url",
        default=os.environ.get("DIRECT_API_URL", DEFAULT_DIRECT_URL),
        help="URL for direct API call",
    )
    parser.add_argument(
        "--direct-token",
        default=os.environ.get("DIRECT_AUTH_TOKEN"),
        help="Bearer token for direct call (optional)",
    )

    # EDC arguments
    parser.add_argument(
        "--asset-id",
        default="POST-inference_battery_optimization",
        help="Asset ID or fuzzy query for EDC negotiation",
    )
    parser.add_argument(
        "--provider-url",
        default=DEFAULT_COUNTERPARTY_PROTOCOL_URL,
        help="Provider connector protocol URL",
    )
    parser.add_argument(
        "--provider-id",
        default=DEFAULT_COUNTERPARTY_PARTICIPANT_ID,
        help="Provider connector ID",
    )
    parser.add_argument(
        "--provider-host",
        default=DEFAULT_COUNTERPARTY_HOST,
        help="Provider host",
    )
    parser.add_argument(
        "--catalog-limit",
        type=int,
        default=None,
        help="Optional catalog limit for EDC negotiation",
    )

    # Common arguments
    parser.add_argument(
        "--file-path",
        default=DEFAULT_FILE_PATH,
        help="Path to payload file",
    )

    args = parser.parse_args()

    logger.info(f"Running in mode: {args.mode}")
    logger.info(f"Using payload file: {args.file_path}")

    results = {}

    # Execute direct call if requested
    if args.mode in ("direct", "both"):
        logger.info("DIRECT CALL (no EDC)")
        try:
            results["direct"] = await direct_multipart_call(
                url=args.direct_url,
                file_path=args.file_path,
                auth_token=args.direct_token,
            )
            logger.info("Direct call succeeded!")
            logger.info(f"Response: {results['direct']}")
        except Exception as e:
            logger.error(f"Direct call failed: {e}")
            results["direct"] = {"error": str(e)}

    # Execute EDC call if requested
    if args.mode in ("edc", "both"):
        logger.info("EDC-MEDIATED CALL")
        try:
            results["edc"] = await edc_multipart_call(
                asset_id=args.asset_id,
                provider_url=args.provider_url,
                provider_id=args.provider_id,
                provider_host=args.provider_host,
                file_path=args.file_path,
                catalog_limit=args.catalog_limit,
            )
            logger.info("EDC call succeeded!")
            logger.info(f"Response: {results['edc']}")
        except Exception as e:
            logger.error(f"EDC call failed: {e}")
            results["edc"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    asyncio.run(main())
