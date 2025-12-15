import argparse
import asyncio
import os
import sys

# Add project root to sys.path to allow imports from root modules
sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv(override=True)

import config  # noqa: E402
from logger_config import logger  # noqa: E402
from services.edcpy_service import run_edcpy_negotiation_and_transfer  # noqa: E402


async def main():
    parser = argparse.ArgumentParser(
        description="Run E2E EDC Negotiation and Transfer Test"
    )

    default_provider_url = config.DASHBOARD_CONNECTOR_PROTOCOL_URL

    parser.add_argument(
        "--asset-id", default="test-asset", help="Asset ID to negotiate"
    )
    parser.add_argument(
        "--provider-url",
        default=default_provider_url,
        help="Provider Connector Protocol URL",
    )
    parser.add_argument(
        "--provider-id",
        default=config.DASHBOARD_PARTICIPANT_ID,
        help="Provider Connector ID",
    )
    parser.add_argument(
        "--provider-host", default=config.DASHBOARD_CONNECTOR_HOST, help="Provider Host"
    )

    args = parser.parse_args()

    try:
        logger.info("Arguments: %s", args)

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
