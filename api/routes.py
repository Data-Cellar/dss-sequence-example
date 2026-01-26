import tempfile
import shutil
import os
import json
from fastapi import APIRouter, Body, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, HttpUrl, field_validator, Field
from typing import Dict, Union, Optional

from json import JSONDecodeError

from auth import keycloak_auth
from services.edcpy_service import (
    run_edcpy_negotiation_and_transfer,
    run_edcpy_negotiation_and_transfer_streaming,
    run_edcpy_negotiation_and_transfer_multipart
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
    
class NegotiationWithJsonPayloadRequest(NegotiationRequest):
    payload_json: str
    
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
    
@router.post("/tools/transfer")
async def initiate_multipart_file_transfer(
    request: NegotiationWithJsonPayloadRequest,
    user: dict = Depends(keycloak_auth)
):
    tmp_path = None
    try:
        try:
            parsed = json.loads(request.payload_json)
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="input is not valid JSON"
            ) from exc
        
        json_bytes = json.dumps(
            parsed,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(json_bytes)
            tmp_path = tmp.name

        return await run_edcpy_negotiation_and_transfer_multipart(
            asset_id=request.asset_id,
            provider_connector_protocol_url=str(
                request.provider_connector_protocol_url
            ),
            provider_connector_id=request.provider_connector_id,
            provider_host=request.provider_host,
            file_path=tmp_path,
            query_params=request.query_params or {},
            catalog_limit=request.catalog_limit,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Multipart negotiation and transfer failed",
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
