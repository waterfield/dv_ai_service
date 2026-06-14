from contextlib import contextmanager
from typing import Literal, Optional
from pydantic import ValidationError

from database import get_db
from app.mcp import mcp, _executor
from app.services.unsupported_log import log_unsupported
from app.services.tools.afe_financial import (
    resolve_afe_financial,
    TEMPLATE_DESCRIPTIONS as FINANCIAL_DESCRIPTIONS,
)
from app.services.tools.afe_master import (
    resolve_afe_master,
    TEMPLATE_DESCRIPTIONS as MASTER_DESCRIPTIONS,
)

FinancialTemplate = Literal[
    "budget_by_cost_center",
    "budget_by_afe",
    "budget_by_afe_type",
    "budget_by_project",
    "budget_by_year",
    "budget_by_month",
    "budget_by_quarter",
    "budget_total",
    "actuals_by_cost_center",
    "actuals_by_afe",
    "actuals_by_afe_type",
    "actuals_by_project",
    "actuals_by_year",
    "actuals_by_month",
    "actuals_by_quarter",
    "budget_vs_actuals_by_year",
    "budget_vs_actuals_by_month",
    "budget_vs_actuals_by_afe",
    "budget_vs_actuals_by_cost_center",
    "budget_vs_actuals_by_afe_type",
    "budget_vs_actuals_by_project",
    "full_picture_by_afe",
    "consumed_pct_by_cost_center",
    "consumed_pct_by_afe",
    "remaining_by_afe",
]

MasterTemplate = Literal[
    "list_afes",
    "afe_detail",
    "afes_by_type",
    "afes_by_project",
    "afes_by_company",
    "afes_by_cost_center",
    "overdue_afes",
    "rejected_afes",
    "upcoming_completions",
    "recently_approved",
    "supplement_list",
    "supplement_count",
]


@contextmanager
def _get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def _run_query(sql: str, params: dict) -> str:
    with _get_db_session() as db:
        df, error = _executor.execute(sql, db, params)
    if error:
        return f"Query failed: {error}"
    if df is None or df.empty:
        return "No results found."
    return df.to_markdown(index=False)


@mcp.tool(
    description=(
        "Query AFE financial data: budget, actuals, commitments, spend, variance, "
        "% consumed, and remaining budget. Use for ANY question about AFE money or spend. "
        "Do NOT use for AFE master data (attributes, timelines, approvals) — use "
        "query_afe_master instead. For a COMPLETE AFE summary, always pair with "
        "query_afe_master. Template values are enumerated in the schema."
    )
)
def query_afe_financial(
    template: FinancialTemplate,
    afe_numbers: list[str] | None = None,
    year: int | None = None,
    status: str | None = None,
    afe_type_description: str | None = None,
    top_n: int = 20,
) -> str:
    """
    template: one of the afe_financial template keys (call get_templates to see options).
    afe_numbers: one or more AFE identifiers e.g. ['AFE-2025-001'] or ['AFE-2025-001', 'AFE-2025-002'].
    year: filter by budget/actuals year e.g. 2024.
    status: 'Open', 'Completed', or 'Rejected'.
    afe_type_description: AFE type e.g. 'Drill & Complete', 'Facility'.
    top_n: max rows to return (1-100, default 20).
    """
    tool_args = {
        "template": template,
        "afe_numbers": afe_numbers,
        "year": year,
        "status": status,
        "afe_type_description": afe_type_description,
        "top_n": top_n,
    }
    try:
        sql, params, _ = resolve_afe_financial(tool_args)
    except ValidationError as e:
        msgs = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return f"Error — invalid parameters: {'; '.join(msgs)}"
    return _run_query(sql, params)


@mcp.tool(
    description=(
        "Query AFE master data: attributes, listings, status, project, company, "
        "timelines, approvals, and rejections. Use for ANY question about AFE properties "
        "or metadata. Do NOT use for budget/actuals/spend — use query_afe_financial instead. "
        "For a COMPLETE AFE summary, always pair with query_afe_financial. "
        "Template values are enumerated in the schema."
    )
)
def query_afe_master(
    template: MasterTemplate,
    afe_number: str | None = None,
    year: int | None = None,
    status: str | None = None,
    afe_type_description: str | None = None,
    afe_project_name: str | None = None,
    company_name: str | None = None,
    division_order_number: str | None = None,
    approved_date_from: str | None = None,
    approved_date_to: str | None = None,
    completion_date_from: str | None = None,
    completion_date_to: str | None = None,
    closed_date_from: str | None = None,
    closed_date_to: str | None = None,
    top_n: int = 20,
) -> str:
    """
    template: one of the afe_master template keys (call get_templates to see options).
    afe_number: specific AFE identifier e.g. 'AFE-2025-001'.
    year: filter by planned start year e.g. 2024.
    status: 'Open', 'Completed', or 'Rejected'.
    afe_type_description: AFE type e.g. 'Drill & Complete', 'Facility'.
    afe_project_name: exact project name e.g. '2023 - MIDSTREAM FACILITY AFEs'.
    company_name: filter by company name.
    division_order_number: filter by division order number (also called DO number).
    approved_date_from: final approval date range start YYYY-MM-DD.
    approved_date_to: final approval date range end YYYY-MM-DD.
    completion_date_from: completion date range start YYYY-MM-DD.
    completion_date_to: completion date range end YYYY-MM-DD.
    closed_date_from: closed date range start YYYY-MM-DD.
    closed_date_to: closed date range end YYYY-MM-DD.
    top_n: max rows to return (1-100, default 20).
    """
    tool_args = {
        "template": template,
        "afe_number": afe_number,
        "year": year,
        "status": status,
        "afe_type_description": afe_type_description,
        "afe_project_name": afe_project_name,
        "company_name": company_name,
        "division_order_number": division_order_number,
        "approved_date_from": approved_date_from,
        "approved_date_to": approved_date_to,
        "completion_date_from": completion_date_from,
        "completion_date_to": completion_date_to,
        "closed_date_from": closed_date_from,
        "closed_date_to": closed_date_to,
        "top_n": top_n,
    }
    try:
        sql, params, _ = resolve_afe_master(tool_args)
    except ValidationError as e:
        msgs = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return f"Error — invalid parameters: {'; '.join(msgs)}"
    return _run_query(sql, params)


@mcp.tool(
    description=(
        "List all available query templates with descriptions. "
        "Call this first when unsure which template to use for query_afe_financial "
        "or query_afe_master. Filter by tool_name to see only financial or master templates."
    )
)
def get_templates(tool_name: str | None = None) -> str:
    """
    tool_name: optional filter — 'afe_financial' or 'afe_master'. Omit for all templates.
    """
    lines = []
    if tool_name != "afe_master":
        lines.append("## afe_financial templates")
        for key, desc in FINANCIAL_DESCRIPTIONS.items():
            lines.append(f"- {key}: {desc}")
    if tool_name != "afe_financial":
        lines.append("## afe_master templates")
        for key, desc in MASTER_DESCRIPTIONS.items():
            lines.append(f"- {key}: {desc}")
    return "\n".join(lines)


@mcp.tool(
    description=(
        "Call this when the user's question cannot be answered by any available template "
        "in query_afe_financial or query_afe_master. Logs the unsupported query so it can "
        "be reviewed and a new template added. Do NOT call this if a template exists — "
        "only use as a last resort."
    )
)
def unknown_query(description: str) -> str:
    """
    description: plain English description of what the user asked for that couldn't be answered.
    """
    log_unsupported("mcp", description)
    return (
        f"No template available for: '{description}'. "
        "This request has been logged for review. "
        "A new template may be added in a future update."
    )
