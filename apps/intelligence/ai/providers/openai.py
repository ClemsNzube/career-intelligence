import json
import logging
from typing import Any

from django.conf import settings
from openai import OpenAI, OpenAIError

from apps.intelligence.ai.providers.base import (
    AIProviderConfigurationError,
    AIProviderError,
)
from apps.intelligence.ai.providers.structured import StructuredIntelligenceProvider

logger = logging.getLogger(__name__)


class OpenAIIntelligenceProvider(StructuredIntelligenceProvider):
    provider_name = "openai"

    def __init__(self, client=None, *, api_key=None, model=None):
        resolved_api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        if client is None and not resolved_api_key:
            raise AIProviderConfigurationError(
                "Set OPENAI_API_KEY to enable OpenAI intelligence."
            )
        self.client = client or OpenAI(api_key=resolved_api_key)
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def _complete_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            )
            content = response.choices[0].message.content
            result = json.loads(content or "")
        except OpenAIError as exc:
            logger.warning(
                "OpenAI intelligence request failed: %s", exc.__class__.__name__
            )
            raise AIProviderError(
                "The AI provider could not complete the request."
            ) from exc
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "The AI provider returned an invalid JSON response."
            ) from exc
        if not isinstance(result, dict):
            raise AIProviderError("The AI provider response must be a JSON object.")
        return result
