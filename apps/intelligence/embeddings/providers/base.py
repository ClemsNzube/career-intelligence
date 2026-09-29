from abc import ABC, abstractmethod


DEFAULT_EMBEDDING_DIMENSIONS = 384


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError