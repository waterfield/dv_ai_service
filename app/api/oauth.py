"""OAuth2 endpoints — authorization code + client credentials flows for MCP access."""
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
from jose import jwt

from config import MCP_OAUTH_CLIENTS, MCP_JWT_SECRET, MCP_JWT_EXPIRY_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store: code → {client_id, redirect_uri, code_challenge, code_challenge_method, expires_at}
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
    for c in [c for c, v in _auth_codes.items() if v["expires_at"] < now]:
        del _auth_codes[c]


def _oauth_error(error: str, description: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": error, "error_description": description},
    )


# ---------------------------------------------------------------------------
# OAuth2 Authorization Server Metadata — RFC 8414
# Claude AI fetches this to discover authorize + token endpoints
# Served at both /.well-known/oauth-authorization-server and
#              /mcp/.well-known/oauth-authorization-server (via /mcp prefix mount)
# ---------------------------------------------------------------------------

def _base_url(request: Request) -> str:
    """Public base URL, honoring X-Forwarded-Proto from nginx."""
    proto = request.headers.get("x-forwarded-proto")
    base = str(request.base_url).rstrip("/")
    if proto:
        # rewrite scheme to whatever nginx terminated (https)
        rest = base.split("://", 1)[-1]
        base = f"{proto}://{rest}"
    return base


@router.get("/.well-known/oauth-authorization-server", tags=["auth"])
async def oauth_metadata(request: Request):
    base = _base_url(request)
    return JSONResponse({
        "issuer":                                base,
        "authorization_endpoint":                f"{base}/mcp/authorize",
        "token_endpoint":                        f"{base}/mcp/oauth/token",
        "registration_endpoint":                 f"{base}/mcp/register",
        "response_types_supported":              ["code"],
        "grant_types_supported":                 ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported":      ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
        "scopes_supported":                      ["read"],
    })


@router.get("/.well-known/oauth-protected-resource", tags=["auth"])
async def protected_resource_metadata(request: Request):
    """RFC 9728 — tells Claude which authorization server protects this MCP resource."""
    base = _base_url(request)
    return JSONResponse({
        "resource":              f"{base}/mcp",
        "authorization_servers": [base],
        "scopes_supported":      ["read"],
        "bearer_methods_supported": ["header"],
    })


# Dynamic Client Registration (RFC 7591) — Claude AI registers itself and gets
# back the pre-configured client_id. Accepts any registration request.
@router.post("/register", tags=["auth"])
async def register_client(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    # Return the single configured client. If multiple, return the first.
    client_id = next(iter(MCP_OAUTH_CLIENTS), "claude_ai")
    client_secret = MCP_OAUTH_CLIENTS.get(client_id, "")
    return JSONResponse(status_code=201, content={
        "client_id":                  client_id,
        "client_secret":              client_secret,
        "client_id_issued_at":        0,
        "client_secret_expires_at":   0,
        "redirect_uris":              body.get("redirect_uris", []),
        "grant_types":                ["authorization_code", "client_credentials"],
        "response_types":             ["code"],
        "token_endpoint_auth_method": "client_secret_post",
    })


# ---------------------------------------------------------------------------
# Step 1 — Consent page (GET /authorize)
# ---------------------------------------------------------------------------

@router.get("/authorize", response_class=HTMLResponse, tags=["auth"])
async def authorize_get(
    response_type:         str = "",
    client_id:             str = "",
    redirect_uri:          str = "",
    state:                 str = "",
    code_challenge:        str = "",
    code_challenge_method: str = "S256",
    scope:                 str = "",
):
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
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f4f8; display: flex; align-items: center;
            justify-content: center; min-height: 100vh; margin: 0; }}
    .card {{ background: #fff; border-radius: 12px; padding: 40px;
             box-shadow: 0 4px 24px rgba(0,0,0,.1); text-align: center; }}
    h1 {{ font-size: 20px; font-weight: 700; color: #0d3344; margin-bottom: 24px; }}
    button {{ padding: 13px 40px; background: #f5a623; color: #fff; border: none;
              border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }}
    button:hover {{ background: #e09410; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>W AI Reporting</h1>
    <form method="POST" action="/mcp/authorize">
      <input type="hidden" name="client_id"             value="{client_id}">
      <input type="hidden" name="redirect_uri"          value="{redirect_uri}">
      <input type="hidden" name="state"                 value="{state}">
      <input type="hidden" name="code_challenge"        value="{code_challenge}">
      <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
      <button type="submit">Authorize</button>
    </form>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Step 2 — Issue code and redirect (POST /authorize)
# ---------------------------------------------------------------------------

@router.post("/authorize", tags=["auth"])
async def authorize_post(
    client_id:             str  = Form(...),
    redirect_uri:          str  = Form(...),
    state:                 str  = Form(""),
    code_challenge:        str  = Form(""),
    code_challenge_method: str  = Form("S256"),
):
    if client_id not in MCP_OAUTH_CLIENTS:
        logger.warning(f"OAuth authorize failed: unknown client_id={client_id!r}")
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

    params: dict = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}", status_code=302)


# ---------------------------------------------------------------------------
# Step 3 — Token exchange (POST /oauth/token)
# Accepts application/x-www-form-urlencoded (OAuth2 standard)
# ---------------------------------------------------------------------------

@router.post("/oauth/token", tags=["auth"])
async def token(
    grant_type:    str           = Form(...),
    client_id:     Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    code:          Optional[str] = Form(None),
    redirect_uri:  Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
):
    if not MCP_JWT_SECRET:
        return _oauth_error("server_error", "JWT secret not configured", 503)

    # --- authorization_code ---
    if grant_type == "authorization_code":
        if not code:
            return _oauth_error("invalid_request", "code is required")
        _purge_expired()
        pending = _auth_codes.pop(code, None)
        if pending is None:
            return _oauth_error("invalid_grant", "Authorization code unknown or expired")
        if redirect_uri and pending["redirect_uri"] != redirect_uri:
            return _oauth_error("invalid_grant", "redirect_uri mismatch")
        if pending["code_challenge"]:
            if not code_verifier:
                return _oauth_error("invalid_request", "code_verifier required")
            if not _verify_pkce(code_verifier, pending["code_challenge"], pending["code_challenge_method"]):
                return _oauth_error("invalid_grant", "PKCE verification failed")
        cid = pending["client_id"]
        logger.info(f"Token issued (authorization_code) client_id={cid!r}")
        return JSONResponse({
            "access_token": _issue_jwt(cid),
            "token_type":   "bearer",
            "expires_in":   MCP_JWT_EXPIRY_SECONDS,
        })

    # --- client_credentials ---
    if grant_type == "client_credentials":
        if not MCP_OAUTH_CLIENTS:
            return _oauth_error("server_error", "OAuth not configured", 503)
        expected = MCP_OAUTH_CLIENTS.get(client_id or "")
        if expected is None or expected != client_secret:
            logger.warning(f"OAuth failed: bad credentials for client_id={client_id!r}")
            return _oauth_error("invalid_client", "Invalid client credentials", 401)
        logger.info(f"Token issued (client_credentials) client_id={client_id!r}")
        return JSONResponse({
            "access_token": _issue_jwt(client_id),
            "token_type":   "bearer",
            "expires_in":   MCP_JWT_EXPIRY_SECONDS,
        })

    return _oauth_error("unsupported_grant_type", f"grant_type={grant_type!r} not supported")
