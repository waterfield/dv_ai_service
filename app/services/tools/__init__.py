from app.services.tools.afe_financial import AFE_TOOL_DEFINITION
from app.services.tools.afe_master import AFE_MASTER_TOOL_DEFINITION

UNKNOWN_QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "unknown_query",
        "description": "Use this ONLY when the question cannot be answered by any available data template. Do not use this if there is any template that could be relevant.",
        "parameters": {"type": "object", "properties": {}},
    },
}

ALL_TOOLS = [AFE_TOOL_DEFINITION, AFE_MASTER_TOOL_DEFINITION, UNKNOWN_QUERY_TOOL]
