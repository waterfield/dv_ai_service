import logging
import threading
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from config import DATABASE_URL, DEBUG, TABLE_KEY_FILTER, TABLE_WHITELIST, TABLE_EXCEPTION_LIST, DATABASE_SCHEMA

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
_relationships_cache = None
_relationships_lock = threading.Lock()


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
        for table in inspector.get_table_names(schema=DATABASE_SCHEMA):
            if not _include_table(table):
                continue
            cols = inspector.get_columns(table, schema=DATABASE_SCHEMA)
            schema[table] = [
                {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
                for c in cols
            ]

        _schema_cache = schema
        if TABLE_KEY_FILTER or TABLE_WHITELIST or TABLE_EXCEPTION_LIST:
            logger.info(
                f"Schema loaded: {len(schema)} tables from {DATABASE_SCHEMA!r} "
                f"(key_filter={TABLE_KEY_FILTER!r}, whitelist={TABLE_WHITELIST or 'none'}, "
                f"exceptions={TABLE_EXCEPTION_LIST or 'none'})"
            )
        else:
            logger.info(f"Schema loaded: {len(schema)} tables from {DATABASE_SCHEMA!r} (no filter)")
        return schema


def get_relationships(schema: dict) -> dict[str, str]:
    global _relationships_cache
    if _relationships_cache is not None:
        return _relationships_cache
    with _relationships_lock:
        if _relationships_cache is not None:
            return _relationships_cache

        schema_tables = set(schema.keys())
        relationships: dict[str, str] = {}
        inspector = inspect(engine)

        for table in inspector.get_table_names(schema=DATABASE_SCHEMA):
            if table not in schema_tables:
                continue
            for fk in inspector.get_foreign_keys(table, schema=DATABASE_SCHEMA):
                ref_table = fk["referred_table"]
                if ref_table not in schema_tables:
                    continue
                for col, ref_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                    relationships[f"{table}.{col}"] = f"{ref_table}.{ref_col}"

        _relationships_cache = relationships
        logger.info(f"Relationships loaded: {len(relationships)} FK mappings")
        return relationships


def invalidate_schema_cache() -> None:
    global _schema_cache, _relationships_cache
    with _schema_lock:
        _schema_cache = None
    with _relationships_lock:
        _relationships_cache = None
    logger.info("Schema and relationships cache cleared")
