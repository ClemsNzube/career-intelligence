import math
from collections.abc import Sequence

from django.contrib.contenttypes.models import ContentType

from apps.intelligence.embeddings.models import Embedding
from apps.intelligence.embeddings.services import similarity as cosine_similarity


def calculate_similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    """Return cosine similarity for two real-valued vectors."""
    if vector_a is None or vector_b is None:
        raise ValueError("Embedding vectors must not be None.")

    values_a = [float(value) for value in vector_a]
    values_b = [float(value) for value in vector_b]

    if not values_a or not values_b:
        raise ValueError("Embedding vectors must not be empty.")
    if len(values_a) != len(values_b):
        raise ValueError("Embedding vectors must have the same number of dimensions.")
    if any(not math.isfinite(value) for value in (*values_a, *values_b)):
        raise ValueError("Embedding vectors must contain only finite values.")
    if all(math.isclose(value, 0.0, abs_tol=1e-12) for value in values_a) or all(
        math.isclose(value, 0.0, abs_tol=1e-12) for value in values_b
    ):
        raise ValueError("Embedding vectors must not be zero vectors.")

    return cosine_similarity(values_a, values_b)


def _get_latest_embedding(obj):
    content_type = ContentType.objects.get_for_model(obj)
    return (
        Embedding.objects.filter(content_type=content_type, object_id=obj.pk)
        .order_by("-updated_at", "-created_at", "-pk")
        .first()
    )


def similarity_for_objects(profile_obj, job_obj) -> float:
    """Return the semantic similarity between the latest saved embeddings for two objects."""
    profile_embedding = _get_latest_embedding(profile_obj)
    if profile_embedding is None:
        raise ValueError("No embedding exists for the profile object.")

    job_embedding = _get_latest_embedding(job_obj)
    if job_embedding is None:
        raise ValueError("No embedding exists for the job object.")

    return calculate_similarity(profile_embedding.embedding, job_embedding.embedding)
