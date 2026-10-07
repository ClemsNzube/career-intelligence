import math
from collections.abc import Sequence
from functools import lru_cache

from django.contrib.contenttypes.models import ContentType

from apps.intelligence.embeddings.models import Embedding
from apps.intelligence.embeddings.providers.base import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
)
from apps.intelligence.embeddings.providers.fastembed import FastEmbedProvider
from apps.intelligence.extraction.services import extract_job_data

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _default_provider() -> EmbeddingProvider:
    return FastEmbedProvider()


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider if provider is not None else _default_provider()

    @property
    def model_name(self) -> str:
        return getattr(self.provider, "model_name", type(self.provider).__name__)

    def embed(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must contain at least one non-whitespace character.")

        vector = [float(value) for value in self.provider.embed(text)]
        if not vector:
            raise ValueError("The embedding provider returned an empty vector.")

        dimensions = getattr(self.provider, "dimensions", None)
        if dimensions is not None and len(vector) != dimensions:
            raise ValueError("The embedding provider returned a vector with an unexpected dimension.")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("The embedding provider returned a non-finite value.")
        return vector

    def save_for_object(self, obj, text: str, *, model_name: str | None = None) -> Embedding:
        vector = self.embed(text)
        provider_dimensions = getattr(self.provider, "dimensions", None)
        if provider_dimensions is not None and provider_dimensions != DEFAULT_EMBEDDING_DIMENSIONS:
            raise ValueError(
                "Embedding provider dimensions do not match the persisted model dimension "
                f"({DEFAULT_EMBEDDING_DIMENSIONS})."
            )

        content_type = ContentType.objects.get_for_model(obj)
        resolved_model_name = model_name or self.model_name

        embedding, _ = Embedding.objects.update_or_create(
            content_type=content_type,
            object_id=obj.pk,
            defaults={
                "source_text": text.strip(),
                "embedding": vector,
                "model_name": resolved_model_name,
            },
        )
        return embedding


def generate_embedding(text: str, provider: EmbeddingProvider | None = None) -> list[float]:
    """Generate an embedding using the selected provider."""
    return EmbeddingService(provider=provider).embed(text)


def similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    """Return cosine similarity for two embedding vectors."""
    if len(vector_a) != len(vector_b):
        raise ValueError("Embedding vectors must have the same number of dimensions.")
    if not vector_a:
        raise ValueError("Embedding vectors must not be empty.")

    values_a = [float(value) for value in vector_a]
    values_b = [float(value) for value in vector_b]
    if not all(math.isfinite(value) for value in (*values_a, *values_b)):
        raise ValueError("Embedding vectors must contain only finite values.")

    norm_a = math.sqrt(math.fsum(value * value for value in values_a))
    norm_b = math.sqrt(math.fsum(value * value for value in values_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    dot_product = math.fsum(a * b for a, b in zip(values_a, values_b))
    return dot_product / (norm_a * norm_b)


def _related_names(instance, relation_name: str, name_attribute: str = "name") -> list[str]:
    relation = getattr(instance, relation_name, None)
    if relation is None:
        return []
    related_items = relation.all() if hasattr(relation, "all") else relation
    return [
        value
        for item in related_items
        if (value := str(getattr(item, name_attribute, item)).strip())
    ]


def build_job_text(job) -> str:
    """Build a focused text representation of a job for embedding."""
    parts = [
        str(getattr(job, "title", "") or "").strip(),
        str(getattr(job, "description", "") or "").strip(),
    ]
    skills = _related_names(job, "skills")
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")

    responsibilities = extract_job_data(getattr(job, "description", "") or "")["responsibilities"]
    if responsibilities:
        parts.append("Responsibilities:\n" + "\n".join(f"- {item}" for item in responsibilities))
    return "\n".join(part for part in parts if part)


def build_profile_text(profile) -> str:
    """Build a focused text representation of a career profile for embedding."""
    parts = []
    headline = getattr(profile, "headline", None) or getattr(profile, "related_name", "")
    bio = getattr(profile, "bio", "")
    if headline and str(headline).strip():
        parts.append(f"Headline: {str(headline).strip()}")
    if bio and str(bio).strip():
        parts.append(f"Bio: {str(bio).strip()}")

    skills = _related_names(profile, "skills")
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")

    experiences = getattr(profile, "work_experiences", None)
    if experiences is not None:
        for experience in experiences.all():
            description = str(getattr(experience, "description", "") or "").strip()
            experience_title = str(getattr(experience, "job_title", "") or "").strip()
            company = str(getattr(experience, "company", "") or "").strip()
            heading = " at ".join(value for value in (experience_title, company) if value)
            experience_skills = _related_names(experience, "skills_used")
            details = [value for value in (heading, description) if value]
            if experience_skills:
                details.append(f"Skills: {', '.join(experience_skills)}")
            if details:
                parts.append("Experience: " + ". ".join(details))

    projects = getattr(profile, "projects", None)
    if projects is not None:
        for project in projects.all():
            name = str(getattr(project, "name", "") or "").strip()
            role = str(getattr(project, "role", "") or "").strip()
            description = str(getattr(project, "description", "") or "").strip()
            project_skills = _related_names(project, "skills_used")
            details = [value for value in (name, role, description) if value]
            if project_skills:
                details.append(f"Skills: {', '.join(project_skills)}")
            if details:
                parts.append("Project: " + ". ".join(details))

    return "\n".join(parts)