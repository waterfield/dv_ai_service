import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import ENABLE_DAX
from database import get_db, get_schema, test_connection, invalidate_schema_cache
from app.schemas import ChatRequest, ChatResponse, ExecuteRequest, ExecuteResponse, IterationDetail
from app.services.llm_service import LLMService
from app.services.sql_generator import SQLGeneratorService
from app.services.dax_generator import DaxGeneratorService
from app.services.query_executor import QueryExecutorService

logger = logging.getLogger(__name__)
router = APIRouter()

_llm: LLMService | None = None
_sql_gen: SQLGeneratorService | None = None
_dax_gen: DaxGeneratorService | None = None
_executor: QueryExecutorService | None = None


def _services() -> tuple[SQLGeneratorService, DaxGeneratorService, QueryExecutorService]:
    global _llm, _sql_gen, _dax_gen, _executor
    if _sql_gen is None:
        _llm = LLMService()
        _sql_gen = SQLGeneratorService(_llm)
        _dax_gen = DaxGeneratorService(_llm)
        _executor = QueryExecutorService()
    return _sql_gen, _dax_gen, _executor


def _qid() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Generate SQL and DAX from a natural language question."""
    qid = _qid()
    sql_gen, dax_gen, _ = _services()
    try:
        schema = get_schema()
        sql, valid = sql_gen.generate(request.user_query, schema)

        dax = None
        if ENABLE_DAX:
            try:
                dax = dax_gen.generate(request.user_query, schema)
            except Exception as dax_err:
                logger.warning(f"DAX generation failed (non-critical): {dax_err}")

        return ChatResponse(
            query_id=qid,
            status="sql_generated" if valid else "validation_failed",
            user_query=request.user_query,
            sql_query=sql,
            dax_query=dax,
            error=None if valid else "Generated SQL failed validation",
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            query_id=qid, status="error", user_query=request.user_query,
            error=str(e), timestamp=datetime.now().isoformat(),
        )


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute a SQL query, auto-fixing and retrying up to 3 times on error."""
    qid = _qid()
    sql_gen, _, executor = _services()
    schema = get_schema()

    sql = request.sql_query
    retries = 0
    last_error = None
    MAX_RETRIES = 3
    iterations: list[IterationDetail] = []

    for attempt in range(MAX_RETRIES + 1):
        df, error = executor.execute(sql, db)
        if error is None:
            iterations.append(IterationDetail(attempt=attempt + 1, sql=sql, success=True))
            rows = df.to_dict(orient="records")
            return ExecuteResponse(
                query_id=qid,
                status="success",
                sql_query=sql,
                columns=list(df.columns),
                rows=rows,
                row_count=len(df),
                retries=retries,
                iterations=iterations,
                timestamp=datetime.now().isoformat(),
            )

        iterations.append(IterationDetail(attempt=attempt + 1, sql=sql, error=error, success=False))
        last_error = error
        if attempt == MAX_RETRIES:
            break

        retries += 1
        logger.warning(f"Attempt {attempt + 1} failed — asking LLM to fix. Error: {error[:200]}")
        try:
            sql = sql_gen.fix_sql(sql, error, schema)
        except Exception as fix_err:
            logger.error(f"LLM fix failed: {fix_err}")
            break

    return ExecuteResponse(
        query_id=qid,
        status="error",
        sql_query=sql,
        retries=retries,
        iterations=iterations,
        error=last_error,
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
    """Clear the schema cache so it reloads on next request (pick up filter config changes)."""
    invalidate_schema_cache()
    return {"message": "Schema cache cleared"}


@router.get("/history")
async def history(limit: int = 20):
    """Return recent query execution history."""
    *_, executor = _services()
    return {"queries": executor.get_history(limit)}


@router.get("/health")
async def health():
    connected = test_connection()
    return {"status": "healthy" if connected else "unhealthy", "database_connected": connected}
