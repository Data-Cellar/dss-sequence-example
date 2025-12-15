import argparse
import asyncio
import os
import sys

# Add project root to sys.path to allow imports from root modules
sys.path.append(os.getcwd())

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from logger_config import logger
from services.edcpy_service import run_edcpy_negotiation_and_transfer


async def main():
    parser = argparse.ArgumentParser(
        description="Run E2E EDC Negotiation and Transfer Test"
    )
    parser.add_argument("--asset-id", required=True, help="Asset ID to negotiate")
    parser.add_argument(
        "--provider-url", required=True, help="Provider Connector Protocol URL"
    )
    parser.add_argument("--provider-id", required=True, help="Provider Connector ID")
    parser.add_argument("--provider-host", required=True, help="Provider Host")

    args = parser.parse_args()

    try:
        logger.info(f"Starting E2E test for asset {args.asset_id}")
        result = await run_edcpy_negotiation_and_transfer(
            asset_id=args.asset_id,
            provider_connector_protocol_url=args.provider_url,
            provider_connector_id=args.provider_id,
            provider_host=args.provider_host,
        )
        logger.info("Test completed successfully!")
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
