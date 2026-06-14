import json
import logging
import os
from datetime import datetime, timezone

_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "unsupported_queries.log")
_LOG_PATH = os.path.abspath(_LOG_PATH)

logger = logging.getLogger(__name__)


def log_unsupported(source: str, query: str) -> None:
    """Append one JSONL entry to unsupported_queries.log and emit a warning."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "query": query,
    }
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.error(f"Failed to write unsupported_queries.log: {e}")
    logger.warning(f"UNSUPPORTED_QUERY source={source!r} query={query!r}")
