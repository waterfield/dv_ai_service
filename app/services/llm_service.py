import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_SUPPORTED_SERVICES = {"groq", "openrouter"}


def _parse_llm_models(raw: str) -> list[tuple[str, str, str | None]]:
    """Parse LLM_MODELS string into (service, model, provider_hint) tuples.

    Format: service:model[@provider_hint]
    Example: groq:llama-3.3-70b-versatile,openrouter:anthropic/claude-3-5-sonnet@Together
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
            raise ValueError("LLM_MODELS is not set. Define at least one entry, e.g. groq:llama-3.3-70b-versatile")
        self._models = _parse_llm_models(raw)
        self._clients: dict[str, object] = {}
        logger.info(f"LLM models: {[(s, m) for s, m, _ in self._models]}")

    def _get_client(self, service: str) -> object:
        if service in self._clients:
            return self._clients[service]

        if service == "groq":
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
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for service, model, provider_hint in self._models:
            try:
                client = self._get_client(service)
                kwargs: dict = dict(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
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
