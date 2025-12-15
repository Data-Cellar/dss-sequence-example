from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from services.edcpy_service import run_edcpy_negotiation_and_transfer
import traceback

"""
API routes for the Dashboard Mediator.

This module defines the endpoints for initiating contract negotiations and data transfers
via the Eclipse Dataspace Connector (EDC).
"""

router = APIRouter()


class NegotiationRequest(BaseModel):
    """
    Request model for initiating a negotiation and transfer process.

    Attributes:
        asset_id (str): The ID of the asset to be transferred.
        provider_connector_protocol_url (HttpUrl): The protocol URL of the provider connector.
        provider_connector_id (str): The ID of the provider connector.
        provider_host (str): The host address of the provider.
    """

    asset_id: str
    provider_connector_protocol_url: HttpUrl
    provider_connector_id: str
    provider_host: str

    @field_validator("asset_id", "provider_connector_id", "provider_host")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """
        Validate that string fields are not empty or whitespace only.

        Args:
            v (str): The string value to validate.

        Returns:
            str: The validated and stripped string.

        Raises:
            ValueError: If the string is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


@router.post("/connector/initiate")
async def initiate_negotiation_and_transfer(request: NegotiationRequest = Body(...)):
    """
    Initiate the negotiation and transfer process for a specific asset.

    This endpoint triggers the negotiation flow with a provider connector for a requested asset.
    It orchestrates the EDC communication and retrieves the access credentials.

    Args:
        request (NegotiationRequest): The request body containing negotiation details.

    Returns:
        dict: A dictionary containing the transfer result, including the bearer token and endpoint URL.

    Raises:
        HTTPException: If the negotiation or transfer process fails (status code 500).
    """
    try:
        return await run_edcpy_negotiation_and_transfer(
            request.asset_id,
            str(request.provider_connector_protocol_url),
            request.provider_connector_id,
            request.provider_host,
        )
    except Exception as e:
        print("FULL ERROR TRACEBACK:")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Negotiation and transfer failed: {str(e)}"
        )
