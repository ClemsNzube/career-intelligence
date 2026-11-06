from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(RuntimeError):
    pass


class AIProviderConfigurationError(AIProviderError):
    pass


class AIProviderUnavailableError(AIProviderError):
    pass


class JobEvaluationProvider(ABC):
    @abstractmethod
    def evaluate_jobs(
        self,
        candidate_text: str,
        candidate_data: dict[str, Any],
        jobs: list[Any],
    ) -> dict[int, dict[str, Any]]:
        raise NotImplementedError
