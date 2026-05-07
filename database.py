import logging
import threading
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from config import DATABASE_URL, DEBUG, TABLE_KEY_FILTER, TABLE_WHITELIST, TABLE_EXCEPTION_LIST, DATABASE_SCHEMAS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_schema_cache = None
_schema_lock = threading.Lock()


def test_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connection successful")
        return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


def _include_table(name: str) -> bool:
    """Return True if the table should be included based on filter config.

    Exception list is checked first (blacklist, highest priority).
    Then inclusion: no filters → include all; otherwise include if matches key filter OR whitelist.
    """
    if TABLE_EXCEPTION_LIST and name in TABLE_EXCEPTION_LIST:
        return False
    if not TABLE_KEY_FILTER and not TABLE_WHITELIST:
        return True
    if TABLE_KEY_FILTER and TABLE_KEY_FILTER in name.lower():
        return True
    if TABLE_WHITELIST and name in TABLE_WHITELIST:
        return True
    return False


def get_schema() -> dict:
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    with _schema_lock:
        if _schema_cache is not None:
            return _schema_cache

        inspector = inspect(engine)
        schema = {}
        for schema_name in DATABASE_SCHEMAS:
            for table in inspector.get_table_names(schema=schema_name):
                # dbo tables are accessible without qualification in SQL Server;
                # non-dbo tables need schema.table syntax in generated SQL.
                key = table if schema_name.lower() == "dbo" else f"{schema_name}.{table}"
                if not _include_table(key):
                    continue
                cols = inspector.get_columns(table, schema=schema_name)
                schema[key] = [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
                    for c in cols
                ]

        _schema_cache = schema
        if TABLE_KEY_FILTER or TABLE_WHITELIST or TABLE_EXCEPTION_LIST:
            logger.info(
                f"Schema loaded: {len(schema)} tables from {DATABASE_SCHEMAS} "
                f"(key_filter={TABLE_KEY_FILTER!r}, whitelist={TABLE_WHITELIST or 'none'}, "
                f"exceptions={TABLE_EXCEPTION_LIST or 'none'})"
            )
        else:
            logger.info(f"Schema loaded: {len(schema)} tables from {DATABASE_SCHEMAS} (no filter)")
        return schema


def invalidate_schema_cache() -> None:
    """Force schema to reload on next call (e.g. after changing filter config)."""
    global _schema_cache
    with _schema_lock:
        _schema_cache = None
    logger.info("Schema cache cleared")
