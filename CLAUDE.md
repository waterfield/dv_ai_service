# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

W AI Reporting is a full-stack service that converts natural language questions into SQL (and DAX) queries for SQL Server databases, powered by Groq's LLM. It targets energy analytics fact/dimension tables with hard-coded domain knowledge baked into the LLM prompts.

**Stack**: FastAPI backend + Streamlit frontend + SQLAlchemy/pyodbc for SQL Server + Groq API for LLM.

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Test SQL Server connection (prints schema summary)
python test_connection.py

# Start API server (dev mode with reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs (Swagger UI) available at `http://localhost:8000/docs` once running.

### Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py          # opens at http://localhost:8501
```

### Environment setup

Copy `.env.example` to `.env` (backend) and `frontend/.env.example` to `frontend/.env`. Required variables:

**Backend** (`.env`):
- `DATABASE_SERVER`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_PORT`
- `GROQ_API_KEY`

**Frontend** (`frontend/.env`):
- `BACKEND_API_URL` — base URL of the backend API (default: `http://localhost:8000`)

Optional schema filtering: `DATABASE_SCHEMA`, `TABLE_KEY_FILTER`, `TABLE_WHITELIST`, `TABLE_EXCEPTION_LIST`.
`DATABASE_SCHEMAS` defaults to `dbo` if not set.

## Architecture

### Request flow

1. User submits a natural language question via Streamlit (`frontend/app.py`)
2. `POST /api/chat` → `SQLGeneratorService` builds a system prompt with domain knowledge + live schema, calls Groq LLM, extracts and validates SQL
3. `POST /api/execute` → `QueryExecutorService` runs the SQL; on failure, calls LLM to fix and retries up to 3 times, tracking each iteration
4. Frontend displays results as a table and optionally renders Plotly charts; retry iterations are viewable on the debug page (`frontend/pages/execution_details.py`)

### Key files

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, lifespan startup check, CORS, router mount at `/api` |
| `app/api/routes.py` | REST endpoints: `/chat`, `/execute`, `/schema`, `/schema/cache`, `/health`, `/history` |
| `app/schemas.py` | Pydantic request/response models: `ChatRequest`, `ChatResponse`, `ExecuteRequest`, `ExecuteResponse`, `IterationDetail` |
| `app/services/sql_generator.py` | Core LLM prompt construction, SQL extraction, hallucination fixes, security validation |
| `app/services/dax_generator.py` | DAX query generation (non-critical; failure doesn't block SQL response) |
| `app/services/query_executor.py` | Executes SELECT queries, tracks history in-memory, auto-retry with LLM fix |
| `app/services/llm_service.py` | Groq client wrapper with model fallback chain |
| `database.py` | SQLAlchemy connection pool, thread-safe schema caching, schema filter logic |
| `config.py` | env-based config via pydantic-settings, builds connection URL |
| `frontend/app.py` | Streamlit chat UI, session state, API calls (60s timeout) |
| `frontend/charts.py` | Plotly chart builder (Auto/Bar/Line/Pie) |
| `frontend/pages/execution_details.py` | Debug page showing per-iteration SQL and errors for retried queries |
| `test_connection.py` | Standalone utility to verify DB connectivity and print schema sample |

### Non-obvious design decisions

**Domain knowledge in prompts** (`sql_generator.py`, `dax_generator.py`)
Energy-domain business logic (AFE budgets/actuals, chart of accounts, division order interest calculations, AP/invoice aging, contract values, volume type allocations) is embedded directly in the LLM system prompt rather than fetched from config or a database. Changing domain coverage means editing the prompt strings in these files.

**LLM model fallback chain** (`llm_service.py`)
Groq calls attempt models in order: `llama-3.3-70b-versatile` → `llama-3.1-70b-versatile` → `llama-3.1-8b-instant`. If a model errors, the next is tried automatically. The model actually used is logged.

**Hallucination fix pass** (`sql_generator.py` → `_fix_dim_pk_references()`)
After SQL is extracted, a secondary pass rewrites hallucinated foreign-key references on dimension tables. This runs before security validation, not inside the retry loop.

**Security validation — two layers**
Both `SQLGeneratorService._validate()` and `QueryExecutorService._validate()` independently forbid the keywords: `DROP`, `DELETE`, `INSERT`, `UPDATE`, `CREATE`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`, `DECLARE`. The double check means even LLM-fixed SQL during retries is re-validated before execution.

**Singleton service pattern** (`routes.py`)
`SQLGeneratorService`, `QueryExecutorService`, and `LLMService` are instantiated once at module load time in `routes.py`, not per-request. Schema is fetched lazily and cached with a threading lock in `database.py` (pool_size=5, max_overflow=10, pre-ping enabled).

**In-memory history only** (`query_executor.py`)
Execution history is stored as a plain Python list inside the `QueryExecutorService` instance. It is lost on server restart and is not shared across workers. The `GET /history` endpoint returns the most recent 20 entries by default.

**Query ID format** (`routes.py`)
Each query gets an ID of the form `q_{uuid.hex[:8]}` (e.g. `q_3f2a1b0c`), used to correlate chat and execute calls in the frontend.

**Chart auto-detection** (`frontend/charts.py`)
`detect_chart_type()` picks: line if any column parses as dates, pie if there is exactly one numeric column and ≤8 category rows, bar otherwise. The user can override via the chart-type selector in the UI.

**Retry debug page** (`frontend/pages/execution_details.py`)
When execution retries occur, the frontend stores iteration details in `st.session_state["debug_iterations"]`. The separate Streamlit page reads this state to show each attempt's SQL and error message in expandable sections.
