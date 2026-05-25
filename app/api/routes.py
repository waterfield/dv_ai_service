import json
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import SHOW_TEMPLATE_DESCRIPTION, ENABLE_ANALYSIS
from database import get_db, get_schema, test_connection, invalidate_schema_cache
from app.schemas import (
    ChatRequest, ChatResponse, ExecuteRequest, ExecuteResponse,
    AnalyzeRequest, AnalyzeResponse, ChartConfig,
)
from app.services.llm_service import LLMService
from app.services.template_service import TemplateService, InvalidParamsError
from app.services.query_executor import QueryExecutorService
from app.services import session_store

logger = logging.getLogger(__name__)
router = APIRouter()

_llm: LLMService | None = None
_template_svc: TemplateService | None = None
_executor: QueryExecutorService | None = None

_ANALYZE_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_result",
        "description": "Analyze query results and provide a natural language summary and best chart configuration.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence insight summary. Highlight key numbers, trends, or anomalies.",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "area", "table"],
                    "description": "Best chart type. Use 'table' when data is not well suited for visualization.",
                },
                "x_col": {
                    "type": "string",
                    "description": "Column name for x-axis or category labels.",
                },
                "y_cols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names for numeric values to plot.",
                },
                "title": {
                    "type": "string",
                    "description": "Short descriptive chart title.",
                },
            },
            "required": ["summary", "chart_type", "x_col", "y_cols", "title"],
        },
    },
}


def _services() -> tuple[LLMService, TemplateService, QueryExecutorService]:
    global _llm, _template_svc, _executor
    if _template_svc is None:
        _llm = LLMService()
        _template_svc = TemplateService(_llm)
        _executor = QueryExecutorService()
    return _llm, _template_svc, _executor


def _qid() -> str:
    return f"q_{uuid.uuid4().hex[:8]}"


def _rows_to_markdown(columns: list[str], rows: list[dict]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = "\n".join(
        "| " + " | ".join(str(row.get(c, "")) for c in columns) + " |"
        for row in rows[:20]
    )
    return f"{header}\n{sep}\n{body}"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Resolve a natural language question to a pre-written SQL template + bind params."""
    qid = _qid()
    _, template_svc, _ = _services()

    session_id = request.session_id
    history = session_store.get_history(session_id) if session_id else []

    try:
        sql, params, template_key, reasoning, tool_name = template_svc.resolve(
            request.user_query, history=history
        )

        if session_id:
            session_store.append_messages(session_id, [
                {"role": "user", "content": request.user_query},
                {"role": "assistant", "content": f"Selected tool={tool_name} template={template_key}"},
            ])

        return ChatResponse(
            query_id=qid,
            status="sql_generated",
            user_query=request.user_query,
            sql_query=sql,
            tool_name=tool_name,
            template_key=template_key,
            params=params,
            reasoning=reasoning if SHOW_TEMPLATE_DESCRIPTION else None,
            timestamp=datetime.now().isoformat(),
        )
    except InvalidParamsError as e:
        return ChatResponse(
            query_id=qid, status="invalid_params", user_query=request.user_query,
            tool_name=e.tool_name, template_key=e.template, error=str(e),
            timestamp=datetime.now().isoformat(),
        )
    except ValueError as e:
        return ChatResponse(
            query_id=qid, status="no_template", user_query=request.user_query,
            error=str(e), timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            query_id=qid, status="error", user_query=request.user_query,
            error=str(e), timestamp=datetime.now().isoformat(),
        )


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute a pre-written SQL template with bind params."""
    qid = _qid()
    _, _, executor = _services()
    df, error = executor.execute(request.sql_query, db, params=request.params)
    if error is None:
        return ExecuteResponse(
            query_id=qid, status="success", sql_query=request.sql_query,
            columns=list(df.columns), rows=df.to_dict(orient="records"),
            row_count=len(df), timestamp=datetime.now().isoformat(),
        )
    return ExecuteResponse(
        query_id=qid, status="error", sql_query=request.sql_query,
        error=error, timestamp=datetime.now().isoformat(),
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """Analyze query results — returns LLM-generated summary and best chart config."""
    if not ENABLE_ANALYSIS:
        raise HTTPException(status_code=404, detail="Analysis endpoint disabled")

    llm, _, _ = _services()
    table_md = _rows_to_markdown(request.columns, request.rows)
    prompt = (
        f"User question: {request.user_query}\n"
        f"Total rows returned: {request.row_count} (showing first 20)\n"
        f"Columns: {', '.join(request.columns)}\n\n"
        f"Data:\n{table_md}"
    )

    _, tool_args = llm.generate_with_tools(prompt, [_ANALYZE_TOOL])

    return AnalyzeResponse(
        summary=tool_args["summary"],
        chart=ChartConfig(
            type=tool_args["chart_type"],
            x_col=tool_args["x_col"],
            y_cols=tool_args["y_cols"],
            title=tool_args["title"],
        ),
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
    _, _, executor = _services()
    return {"queries": executor.get_history(limit)}


@router.get("/health")
async def health():
    connected = test_connection()
    return {"status": "healthy" if connected else "unhealthy", "database_connected": connected}
