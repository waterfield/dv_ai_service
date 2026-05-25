# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

W AI Reporting is a full-stack service that resolves natural language questions into pre-written, engineer-verified SQL templates for SQL Server databases, powered by configurable LLM providers (Anthropic, Groq, OpenRouter). The LLM never writes SQL — it only picks a template key and typed filter values. All SQL is hand-written and hand-tested.

**Stack**: FastAPI backend + Streamlit frontend + SQLAlchemy/pyodbc for SQL Server + Anthropic/Groq/OpenRouter for LLM tool-use.

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
- `ANTHROPIC_API_KEY` — required if any entry uses `anthropic:`
- `GROQ_API_KEY` — required if any entry uses `groq:`
- `OPENROUTER_API_KEY` — required if any entry uses `openrouter:`
- `SHOW_TEMPLATE_DESCRIPTION` — `true` to return template description in chat response (default: `false`)

**Frontend** (`frontend/.env`):
- `BACKEND_API_URL` — base URL of the backend API (default: `http://localhost:8000`)

Optional schema filtering:
- `DATABASE_SCHEMA` — single schema name (default: `dbo`); comma-separated list raises `ValueError`
- `TABLE_KEY_FILTER` — single substring; only tables whose name contains this string are included (case-insensitive)
- `TABLE_WHITELIST` — comma-separated explicit list of table names to include
- `TABLE_EXCEPTION_LIST` — comma-separated blacklist; always excluded even if matched by filter/whitelist

**Important**: `TABLE_KEY_FILTER` is a single substring, not a list. For an explicit list of tables use `TABLE_WHITELIST`.

## Architecture

### Request flow

1. User submits natural language question via Streamlit (`frontend/app.py`)
2. `POST /api/chat` → `TemplateService.resolve()` calls LLM via `generate_with_tools()` with OpenAI-compatible tool definitions; LLM returns a tool-use block selecting a tool + template key + typed filter values; Pydantic validates; dict lookup returns pre-written SQL string + params dict + reasoning string
3. Frontend auto-executes: `POST /api/execute` → `QueryExecutorService.execute(sql, db, params=params)` runs `db.execute(text(sql), params)` — one attempt, no retry
4. Frontend displays results in tabs (Table / Chart / Query / optional Reasoning); Query tab shows tool + template badge and active bind params

### Key files

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, lifespan startup DB check, CORS (`allow_origins=["*"]`), router mount at `/api` |
| `app/api/routes.py` | REST endpoints: `/chat`, `/execute`, `/schema`, `/schema/cache`, `/health`, `/history`; lazy service init; no retry loop |
| `app/schemas.py` | Pydantic models: `ChatRequest`, `ChatResponse` (includes `tool_name`, `template_key`, `params`), `ExecuteRequest` (includes `params`), `ExecuteResponse` |
| `app/services/template_service.py` | `TemplateService.resolve()` — calls LLM, dispatches to per-tool resolver, catches `ValidationError` → `InvalidParamsError`, handles `unknown_query` sentinel |
| `app/services/tools/__init__.py` | Exports `ALL_TOOLS` list (all tool definitions + `unknown_query` sentinel) |
| `app/services/tools/afe_financial.py` | `AFEFinancialRequest` Pydantic model, 17 SQL templates, `resolve_afe_financial()`, `AFE_TOOL_DEFINITION` |
| `app/services/tools/afe_master.py` | `AFEMasterRequest` Pydantic model, 10 SQL templates for AFE master data, `resolve_afe_master()`, `AFE_MASTER_TOOL_DEFINITION` |
| `app/services/llm_service.py` | Multi-provider LLM dispatcher (Anthropic primary, Groq, OpenRouter); `generate()` for plain text, `generate_with_tools()` for tool-use |
| `app/services/query_executor.py` | Single-attempt SQL execution via `db.execute(text(sql), params)`, module-level history list |
| `app/services/sql_generator.py` | **Unused** — previous LLM SQL generation approach; kept for reference |
| `app/services/dax_generator.py` | **Unused** — DAX query generation; kept for reference |
| `database.py` | SQLAlchemy engine + pool, `inspect`-based schema + FK relationship loading, table descriptions loader, thread-safe caches |
| `config.py` | `os.getenv`-based config; builds `DATABASE_URL`; parses `LLM_MODELS`, `DATABASE_SCHEMA`, filter lists, `SHOW_TEMPLATE_DESCRIPTION` |
| `frontend/app.py` | Streamlit chat UI (wide layout), sidebar with example questions, session state, API calls (60s timeout), tab result display, `render_error()` for structured error cards |
| `frontend/charts.py` | Plotly chart builder (Auto/Bar/Line/Pie) with `_coerce_numerics` pre-pass |
| `frontend/pages/execution_details.py` | Debug page (legacy — retries no longer occur) |
| `test_connection.py` | Standalone utility to verify DB connectivity and print schema sample |

### Non-obvious design decisions

**LLM never writes SQL** (`template_service.py`, `tools/`)
`TemplateService.resolve()` calls the LLM with OpenAI-compatible function definitions. The LLM picks a tool (e.g. `afe_financial`), a template key (e.g. `budget_vs_actuals_by_afe`), and typed filter values (e.g. `year=2025`). Pydantic validates against `Literal` enums and range constraints. A dict lookup returns the pre-written SQL string. The LLM never sees a cursor or writes a character of SQL.

**Two tools, distinct domains** (`tools/afe_financial.py`, `tools/afe_master.py`)
- `afe_financial` — budget, actuals, commitments, spend analysis; 17 templates on `fact_afe_budgets`, `fact_afe_actuals`, `fact_afe_commitments`
- `afe_master` — AFE attributes, listings, timelines, approvals, rejections; 10 templates on `dim_afe`
Tool docstrings explicitly tell the LLM which to use and when NOT to use each.

**NULL filter pattern** (`tools/`)
All filter params are optional. Every template uses `(:param IS NULL OR col = :param)` — when param is `None`, SQLAlchemy binds it as SQL `NULL`, and `NULL IS NULL` short-circuits to `TRUE`, applying no filter. One template handles all filter combinations without branching.

**Bind params via SQLAlchemy `text()`** (`query_executor.py`)
`QueryExecutorService.execute(sql, db, params)` calls `db.execute(text(sql), params or {})`. SQLAlchemy translates `:param` named syntax → `?` positional → SQL Server via pyodbc. `None` values become SQL `NULL`. Column names and structural SQL (GROUP BY, JOIN) are hard-coded in templates — bind params are for values only.

**Structured validation errors** (`template_service.py`, `routes.py`)
`resolve()` catches `pydantic.ValidationError` and raises `InvalidParamsError(tool_name, template, field_errors)` — a `ValueError` subclass carrying structured attributes. `routes.py` catches it before `ValueError` and returns `status="invalid_params"` with `tool_name` + `template_key` populated. Frontend `render_error()` displays a styled card with tool/template metadata and per-field error list.

**`unknown_query` sentinel tool** (`tools/__init__.py`, `template_service.py`)
`ALL_TOOLS` includes an `unknown_query` tool with no parameters. The LLM picks this when the question doesn't match any available template. `TemplateService.resolve()` raises `ValueError` → `status="no_template"`. Forces `tool_choice="required"` so the LLM always picks a tool.

**`SHOW_TEMPLATE_DESCRIPTION`** (`config.py`, `routes.py`)
Controls whether the template description string (e.g. `"Budget per individual AFE"`) is returned in `ChatResponse.reasoning`. When `false` (default), `reasoning=None` → Reasoning tab hidden in frontend. Not LLM chain-of-thought — just a human-readable label from `TEMPLATE_DESCRIPTIONS` dict in each tool file.

**No retry loop** (`routes.py`)
The `/execute` endpoint does one execution attempt and returns. Pre-written SQL is deterministic — there is nothing for LLM repair to fix. `IterationDetail` and `retries` fields remain in `ExecuteResponse` schema for backward compatibility but are never populated.

**Lazy singleton services** (`routes.py` → `_services()`)
`LLMService`, `TemplateService`, and `QueryExecutorService` are not created at import time. `_services()` creates them on the first request and returns the same instances thereafter. Schema is fetched lazily and cached with a threading lock in `database.py` (pool_size=5, max_overflow=10, pre-ping enabled).

**Multi-provider LLM dispatch** (`llm_service.py`)
`LLM_MODELS` is parsed into `(service, model, provider_hint)` tuples. Tried in order; falls through on error. Both `generate()` (plain text) and `generate_with_tools()` (tool-use) follow the same fallback chain. Supported services: `anthropic` (primary), `groq`, `openrouter`. Format: `anthropic:claude-sonnet-4-6` or `groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-3-5-sonnet@Together`.

**Anthropic vs OpenAI-compatible tool format** (`llm_service.py`)
Tool definitions in `tools/` use OpenAI function-calling format. When the active service is `anthropic`, `generate_with_tools()` converts them internally: `parameters` → `input_schema`, strips `type: function` wrapper, uses `tool_choice={"type": "any"}` instead of `"required"`. Anthropic response blocks are iterated for `block.type == "tool_use"` to extract `block.name` and `block.input`. For plain `generate()`, Anthropic system prompts are passed as the `system=` parameter (not in the messages list).

**Adding a new tool** (`tools/`)
1. Create `app/services/tools/<domain>.py` — Pydantic model with `Literal` template field, SQL templates dict, `resolve_<domain>()`, `_build_tool_definition()` returning OpenAI-format tool def. Add explicit docstring guidance on when to use vs. NOT use this tool vs. other tools.
2. Import and add to `ALL_TOOLS` in `app/services/tools/__init__.py`
3. Add `elif tool_name == "<domain>": resolver = resolve_<domain>` in `TemplateService.resolve()`

**Frontend result tabs** (`frontend/app.py`)
Results shown in tabs: **Table** (dataframe), **Chart** (Plotly with type selector), **Query** (SQL + tool/template badge + active bind params as JSON; DAX sub-tab if present), **Reasoning** (only when `SHOW_TEMPLATE_DESCRIPTION=true`). Reasoning and DAX tabs hidden when content absent.

**Frontend error display** (`frontend/app.py` → `render_error()`)
Three error types with distinct UI:
- `invalid_params` → styled card with tool/template metadata + bulleted field errors
- `no_template` → teal info card with suggestion text
- generic → plain `st.error()`
Error data stored structured in session state (`chat_error_type`, `chat_error_tool`, `chat_error_template`, `chat_error`).

**Security validation** (`query_executor.py`)
`QueryExecutorService._validate()` forbids: `DROP DELETE INSERT UPDATE CREATE ALTER TRUNCATE EXEC EXECUTE` plus SQL comments (`--`, `/*`). Templates always start with `SELECT` or `WITH` (CTE). SQL injection is structurally impossible — all user-supplied values are bind params, never concatenated.

**`inspect`-based schema loading** (`database.py`)
Schema loaded via `inspect(engine)`: `get_table_names(schema=)` + `get_columns(table, schema=)` per table. O(N) round-trips but returns richer SQLAlchemy type strings (e.g. `VARCHAR(255)`). Used by `/schema` endpoint only — templates do not depend on runtime schema.

**Single schema enforced** (`config.py`, `database.py`)
`DATABASE_SCHEMA` must be a single schema name — comma-separated value raises `ValueError` at startup. All table keys use plain table names (no `schema.table` qualification).

**In-memory history** (`query_executor.py`)
`_history` is a module-level list (not an instance variable). It persists for the process lifetime and is shared across all instances, but is lost on server restart and not shared across workers. `GET /history` returns the most recent 20 entries by default.

**Query ID format** (`routes.py`)
Each query gets an ID `q_{uuid.hex[:8]}` (e.g. `q_3f2a1b0c`), used to correlate chat and execute calls.

**Chart auto-detection** (`frontend/charts.py`)
`detect_chart_type()` runs `_coerce_numerics` first, then picks: line if any column parses as dates + has numerics, pie if exactly one numeric column and ≤8 unique category values, bar otherwise. User can override via the chart-type selector.

**`execution_time` in `ExecuteResponse`**
Field exists in Pydantic schema but never populated by `routes.py` (always `None`). Actual execution time logged server-side and stored in history list.
