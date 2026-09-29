import hashlib

from apps.intelligence.embeddings.providers.base import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS):
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero.")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        encoded_text = text.encode("utf-8")
        vector = []
        for index in range(self.dimensions):
            digest = hashlib.blake2b(
                encoded_text + index.to_bytes(4, "big"),
                digest_size=4,
            ).digest()
            value = int.from_bytes(digest, "big") / (2**32 - 1)
            vector.append(value * 2 - 1)
        return vector