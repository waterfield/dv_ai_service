import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_SERVER = os.getenv("DATABASE_SERVER", "localhost")
DATABASE_NAME = os.getenv("DATABASE_NAME", "mydb")
DATABASE_USER = os.getenv("DATABASE_USER", "sa")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "1433"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
# SQL echo is noisy (logs every full statement). Decoupled from DEBUG and off
# by default — set SQL_ECHO=true only when debugging SQL.
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() == "true"

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
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
ENABLE_DAX: bool = os.getenv("ENABLE_DAX", "false").lower() == "true"

# MCP API keys — comma-separated list of valid bearer tokens
# Empty = MCP auth disabled (dev/local use)
_raw_mcp_keys = os.getenv("MCP_API_KEYS", "")
MCP_API_KEYS: set[str] = (
    {k.strip() for k in _raw_mcp_keys.split(",") if k.strip()}
    if _raw_mcp_keys.strip()
    else set()
)

# OAuth2 client credentials — comma-separated list of client_id:client_secret pairs
# Example: MCP_OAUTH_CLIENTS=claude_ai:secret123,myapp:anothersecret
# Empty = OAuth disabled
_raw_clients = os.getenv("MCP_OAUTH_CLIENTS", "")
MCP_OAUTH_CLIENTS: dict[str, str] = {}
for _entry in _raw_clients.split(","):
    _entry = _entry.strip()
    if ":" in _entry:
        _cid, _csecret = _entry.split(":", 1)
        MCP_OAUTH_CLIENTS[_cid.strip()] = _csecret.strip()

# Secret key for signing JWT tokens — generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
MCP_JWT_SECRET: str = os.getenv("MCP_JWT_SECRET", "")
MCP_JWT_EXPIRY_SECONDS: int = int(os.getenv("MCP_JWT_EXPIRY_SECONDS", "3600"))
SHOW_TEMPLATE_DESCRIPTION: bool = os.getenv("SHOW_TEMPLATE_DESCRIPTION", "false").lower() == "true"
ENABLE_ANALYSIS: bool = os.getenv("ENABLE_ANALYSIS", "true").lower() == "true"

# Single SQL Server schema to introspect — multiple schemas are not supported
_raw_schema = os.getenv("DATABASE_SCHEMA", "dbo").strip()
if "," in _raw_schema:
    raise ValueError("DATABASE_SCHEMA must be a single schema name, not a comma-separated list")
DATABASE_SCHEMA: str = _raw_schema

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
