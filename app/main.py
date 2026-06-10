import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import MCP_API_KEYS
from database import test_connection
from app.api.routes import router
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
app.mount("/mcp", _mcp_http)


@app.middleware("http")
async def mcp_auth(request: Request, call_next):
    if request.url.path.startswith("/mcp") and MCP_API_KEYS:
        key = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if key not in MCP_API_KEYS:
            return JSONResponse(status_code=401, content={"error": "Invalid or missing API key"})
    return await call_next(request)


@app.get("/")
async def root():
    return {"message": "W AI Reporting", "docs": "/docs"}
