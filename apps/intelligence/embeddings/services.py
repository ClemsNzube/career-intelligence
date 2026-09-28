from collections.abc import Sequence
from functools import lru_cache
import math
from typing import Protocol

from apps.intelligence.extraction.services import extract_job_data


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIMENSIONS = 384


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...


class FastEmbedProvider:
    """Local ONNX embedding provider, isolated behind the provider interface."""

    model_name = DEFAULT_EMBEDDING_MODEL
    dimensions = DEFAULT_EMBEDDING_DIMENSIONS

    def __init__(self):
        self._model = None

    def embed(self, text: str) -> Sequence[float]:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)

        vector = next(self._model.embed([text]), None)
        if vector is None:
            raise RuntimeError("The embedding provider returned no vector.")
        return [float(value) for value in vector]


@lru_cache(maxsize=1)
def _default_provider() -> FastEmbedProvider:
    return FastEmbedProvider()


def generate_embedding(text: str, provider: EmbeddingProvider | None = None) -> list[float]:
    """Generate an embedding using the selected provider, defaulting to FastEmbed."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must contain at least one non-whitespace character.")

    selected_provider = provider or _default_provider()
    vector = [float(value) for value in selected_provider.embed(text)]
    if not vector:
        raise ValueError("The embedding provider returned an empty vector.")
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("The embedding provider returned a non-finite value.")
    return vector


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