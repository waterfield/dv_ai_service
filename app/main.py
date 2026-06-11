import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from starlette.types import ASGIApp, Receive, Scope, Send

from config import MCP_API_KEYS, MCP_OAUTH_CLIENTS, MCP_JWT_SECRET
from database import test_connection
from app.api.routes import router
from app.api.oauth import router as oauth_router
from app.mcp import mcp
from app.mcp import tools, prompts  # noqa: F401 — registers @mcp.tool / @mcp.prompt decorators

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_mcp_http = mcp.http_app(path="/", transport="sse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _mcp_http.router.lifespan_context(_mcp_http):
        ok = test_connection()
        if ok:
            logger.info("Database connection verified at startup")
        else:
            logger.warning("Database connection failed at startup — check .env credentials")
        yield
    logger.info("Shutting down")


app = FastAPI(
    title="W AI Reporting",
    description="Natural language to SQL for SQL Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["api"])
app.include_router(oauth_router, tags=["auth"])


def _validate_mcp_token(auth_header: str) -> bool:
    """Returns True if the bearer token is valid (API key or JWT)."""
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return False
    # API key check (Claude Desktop / Claude Code)
    if token in MCP_API_KEYS:
        return True
    # JWT check (claude.ai OAuth flow)
    if MCP_JWT_SECRET:
        try:
            jwt.decode(token, MCP_JWT_SECRET, algorithms=["HS256"])
            return True
        except JWTError:
            pass
    return False


class MCPAuthMiddleware:
    """Pure ASGI middleware — safe for SSE streaming unlike BaseHTTPMiddleware."""
    def __init__(self, asgi_app: ASGIApp) -> None:
        self.app = asgi_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            auth_required = bool(MCP_API_KEYS or MCP_OAUTH_CLIENTS)
            if auth_required:
                headers = dict(scope.get("headers", []))
                auth = headers.get(b"authorization", b"").decode()
                if not _validate_mcp_token(auth):
                    response = JSONResponse(
                        status_code=401,
                        content={"error": "Invalid or missing API key"},
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


app.mount("/mcp", _mcp_http)
app.add_middleware(MCPAuthMiddleware)


@app.get("/")
async def root():
    return {"message": "W AI Reporting", "docs": "/docs"}
