from pydantic import BaseModel
from typing import Optional, Any, Literal


class ChatRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None
    history: list[dict] = []


class ExecuteRequest(BaseModel):
    sql_query: str
    params: Optional[dict] = None
    user_query: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    query_id: str
    status: str
    user_query: str
    sql_query: Optional[str] = None
    tool_name: Optional[str] = None
    template_key: Optional[str] = None
    params: Optional[dict] = None
    dax_query: Optional[str] = None
    reasoning: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class IterationDetail(BaseModel):
    attempt: int
    sql: str
    error: Optional[str] = None
    success: bool = False


class ChartConfig(BaseModel):
    type: Literal["bar", "line", "pie", "scatter", "area", "table"]
    x_col: str
    y_cols: list[str]
    title: str


class AnalyzeRequest(BaseModel):
    user_query: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    session_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    summary: str
    chart: ChartConfig


class ExecuteResponse(BaseModel):
    query_id: str
    status: str
    sql_query: str
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    execution_time: Optional[float] = None
    retries: int = 0
    iterations: list[IterationDetail] = []
    error: Optional[str] = None
    timestamp: str
