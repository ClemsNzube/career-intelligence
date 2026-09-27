from apps.matching.services.match_job_to_profile import match_job_to_profile
from apps.recommendations.selectors.recommendation_selectors import get_available_jobs, get_profile_for_user


DEFAULT_RECOMMENDATION_LIMIT = 20


def recommend_jobs(profile, jobs, limit=DEFAULT_RECOMMENDATION_LIMIT):
    if limit is not None and limit < 1:
        raise ValueError("limit must be a positive integer.")

    scored_jobs = []
    for job in jobs:
        result = match_job_to_profile(profile, job)
        components = {name: result[name] for name in ("skill", "experience", "work_type", "location", "title")}
        scored_jobs.append({"job": job, "components": components, **result})

    ranked_jobs = sorted(scored_jobs, key=lambda item: (-item["score"], item["job"].pk))
    if limit is not None:
        ranked_jobs = ranked_jobs[:limit]

    return [{"rank": rank, **item} for rank, item in enumerate(ranked_jobs, start=1)]


def get_recommended_jobs(user, limit=DEFAULT_RECOMMENDATION_LIMIT):
    profile = get_profile_for_user(user)
    if profile is None:
        return None

    return recommend_jobs(profile, get_available_jobs(), limit=limit)