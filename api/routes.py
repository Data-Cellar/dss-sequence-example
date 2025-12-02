from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, HttpUrl, field_validator
from services.edcpy_service import run_edcpy_negotiation_and_transfer

router = APIRouter()


class NegotiationRequest(BaseModel):
    asset_id: str
    provider_connector_protocol_url: HttpUrl
    provider_connector_id: str
    provider_host: str

    @field_validator("asset_id", "provider_connector_id", "provider_host")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


@router.post("/connector/initiate")
async def initiate_negotiation_and_transfer(
        request: NegotiationRequest = Body(...)):
    try:
        return await run_edcpy_negotiation_and_transfer(
            request.asset_id,
            str(request.provider_connector_protocol_url),
            request.provider_connector_id,
            request.provider_host
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Negotiation and transfer failed: {str(e)}"
        )
