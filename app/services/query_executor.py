import re
import logging
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FORBIDDEN = ["DROP", "DELETE", "INSERT", "UPDATE", "CREATE", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"]

_history: list[dict] = []


class QueryExecutorService:
    def execute(
        self,
        sql: str,
        db: Session,
        timeout: int = 30,
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        err = self._validate(sql)
        if err:
            return None, err

        start = datetime.now()
        try:
            result = db.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)
            elapsed = (datetime.now() - start).total_seconds()
            logger.info(f"Query returned {len(df)} rows in {elapsed:.2f}s")
            _history.append({
                "sql": sql, "timestamp": start.isoformat(),
                "row_count": len(df), "execution_time": elapsed, "success": True,
            })
            return df, None
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            _history.append({
                "sql": sql, "timestamp": start.isoformat(),
                "execution_time": elapsed, "error": str(e), "success": False,
            })
            logger.error(f"Query failed: {e}")
            return None, str(e)

    def _validate(self, sql: str) -> Optional[str]:
        if not sql or not sql.strip():
            return "Query cannot be empty"
        upper = sql.strip().upper()
        if not upper.startswith("SELECT"):
            return "Only SELECT queries are allowed"
        for kw in FORBIDDEN:
            if re.search(rf"\b{kw}\b", upper):
                return f"{kw} queries are not allowed"
        if "--" in sql or "/*" in sql:
            return "SQL comments are not allowed"
        return None

    def get_history(self, limit: int = 20) -> list[dict]:
        return list(reversed(_history))[:limit]
