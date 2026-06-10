"""Standalone MCP server entry point — launched via stdio by Claude Desktop."""
import sys
import os
import logging

# ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

# Redirect ALL logging to a file — stdout is the MCP JSON-RPC channel and
# Claude Desktop captures both stdout AND stderr, so any log output corrupts
# the protocol stream.
os.environ.setdefault("DEBUG", "False")
_log_path = os.path.join(os.path.dirname(__file__), "mcp_server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.FileHandler(_log_path, encoding="utf-8")],
    force=True,
)

from app.mcp import mcp
from app.mcp import tools, prompts  # noqa: F401 — registers decorators

if __name__ == "__main__":
    mcp.run()
