import re
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class DaxGeneratorService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def generate(self, user_query: str, schema: dict) -> str:
        system_prompt = self._build_system_prompt(schema)
        try:
            response = self.llm.generate(
                prompt=user_query,
                system_message=system_prompt,
                temperature=0.1,
                max_tokens=1024,
            )
            return self._extract_dax(response)
        except Exception as e:
            logger.error(f"DAX generation error: {e}")
            raise

    def _build_system_prompt(self, schema: dict) -> str:
        lines = []
        for table, cols in list(schema.items())[:30]:
            col_names = [c["name"] for c in cols]
            sample = ", ".join(col_names[:10])
            lines.append(f"- {table}: {sample}")
        schema_str = "\n".join(lines)
        return f"""You are a DAX expert for Power BI and Analysis Services.
Convert the user's question into a DAX query.

Available tables and columns:
{schema_str}

Domain knowledge:
- Actual spend / actual expense → SUM(fact_afe_actuals[amount])
- Budget / planned spend → SUM(fact_afe_budgets[amount])
- dim_chart_of_account has no "name" column — use dim_chart_of_account[account_code] or dim_chart_of_account[description]
- Table relationships are already defined in the model — do not specify joins

DAX rules:
1. Always start the query with EVALUATE
2. Reference columns as table[column] — e.g. dim_afe[name], fact_afe_actuals[amount]
3. Use SUMMARIZECOLUMNS for group-by aggregations
4. Use CALCULATE to apply filters or context transitions
5. Use TOPN(n, table, expression) instead of TOP N
6. Return ONLY the DAX query, no markdown, no explanation"""

    def _extract_dax(self, response: str) -> str:
        if "```dax" in response.lower():
            return re.split(r"```dax", response, flags=re.IGNORECASE)[1].split("```")[0].strip()
        if "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()
