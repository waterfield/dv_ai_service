from pydantic import BaseModel, Field
from typing import Literal


class AFEMasterRequest(BaseModel):
    """
    AFE master data: attributes, listings, status, project, company, and timeline info.

    Use for ANY question about AFE properties, lists, details, timelines, approvals,
    rejections, supplements, or metadata. Do NOT use for budget/actuals/spend — use afe_financial instead.

    Date range filters: approved_date_from/to (final_approval_date), completion_date_from/to
    (completion_date), closed_date_from/to (closed_date). All accept YYYY-MM-DD strings.
    Use both _from and _to for "between X and Y"; either alone for "after X" or "before Y".

    division_order_number: user may say "DO number", "division order", "DO", or "division order number" —
    all map to this filter.

    AFE supplements: amendments/revisions to an original AFE. supplement_number=0 is the original;
    1, 2, 3... are sequentially numbered supplements stored in dim_afe_supplement.

    template guide:
      list_afes               -> list individual AFEs; use when user asks for AFEs under/in/belonging to a specific project, company, type, or status — filters by those values
      afe_detail              -> full details for a specific AFE number
      afes_by_type            -> summary COUNT grouped by ALL types; do NOT use if user names a specific type and wants its AFEs — use list_afes instead
      afes_by_project         -> summary COUNT grouped by ALL projects; do NOT use if user names a specific project and wants its AFEs — use list_afes instead
      afes_by_company         -> summary COUNT grouped by ALL companies; do NOT use if user names a specific company — use list_afes instead
      afes_by_cost_center     -> summary COUNT grouped by ALL cost centers
      overdue_afes            -> open AFEs past their planned completion date
      rejected_afes           -> rejected AFEs with rejection reasons
      upcoming_completions    -> open AFEs sorted by planned completion date (soonest first)
      recently_approved       -> recently final-approved AFEs
      supplement_list         -> original AFE (supplement 0) + all numbered supplements; use when user asks about supplement history, amendments, or revisions for a specific AFE — filter by afe_number
      supplement_count        -> AFEs ranked by number of supplements; use when user asks which AFEs have been supplemented/amended most
    """

    template: Literal[
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

    year:                 int | None = Field(None, ge=2000, le=2030, description="Filter by planned start year (exact)")
    approved_date_from:   str | None = Field(None, description="Final approval date range start (YYYY-MM-DD) — use for 'approved after X' or 'approved between X and Y'")
    approved_date_to:     str | None = Field(None, description="Final approval date range end (YYYY-MM-DD) — use for 'approved before Y' or 'approved between X and Y'")
    completion_date_from: str | None = Field(None, description="Actual completion date range start (YYYY-MM-DD) — use for 'completed after X' or 'completed between X and Y'")
    completion_date_to:   str | None = Field(None, description="Actual completion date range end (YYYY-MM-DD)")
    closed_date_from:     str | None = Field(None, description="Closed date range start (YYYY-MM-DD) — use for 'closed after X' or 'closed between X and Y'")
    closed_date_to:       str | None = Field(None, description="Closed date range end (YYYY-MM-DD)")
    status:               Literal["Open", "Completed", "Rejected"] | None = None
    afe_type_description: Literal[
        "Expense Workover", "Plug & Abandonment", "Recompletion", "Reclamation",
        "Stake & Permit", "Facility", "Land/Acquisition", "Nonop Drill & Complete",
        "Environmental", "Lease and Well Equipment", "Other", "Geological & Geospatial",
        "Drill & Complete", "Internal",
    ] | None = None
    afe_number:             str | None = Field(None, description="Specific AFE number e.g. AFE-2025-001")
    afe_project_name:       str | None = Field(None, description="Filter by project name e.g. '2023 - MIDSTREAM FACILITY AFEs'")
    company_name:           str | None = Field(None, description="Filter by company name")
    division_order_number:  str | None = Field(None, description="Filter by division order number (also called DO number, division order, DO) — maps to dim_afe.division_order_number")
    top_n:                  int = Field(20, ge=1, le=100, description="Maximum rows to return")


TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "list_afes":            "List of AFEs with key attributes",
    "afe_detail":           "Full details for a specific AFE",
    "afes_by_type":         "AFE count and list grouped by type",
    "afes_by_project":      "AFEs grouped by project",
    "afes_by_company":      "AFEs grouped by company",
    "afes_by_cost_center":  "AFEs grouped by cost center",
    "overdue_afes":         "Open AFEs past their planned completion date",
    "rejected_afes":        "Rejected AFEs with rejection reasons",
    "upcoming_completions": "Open AFEs sorted by upcoming planned completion date",
    "recently_approved":    "Recently final-approved AFEs",
    "supplement_list":      "Original AFE + all numbered supplements with status and budget",
    "supplement_count":     "AFEs ranked by number of supplements (most amended first)",
}

AFE_MASTER_TEMPLATES: dict[str, str] = {

    "list_afes": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.status                   AS [Status],
            da.afe_type_description     AS [Type],
            da.afe_project_name         AS [Project],
            da.company_name             AS [Company],
            da.planned_start_date       AS [Planned Start],
            da.planned_completion_date  AS [Planned Completion],
            da.final_approval_date      AS [Approval Date],
            da.completion_date          AS [Completion Date],
            da.closed_date              AS [Closed Date],
            da.budget_total             AS [Budget Total]
        FROM dim_afe da
        WHERE (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:afe_number            IS NULL OR da.number = :afe_number)
          AND (:afe_project_name      IS NULL OR da.afe_project_name = :afe_project_name)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY da.planned_start_date DESC
    """,

    "afe_detail": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.description              AS [Description],
            da.status                   AS [Status],
            da.afe_type_name            AS [Type Name],
            da.afe_type_description     AS [Type Description],
            da.afe_project_name         AS [Project Name],
            da.afe_project_number       AS [Project Number],
            da.afe_project_description  AS [Project Description],
            da.company_name             AS [Company],
            da.company_description      AS [Company Description],
            da.planned_start_date       AS [Planned Start],
            da.planned_completion_date  AS [Planned Completion],
            da.final_approval_date      AS [Final Approval Date],
            da.completion_date          AS [Completion Date],
            da.closed_date              AS [Closed Date],
            da.max_months               AS [Max Months],
            da.net_interest             AS [Net Interest],
            da.budget_total             AS [Budget Total],
            da.combined_budget_total    AS [Combined Budget Total],
            da.financial_afe_number     AS [Financial AFE Number],
            da.reject_reason            AS [Reject Reason]
        FROM dim_afe da
        WHERE (:afe_number            IS NULL OR da.number = :afe_number)
          AND (:status                IS NULL OR da.status = :status)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY da.planned_start_date DESC
    """,

    "afes_by_type": """
        SELECT TOP (:top_n)
            da.afe_type_description     AS [Type],
            COUNT(*)                    AS [AFE Count],
            SUM(da.budget_total)        AS [Total Budget]
        FROM dim_afe da
        WHERE (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        GROUP BY da.afe_type_description
        ORDER BY [AFE Count] DESC
    """,

    "afes_by_project": """
        SELECT TOP (:top_n)
            da.afe_project_number       AS [Project Number],
            da.afe_project_name         AS [Project Name],
            COUNT(*)                    AS [AFE Count],
            SUM(da.budget_total)        AS [Total Budget],
            MIN(da.planned_start_date)  AS [Earliest Start],
            MAX(da.planned_completion_date) AS [Latest Completion]
        FROM dim_afe da
        WHERE (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        GROUP BY da.afe_project_number, da.afe_project_name
        ORDER BY [AFE Count] DESC
    """,

    "afes_by_company": """
        SELECT TOP (:top_n)
            da.company_name             AS [Company],
            COUNT(*)                    AS [AFE Count],
            SUM(da.budget_total)        AS [Total Budget]
        FROM dim_afe da
        WHERE (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        GROUP BY da.company_name
        ORDER BY [AFE Count] DESC
    """,

    "afes_by_cost_center": """
        SELECT TOP (:top_n)
            dc.name                     AS [Cost Center],
            COUNT(*)                    AS [AFE Count],
            SUM(da.budget_total)        AS [Total Budget]
        FROM dim_afe da
        JOIN dim_cost_center dc ON da.cost_center_id = dc.id
        WHERE (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        GROUP BY dc.name
        ORDER BY [AFE Count] DESC
    """,

    "overdue_afes": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.afe_type_description     AS [Type],
            da.planned_completion_date  AS [Planned Completion],
            DATEDIFF(DAY, da.planned_completion_date, GETDATE()) AS [Days Overdue],
            da.budget_total             AS [Budget Total],
            da.company_name             AS [Company]
        FROM dim_afe da
        WHERE da.status = 'Open'
          AND da.planned_completion_date < GETDATE()
          AND (:year                  IS NULL OR YEAR(da.planned_start_date) = :year)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:afe_project_name      IS NULL OR da.afe_project_name = :afe_project_name)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY [Days Overdue] DESC
    """,

    "rejected_afes": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.afe_type_description     AS [Type],
            da.reject_reason            AS [Reject Reason],
            da.status_date              AS [Rejection Date],
            da.budget_total             AS [Budget Total],
            da.company_name             AS [Company]
        FROM dim_afe da
        WHERE da.status = 'Rejected'
          AND (:year                  IS NULL OR YEAR(da.status_date) = :year)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:afe_number            IS NULL OR da.number = :afe_number)
          AND (:afe_project_name         IS NULL OR da.afe_project_name = :afe_project_name)
          AND (:company_name             IS NULL OR da.company_name = :company_name)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY da.status_date DESC
    """,

    "upcoming_completions": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.afe_type_description     AS [Type],
            da.planned_completion_date  AS [Planned Completion],
            DATEDIFF(DAY, GETDATE(), da.planned_completion_date) AS [Days Remaining],
            da.budget_total             AS [Budget Total],
            da.company_name             AS [Company]
        FROM dim_afe da
        WHERE da.status = 'Open'
          AND da.planned_completion_date >= GETDATE()
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:afe_project_name      IS NULL OR da.afe_project_name = :afe_project_name)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY da.planned_completion_date ASC
    """,

    "recently_approved": """
        SELECT TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.afe_type_description     AS [Type],
            da.final_approval_date      AS [Approval Date],
            da.planned_start_date       AS [Planned Start],
            da.planned_completion_date  AS [Planned Completion],
            da.budget_total             AS [Budget Total],
            da.company_name             AS [Company]
        FROM dim_afe da
        WHERE da.final_approval_date IS NOT NULL
          AND (:year                  IS NULL OR YEAR(da.final_approval_date) = :year)
          AND (:status                IS NULL OR da.status = :status)
          AND (:afe_type_description  IS NULL OR da.afe_type_description = :afe_type_description)
          AND (:afe_project_name      IS NULL OR da.afe_project_name = :afe_project_name)
          AND (:company_name          IS NULL OR da.company_name = :company_name)
          AND (:approved_date_from       IS NULL OR da.final_approval_date >= :approved_date_from)
          AND (:approved_date_to         IS NULL OR da.final_approval_date <= :approved_date_to)
          AND (:completion_date_from     IS NULL OR da.completion_date >= :completion_date_from)
          AND (:completion_date_to       IS NULL OR da.completion_date <= :completion_date_to)
          AND (:closed_date_from         IS NULL OR da.closed_date >= :closed_date_from)
          AND (:closed_date_to           IS NULL OR da.closed_date <= :closed_date_to)
          AND (:division_order_number    IS NULL OR da.division_order_number = :division_order_number)
        ORDER BY da.final_approval_date DESC
    """,

    "supplement_list": """
        WITH afe_supplement_list AS (
            SELECT  da.number              AS [AFE Number],
                    da.name                AS [AFE Name],
                    0                      AS [Supplement Number],
                    da.status              AS [Status],
                    da.planned_start_date  AS [Planned Start Date],
                    da.budget_total        AS [Budget Total]
            FROM    dim_afe da
            WHERE   (:afe_number IS NULL OR da.number = :afe_number)

            UNION ALL

            SELECT  da.number              AS [AFE Number],
                    da.name                AS [AFE Name],
                    sup.number             AS [Supplement Number],
                    sup.status             AS [Status],
                    sup.planned_start_date AS [Planned Start Date],
                    sup.budget_total       AS [Budget Total]
            FROM    dim_afe_supplement sup
            JOIN    dim_afe da ON sup.afe_id = da.id
            WHERE   (:afe_number IS NULL OR da.number = :afe_number)
        )
        SELECT  TOP (:top_n)
            [AFE Number],
            [AFE Name],
            [Supplement Number],
            [Status],
            [Planned Start Date],
            [Budget Total]
        FROM    afe_supplement_list
        ORDER BY [AFE Number], [Supplement Number]
    """,

    "supplement_count": """
        SELECT  TOP (:top_n)
            da.number                   AS [AFE Number],
            da.name                     AS [AFE Name],
            da.status                   AS [Status],
            da.afe_type_description     AS [Type],
            da.company_name             AS [Company],
            COUNT(sup.number)           AS [Supplement Count],
            da.budget_total             AS [Original Budget Total]
        FROM    dim_afe da
        LEFT JOIN dim_afe_supplement sup ON sup.afe_id = da.id
        WHERE   (:year                 IS NULL OR YEAR(da.planned_start_date) = :year)
          AND   (:status               IS NULL OR da.status = :status)
          AND   (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
          AND   (:company_name         IS NULL OR da.company_name = :company_name)
          AND   (:afe_number           IS NULL OR da.number = :afe_number)
        GROUP BY da.number, da.name, da.status, da.afe_type_description, da.company_name, da.budget_total
        HAVING  COUNT(sup.number) > 0
        ORDER BY [Supplement Count] DESC
    """,
}


def resolve_afe_master(tool_args: dict) -> tuple[str, dict, str]:
    """Validate tool_args via Pydantic, look up template, build params dict.

    Returns: (sql_string, params_dict, reasoning_string)
    Raises: pydantic.ValidationError if tool_args are invalid.
    """
    request = AFEMasterRequest(**tool_args)
    sql = AFE_MASTER_TEMPLATES[request.template]
    params = {
        "year":                 request.year,
        "approved_date_from":   request.approved_date_from,
        "approved_date_to":     request.approved_date_to,
        "completion_date_from": request.completion_date_from,
        "completion_date_to":   request.completion_date_to,
        "closed_date_from":     request.closed_date_from,
        "closed_date_to":       request.closed_date_to,
        "status":               request.status,
        "afe_type_description": request.afe_type_description,
        "afe_number":             request.afe_number,
        "afe_project_name":       request.afe_project_name,
        "company_name":           request.company_name,
        "division_order_number":  request.division_order_number,
        "top_n":                  request.top_n,
    }
    reasoning = TEMPLATE_DESCRIPTIONS.get(request.template, request.template)
    return sql, params, reasoning


def _build_tool_definition() -> dict:
    schema = AFEMasterRequest.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return {
        "type": "function",
        "function": {
            "name": "afe_master",
            "description": AFEMasterRequest.__doc__.strip(),
            "parameters": schema,
        },
    }


AFE_MASTER_TOOL_DEFINITION = _build_tool_definition()
