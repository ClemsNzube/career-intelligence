from django.conf import settings

from apps.intelligence.ai.providers.base import (
    AIProviderConfigurationError,
    JobEvaluationProvider,
)


def get_intelligence_provider() -> JobEvaluationProvider:
    provider_name = getattr(settings, "AI_PROVIDER", "ollama").strip().lower()
    if provider_name == "ollama":
        from apps.intelligence.ai.providers.ollama import OllamaIntelligenceProvider

        return OllamaIntelligenceProvider()
    if provider_name == "openai":
        from apps.intelligence.ai.providers.openai import OpenAIIntelligenceProvider

        return OpenAIIntelligenceProvider()
    raise AIProviderConfigurationError(
        "AI_PROVIDER must be set to either 'ollama' or 'openai'."
    )