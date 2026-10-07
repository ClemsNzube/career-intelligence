from apps.intelligence.embeddings.providers.base import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
)

DEFAULT_FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"


class FastEmbedProvider(EmbeddingProvider):
    """Local ONNX embedding provider isolated behind the provider interface."""

    model_name = DEFAULT_FASTEMBED_MODEL
    dimensions = DEFAULT_EMBEDDING_DIMENSIONS

    def __init__(self, model_name: str | None = None, dimensions: int | None = None):
        if model_name is not None:
            self.model_name = model_name
        if dimensions is not None:
            self.dimensions = dimensions
        self._model = None

    def embed(self, text: str) -> list[float]:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)

        vector = next(self._model.embed([text]), None)
        if vector is None:
            raise RuntimeError("The embedding provider returned no vector.")
        return [float(value) for value in vector]
