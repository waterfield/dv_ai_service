import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import ENABLE_REASONING
from database import get_db, get_schema, test_connection, invalidate_schema_cache
from app.schemas import ChatRequest, ChatResponse, ExecuteRequest, ExecuteResponse
from app.services.llm_service import LLMService
from app.services.template_service import TemplateService
from app.services.query_executor import QueryExecutorService

logger = logging.getLogger(__name__)
router = APIRouter()

_llm: LLMService | None = None
_template_svc: TemplateService | None = None
_executor: QueryExecutorService | None = None


def _services() -> tuple[TemplateService, QueryExecutorService]:
    global _llm, _template_svc, _executor
    if _template_svc is None:
        _llm = LLMService()
        _template_svc = TemplateService(_llm)
        _executor = QueryExecutorService()
    return _template_svc, _executor


def _qid() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Resolve a natural language question to a pre-written SQL template + bind params."""
    qid = _qid()
    template_svc, _ = _services()
    try:
        sql, params, template_key, reasoning = template_svc.resolve(request.user_query)
        return ChatResponse(
            query_id=qid,
            status="sql_generated",
            user_query=request.user_query,
            sql_query=sql,
            template_key=template_key,
            params=params,
            reasoning=reasoning if ENABLE_REASONING else None,
            timestamp=datetime.now().isoformat(),
        )
    except ValueError as e:
        return ChatResponse(
            query_id=qid,
            status="no_template",
            user_query=request.user_query,
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            query_id=qid,
            status="error",
            user_query=request.user_query,
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute a pre-written SQL template with bind params."""
    qid = _qid()
    _, executor = _services()

    df, error = executor.execute(request.sql_query, db, params=request.params)

    if error is None:
        return ExecuteResponse(
            query_id=qid,
            status="success",
            sql_query=request.sql_query,
            columns=list(df.columns),
            rows=df.to_dict(orient="records"),
            row_count=len(df),
            timestamp=datetime.now().isoformat(),
        )

    return ExecuteResponse(
        query_id=qid,
        status="error",
        sql_query=request.sql_query,
        error=error,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/schema")
async def schema():
    """Return filtered tables and their columns."""
    try:
        s = get_schema()
        return {"table_count": len(s), "tables": s}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schema/cache")
async def clear_schema_cache():
    """Clear the schema cache so it reloads on next request."""
    invalidate_schema_cache()
    return {"message": "Schema cache cleared"}


@router.get("/history")
async def history(limit: int = 20):
    """Return recent query execution history."""
    _, executor = _services()
    return {"queries": executor.get_history(limit)}


@router.get("/health")
async def health():
    connected = test_connection()
    return {"status": "healthy" if connected else "unhealthy", "database_connected": connected}
