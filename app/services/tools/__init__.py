from app.services.tools.afe_financial import AFE_TOOL_DEFINITION
from app.services.tools.afe_master import AFE_MASTER_TOOL_DEFINITION

UNKNOWN_QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "unknown_query",
        "description": (
            "Use this ONLY when the question is completely unrelated to AFE financial data "
            "(budgets, actuals, commitments, spend, variance) AND completely unrelated to AFE "
            "master data (attributes, lists, status, timelines, approvals). "
            "If the question is about AFEs, money, projects, or operational data — even loosely — "
            "pick the closest matching template from afe_financial or afe_master instead. "
            "NEVER use this tool just because the question does not match a template name exactly."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

ALL_TOOLS = [AFE_TOOL_DEFINITION, AFE_MASTER_TOOL_DEFINITION, UNKNOWN_QUERY_TOOL]
