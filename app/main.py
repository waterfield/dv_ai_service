import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import test_connection
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/")
async def root():
    return {"message": "W AI Reporting", "docs": "/docs"}
