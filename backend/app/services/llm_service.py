from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    used_provider: bool = False


class LLMService:
    """Optional LLM abstraction for later providers.

    Agent 1 currently uses deterministic parsing so tests and local development do
    not require OpenAI or Gemini credentials.
    """

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.llm_provider

    def is_configured(self) -> bool:
        if self.provider == "openai":
            return bool(settings.openai_api_key)
        if self.provider == "gemini":
            return bool(settings.gemini_api_key)
        return False

    def complete(self, prompt: str) -> LLMResponse:
        del prompt
        return LLMResponse(
            content="",
            provider=self.provider,
            used_provider=False,
        )

