import math
from typing import Any


SCORE_BANDS = (
    (0.80, "Strong match", "Apply"),
    (0.60, "Good match", "Apply"),
    (0.40, "Partial match", "Consider applying"),
    (0.00, "Weak match", "Look for a closer match"),
)


def _get_value(obj: Any, *names: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return default

    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return default


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "all"):
        return list(value.all())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _skill_label(skill: Any) -> str:
    return str(getattr(skill, "name", skill)).strip()


def _normalize_skill(skill: str) -> str:
    return " ".join(skill.casefold().split())


def _skill_lists(profile: Any, job: Any) -> tuple[list[str], list[str]]:
    profile_skills = [
        _skill_label(skill)
        for skill in _as_items(_get_value(profile, "skills", "skill_names", "preferred_skills"))
    ]
    job_skills = [
        _skill_label(skill)
        for skill in _as_items(_get_value(job, "skills"))
    ]
    profile_skill_keys = {_normalize_skill(skill) for skill in profile_skills if skill}
    matched = [
        skill
        for skill in job_skills
        if skill and _normalize_skill(skill) in profile_skill_keys
    ]
    missing = [
        skill
        for skill in job_skills
        if skill and _normalize_skill(skill) not in profile_skill_keys
    ]
    return matched, missing


def _score_band(score: float) -> tuple[str, str]:
    for threshold, label, recommendation in SCORE_BANDS:
        if score >= threshold:
            return label, recommendation
    return SCORE_BANDS[-1][1], SCORE_BANDS[-1][2]


def _component_score(rule_details: dict[str, Any], name: str) -> float | None:
    value = rule_details.get(name)
    if value is None:
        return None
    return float(value)


def explain_match(profile: Any, job: Any, hybrid_result: dict[str, Any]) -> dict[str, Any]:
    """Explain a previously calculated hybrid result without recalculating its scores."""
    try:
        final_score = float(hybrid_result["final_score"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("hybrid_result must contain a numeric final_score.") from error
    if not math.isfinite(final_score) or not 0.0 <= final_score <= 1.0:
        raise ValueError("final_score must be between 0 and 1.")

    rule_score = float(hybrid_result["rule_score"])
    semantic_score = float(hybrid_result["semantic_score"])
    rule_details = hybrid_result.get("rule_details", {})
    band, recommendation = _score_band(final_score)
    strengths: list[str] = []
    gaps: list[str] = []

    if semantic_score >= 0.8:
        strengths.append("Strong semantic similarity")
    elif semantic_score >= 0.6:
        strengths.append("Good semantic similarity")
    elif semantic_score < 0.4:
        gaps.append("Low semantic similarity")

    if rule_score >= 0.8:
        strengths.append("Strong rule-based match")
    elif rule_score < 0.4:
        gaps.append("Weak rule-based match")

    matched_skills, missing_skills = _skill_lists(profile, job)
    required_skills = matched_skills + missing_skills
    if matched_skills:
        strengths.append(
            f"You match {len(matched_skills)} of {len(required_skills)} required skills"
        )
    if missing_skills:
        count = len(missing_skills)
        noun = "skill" if count == 1 else "skills"
        gaps.append(f"You are missing {count} required {noun}: {', '.join(missing_skills)}")

    candidate_years = _get_value(
        profile, "years_of_experience", "year_of_experience", "experience_years", default=0
    )
    required_years = _get_value(
        job, "min_years_experience", "minimum_years_experience", default=0
    )
    try:
        candidate_years = float(candidate_years or 0)
        required_years = float(required_years or 0)
    except (TypeError, ValueError):
        candidate_years = required_years = 0.0
    if required_years > 0:
        if candidate_years >= required_years:
            strengths.append("You meet the required experience")
        else:
            gaps.append(
                f"You have {candidate_years:g} years of experience; "
                f"the role requires {required_years:g}"
            )

    preferred_work_type = _get_value(profile, "work_type", "preferred_work_type")
    job_work_type = _get_value(job, "work_type")
    work_type_score = _component_score(rule_details, "work_type")
    if preferred_work_type and job_work_type and work_type_score is not None:
        if work_type_score >= 0.5:
            strengths.append("Your work type preference matches")
        else:
            gaps.append("The job's work type differs from your preference")

    preferred_location = _get_value(
        profile, "location", "preferred_location", "preferred_locations"
    )
    job_location = _get_value(job, "location")
    location_score = _component_score(rule_details, "location")
    if _as_items(preferred_location) and job_location and location_score is not None:
        if location_score >= 0.5:
            strengths.append("Your location preference matches")
        else:
            gaps.append("The job location does not match your preference")

    preferred_title = _get_value(
        profile, "title", "job_title", "desired_title", "target_title"
    )
    job_title = _get_value(job, "title", "job_title")
    title_score = _component_score(rule_details, "title")
    if preferred_title and job_title and title_score is not None:
        if title_score >= 0.5:
            strengths.append("Your preferred title aligns with this role")
        else:
            gaps.append("The role title differs from your preference")

    return {
        "summary": f"{band} for this role.",
        "score_band": band,
        "strengths": strengths,
        "gaps": gaps,
        "recommendation": recommendation,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
