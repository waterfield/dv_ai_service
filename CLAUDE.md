# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

W AI Reporting is a full-stack service that converts natural language questions into SQL (and DAX) queries for SQL Server databases, powered by configurable LLM providers (Groq and OpenRouter). It targets energy analytics fact/dimension tables with domain knowledge baked into the LLM prompts.

**Stack**: FastAPI backend + Streamlit frontend + SQLAlchemy/pyodbc for SQL Server + Groq/OpenRouter for LLM.

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
- `LLM_MODELS` — comma-separated list of `service:model[@provider_hint]` entries (required, no default)
- `GROQ_API_KEY` — required if any entry in `LLM_MODELS` uses `groq:`
- `OPENROUTER_API_KEY` — required if any entry in `LLM_MODELS` uses `openrouter:`

**Frontend** (`frontend/.env`):
- `BACKEND_API_URL` — base URL of the backend API (default: `http://localhost:8000`)

Optional feature flags:
- `ENABLE_DAX` — enable DAX query generation (default: `false`; makes a second LLM call per prompt)
- `ENABLE_REASONING` — include one-sentence reasoning with each SQL query (default: `false`)

Optional schema filtering:
- `DATABASE_SCHEMA` — single schema name (default: `dbo`); comma-separated list raises `ValueError`
- `TABLE_KEY_FILTER` — single substring; only tables whose name contains this string are included (case-insensitive)
- `TABLE_WHITELIST` — comma-separated explicit list of table names to include
- `TABLE_EXCEPTION_LIST` — comma-separated blacklist; always excluded even if matched by filter/whitelist

**Important**: `TABLE_KEY_FILTER` is a single substring, not a list. For an explicit list of tables use `TABLE_WHITELIST`.

## Architecture

### Request flow

1. User submits a natural language question via Streamlit (`frontend/app.py`)
2. `POST /api/chat` → `SQLGeneratorService` builds a system prompt with domain knowledge + live schema (capped at 30 tables) + auto-detected FK relationships + table/column descriptions, calls LLM, extracts SQL and optional reasoning, runs `_fix_dim_pk_references`, then validates
3. Frontend auto-executes the SQL: `POST /api/execute` → `routes.py` runs `QueryExecutorService.execute()` in a loop; on failure, calls `SQLGeneratorService.fix_sql()` and retries up to 3 times, tracking each iteration
4. Frontend displays results in four tabs (Table / Chart / Query / Reasoning); retry iterations are viewable on the debug page (`frontend/pages/execution_details.py`)

### Key files

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, lifespan startup DB check, CORS (`allow_origins=["*"]`), router mount at `/api` |
| `app/api/routes.py` | REST endpoints: `/chat`, `/execute`, `/schema`, `/schema/cache`, `/health`, `/history`; owns the retry loop and lazy service init |
| `app/schemas.py` | Pydantic models: `ChatRequest`, `ChatResponse`, `ExecuteRequest`, `ExecuteResponse`, `IterationDetail` |
| `app/services/sql_generator.py` | LLM prompt construction, SQL + reasoning extraction, `_fix_dim_pk_references`, `fix_sql` (LLM repair), security validation |
| `app/services/dax_generator.py` | DAX query generation (non-critical; only runs when `ENABLE_DAX=true`) |
| `app/services/query_executor.py` | Single-attempt SQL execution via SQLAlchemy, module-level history list |
| `app/services/llm_service.py` | Multi-provider LLM dispatcher (Groq + OpenRouter); parses `LLM_MODELS`, lazy per-provider client init |
| `database.py` | SQLAlchemy engine + pool, `inspect`-based schema + FK relationship loading, table descriptions loader, thread-safe caches |
| `config.py` | `os.getenv`-based config; builds `DATABASE_URL`; parses `LLM_MODELS`, `DATABASE_SCHEMA`, filter lists, feature flags |
| `table_descriptions.json` | Per-table and per-column descriptions injected inline into LLM schema prompt |
| `frontend/app.py` | Streamlit chat UI, session state, API calls (60s timeout), 4-tab result display |
| `frontend/charts.py` | Plotly chart builder (Auto/Bar/Line/Pie) with `_coerce_numerics` pre-pass |
| `frontend/pages/execution_details.py` | Debug page: shows per-attempt SQL and error for retried queries |
| `test_connection.py` | Standalone utility to verify DB connectivity and print schema sample |

### Non-obvious design decisions

**Retry loop is in `routes.py`, not `query_executor.py`**
`QueryExecutorService.execute()` does exactly one execution attempt and returns `(DataFrame | None, error | None)`. The retry loop (up to 3 retries, calling `sql_gen.fix_sql()` between attempts) lives in the `POST /api/execute` handler in `routes.py`. `IterationDetail` records are built there too.

**Lazy singleton services** (`routes.py` → `_services()`)
`LLMService`, `SQLGeneratorService`, `DaxGeneratorService`, and `QueryExecutorService` are not created at import time. `_services()` creates them on the first request and returns the same instances thereafter. Schema is fetched lazily and cached with a threading lock in `database.py` (pool_size=5, max_overflow=10, pre-ping enabled).

**Multi-provider LLM dispatch** (`llm_service.py`)
`LLM_MODELS` is parsed into `(service, model, provider_hint)` tuples. Tried in order; falls through on error. Format: `groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-3-5-sonnet@Together`. Provider hint is optional — passes `provider.order` to OpenRouter when set. OpenRouter client uses `X-Data-Collection: deny` header. API keys validated lazily per-service on first use.

**Auto-detected FK relationships** (`database.py` → `get_relationships()`)
FK relationships are loaded via `inspector.get_foreign_keys()` per table and cached. Only relationships where both tables are in the filtered schema are included. Replaces the previous hard-coded join list in `sql_generator.py`. Cache cleared together with schema cache via `invalidate_schema_cache()`.

**Table descriptions** (`table_descriptions.json` → `get_descriptions()`)
Per-table and per-column descriptions are loaded from `table_descriptions.json` at project root and cached in memory. Injected inline into the schema listing in the LLM prompt — table description appears after the table name, column descriptions appear inline with column names. Tables/columns without descriptions degrade gracefully to plain names.

**Single schema enforced** (`config.py`, `database.py`)
`DATABASE_SCHEMA` must be a single schema name — comma-separated value raises `ValueError` at startup. All table keys use plain table names (no `schema.table` qualification).

**Domain knowledge in prompts** (`sql_generator.py`, `dax_generator.py`)
Energy-domain business logic (AFE budgets/actuals, chart of accounts, division order interest calculations, AP/invoice aging, contract values, volume type allocations) is embedded directly in the LLM system prompt. Changing domain coverage means editing the prompt strings in these files. Schema section capped at first 30 tables.

**Reasoning extraction** (`sql_generator.py` → `_extract_sql()`)
When `ENABLE_REASONING=true`, prompt instructs LLM to return `REASONING: <one sentence>\nSQL: <query>`. `_extract_sql()` always returns `(sql, reasoning)` tuple — `fix_sql` discards reasoning with `_`. Empty string when reasoning disabled.

**Hallucination fix pass** (`sql_generator.py` → `_fix_dim_pk_references()`)
After SQL is extracted (and again after `fix_sql`), this pass rewrites two classes of LLM hallucinations on JOINed dim table aliases:
1. `alias.some_table_id` (FK column that only exists on fact tables) → `alias.id`
2. `alias.nonexistent_label` (e.g. `.name` on `dim_chart_of_account`) → `alias.<best_label_col>`

**Security validation — two independent layers**
`SQLGeneratorService._validate()` forbids: `DROP DELETE INSERT UPDATE CREATE ALTER TRUNCATE EXEC EXECUTE DECLARE` plus SQL comments (`--`, `/*`), and checks the first FROM table exists in schema.
`QueryExecutorService._validate()` forbids: `DROP DELETE INSERT UPDATE CREATE ALTER TRUNCATE EXEC EXECUTE` plus SQL comments. Note: `DECLARE` is only in the generator's list.

**In-memory history** (`query_executor.py`)
`_history` is a module-level list (not an instance variable). It persists for the process lifetime and is shared across all instances, but is lost on server restart and not shared across workers. `GET /history` returns the most recent 20 entries by default.

**`inspect`-based schema loading** (`database.py`)
Schema loaded via `inspect(engine)`: `get_table_names(schema=)` + `get_columns(table, schema=)` per table. O(N) round-trips but returns richer SQLAlchemy type strings (e.g. `VARCHAR(255)`).

**Query ID format** (`routes.py`)
Each query gets an ID `q_{uuid.hex[:8]}` (e.g. `q_3f2a1b0c`), used to correlate chat and execute calls.

**Chart auto-detection** (`frontend/charts.py`)
`detect_chart_type()` runs `_coerce_numerics` first, then picks: line if any column parses as dates + has numerics, pie if exactly one numeric column and ≤8 unique category values, bar otherwise. User can override via the chart-type selector.

**Frontend result tabs** (`frontend/app.py`)
Results shown in four tabs: **Table** (dataframe + retry link if retries > 0), **Chart** (Plotly with type selector), **Query** (nested SQL / DAX sub-tabs), **Reasoning** (one-sentence LLM explanation when `ENABLE_REASONING=true`). DAX code rendered with `language="python"` as Streamlit has no DAX lexer.

**Retry debug page** (`frontend/pages/execution_details.py`)
Iteration details stored in `st.session_state["debug_iterations"]` when retries occur. Separate Streamlit page reads this state to show each attempt's SQL and error in expandable sections.

**`execution_time` in `ExecuteResponse`**
Field exists in Pydantic schema but never populated by `routes.py` (always `None`). Actual execution time logged server-side and stored in history list.
