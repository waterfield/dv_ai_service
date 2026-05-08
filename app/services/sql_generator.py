import re
import logging
from typing import Tuple
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

FORBIDDEN = [
    "DROP", "DELETE", "INSERT", "UPDATE", "CREATE",
    "ALTER", "TRUNCATE", "EXEC", "EXECUTE", "DECLARE",
]


class SQLGeneratorService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def generate(self, user_query: str, schema: dict, relationships: dict, descriptions: dict) -> Tuple[str, bool]:
        system_prompt = self._build_system_prompt(schema, relationships, descriptions)
        response = self.llm.generate(
            prompt=user_query,
            system_message=system_prompt,
            temperature=0.1,
            max_tokens=1024,
        )
        sql = self._extract_sql(response)
        sql = self._fix_dim_pk_references(sql, schema)
        valid, error = self._validate(sql, schema)
        if not valid:
            logger.warning(f"SQL validation failed: {error}")
        return sql, valid

    def _build_system_prompt(self, schema: dict, relationships: dict, descriptions: dict) -> str:
        lines = []
        for table, cols in list(schema.items())[:30]:
            col_names = [c["name"] for c in cols]
            pk = "id" if "id" in col_names else col_names[0]
            table_info = descriptions.get(table, {})
            table_desc = f"  [{table_info['description']}]" if "description" in table_info else ""
            col_descs = table_info.get("columns", {})
            col_parts = []
            for c in col_names:
                if c == pk:
                    continue
                col_parts.append(f"{c} ({col_descs[c]})" if c in col_descs else c)
            others = ", ".join(col_parts)
            lines.append(f"- {table}{table_desc}  [PK: {pk}]  columns: {others}")
        schema_str = "\n".join(lines)
        rel_str = "\n".join(f"- {src} → {tgt}" for src, tgt in relationships.items())
        return f"""You are a Microsoft SQL Server expert. Convert the user's question into a SQL query.

Available tables:
{schema_str}

Domain knowledge:
- When the user asks about "actual budget", "actuals", "actual spend", "actual cost", or "actual amount" for AFE, use fact_afe_actuals.amount.
- When the user asks about "budget", "budgeted amount", or "planned spend", use fact_afe_budgets.amount
- Date columns on AFE fact tables: fact_afe_actuals uses accounting_date for date/year filtering and grouping (use activity_date only when the user explicitly asks for activity date). fact_afe_budgets uses afe_budget_date for date/year filtering and grouping. Never use accounting_date on fact_afe_budgets.
- For year, month, quarter, or date-based grouping and filtering, always prefer SQL Server date functions directly on the fact table date column: YEAR(), MONTH(), DATEPART(), EOMONTH(), DATEADD(), etc. Only join to dim_date when the required attribute (e.g. fiscal year, week name) cannot be derived from these functions.
- dim_chart_of_account has NO "name" column — use "account_code" for the code and "description" for the label.
- For division order owner information (owner number, owner name, decimal interest, interest type), use dim_do_lines_of_interest joined to dim_business_associate and dim_division_order. Owner Number = dim_business_associate.number, Owner Name = dim_business_associate.name, Decimal Interest = dim_do_lines_of_interest.nri, Interest Type = dim_do_lines_of_interest.interest_type_name. Never use decimal_interest as a column name — the correct column is nri.
- For AP outstanding amounts, overdue invoices, or aging payables, use dim_invoice — NOT dim_ap_payment. dim_ap_payment records completed payments. Use dim_invoice.current_total for the unpaid balance, dim_invoice.effective_invoice_due_date for aging (e.g. overdue > 120 days: effective_invoice_due_date < DATEADD(day, -120, GETDATE())), dim_invoice.company_name for vendor name. Always filter is_void = 0 and current_total > 0 for open invoices.
- dim_invoice has NO chart_of_account_id column. For outstanding amounts broken down by chart of account, join fact_gl_transactions (which has invoice_id and chart_of_account_id) to dim_invoice and dim_chart_of_account. Use fact_gl_transactions.invoice_id → dim_invoice.id and fact_gl_transactions.chart_of_account_id → dim_chart_of_account.id.
- For Gross MCF, Total Revenue, Fees, Margin, or Total Costs per meter, use fact_rpt_contract_values. Column mapping: Gross MCF = meas_mcf, Total Revenue = tot_product_value, Fees = tot_fee_value, Margin = margin_value, Total Costs = tot_fee_value + total_tax_value. Meter info (meter_number, meter_name) is already on this table — no join to dim_meter needed. Filter by accounting_date for a specific period.
- For volumes by volume type (Gross Wellhead, Field Fuel, Plant Inlet, or any named usage/volume category) per meter, use fact_allocated_results_monthly joined to dim_usage (for volume type name) and dim_meter (for meter name/number). Volume = allocated_quantity, Volume Type = dim_usage.name. Join: fact_allocated_results_monthly.usage_id → dim_usage.id, fact_allocated_results_monthly.meter_id → dim_meter.id. Filter by meter (dim_meter.number or dim_meter.name) and accounting_date.

Join relationships (all dimension tables use "id" as their primary key):
{rel_str}

Rules:
1. Only generate SELECT queries — never INSERT, UPDATE, DELETE, DROP, or any DDL.
2. Use exact table and column names from the schema above — never guess or invent column names.
3. Return ONLY the SQL query, no markdown, no explanation.
4. Use TOP N instead of LIMIT N for row limits.
5. Never use correlated subqueries in the SELECT list when the query has GROUP BY — use JOINs or CTEs instead. Every column referenced outside an aggregate function must appear in the GROUP BY clause.
6. When combining aggregates from multiple fact tables (e.g. fact_afe_actuals + fact_afe_budgets), you MUST aggregate each fact table individually in its own CTE or subquery first, then join the pre-aggregated results. NEVER join two raw fact tables and aggregate after — this causes row fan-out and wrong sums. Aggregate each CTE at exactly the granularity of the final output (e.g. year-level output → group each CTE by year only). Example correct pattern:
   WITH actuals AS (SELECT YEAR(accounting_date) AS yr, SUM(amount) AS actual FROM fact_afe_actuals GROUP BY YEAR(accounting_date)),
        budgets AS (SELECT YEAR(afe_budget_date) AS yr, SUM(amount) AS budget FROM fact_afe_budgets GROUP BY YEAR(afe_budget_date))
   SELECT a.yr, IIF(b.budget > 0, a.actual * 100.0 / b.budget, 0) AS pct FROM actuals a JOIN budgets b ON a.yr = b.yr ORDER BY a.yr
7. Dimension tables (dim_*) use "id" as their primary key — never reference "dim_chart_of_account.chart_of_account_id", "dim_cost_center.cost_center_id", etc. Those FK columns only exist on the fact tables.
8. For percentage, consumption, or utilization calculations (e.g. budget consumed %, variance %, utilization rate), always protect against division by zero using IIF: IIF(denominator > 0, (numerator * 100.0 / denominator), 0). Use IIF for simple conditional expressions in SQL Server instead of CASE WHEN."""

    def _fix_dim_pk_references(self, sql: str, schema: dict) -> str:
        """Fix hallucinated FK column references on dim table aliases.

        The LLM sometimes writes `da.chart_of_account_id` when it means `da.id`
        because it sees the FK name on the fact table. This finds every
        JOIN dim_* alias and replaces alias.{col} with alias.id when {col}
        does not exist on that dim table.
        """
        # Build alias → {valid_cols} and alias → fallback_label maps from JOIN clauses
        alias_cols: dict[str, set[str]] = {}
        alias_label: dict[str, str] = {}  # best display column per alias
        _ts = {"created_at", "updated_at", "created_timestamp", "modified_timestamp"}

        for match in re.finditer(
            r'\bJOIN\s+([\w]+)\s+(?:AS\s+)?([\w]+)', sql, re.IGNORECASE
        ):
            table, alias = match.group(1), match.group(2)
            if table not in schema:
                continue
            cols = [c["name"] for c in schema[table]]
            alias_cols[alias] = set(cols)
            # Best label: first non-id, non-timestamp, non-numeric-looking string col
            for c in cols:
                if c not in _ts and c != "id" and not c.endswith("_id"):
                    alias_label[alias] = c
                    break

        if not alias_cols:
            return sql

        def replace_col(m: re.Match) -> str:
            alias, col = m.group(1), m.group(2)
            valid = alias_cols.get(alias)
            if valid is None or col in valid:
                return m.group(0)
            # Hallucinated _id FK → replace with dim PK
            if col.endswith("_id") and "id" in valid:
                logger.info(f"Auto-fixed PK: {alias}.{col} → {alias}.id")
                return f"{alias}.id"
            # Hallucinated label column (e.g. .name on dim_chart_of_account) → use best label
            fallback = alias_label.get(alias)
            if fallback:
                logger.info(f"Auto-fixed col: {alias}.{col} → {alias}.{fallback}")
                return f"{alias}.{fallback}"
            return m.group(0)

        fixed = re.sub(r'\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)', replace_col, sql)
        return fixed

    def fix_sql(self, sql: str, error: str, schema: dict, relationships: dict, descriptions: dict) -> str:
        """Ask the LLM to fix a SQL query that failed with the given error."""
        system_prompt = self._build_system_prompt(schema, relationships, descriptions)
        prompt = (
            f"The following SQL query failed with this error:\n\n"
            f"Error: {error}\n\n"
            f"SQL:\n{sql}\n\n"
            f"Fix the SQL so it runs without errors. Return ONLY the corrected SQL query."
        )
        response = self.llm.generate(
            prompt=prompt,
            system_message=system_prompt,
            temperature=0.1,
            max_tokens=1024,
        )
        fixed = self._extract_sql(response)
        fixed = self._fix_dim_pk_references(fixed, schema)
        logger.info(f"LLM fixed SQL:\n{fixed}")
        return fixed

    def _extract_sql(self, response: str) -> str:
        if "```sql" in response:
            sql = response.split("```sql")[1].split("```")[0].strip()
        elif "```" in response:
            sql = response.split("```")[1].split("```")[0].strip()
        else:
            sql = response.strip()
        # Strip single-line comments added by weaker fallback models
        sql = re.sub(r'--[^\n]*', '', sql)
        return sql.strip()

    def _validate(self, sql: str, schema: dict) -> Tuple[bool, str]:
        if not sql:
            return False, "Empty query"
        upper = sql.strip().upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            return False, "Query must start with SELECT or WITH"
        for kw in FORBIDDEN:
            if re.search(rf"\b{kw}\b", upper):
                return False, f"Forbidden keyword: {kw}"
        if "--" in sql or "/*" in sql:
            return False, "SQL comments not allowed"
        match = re.search(r"\bFROM\s+([\w.]+)", sql, re.IGNORECASE)
        if match:
            table = match.group(1)
            schema_lower = {t.lower() for t in schema}
            if table.lower() not in schema_lower:
                return False, f"Table '{table}' not in schema"
        return True, ""
