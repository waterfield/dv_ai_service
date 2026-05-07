import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_SERVER = os.getenv("DATABASE_SERVER", "localhost")
DATABASE_NAME = os.getenv("DATABASE_NAME", "mydb")
DATABASE_USER = os.getenv("DATABASE_USER", "sa")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "1433"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

DATABASE_URL = (
    f"mssql+pyodbc://{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_SERVER}:{DATABASE_PORT}/{DATABASE_NAME}"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Connection+Timeout=10"
)

# LLM configuration
# Format: comma-separated list of service:model[@provider_hint]
# service = groq | openrouter
# provider_hint (openrouter only) = preferred underlying provider, e.g. @Together
# Example: groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-3-5-sonnet,openrouter:meta-llama/llama-3.3-70b@Together
LLM_MODELS: str = os.getenv("LLM_MODELS", "").strip()
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
ENABLE_DAX: bool = os.getenv("ENABLE_DAX", "false").lower() == "true"

# SQL Server schema(s) to introspect — comma-separated, defaults to dbo
# Single schema: plain table names used as keys (e.g. my_table)
# Multiple schemas: fully qualified keys used (e.g. dbo.my_table, staging.my_table)
_raw_schemas = os.getenv("DATABASE_SCHEMA", "dbo")
DATABASE_SCHEMAS: list[str] = [s.strip() for s in _raw_schemas.split(",") if s.strip()]

# Schema filtering — all are optional and combinable
# TABLE_KEY_FILTER:     only include tables whose name contains this substring (case-insensitive)
# TABLE_WHITELIST:      explicit comma-separated list of table names to include
# TABLE_EXCEPTION_LIST: comma-separated blacklist — always excluded, even if matched by filter/whitelist
_raw_whitelist = os.getenv("TABLE_WHITELIST", "")
_raw_exception = os.getenv("TABLE_EXCEPTION_LIST", "")
TABLE_KEY_FILTER: str = os.getenv("TABLE_KEY_FILTER", "").strip().lower()
TABLE_WHITELIST: set[str] = (
    {t.strip() for t in _raw_whitelist.split(",") if t.strip()}
    if _raw_whitelist.strip()
    else set()
)
TABLE_EXCEPTION_LIST: set[str] = (
    {t.strip() for t in _raw_exception.split(",") if t.strip()}
    if _raw_exception.strip()
    else set()
)
