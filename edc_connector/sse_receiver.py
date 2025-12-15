import httpx
import asyncio
import pprint
import json
from typing import Dict, Any

from config import (
    AUTHORIZATION_HEADER,
    ACCEPT_HEADER,
    SSE_CONTENT_TYPE,
    SSE_DATA_PREFIX_LENGTH,
    CREDENTIALS_TIMEOUT_SECONDS,
    SSE_POLL_INTERVAL_SECONDS,
)
from utils.http import _extract_hostname
from logger_config import logger

"""
SSE Receiver for EDC Credentials.

This module implements a receiver for Server-Sent Events (SSE) to capture access credentials
sent by the consumer backend during the data transfer process.
"""


class SSEPullCredentialsReceiver:
    """
    Handles SSE-based access token reception from consumer backend.

    This class establishes a connection to the consumer backend's SSE endpoint
    and listens for events containing transfer credentials.

    Attributes:
        consumer_backend_url (str): The base URL of the consumer backend.
        api_key (str): The API key for authentication with the backend.
        credentials (Dict[str, Any]): A dictionary storing received credentials keyed by transfer ID.
        _listening (bool): Flag indicating if the receiver is currently listening.
        _client (httpx.AsyncClient): The HTTP client used for the SSE connection.
    """

    def __init__(self, consumer_backend_url: str, api_key: str):
        """
        Initialize the SSE receiver.

        Args:
            consumer_backend_url (str): The URL of the consumer backend service.
            api_key (str): The API key used to authenticate requests to the backend.
        """
        self.consumer_backend_url = consumer_backend_url
        self.api_key = api_key
        self.credentials = {}
        self._listening = False
        self._client = None

    async def start_listening(self, provider_host: str):
        """
        Start listening for SSE messages from the consumer backend.

        Establishes a persistent connection to the SSE endpoint and processes incoming
        events to extract transfer credentials.

        Args:
            provider_host (str): The hostname of the data provider to subscribe to.

        Raises:
            Exception: If the connection fails or is interrupted unexpectedly.
        """

        provider_host = _extract_hostname(provider_host)
        sse_url = f"{self.consumer_backend_url}/pull/stream/provider/{provider_host}"

        headers = {
            AUTHORIZATION_HEADER: f"Bearer {self.api_key}",
            ACCEPT_HEADER: SSE_CONTENT_TYPE,
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
        """
        Process individual SSE message lines.

        Parses the 'data' field from the SSE message, extracts the transfer ID,
        and stores the credentials in the internal dictionary.

        Args:
            line (str): A single line of text received from the SSE stream.
        """

        if line.startswith("data: "):
            try:
                data = json.loads(
                    line[SSE_DATA_PREFIX_LENGTH:]
                )  # Remove 'data: ' prefix

                transfer_id = data.get("transfer_process_id")

                if transfer_id:
                    self.credentials[transfer_id] = data
                    logger.info(f"Received credentials for transfer {transfer_id}:")

                    logger.debug(
                        f"SSE message for transfer '{transfer_id}':\n{pprint.pformat(data)}"
                    )
            except json.JSONDecodeError:
                pass

    async def get_credentials(
        self, transfer_id: str, timeout: int = CREDENTIALS_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Wait for and retrieve credentials for a specific transfer.

        Polls the internal credentials storage until the credentials for the given
        transfer ID are available or the timeout is reached.

        Args:
            transfer_id (str): The ID of the transfer process to retrieve credentials for.
            timeout (int, optional): The maximum time to wait in seconds. Defaults to CREDENTIALS_TIMEOUT_SECONDS.

        Returns:
            Dict[str, Any]: The credentials dictionary for the transfer.

        Raises:
            TimeoutError: If the credentials are not received within the specified timeout.
        """

        for _ in range(timeout):
            if transfer_id in self.credentials:
                return self.credentials[transfer_id]

            await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)

        raise TimeoutError(f"Credentials not received for transfer {transfer_id}")

    async def stop_listening(self):
        """
        Stop listening for SSE messages.

        Sets the listening flag to False and closes the HTTP client connection.
        """

        self._listening = False

        if self._client:
            await self._client.aclose()
