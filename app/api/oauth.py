"""OAuth2 client credentials flow for MCP endpoint access."""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from jose import jwt

from config import MCP_OAUTH_CLIENTS, MCP_JWT_SECRET, MCP_JWT_EXPIRY_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter()


class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str


@router.post("/oauth/token", tags=["auth"])
async def token(body: TokenRequest):
    if body.grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    if not MCP_OAUTH_CLIENTS:
        raise HTTPException(status_code=503, detail="OAuth not configured on this server")

    if not MCP_JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT secret not configured on this server")

    expected_secret = MCP_OAUTH_CLIENTS.get(body.client_id)
    if expected_secret is None or expected_secret != body.client_secret:
        logger.warning(f"OAuth failed: invalid credentials for client_id={body.client_id!r}")
        raise HTTPException(status_code=401, detail="invalid_client")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": body.client_id,
        "iat": now,
        "exp": now + timedelta(seconds=MCP_JWT_EXPIRY_SECONDS),
    }
    token_str = jwt.encode(payload, MCP_JWT_SECRET, algorithm="HS256")
    logger.info(f"OAuth token issued for client_id={body.client_id!r}")

    return JSONResponse({
        "access_token": token_str,
        "token_type": "bearer",
        "expires_in": MCP_JWT_EXPIRY_SECONDS,
    })
