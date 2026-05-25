# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

W AI Reporting is a full-stack service that resolves natural language questions into pre-written, engineer-verified SQL templates for SQL Server databases, powered by configurable LLM providers (Anthropic, Groq, OpenRouter). The LLM never writes SQL — it only picks a template key and typed filter values. All SQL is hand-written and hand-tested.

**Stack**: FastAPI backend + Next.js 14 (App Router) frontend + SQLAlchemy/pyodbc for SQL Server + Anthropic/Groq/OpenRouter for LLM tool-use.

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Test SQL Server connection (prints schema summary)
python test_connection.py

# Test all SQL templates against live DB (27 templates, reports PASS/FAIL)
python test_templates.py           # all templates
python test_templates.py financial # afe_financial only
python test_templates.py master    # afe_master only

# Start API server (dev mode with reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs (Swagger UI) available at `http://localhost:8000/docs` once running.

### Frontend (Next.js)

```bash
cd frontend-next
npm install
npm run dev       # opens at http://localhost:3000
npm run build     # production build
```

### Environment setup

Copy `.env.example` to `.env`. Required variables:

**Backend** (`.env`):
- `DATABASE_SERVER`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_PORT`
- `LLM_MODELS` — comma-separated list of `service:model[@provider_hint]` entries (required, no default)
- `ANTHROPIC_API_KEY` — required if any entry uses `anthropic:`
- `GROQ_API_KEY` — required if any entry uses `groq:`
- `OPENROUTER_API_KEY` — required if any entry uses `openrouter:`
- `SHOW_TEMPLATE_DESCRIPTION` — `true` to return template description in chat response (default: `false`)
- `ENABLE_ANALYSIS` — `false` to disable the `/analyze` endpoint (default: `true`)

Optional schema filtering:
- `DATABASE_SCHEMA` — single schema name (default: `dbo`); comma-separated list raises `ValueError`
- `TABLE_KEY_FILTER` — single substring; only tables whose name contains this string are included (case-insensitive)
- `TABLE_WHITELIST` — comma-separated explicit list of table names to include
- `TABLE_EXCEPTION_LIST` — comma-separated blacklist; always excluded even if matched by filter/whitelist

**Important**: `TABLE_KEY_FILTER` is a single substring, not a list. For an explicit list of tables use `TABLE_WHITELIST`.

## Architecture

### Request flow

1. User submits natural language question via Next.js frontend (`frontend-next/`)
2. `POST /api/chat` → `TemplateService.resolve()` loads session history → calls LLM via `generate_with_tools()` with conversation context; LLM picks tool + template key + typed filter values; Pydantic validates; dict lookup returns pre-written SQL + params dict; session history updated
3. Frontend auto-executes: `POST /api/execute` → `QueryExecutorService.execute(sql, db, params=params)` — one attempt, no retry
4. Frontend async fires: `POST /api/analyze` → LLM summarizes result rows + picks best chart type → returns `summary` + `ChartConfig`
5. Frontend renders: 4-tab card (Table / Chart / Summary / Query); analyze result streams in after data is shown

### Key files

| File | Role |
|------|------|
| `app/main.py` | FastAPI app, lifespan startup DB check, CORS (`allow_origins=["*"]`), router mount at `/api` |
| `app/api/routes.py` | REST endpoints: `/chat`, `/execute`, `/analyze`, `/schema`, `/schema/cache`, `/health`, `/history`; lazy service init; `_ANALYZE_TOOL` definition; `_rows_to_markdown()` helper |
| `app/schemas.py` | Pydantic models: `ChatRequest` (includes `session_id`), `ChatResponse`, `ExecuteRequest`, `ExecuteResponse`, `AnalyzeRequest`, `AnalyzeResponse`, `ChartConfig` |
| `app/services/template_service.py` | `TemplateService.resolve(user_query, history=[])` — accepts conversation history, passes to LLM |
| `app/services/session_store.py` | Thread-safe in-memory session store: `{session_id: {messages, updated}}`; TTL 60 min, capped at 20 messages; `get_history()`, `append_messages()`, `clear_session()` |
| `app/services/tools/__init__.py` | Exports `ALL_TOOLS` list (all tool definitions + `unknown_query` sentinel) |
| `app/services/tools/afe_financial.py` | `AFEFinancialRequest` Pydantic model, 17 SQL templates, `resolve_afe_financial()`, `AFE_TOOL_DEFINITION`; filter params: `year`, `status`, `afe_type_description`, `afe_number`, `top_n`; all `fact_afe_budgets` queries filter `approved_copy = 0` |
| `app/services/tools/afe_master.py` | `AFEMasterRequest` Pydantic model, 10 SQL templates for AFE master data, `resolve_afe_master()`, `AFE_MASTER_TOOL_DEFINITION`; filter params: same as `afe_financial` plus `afe_project_name` and `company_name` |
| `app/services/llm_service.py` | Multi-provider LLM dispatcher; `generate()` for plain text, `generate_with_tools(history=[])` for tool-use with conversation context |
| `app/services/query_executor.py` | Single-attempt SQL execution via `db.execute(text(sql), params)`, module-level history list |
| `app/services/sql_generator.py` | **Unused** — previous LLM SQL generation approach; kept for reference |
| `app/services/dax_generator.py` | **Unused** — DAX query generation; kept for reference |
| `database.py` | SQLAlchemy engine + pool, `inspect`-based schema + FK relationship loading, `get_descriptions()` loads `table_descriptions.json` (not called by any endpoint), thread-safe caches |
| `config.py` | `os.getenv`-based config; builds `DATABASE_URL`; parses `LLM_MODELS`, `DATABASE_SCHEMA`, filter lists, `SHOW_TEMPLATE_DESCRIPTION`, `ENABLE_ANALYSIS`; `DEBUG` defaults to `True` (SQLAlchemy echo on — set `DEBUG=False` in production) |
| `table_descriptions.json` | Optional JSON file mapping table names to descriptions; loaded by `database.py:get_descriptions()` but not wired to any API endpoint yet |
| `test_templates.py` | Standalone script: runs every SQL template against live DB with null params (no filters, `top_n=5`), reports PASS/FAIL per template + summary. Exit code 1 if any fail (CI-friendly). |
| `docs/` | Research docs (`docs/research/`) and implementation plans (`docs/superpowers/plans/`) — not production code |
| `frontend-next/` | Next.js 14 (App Router) frontend — see below |
| `frontend/app.py` | **Legacy** Streamlit frontend — superseded by `frontend-next/`; kept for reference |

### Frontend — `frontend-next/`

| File | Role |
|------|------|
| `src/app/layout.tsx` | Root layout: Inter font, `AppRouterCacheProvider` (Emotion SSR), `ThemeRegistry` |
| `src/app/page.tsx` | Main page: 280px permanent Drawer (dark teal sidebar), AppBar, 3-step async query flow, session-scoped `SESSION_ID` |
| `src/app/globals.css` | Minimal reset only (`box-sizing`, `margin: 0`) |
| `src/theme/theme.ts` | MUI v9 theme: W Energy brand — orange `#f5a623` primary, dark teal `#0d3344` secondary, light mode |
| `src/components/shared/ThemeRegistry.tsx` | `'use client'` — `ThemeProvider` + `CssBaseline`; `AppRouterCacheProvider` lives in `layout.tsx` (server), not here |
| `src/components/shared/ConnectionStatus.tsx` | Health check on mount → green pill "Connected to database" or red "Database offline" |
| `src/components/shared/ErrorCard.tsx` | 3 error states: `no_template` (info), `invalid_params` (warning with field list), generic (error) |
| `src/components/chat/ChatInput.tsx` | Multiline TextField + orange Send button; Enter submits, Shift+Enter newline |
| `src/components/chat/ChatMessage.tsx` | User bubble (right, orange) + Assistant bubble (left, skeleton → ResultCard or ErrorCard) |
| `src/components/chat/TypingIndicator.tsx` | Bouncing dots animation while `/chat` or `/execute` in flight |
| `src/components/sidebar/ExampleQuestions.tsx` | Suggested questions with colored icons; dark sidebar-aware styling |
| `src/components/results/ResultCard.tsx` | 4-tab Card: Table / Chart / Summary / Query; shows skeleton while `execute` pending |
| `src/components/results/ResultTable.tsx` | MUI X DataGrid with `GridToolbar` + quick filter |
| `src/components/results/ResultChart.tsx` | MUI X BarChart / LineChart / PieChart driven by `ChartConfig` from `/analyze` |
| `src/components/results/ResultSummary.tsx` | Skeleton while analyzing → AutoAwesome icon + LLM summary text |
| `src/components/results/QueryBadge.tsx` | Tool/template Chips + collapsible SQL pre block + active bind params |
| `src/lib/types.ts` | All TypeScript interfaces (ChatRequest/Response, ExecuteRequest/Response, ChartConfig, AnalyzeRequest/Response, ConversationEntry, QueryResult) |
| `src/lib/api.ts` | `apiChat()`, `apiExecute()`, `apiAnalyze()`, `apiHealth()` — all with 60s timeout |

### Non-obvious design decisions

**LLM never writes SQL** (`template_service.py`, `tools/`)
`TemplateService.resolve()` calls the LLM with OpenAI-compatible function definitions. The LLM picks a tool (e.g. `afe_financial`), a template key (e.g. `budget_vs_actuals_by_afe`), and typed filter values (e.g. `year=2025`). Pydantic validates against `Literal` enums and range constraints. A dict lookup returns the pre-written SQL string. The LLM never sees a cursor or writes a character of SQL.

**Conversational session history** (`session_store.py`, `routes.py`, `llm_service.py`)
Each browser session gets a UUID (`SESSION_ID` in `page.tsx`, generated once on page load). `/chat` calls `session_store.get_history(session_id)` and passes history to `generate_with_tools()` as prior messages. After the exchange, user + assistant messages are appended back. TTL 60 min, max 20 messages per session. Resetting on page reload is intentional — new page = new conversation.

**LLM-driven analysis** (`routes.py` → `POST /analyze`, `ResultChart.tsx`, `ResultSummary.tsx`)
After execute succeeds, frontend async fires `/analyze` with columns + rows (markdown-formatted) + `row_count`. Backend calls LLM with `_ANALYZE_TOOL` (OpenAI function format) which returns `ChartConfig` (type, x_key, y_keys, title) + `summary` string. Frontend shows data immediately; summary and chart config stream in non-blocking. Analyze failure is non-fatal — UI degrades gracefully.

**`approved_copy = 0` filter** (`tools/afe_financial.py`)
Every query against `fact_afe_budgets` includes `WHERE fb.approved_copy = 0 AND ...` as the first condition. This excludes supplemental/approved budget copies and returns only the working budget rows. Applied to all 12 templates that join `fact_afe_budgets`.

**Two tools, distinct domains** (`tools/afe_financial.py`, `tools/afe_master.py`)
- `afe_financial` — budget, actuals, commitments, spend analysis; 17 templates on `fact_afe_budgets`, `fact_afe_actuals`, `fact_afe_commitments`; filter params: `year`, `status`, `afe_type_description`, `afe_number`, `top_n`
- `afe_master` — AFE attributes, listings, timelines, approvals, rejections; 10 templates on `dim_afe`; filter params: same as `afe_financial` plus `afe_project_name` (project name exact match) and `company_name` (company exact match)
Tool docstrings explicitly tell the LLM which to use and when NOT to use each.

**NULL filter pattern** (`tools/`)
All filter params are optional. Every template uses `(:param IS NULL OR col = :param)` — when param is `None`, SQLAlchemy binds it as SQL `NULL`, and `NULL IS NULL` short-circuits to `TRUE`, applying no filter. One template handles all filter combinations without branching.

**Bind params via SQLAlchemy `text()`** (`query_executor.py`)
`QueryExecutorService.execute(sql, db, params)` calls `db.execute(text(sql), params or {})`. SQLAlchemy translates `:param` named syntax → `?` positional → SQL Server via pyodbc. `None` values become SQL `NULL`. Column names and structural SQL (GROUP BY, JOIN) are hard-coded in templates — bind params are for values only.

**Structured validation errors** (`template_service.py`, `routes.py`)
`resolve()` catches `pydantic.ValidationError` and raises `InvalidParamsError(tool_name, template, field_errors)` — a `ValueError` subclass carrying structured attributes. `routes.py` catches it before `ValueError` and returns `status="invalid_params"` with `tool_name` + `template_key` populated. Frontend `ErrorCard` displays tool/template metadata and per-field error list.

**`unknown_query` sentinel tool** (`tools/__init__.py`, `template_service.py`)
`ALL_TOOLS` includes an `unknown_query` tool with no parameters. The LLM picks this when the question doesn't match any available template. `TemplateService.resolve()` raises `ValueError` → `status="no_template"`. Forces `tool_choice="required"` so the LLM always picks a tool.

**MUI v9 + Next.js App Router SSR** (`layout.tsx`, `ThemeRegistry.tsx`)
`AppRouterCacheProvider` (from `@mui/material-nextjs/v16-appRouter`) lives in `layout.tsx` (Server Component) — it injects Emotion styles into the SSR HTML. `ThemeRegistry` is `'use client'` and holds `ThemeProvider` + `CssBaseline`. This split is required: passing a MUI theme object (which contains functions) from a Server Component to a Client Component causes a Next.js serialization error.

**`SHOW_TEMPLATE_DESCRIPTION`** (`config.py`, `routes.py`)
Controls whether the template description string is returned in `ChatResponse.reasoning`. When `false` (default), `reasoning=None`. Not LLM chain-of-thought — just a human-readable label from `TEMPLATE_DESCRIPTIONS` dict in each tool file.

**No retry loop** (`routes.py`)
The `/execute` endpoint does one execution attempt and returns. Pre-written SQL is deterministic — there is nothing for LLM repair to fix. `IterationDetail` and `retries` fields remain in `ExecuteResponse` schema for backward compatibility but are never populated.

**Lazy singleton services** (`routes.py` → `_services()`)
`LLMService`, `TemplateService`, and `QueryExecutorService` are not created at import time. `_services()` creates them on the first request and returns the same instances thereafter. Returns a 3-tuple `(llm, template_svc, executor)`.

**Multi-provider LLM dispatch** (`llm_service.py`)
`LLM_MODELS` is parsed into `(service, model, provider_hint)` tuples. Tried in order; falls through on error. Both `generate()` (plain text) and `generate_with_tools()` (tool-use) follow the same fallback chain. Supported services: `anthropic` (primary), `groq`, `openrouter`. Format: `anthropic:claude-sonnet-4-6` or `groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-3-5-sonnet@Together`.

**Anthropic vs OpenAI-compatible tool format** (`llm_service.py`)
Tool definitions in `tools/` use OpenAI function-calling format. When the active service is `anthropic`, `generate_with_tools()` converts them internally: `parameters` → `input_schema`, strips `type: function` wrapper, uses `tool_choice={"type": "any"}` instead of `"required"`. Anthropic response blocks are iterated for `block.type == "tool_use"` to extract `block.name` and `block.input`. For plain `generate()`, Anthropic system prompts are passed as the `system=` parameter (not in the messages list).

**Adding a new tool** (`tools/`)
1. Create `app/services/tools/<domain>.py` — Pydantic model with `Literal` template field, SQL templates dict, `resolve_<domain>()`, `_build_tool_definition()` returning OpenAI-format tool def. Add explicit docstring guidance on when to use vs. NOT use this tool vs. other tools.
2. Import and add to `ALL_TOOLS` in `app/services/tools/__init__.py`
3. Add `elif tool_name == "<domain>": resolver = resolve_<domain>` in `TemplateService.resolve()`

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

**`execution_time` in `ExecuteResponse`**
Field exists in Pydantic schema but never populated by `routes.py` (always `None`). Actual execution time logged server-side and stored in history list.
