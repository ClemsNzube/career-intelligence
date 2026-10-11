import math
from typing import Any

from apps.intelligence.similarity.services import MissingEmbeddingError, similarity_for_objects
from apps.matching.services.match_job_to_profile import match_job_to_profile

RULE_WEIGHT = 0.6
SEMANTIC_WEIGHT = 0.4


def _validate_score(score: float, name: str, minimum: float, maximum: float) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number.") from error

    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def hybrid_match(profile: Any, job: Any) -> dict[str, Any]:
    """Blend rule and semantic scores, falling back to rules if embeddings are absent."""
    rule_result = match_job_to_profile(profile, job)
    rule_score = _validate_score(rule_result["score"], "Rule score", 0.0, 1.0)
    try:
        cosine_score = _validate_score(
            similarity_for_objects(profile, job), "Semantic score", -1.0, 1.0
        )
    except MissingEmbeddingError:
        semantic_score = None
        final_score = rule_score
        weights = {"rule": 1.0, "semantic": 0.0}
        semantic_available = False
    else:
        semantic_score = max(0.0, cosine_score)
        final_score = (rule_score * RULE_WEIGHT) + (semantic_score * SEMANTIC_WEIGHT)
        weights = {"rule": RULE_WEIGHT, "semantic": SEMANTIC_WEIGHT}
        semantic_available = True

    return {
        "rule_score": rule_score,
        "semantic_score": semantic_score,
        "semantic_available": semantic_available,
        "final_score": final_score,
        "rule_details": {
            name: rule_result[name]
            for name in ("skill", "experience", "work_type", "location", "title")
            if name in rule_result
        },
        "weights": weights,
    }
