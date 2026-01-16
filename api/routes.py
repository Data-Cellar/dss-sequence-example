from fastapi import APIRouter, Body, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, field_validator, Field
from typing import Dict, Union, Optional

from auth import keycloak_auth
from services.edcpy_service import (
    run_edcpy_negotiation_and_transfer,
    run_edcpy_negotiation_and_transfer_streaming,
)

QueryValue = Union[str, int, float, bool]

router = APIRouter()


class NegotiationRequest(BaseModel):
    asset_id: str
    provider_connector_protocol_url: HttpUrl
    provider_connector_id: str
    provider_host: str
    query_params: Optional[Dict[str, QueryValue]] = None
    catalog_limit: Optional[int] = Field(default=10000, ge=1)

    @field_validator("asset_id", "provider_connector_id", "provider_host")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
@router.post("/datasets/transfer")
async def initiate_negotiation_and_transfer(
    request: NegotiationRequest = Body(...),
    user: dict = Depends(keycloak_auth),
):
    try:
        return await run_edcpy_negotiation_and_transfer(
            asset_id=request.asset_id,
            provider_connector_protocol_url=str(
                request.provider_connector_protocol_url
            ),
            provider_connector_id=request.provider_connector_id,
            provider_host=request.provider_host,
            query_params=request.query_params or {},
            catalog_limit=request.catalog_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Negotiation and transfer failed: {exc}",
        )

@router.post("/datasets/transfer/stream")
async def initiate_negotiation_and_transfer_stream(
    request: NegotiationRequest = Body(...),
    user: dict = Depends(keycloak_auth),
):
    try:
        return await run_edcpy_negotiation_and_transfer_streaming(
            asset_id=request.asset_id,
            provider_connector_protocol_url=str(
                request.provider_connector_protocol_url
            ),
            provider_connector_id=request.provider_connector_id,
            provider_host=request.provider_host,
            query_params=request.query_params or {},
            catalog_limit=request.catalog_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Streaming negotiation and transfer failed: {exc}",
        )
