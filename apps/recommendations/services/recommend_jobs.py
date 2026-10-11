from apps.intelligence.explanations.services import explain_match
from apps.intelligence.matching.hybrid import hybrid_match
from apps.recommendations.selectors.recommendation_selectors import get_available_jobs, get_profile_for_user


DEFAULT_RECOMMENDATION_LIMIT = 20


def recommend_jobs(profile, jobs, limit=DEFAULT_RECOMMENDATION_LIMIT):
    if limit is not None and limit < 1:
        raise ValueError("limit must be a positive integer.")

    scored_jobs = []
    for job in jobs:
        hybrid_result = hybrid_match(profile, job)
        explanation = explain_match(profile, job, hybrid_result)
        components = hybrid_result["rule_details"]
        scored_jobs.append(
            {
                "job": job,
                "score": hybrid_result["final_score"],
                "match": hybrid_result["final_score"] >= 0.5,
                "components": components,
                "scores": {
                    "rule": hybrid_result["rule_score"],
                    "semantic": hybrid_result["semantic_score"],
                    "final": hybrid_result["final_score"],
                    "semantic_available": hybrid_result["semantic_available"],
                },
                "explanation": explanation,
            }
        )

    ranked_jobs = sorted(
        scored_jobs,
        key=lambda item: (
            -item["score"],
            item["job"].posted_at is None,
            -(item["job"].posted_at.timestamp()) if item["job"].posted_at else 0,
            -item["job"].pk,
        ),
    )
    if limit is not None:
        ranked_jobs = ranked_jobs[:limit]

    return [{"rank": rank, **item} for rank, item in enumerate(ranked_jobs, start=1)]


def get_recommended_jobs(user, limit=DEFAULT_RECOMMENDATION_LIMIT):
    profile = get_profile_for_user(user)
    if profile is None:
        return None

    return recommend_jobs(profile, get_available_jobs(), limit=limit)