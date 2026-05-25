import logging
from pydantic import ValidationError
from app.services.llm_service import LLMService
from app.services.tools import ALL_TOOLS
from app.services.tools.afe_financial import resolve_afe_financial
from app.services.tools.afe_master import resolve_afe_master

logger = logging.getLogger(__name__)


class InvalidParamsError(ValueError):
    def __init__(self, tool_name: str, template: str, field_errors: list[str]):
        self.tool_name = tool_name
        self.template = template
        self.field_errors = field_errors
        super().__init__("; ".join(field_errors))


class TemplateService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def resolve(self, user_query: str, history: list[dict] = []) -> tuple[str, dict, str, str, str]:
        """Resolve a user question to a pre-written SQL template + bind params.

        Returns: (sql_string, params_dict, template_key, reasoning_string, tool_name)
        Raises: ValueError if no template matches, InvalidParamsError if params are invalid.
        """
        tool_name, tool_args = self.llm.generate_with_tools(user_query, ALL_TOOLS, history=history)

        if tool_name == "unknown_query":
            raise ValueError("Question not covered by any available template")

        resolver = None
        if tool_name == "afe_financial":
            resolver = resolve_afe_financial
        elif tool_name == "afe_master":
            resolver = resolve_afe_master

        if resolver:
            try:
                sql, params, reasoning = resolver(tool_args)
            except ValidationError as e:
                template = tool_args.get("template", "unknown")
                field_errors = []
                for err in e.errors():
                    field = ".".join(str(x) for x in err["loc"]) if err["loc"] else "unknown"
                    received = err.get("input")
                    field_errors.append(f"{field}: {err['msg']} (received: {received!r})")
                raise InvalidParamsError(tool_name, template, field_errors)
            return sql, params, tool_args.get("template", tool_name), reasoning, tool_name

        raise ValueError(f"Unknown tool returned by LLM: {tool_name!r}")
