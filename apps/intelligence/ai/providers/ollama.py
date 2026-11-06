import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.intelligence.ai.providers.base import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderUnavailableError,
)
from apps.intelligence.ai.providers.structured import StructuredIntelligenceProvider

logger = logging.getLogger(__name__)


class OllamaIntelligenceProvider(StructuredIntelligenceProvider):
    """Local Ollama provider implementing the shared structured-AI contract."""

    provider_name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (
            base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
        self.timeout = timeout or getattr(settings, "OLLAMA_TIMEOUT", 120)
        if self.timeout <= 0:
            raise AIProviderConfigurationError("OLLAMA_TIMEOUT must be greater than zero.")

    def _complete_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read())
        except HTTPError as exc:
            logger.warning("Ollama returned HTTP status %s", exc.code)
            if exc.code in {404, 502, 503, 504}:
                raise AIProviderUnavailableError(
                    "Ollama is unavailable or the configured model is not installed."
                ) from exc
            raise AIProviderError(
                f"Ollama rejected the request with HTTP status {exc.code}."
            ) from exc
        except (URLError, TimeoutError, ConnectionError) as exc:
            logger.warning("Ollama connection failed: %s", exc.__class__.__name__)
            raise AIProviderUnavailableError(
                "Cannot connect to Ollama. Start Ollama and ensure the configured model is available."
            ) from exc
        except OSError as exc:
            logger.warning("Ollama response could not be read: %s", exc.__class__.__name__)
            raise AIProviderUnavailableError(
                "Ollama could not complete the request. Check that the local service is running."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AIProviderError("Ollama returned an invalid response.") from exc

        if not isinstance(response_data, dict):
            raise AIProviderError("Ollama returned an invalid response object.")
        message = response_data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        try:
            result = json.loads(content or "")
        except (TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("Ollama returned invalid JSON content.") from exc
        if not isinstance(result, dict):
            raise AIProviderError("Ollama response content must be a JSON object.")
        return result

    def extract(self, text: str) -> dict[str, Any]:
        result = super().extract(text)
        result["extraction_method"] = "ollama"
        return result
