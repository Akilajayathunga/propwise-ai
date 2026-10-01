"""Agent 4 provider transport. Fixed endpoints, no tools, no logging or retries."""
import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote

import httpx
from pydantic import SecretStr


class ProviderError(RuntimeError):
    """Only sanitized application error codes cross this boundary."""


class ExplanationProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    def synthesize(self, system_prompt: str, evidence_json: str, output_schema: dict) -> str: ...


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: SecretStr = field(repr=False)
    timeout_seconds: float = 20.0
    max_output_tokens: int = 4000
    max_response_bytes: int = 128_000

    def __post_init__(self):
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("Timeout must be in (0, 60]")
        if not 256 <= self.max_output_tokens <= 8000:
            raise ValueError("Output token limit must be 256--8000")
        if not 1024 <= self.max_response_bytes <= 256_000:
            raise ValueError("Response byte limit must be 1024--256000")

    @classmethod
    def from_settings(cls, settings=None):
        if settings is None:
            from app.config import get_settings
            settings = get_settings()
        provider = settings.llm_provider.strip().lower()
        key = settings.openai_api_key if provider == "openai" else settings.gemini_api_key if provider == "gemini" else ""
        return cls(provider=provider, model=settings.llm_model.strip(), api_key=SecretStr(key))


class HTTPExplanationProvider:
    def __init__(self, config: ProviderConfig, *, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.config.provider in {"openai", "gemini"} and
                    re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,150}", self.config.model) and
                    self.config.api_key.get_secret_value().strip())

    def synthesize(self, system_prompt: str, evidence_json: str, output_schema: dict) -> str:
        if not self.configured:
            raise ProviderError("NOT_CONFIGURED")
        cfg = self.config
        key = cfg.api_key.get_secret_value()
        if cfg.provider == "openai":
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": "Bearer " + key}
            body = {"model": cfg.model, "instructions": system_prompt,
                    "input": [{"role": "user", "content": evidence_json}],
                    "text": {"format": {"type": "json_schema", "name": "propwise_explanation",
                                        "strict": True, "schema": output_schema}},
                    "max_output_tokens": cfg.max_output_tokens, "store": False}
        else:
            url = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(cfg.model, safe="") + ":generateContent"
            headers = {"x-goog-api-key": key}
            body = {"systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": evidence_json}]}],
                    "generationConfig": {"responseMimeType": "application/json",
                                         "responseJsonSchema": output_schema,
                                         "maxOutputTokens": cfg.max_output_tokens,
                                         "candidateCount": 1}}
        try:
            started = time.monotonic()
            with httpx.Client(timeout=cfg.timeout_seconds, follow_redirects=False,
                              trust_env=False, transport=self._transport) as client:
                with client.stream("POST", url, headers=headers, json=body) as response:
                    if not 200 <= response.status_code < 300:
                        raise ProviderError("PROVIDER_HTTP_ERROR")
                    content = bytearray()
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if time.monotonic() - started > cfg.timeout_seconds:
                            raise ProviderError("PROVIDER_TIMEOUT")
                        content.extend(chunk)
                        if len(content) > cfg.max_response_bytes:
                            raise ProviderError("PROVIDER_RESPONSE_TOO_LARGE")
            envelope = json.loads(content)
            if cfg.provider == "openai":
                if envelope.get("status") != "completed":
                    raise ProviderError("PROVIDER_INCOMPLETE")
                parts = []
                for item in envelope.get("output", []):
                    if item.get("type") == "reasoning":
                        continue
                    if item.get("type") != "message":
                        raise ProviderError("PROVIDER_UNEXPECTED_OUTPUT")
                    for part in item.get("content", []):
                        if part.get("type") != "output_text":
                            raise ProviderError("PROVIDER_REFUSAL")
                        parts.append(part["text"])
            else:
                if envelope.get("promptFeedback", {}).get("blockReason"):
                    raise ProviderError("PROVIDER_REFUSAL")
                candidates = envelope.get("candidates", [])
                if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                    raise ProviderError("PROVIDER_INCOMPLETE")
                parts = []
                for part in candidates[0].get("content", {}).get("parts", []):
                    if part.get("thought") is True:
                        continue
                    if set(part) - {"text", "thought", "thoughtSignature"} or "text" not in part:
                        raise ProviderError("PROVIDER_UNEXPECTED_OUTPUT")
                    parts.append(part["text"])
            text = "".join(parts)
            if not text.strip():
                raise ProviderError("PROVIDER_EMPTY")
            return text
        except ProviderError:
            raise
        except httpx.TimeoutException:
            raise ProviderError("PROVIDER_TIMEOUT") from None
        except Exception:
            # Never leak exception/request repr, headers, response bodies or keys.
            raise ProviderError("PROVIDER_FAILURE") from None
