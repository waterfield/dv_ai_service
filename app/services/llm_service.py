import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_SUPPORTED_SERVICES = {"groq", "openrouter", "anthropic"}


def _parse_llm_models(raw: str) -> list[tuple[str, str, str | None]]:
    """Parse LLM_MODELS string into (service, model, provider_hint) tuples.

    Format: service:model[@provider_hint]
    Examples:
      anthropic:claude-sonnet-4-6
      groq:llama-3.3-70b-versatile
      openrouter:anthropic/claude-3-5-sonnet@Together
    """
    models = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            raise ValueError(f"LLM_MODELS entry must be 'service:model[@provider]', got: {entry!r}")
        service, rest = entry.split(":", 1)
        service = service.strip().lower()
        if service not in _SUPPORTED_SERVICES:
            raise ValueError(f"Unknown LLM service {service!r}. Supported: {_SUPPORTED_SERVICES}")
        if "@" in rest:
            model, provider_hint = rest.rsplit("@", 1)
        else:
            model, provider_hint = rest, None
        models.append((service, model.strip(), provider_hint.strip() if provider_hint else None))
    return models


class LLMService:
    def __init__(self):
        raw = os.getenv("LLM_MODELS", "").strip()
        if not raw:
            raise ValueError("LLM_MODELS is not set. Define at least one entry, e.g. anthropic:claude-sonnet-4-6")
        self._models = _parse_llm_models(raw)
        self._clients: dict[str, object] = {}
        logger.info(f"LLM models: {[(s, m) for s, m, _ in self._models]}")

    def _get_client(self, service: str) -> object:
        if service in self._clients:
            return self._clients[service]

        if service == "anthropic":
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using anthropic service")
            client = anthropic.Anthropic(api_key=api_key)

        elif service == "groq":
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise ValueError("GROQ_API_KEY is required when using groq service")
            client = Groq(api_key=api_key)

        elif service == "openrouter":
            from openai import OpenAI
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is required when using openrouter service")
            client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=api_key,
                default_headers={"X-Data-Collection": "deny"},
            )

        else:
            raise ValueError(f"Unsupported service: {service!r}")

        self._clients[service] = client
        return client

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        last_error = None
        for service, model, provider_hint in self._models:
            try:
                client = self._get_client(service)

                if service == "anthropic":
                    kwargs: dict = dict(model=model, max_tokens=max_tokens, temperature=temperature,
                                        messages=[{"role": "user", "content": prompt}])
                    if system_message:
                        kwargs["system"] = system_message
                    resp = client.messages.create(**kwargs)
                    logger.info(f"LLM response from {service}:{model}")
                    return resp.content[0].text

                # OpenAI-compatible (groq, openrouter)
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
                kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
                if service == "openrouter" and provider_hint:
                    kwargs["extra_body"] = {
                        "provider": {"order": [provider_hint], "allow_fallbacks": True}
                    }
                resp = client.chat.completions.create(**kwargs)
                logger.info(f"LLM response from {service}:{model}")
                return resp.choices[0].message.content

            except Exception as e:
                last_error = e
                logger.warning(f"{service}:{model} failed: {e}")

        raise last_error or RuntimeError("All LLM models failed")

    def generate_with_tools(
        self,
        user_query: str,
        tools: list[dict],
        history: list[dict] = [],
    ) -> tuple[str, dict]:
        """Call LLM with tool definitions. Returns (tool_name, tool_args_dict).

        tools must be in OpenAI function-calling format:
          [{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}]

        Anthropic format is derived internally. history is a list of prior messages.
        Raises RuntimeError if all models fail or no tool call is returned.
        """
        last_error = None
        for service, model, provider_hint in self._models:
            try:
                client = self._get_client(service)

                if service == "anthropic":
                    anthropic_tools = [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "input_schema": t["function"]["parameters"],
                        }
                        for t in tools
                    ]
                    messages = [*history, {"role": "user", "content": user_query}]
                    resp = client.messages.create(
                        model=model,
                        max_tokens=512,
                        temperature=0.0,
                        messages=messages,
                        tools=anthropic_tools,
                        tool_choice={"type": "any"},
                    )
                    for block in resp.content:
                        if block.type == "tool_use":
                            logger.info(f"Tool selected: {block.name} args={block.input}")
                            return block.name, block.input
                    raise ValueError("Anthropic did not return a tool use block")

                # OpenAI-compatible (groq, openrouter)
                messages = [*history, {"role": "user", "content": user_query}]
                kwargs: dict = dict(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="required",
                    max_tokens=512,
                    temperature=0.0,
                )
                if service == "openrouter" and provider_hint:
                    kwargs["extra_body"] = {
                        "provider": {"order": [provider_hint], "allow_fallbacks": True}
                    }
                resp = client.chat.completions.create(**kwargs)
                choice = resp.choices[0]
                if not choice.message.tool_calls:
                    raise ValueError("LLM did not return a tool call")
                tool_call = choice.message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                logger.info(f"Tool selected: {tool_name} args={tool_args}")
                return tool_name, tool_args

            except Exception as e:
                last_error = e
                logger.warning(f"{service}:{model} tool-use failed: {e}")

        raise last_error or RuntimeError("All LLM models failed for tool-use")
