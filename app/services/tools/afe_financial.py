from pydantic import BaseModel, Field
from typing import Literal


class AFEFinancialRequest(BaseModel):
    """
    AFE financial data: budget, actuals, commitments, and comparisons.

    Use for ANY question about AFE money, spend, costs, variance, remaining budget,
    or % consumed. Do NOT use for AFE master data / attribute lists.

    template guide:
      budget_by_cost_center             -> budget breakdown by department
      budget_by_afe                     -> budget per individual AFE
      budget_by_year                    -> budget trend over years
      budget_by_quarter                 -> budget trend by quarter
      budget_total                      -> single grand total
      actuals_by_cost_center            -> actual spend by department
      actuals_by_afe                    -> actual spend per AFE
      actuals_by_year                   -> actual spend trend by year
      actuals_by_quarter                -> actual spend trend by quarter
      actuals_by_region                 -> actual spend by region
      budget_vs_actuals_by_year         -> budget vs actuals comparison with variance by year
      budget_vs_actuals_by_afe          -> budget vs actuals comparison per AFE
      budget_vs_actuals_by_cost_center  -> budget vs actuals comparison by department
      full_picture_by_afe               -> budget + actuals + commitments + remaining per AFE
      consumed_pct_by_cost_center       -> % budget spent by department
      consumed_pct_by_afe               -> % budget spent per AFE
      remaining_by_afe                  -> remaining budget per AFE after actuals + commitments
    """

    template: Literal[
        "budget_by_cost_center",
        "budget_by_afe",
        "budget_by_year",
        "budget_by_quarter",
        "budget_total",
        "actuals_by_cost_center",
        "actuals_by_afe",
        "actuals_by_year",
        "actuals_by_quarter",
        "actuals_by_region",
        "budget_vs_actuals_by_year",
        "budget_vs_actuals_by_afe",
        "budget_vs_actuals_by_cost_center",
        "full_picture_by_afe",
        "consumed_pct_by_cost_center",
        "consumed_pct_by_afe",
        "remaining_by_afe",
    ]

    year:       int | None = Field(None, ge=2000, le=2030, description="Budget/actuals year")
    status:     Literal["Open", "Completed", "Rejected"] | None = None
    afe_type_description:   Literal["Expense Workover", "Plug & Abandonment", "Recompletion", "Reclamation", "Stake & Permit", "Facility", "Land/Acquisition", "Nonop Drill & Complete", "Environmental", "Lease and Well Equipment", "Other", "Geological & Geospatial", "Drill & Complete", "Internal"] | None = None
    afe_number: str | None = Field(None, description="Specific AFE identifier e.g. AFE-2025-001")
    top_n:      int = Field(20, ge=1, le=100, description="Maximum rows to return")


TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "budget_by_cost_center":            "Budget breakdown by cost center",
    "budget_by_afe":                    "Budget per individual AFE",
    "budget_by_year":                   "Budget trend over years",
    "budget_by_quarter":                "Budget trend by quarter",
    "budget_total":                     "Grand total budget amount and AFE count",
    "actuals_by_cost_center":           "Actual spend by cost center",
    "actuals_by_afe":                   "Actual spend per AFE",
    "actuals_by_year":                  "Actual spend trend by year",
    "actuals_by_quarter":               "Actual spend trend by quarter",
    "actuals_by_region":                "Actual spend by geographic region",
    "budget_vs_actuals_by_year":        "Budget vs actuals with variance by year",
    "budget_vs_actuals_by_afe":         "Budget vs actuals with % consumed per AFE",
    "budget_vs_actuals_by_cost_center": "Budget vs actuals with variance by cost center",
    "full_picture_by_afe":              "Full picture: budget, actuals, commitments, and remaining per AFE",
    "consumed_pct_by_cost_center":      "% of budget consumed by cost center",
    "consumed_pct_by_afe":              "% of budget consumed per AFE",
    "remaining_by_afe":                 "Remaining budget after actuals and commitments per AFE",
}

AFE_FINANCIAL_TEMPLATES: dict[str, str] = {

    "budget_by_cost_center": """
        SELECT TOP (:top_n)
            dc.name             AS [Cost Center],
            SUM(fb.amount)      AS [Budget Amount]
        FROM fact_afe_budgets fb
        JOIN dim_cost_center dc ON fb.cost_center_id = dc.id
        JOIN dim_afe da         ON fb.afe_id = da.id
        WHERE (:year     IS NULL OR YEAR(fb.afe_budget_date) = :year)
          AND (:status   IS NULL OR da.status   = :status)
          AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
        GROUP BY dc.name
        ORDER BY [Budget Amount] DESC
    """,

    "budget_by_afe": """
        SELECT TOP (:top_n)
            da.number       AS [AFE Number],
            da.name             AS [AFE Name],
            da.status           AS [Status],
            SUM(fb.amount)      AS [Budget Amount]
        FROM fact_afe_budgets fb
        JOIN dim_afe da ON fb.afe_id = da.id
        WHERE (:year       IS NULL OR YEAR(fb.afe_budget_date) = :year)
          AND (:status     IS NULL OR da.status     = :status)
          AND (:afe_type_description   IS NULL OR da.afe_type_description   = :afe_type_description)
          AND (:afe_number IS NULL OR da.number = :afe_number)
        GROUP BY da.number, da.name, da.status
        ORDER BY [Budget Amount] DESC
    """,

    "budget_by_year": """
        SELECT TOP (:top_n)
            YEAR(fb.afe_budget_date)    AS [Year],
            SUM(fb.amount)              AS [Budget Amount]
        FROM fact_afe_budgets fb
        JOIN dim_afe da ON fb.afe_id = da.id
        WHERE (:status   IS NULL OR da.status   = :status)
          AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
        GROUP BY YEAR(fb.afe_budget_date)
        ORDER BY [Year] DESC
    """,

    "budget_by_quarter": """
        SELECT TOP (:top_n)
            YEAR(fb.afe_budget_date)                AS [Year],
            DATEPART(QUARTER, fb.afe_budget_date)   AS [Quarter],
            SUM(fb.amount)                          AS [Budget Amount]
        FROM fact_afe_budgets fb
        JOIN dim_afe da ON fb.afe_id = da.id
        WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
          AND (:status IS NULL OR da.status = :status)
        GROUP BY YEAR(fb.afe_budget_date), DATEPART(QUARTER, fb.afe_budget_date)
        ORDER BY [Year] DESC, [Quarter] ASC
    """,

    "budget_total": """
        SELECT
            SUM(fb.amount)                  AS [Budget Amount],
            COUNT(DISTINCT da.number)   AS [AFE Count]
        FROM fact_afe_budgets fb
        JOIN dim_afe da ON fb.afe_id = da.id
        WHERE (:year     IS NULL OR YEAR(fb.afe_budget_date) = :year)
          AND (:status   IS NULL OR da.status   = :status)
          AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
    """,

    "actuals_by_cost_center": """
        SELECT TOP (:top_n)
            dc.name             AS [Cost Center],
            SUM(fa.amount)      AS [Actual Amount]
        FROM fact_afe_actuals fa
        JOIN dim_cost_center dc ON fa.cost_center_id = dc.id
        JOIN dim_afe da         ON fa.afe_id = da.id
        WHERE (:year     IS NULL OR YEAR(fa.accounting_date) = :year)
          AND (:status   IS NULL OR da.status   = :status)
          AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
        GROUP BY dc.name
        ORDER BY [Actual Amount] DESC
    """,

    "actuals_by_afe": """
        SELECT TOP (:top_n)
            da.number       AS [AFE Number],
            da.name             AS [AFE Name],
            da.status           AS [Status],
            SUM(fa.amount)      AS [Actual Amount]
        FROM fact_afe_actuals fa
        JOIN dim_afe da ON fa.afe_id = da.id
        WHERE (:year       IS NULL OR YEAR(fa.accounting_date) = :year)
          AND (:status     IS NULL OR da.status     = :status)
          AND (:afe_number IS NULL OR da.number = :afe_number)
        GROUP BY da.number, da.name, da.status
        ORDER BY [Actual Amount] DESC
    """,

    "actuals_by_year": """
        SELECT TOP (:top_n)
            YEAR(fa.accounting_date)    AS [Year],
            SUM(fa.amount)              AS [Actual Amount]
        FROM fact_afe_actuals fa
        JOIN dim_afe da ON fa.afe_id = da.id
        WHERE (:status   IS NULL OR da.status   = :status)
          AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
        GROUP BY YEAR(fa.accounting_date)
        ORDER BY [Year] DESC
    """,

    "actuals_by_quarter": """
        SELECT TOP (:top_n)
            YEAR(fa.accounting_date)                AS [Year],
            DATEPART(QUARTER, fa.accounting_date)   AS [Quarter],
            SUM(fa.amount)                          AS [Actual Amount]
        FROM fact_afe_actuals fa
        JOIN dim_afe da ON fa.afe_id = da.id
        WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
          AND (:status IS NULL OR da.status = :status)
        GROUP BY YEAR(fa.accounting_date), DATEPART(QUARTER, fa.accounting_date)
        ORDER BY [Year] DESC, [Quarter] ASC
    """,

    "actuals_by_region": """
        SELECT TOP (:top_n)
            da.region                           AS [Region],
            SUM(fa.amount)                      AS [Actual Amount],
            COUNT(DISTINCT da.number)       AS [AFE Count]
        FROM fact_afe_actuals fa
        JOIN dim_afe da ON fa.afe_id = da.id
        WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
          AND (:status IS NULL OR da.status = :status)
        GROUP BY da.region
        ORDER BY [Actual Amount] DESC
    """,

    "budget_vs_actuals_by_year": """
        WITH budgets AS (
            SELECT YEAR(fb.afe_budget_date)  AS [Year],
                   SUM(fb.amount)            AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_afe da ON fb.afe_id = da.id
            WHERE (:status   IS NULL OR da.status   = :status)
              AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
            GROUP BY YEAR(fb.afe_budget_date)
        ),
        actuals AS (
            SELECT YEAR(fa.accounting_date)  AS [Year],
                   SUM(fa.amount)            AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_afe da ON fa.afe_id = da.id
            WHERE (:status   IS NULL OR da.status   = :status)
              AND (:afe_type_description IS NULL OR da.afe_type_description = :afe_type_description)
            GROUP BY YEAR(fa.accounting_date)
        )
        SELECT TOP (:top_n)
            COALESCE(b.[Year], a.[Year])                                      AS [Year],
            COALESCE(b.[Budget Amount], 0)                                    AS [Budget Amount],
            COALESCE(a.[Actual Amount], 0)                                    AS [Actual Amount],
            COALESCE(a.[Actual Amount], 0) - COALESCE(b.[Budget Amount], 0)   AS [Variance],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                (COALESCE(a.[Actual Amount], 0) - COALESCE(b.[Budget Amount], 0))
                * 100.0 / b.[Budget Amount], 0)                               AS [Variance %]
        FROM budgets b
        FULL OUTER JOIN actuals a ON b.[Year] = a.[Year]
        ORDER BY [Year] DESC
    """,

    "budget_vs_actuals_by_afe": """
        WITH budgets AS (
            SELECT da.number afe_number, da.name, da.status,
                   SUM(fb.amount)  AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_afe da ON fb.afe_id = da.id
            WHERE (:year     IS NULL OR YEAR(fb.afe_budget_date) = :year)
              AND (:status   IS NULL OR da.status   = :status)
            GROUP BY da.number, da.name, da.status
        ),
        actuals AS (
            SELECT da.number afe_number,
                   SUM(fa.amount)  AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_afe da ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
            GROUP BY da.number
        )
        SELECT TOP (:top_n)
            b.afe_number                                                      AS [AFE Number],
            b.name                                                            AS [AFE Name],
            b.status                                                          AS [Status],
            COALESCE(b.[Budget Amount], 0)                                    AS [Budget Amount],
            COALESCE(a.[Actual Amount], 0)                                    AS [Actual Amount],
            COALESCE(a.[Actual Amount], 0) - COALESCE(b.[Budget Amount], 0)   AS [Variance],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                COALESCE(a.[Actual Amount], 0) * 100.0 / b.[Budget Amount], 0) AS [% Consumed]
        FROM budgets b
        LEFT JOIN actuals a ON b.afe_number = a.afe_number
        ORDER BY [% Consumed] DESC
    """,

    "budget_vs_actuals_by_cost_center": """
        WITH budgets AS (
            SELECT dc.name          AS [Cost Center],
                   SUM(fb.amount)   AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_cost_center dc ON fb.cost_center_id = dc.id
            JOIN dim_afe da         ON fb.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
              AND (:status IS NULL OR da.status = :status)
            GROUP BY dc.name
        ),
        actuals AS (
            SELECT dc.name          AS [Cost Center],
                   SUM(fa.amount)   AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_cost_center dc ON fa.cost_center_id = dc.id
            JOIN dim_afe da         ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
              AND (:status IS NULL OR da.status = :status)
            GROUP BY dc.name
        )
        SELECT TOP (:top_n)
            COALESCE(b.[Cost Center], a.[Cost Center])               AS [Cost Center],
            COALESCE(b.[Budget Amount], 0)                           AS [Budget Amount],
            COALESCE(a.[Actual Amount], 0)                           AS [Actual Amount],
            COALESCE(a.[Actual Amount], 0) - COALESCE(b.[Budget Amount], 0) AS [Variance],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                (COALESCE(a.[Actual Amount], 0) - COALESCE(b.[Budget Amount], 0))
                * 100.0 / b.[Budget Amount], 0)                     AS [Variance %]
        FROM budgets b
        FULL OUTER JOIN actuals a ON b.[Cost Center] = a.[Cost Center]
        ORDER BY [Variance %] DESC
    """,

    "full_picture_by_afe": """
        WITH budgets AS (
            SELECT da.number, da.name, da.status,
                   SUM(fb.amount)           AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_afe da ON fb.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
              AND (:status IS NULL OR da.status = :status)
            GROUP BY da.number, da.name, da.status
        ),
        actuals AS (
            SELECT da.number,
                   SUM(fa.amount)           AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_afe da ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
            GROUP BY da.number
        ),
        commitments AS (
            SELECT da.number,
                   SUM(fc.committed_amount) AS [Committed Amount]
            FROM fact_afe_commitments fc
            JOIN dim_afe da ON fc.afe_id = da.id
            WHERE fc.status != 'Cancelled'
            GROUP BY da.number
        )
        SELECT TOP (:top_n)
            b.afe_number                                                AS [AFE Number],
            b.name                                                      AS [AFE Name],
            b.status                                                    AS [Status],
            COALESCE(b.[Budget Amount],    0)                           AS [Budget Amount],
            COALESCE(a.[Actual Amount],    0)                           AS [Actual Amount],
            COALESCE(c.[Committed Amount], 0)                           AS [Committed Amount],
            COALESCE(b.[Budget Amount],    0)
                - COALESCE(a.[Actual Amount],    0)
                - COALESCE(c.[Committed Amount], 0)                    AS [Remaining Budget],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                COALESCE(a.[Actual Amount], 0) * 100.0
                    / b.[Budget Amount], 0)                            AS [% Consumed],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                (COALESCE(a.[Actual Amount], 0) + COALESCE(c.[Committed Amount], 0))
                    * 100.0 / b.[Budget Amount], 0)                   AS [% Exposed]
        FROM budgets b
        LEFT JOIN actuals     a ON b.afe_number = a.afe_number
        LEFT JOIN commitments c ON b.afe_number = c.afe_number
        ORDER BY [% Exposed] DESC
    """,

    "consumed_pct_by_cost_center": """
        WITH budgets AS (
            SELECT dc.name          AS [Cost Center],
                   SUM(fb.amount)   AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_cost_center dc ON fb.cost_center_id = dc.id
            JOIN dim_afe da         ON fb.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
            GROUP BY dc.name
        ),
        actuals AS (
            SELECT dc.name          AS [Cost Center],
                   SUM(fa.amount)   AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_cost_center dc ON fa.cost_center_id = dc.id
            JOIN dim_afe da         ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
            GROUP BY dc.name
        )
        SELECT TOP (:top_n)
            b.[Cost Center],
            COALESCE(b.[Budget Amount], 0)  AS [Budget Amount],
            COALESCE(a.[Actual Amount], 0)  AS [Actual Amount],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                COALESCE(a.[Actual Amount], 0) * 100.0 / b.[Budget Amount], 0) AS [% Consumed]
        FROM budgets b
        LEFT JOIN actuals a ON b.[Cost Center] = a.[Cost Center]
        ORDER BY [% Consumed] DESC
    """,

    "consumed_pct_by_afe": """
        WITH budgets AS (
            SELECT da.number, da.name, da.status,
                   SUM(fb.amount) AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_afe da ON fb.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
              AND (:status IS NULL OR da.status = :status)
            GROUP BY da.number, da.name, da.status
        ),
        actuals AS (
            SELECT da.number,
                   SUM(fa.amount) AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_afe da ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
            GROUP BY da.number
        )
        SELECT TOP (:top_n)
            b.afe_number                                             AS [AFE Number],
            b.name                                                   AS [AFE Name],
            b.status                                                 AS [Status],
            COALESCE(b.[Budget Amount], 0)                           AS [Budget Amount],
            COALESCE(a.[Actual Amount], 0)                           AS [Actual Amount],
            IIF(COALESCE(b.[Budget Amount], 0) > 0,
                COALESCE(a.[Actual Amount], 0) * 100.0 / b.[Budget Amount], 0) AS [% Consumed]
        FROM budgets b
        LEFT JOIN actuals a ON b.afe_number = a.afe_number
        ORDER BY [% Consumed] DESC
    """,

    "remaining_by_afe": """
        WITH budgets AS (
            SELECT da.number, da.name, da.status,
                   SUM(fb.amount) AS [Budget Amount]
            FROM fact_afe_budgets fb
            JOIN dim_afe da ON fb.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fb.afe_budget_date) = :year)
              AND (:status IS NULL OR da.status = :status)
            GROUP BY da.number, da.name, da.status
        ),
        actuals AS (
            SELECT da.number,
                   SUM(fa.amount) AS [Actual Amount]
            FROM fact_afe_actuals fa
            JOIN dim_afe da ON fa.afe_id = da.id
            WHERE (:year   IS NULL OR YEAR(fa.accounting_date) = :year)
            GROUP BY da.number
        ),
        commitments AS (
            SELECT da.number,
                   SUM(fc.committed_amount) AS [Committed Amount]
            FROM fact_afe_commitments fc
            JOIN dim_afe da ON fc.afe_id = da.id
            WHERE fc.status != 'Cancelled'
            GROUP BY da.number
        )
        SELECT TOP (:top_n)
            b.afe_number                                              AS [AFE Number],
            b.name                                                    AS [AFE Name],
            b.status                                                  AS [Status],
            COALESCE(b.[Budget Amount],    0)                         AS [Budget Amount],
            COALESCE(a.[Actual Amount],    0)                         AS [Actual Amount],
            COALESCE(c.[Committed Amount], 0)                         AS [Committed Amount],
            COALESCE(b.[Budget Amount],    0)
                - COALESCE(a.[Actual Amount],    0)
                - COALESCE(c.[Committed Amount], 0)                  AS [Remaining Budget]
        FROM budgets b
        LEFT JOIN actuals     a ON b.afe_number = a.afe_number
        LEFT JOIN commitments c ON b.afe_number = c.afe_number
        ORDER BY [Remaining Budget] ASC
    """,
}


def resolve_afe_financial(tool_args: dict) -> tuple[str, dict, str]:
    """Validate tool_args via Pydantic, look up template, build params dict.

    Returns: (sql_string, params_dict, reasoning_string)
    Raises: pydantic.ValidationError if tool_args are invalid.
    """
    request = AFEFinancialRequest(**tool_args)
    sql = AFE_FINANCIAL_TEMPLATES[request.template]
    params = {
        "year":       request.year,
        "status":     request.status,
        "afe_type_description":   request.afe_type_description,
        "afe_number": request.afe_number,
        "top_n":      request.top_n,
    }
    reasoning = TEMPLATE_DESCRIPTIONS.get(request.template, request.template)
    return sql, params, reasoning


def _build_tool_definition() -> dict:
    schema = AFEFinancialRequest.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return {
        "type": "function",
        "function": {
            "name": "afe_financial",
            "description": AFEFinancialRequest.__doc__.strip(),
            "parameters": schema,
        },
    }


AFE_TOOL_DEFINITION = _build_tool_definition()
