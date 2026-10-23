from __future__ import annotations

from typing import Any


def _get_value(obj: Any, *names: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return None
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    all_items = getattr(value, "all", None)
    if callable(all_items):
        return list(all_items())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _clean_values(value: Any) -> list[str]:
    return [cleaned for item in _as_items(value) if (cleaned := str(item).strip())]


def get_profile_skills(profile: Any) -> list[str]:
    skills = _as_items(_get_value(profile, "skills", "skill_names", "preferred_skills"))
    experiences = _as_items(_get_value(profile, "work_experiences", "experiences"))
    for experience in experiences:
        skills.extend(_as_items(_get_value(experience, "skills_used")))

    unique_skills = []
    seen = set()
    for skill in skills:
        label = str(getattr(skill, "name", skill)).strip()
        key = " ".join(label.casefold().split())
        if key and key not in seen:
            unique_skills.append(label)
            seen.add(key)
    return unique_skills


def _first_nonempty_values(obj: Any, *names: str) -> list[str]:
    for name in names:
        values = _clean_values(_get_value(obj, name))
        if values:
            return values
    return []


def get_profile_matching_preferences(profile: Any) -> dict[str, list[str]]:
    preferences = _get_value(profile, "preferences")

    target_job_titles = _clean_values(_get_value(preferences, "target_job_titles"))
    if not target_job_titles:
        target_job_titles = _first_nonempty_values(
            profile,
            "title",
            "job_title",
            "desired_title",
            "target_title",
            "related_name",
        )

    preferred_locations = _clean_values(_get_value(preferences, "preferred_locations"))
    if not preferred_locations:
        preferred_locations = _first_nonempty_values(
            profile, "location", "preferred_location", "preferred_locations"
        )

    preferred_work_types = _clean_values(_get_value(preferences, "preferred_work_types"))
    if not preferred_work_types:
        preferred_work_types = _first_nonempty_values(
            profile, "work_type", "preferred_work_type"
        )

    return {
        "target_job_titles": target_job_titles,
        "preferred_locations": preferred_locations,
        "preferred_work_types": preferred_work_types,
    }
