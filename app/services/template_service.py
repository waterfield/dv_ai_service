import logging
from pydantic import ValidationError
from app.services.llm_service import LLMService
from app.services.tools import ALL_TOOLS
from app.services.tools.afe_financial import resolve_afe_financial

logger = logging.getLogger(__name__)


class InvalidParamsError(ValueError):
    pass


class TemplateService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def resolve(self, user_query: str) -> tuple[str, dict, str, str, str]:
        """Resolve a user question to a pre-written SQL template + bind params.

        Returns: (sql_string, params_dict, template_key, reasoning_string, tool_name)
        Raises: ValueError if no template matches, InvalidParamsError if params are invalid.
        """
        tool_name, tool_args = self.llm.generate_with_tools(user_query, ALL_TOOLS)

        if tool_name == "unknown_query":
            raise ValueError("Question not covered by any available template")

        if tool_name == "afe_financial":
            try:
                sql, params, reasoning = resolve_afe_financial(tool_args)
            except ValidationError as e:
                msgs = []
                for err in e.errors():
                    field = ".".join(str(x) for x in err["loc"]) if err["loc"] else "unknown"
                    received = err.get("input")
                    msgs.append(f"{field}: {err['msg']} (received: {received!r})")
                raise InvalidParamsError("; ".join(msgs))
            return sql, params, tool_args.get("template", "afe_financial"), reasoning, tool_name

        raise ValueError(f"Unknown tool returned by LLM: {tool_name!r}")
