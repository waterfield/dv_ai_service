"""OAuth2 endpoints — client credentials + authorization code flows for MCP access."""
import base64
import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from jose import jwt

from config import MCP_OAUTH_CLIENTS, MCP_JWT_SECRET, MCP_JWT_EXPIRY_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for pending authorization codes
# { code: {client_id, redirect_uri, code_challenge, code_challenge_method, expires_at} }
_auth_codes: dict[str, dict] = {}
_CODE_TTL = 300  # 5 minutes


def _issue_jwt(client_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": client_id,
        "iat": now,
        "exp": now + timedelta(seconds=MCP_JWT_EXPIRY_SECONDS),
    }
    return jwt.encode(payload, MCP_JWT_SECRET, algorithm="HS256")


def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return computed == code_challenge
    if method == "plain":
        return code_verifier == code_challenge
    return False


def _purge_expired():
    now = time.time()
    expired = [c for c, v in _auth_codes.items() if v["expires_at"] < now]
    for c in expired:
        del _auth_codes[c]


# ---------------------------------------------------------------------------
# Authorization code flow
# ---------------------------------------------------------------------------

@router.get("/authorize", response_class=HTMLResponse, tags=["auth"])
async def authorize(
    response_type: str = "",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
    scope: str = "",
):
    """Step 1 — render consent page. Claude AI redirects users here."""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported_response_type")
    if not client_id or client_id not in MCP_OAUTH_CLIENTS:
        raise HTTPException(status_code=400, detail="invalid_client")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="invalid_request: redirect_uri required")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>W AI Reporting — Connect</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f4f8; display: flex; align-items: center;
            justify-content: center; min-height: 100vh; }}
    .card {{ background: #fff; border-radius: 12px; padding: 40px;
             box-shadow: 0 4px 24px rgba(0,0,0,.1); width: 100%; max-width: 420px; }}
    h1 {{ font-size: 22px; font-weight: 700; color: #0d3344; margin-bottom: 6px; }}
    p.sub {{ font-size: 14px; color: #666; margin-bottom: 28px; }}
    label {{ font-size: 13px; font-weight: 600; color: #333; display: block; margin-bottom: 6px; }}
    .client-id {{ background: #f5f7fa; border: 1px solid #dde; border-radius: 6px;
                  padding: 10px 14px; font-size: 14px; color: #444; margin-bottom: 20px; }}
    input[type=password] {{ width: 100%; padding: 10px 14px; border: 1px solid #ccd;
                            border-radius: 6px; font-size: 14px; margin-bottom: 24px;
                            outline: none; transition: border .2s; }}
    input[type=password]:focus {{ border-color: #f5a623; }}
    button {{ width: 100%; padding: 12px; background: #f5a623; color: #fff;
              border: none; border-radius: 6px; font-size: 15px; font-weight: 600;
              cursor: pointer; transition: background .2s; }}
    button:hover {{ background: #e09410; }}
    .err {{ color: #c0392b; font-size: 13px; margin-bottom: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>W AI Reporting</h1>
    <p class="sub">Authorize access to AFE financial and master data.</p>
    <form method="POST" action="/authorize">
      <input type="hidden" name="client_id"             value="{client_id}">
      <input type="hidden" name="redirect_uri"          value="{redirect_uri}">
      <input type="hidden" name="state"                 value="{state}">
      <input type="hidden" name="code_challenge"        value="{code_challenge}">
      <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
      <label>Client ID</label>
      <div class="client-id">{client_id}</div>
      <label for="secret">Client Secret</label>
      <input type="password" id="secret" name="client_secret"
             placeholder="Enter client secret" autofocus required>
      <button type="submit">Authorize</button>
    </form>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/authorize", tags=["auth"])
async def authorize_submit(
    client_id:             str = Form(...),
    client_secret:         str = Form(...),
    redirect_uri:          str = Form(...),
    state:                 str = Form(""),
    code_challenge:        str = Form(""),
    code_challenge_method: str = Form("S256"),
):
    """Step 2 — validate secret, issue code, redirect back to client."""
    expected = MCP_OAUTH_CLIENTS.get(client_id)
    if expected is None or expected != client_secret:
        logger.warning(f"OAuth authorize failed: bad secret for client_id={client_id!r}")
        raise HTTPException(status_code=401, detail="invalid_client")

    _purge_expired()
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id":             client_id,
        "redirect_uri":          redirect_uri,
        "code_challenge":        code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at":            time.time() + _CODE_TTL,
    }
    logger.info(f"OAuth code issued for client_id={client_id!r}")

    params = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(
        url=f"{redirect_uri}?{urlencode(params)}",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# Token endpoint — client_credentials + authorization_code
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    grant_type:    str
    client_id:     Optional[str] = None
    client_secret: Optional[str] = None
    code:          Optional[str] = None
    redirect_uri:  Optional[str] = None
    code_verifier: Optional[str] = None


@router.post("/oauth/token", tags=["auth"])
async def token(body: TokenRequest):
    if not MCP_JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT secret not configured")

    # --- authorization_code ---
    if body.grant_type == "authorization_code":
        if not body.code:
            raise HTTPException(status_code=400, detail="invalid_request: code required")

        _purge_expired()
        pending = _auth_codes.pop(body.code, None)
        if pending is None:
            raise HTTPException(status_code=400, detail="invalid_grant: unknown or expired code")

        if pending["redirect_uri"] != body.redirect_uri:
            raise HTTPException(status_code=400, detail="invalid_grant: redirect_uri mismatch")

        # Verify PKCE if challenge was provided
        if pending["code_challenge"]:
            if not body.code_verifier:
                raise HTTPException(status_code=400, detail="invalid_request: code_verifier required")
            if not _verify_pkce(body.code_verifier, pending["code_challenge"], pending["code_challenge_method"]):
                raise HTTPException(status_code=400, detail="invalid_grant: PKCE verification failed")

        client_id = pending["client_id"]
        logger.info(f"OAuth token issued (authorization_code) for client_id={client_id!r}")
        return JSONResponse({
            "access_token": _issue_jwt(client_id),
            "token_type":   "bearer",
            "expires_in":   MCP_JWT_EXPIRY_SECONDS,
        })

    # --- client_credentials ---
    if body.grant_type == "client_credentials":
        if not MCP_OAUTH_CLIENTS:
            raise HTTPException(status_code=503, detail="OAuth not configured on this server")
        expected = MCP_OAUTH_CLIENTS.get(body.client_id or "")
        if expected is None or expected != body.client_secret:
            logger.warning(f"OAuth failed: invalid credentials for client_id={body.client_id!r}")
            raise HTTPException(status_code=401, detail="invalid_client")
        logger.info(f"OAuth token issued (client_credentials) for client_id={body.client_id!r}")
        return JSONResponse({
            "access_token": _issue_jwt(body.client_id),
            "token_type":   "bearer",
            "expires_in":   MCP_JWT_EXPIRY_SECONDS,
        })

    raise HTTPException(status_code=400, detail="unsupported_grant_type")
