import re
from collections.abc import Iterable

from apps.skills.models import Skill


_SKILL_ALIASES = {
    "drf": "Django REST Framework",
    "django rest": "Django REST Framework",
    "django rest framework": "Django REST Framework",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
}


def _normalize_format(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def _lookup_key(name: str) -> str:
    return _normalize_format(name).casefold()


def normalize_skills(skill_names: Iterable[str] | None) -> list[str]:
    """Resolve skill names and known aliases to existing canonical skill names.

    Names without a matching Skill record are returned with whitespace cleaned,
    so callers can retain them as unresolved input without creating records.
    """
    if skill_names is None:
        return []

    skills_by_key = {
        _lookup_key(skill.name): skill.name
        for skill in Skill.objects.only("name").order_by("name", "pk")
    }

    normalized = []
    seen = set()
    for raw_name in skill_names:
        if not isinstance(raw_name, str):
            continue
        cleaned_name = _normalize_format(raw_name)
        if not cleaned_name:
            continue

        lookup_key = _lookup_key(cleaned_name)
        canonical_name = skills_by_key.get(_lookup_key(_SKILL_ALIASES.get(lookup_key, cleaned_name)))
        resolved_name = canonical_name or cleaned_name
        resolved_key = _lookup_key(resolved_name)
        if resolved_key not in seen:
            normalized.append(resolved_name)
            seen.add(resolved_key)

    return normalized