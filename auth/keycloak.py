import os
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from cachetools import TTLCache

bearer_scheme = HTTPBearer(auto_error=False)

KEYCLOAK_DOMAIN = os.getenv("KEYCLOAK_DOMAIN")
REALM_NAME = os.getenv("REALM_NAME")
ALGORITHM = os.getenv("ENCRYPTION_ALGORITHM", "RS256")

JWKS_URL = (
    f"{KEYCLOAK_DOMAIN}/realms/{REALM_NAME}"
    "/protocol/openid-connect/certs"
)
ISSUER = f"{KEYCLOAK_DOMAIN}/realms/{REALM_NAME}"

jwks_cache = TTLCache(maxsize=1, ttl=600)

async def get_jwks():
    if "jwks" in jwks_cache:
        return jwks_cache["jwks"]

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
        jwks = resp.json()
    
    jwks_cache["jwks"] = jwks
    return jwks

async def get_public_key(token: str):
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header.")
    
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing kid.")
    
    jwks = await get_jwks()

    for key in jwks["keys"]:
        if key["kid"] == kid:
            return key
        
async def verify_token(token: str):
    try:
        key = await get_public_key(token)

        payload = jwt.decode(
            token=token, 
            key=key, 
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={
                "verify_aud": False
            },
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    
async def keycloak_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    
    token = credentials.credentials
    return await verify_token(token)



# {
#   "asset_id": "471aa05d-75e0-4a96-8ca2-90074cb5d3f6",
#   "provider_connector_protocol_url": "https://ctic.dcserver.cticpoc.com/protocol",
#   "provider_connector_id": "ctic",
#   "provider_host": "ctic.dcserver.cticpoc.com",
#   "query_params": {"timeseries_id": "bf518303-9da9-41f4-93b7-eb4932710666", "granularity": "7200", "method": "sum"}
# }