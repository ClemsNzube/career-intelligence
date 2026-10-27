from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from apps.intelligence.normalization.skills import SKILL_ALIASES
from apps.skills.models import Skill


_NEGATED_MENTION = re.compile(
    r"\b(?:no\s+(?:experience|knowledge|skills?)\s+(?:with|in|of)|"
    r"not\s+(?:familiar|experienced|proficient|skilled|comfortable)\s+(?:with|in)|"
    r"unfamiliar\s+with|lack(?:s|ing)?\s+(?:experience|knowledge)|"
    r"don't\s+know|doesn't\s+know|didn't\s+know|learning)\b[^.!?;\n]{0,60}$",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9+#.]+", re.IGNORECASE)
_SUGGESTION_THRESHOLD = 0.80


def _value(obj: Any, name: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    all_items = getattr(value, "all", None)
    if callable(all_items):
        return list(all_items())
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _profile_text_sources(profile: Any) -> list[str]:
    sources = [
        _value(profile, "bio"),
        *[
            _value(profile, "related_name"),
        ],
    ]
    for experience in _items(_value(profile, "work_experiences", _value(profile, "experiences"))):
        sources.extend(
            (_value(experience, "job_title"), _value(experience, "description"))
        )
    for project in _items(_value(profile, "projects")):
        sources.extend(
            (
                _value(project, "name"),
                _value(project, "role"),
                _value(project, "description"),
            )
        )
    return [source for source in sources if isinstance(source, str) and source.strip()]


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    words = re.split(r"\s+", phrase.strip())
    expression = r"\s+".join(re.escape(word) for word in words if word)
    return re.compile(rf"(?<!\w){expression}(?!\w)", re.IGNORECASE)


def _skill_phrases(skill: Skill) -> set[str]:
    phrases = {skill.name}
    canonical = " ".join(skill.name.casefold().split())
    phrases.update(
        alias
        for alias, target in SKILL_ALIASES.items()
        if " ".join(target.casefold().split()) == canonical
    )
    return phrases


def _mentioned_exactly(text: str, phrases: set[str]) -> tuple[bool, bool]:
    for phrase in sorted(phrases, key=len, reverse=True):
        for match in _phrase_pattern(phrase).finditer(text):
            if _NEGATED_MENTION.search(text[max(0, match.start() - 80) : match.start()]):
                return True, True
            return True, False
    return False, False


def _has_near_match(text: str, phrases: set[str]) -> bool:
    text_words = _WORD.findall(text.casefold())
    if not text_words:
        return False

    for phrase in phrases:
        phrase_words = _WORD.findall(phrase.casefold())
        if not phrase_words or len("".join(phrase_words)) < 5:
            continue
        width = len(phrase_words)
        for start in range(max(1, len(text_words) - width + 2)):
            candidate = " ".join(text_words[start : start + width])
            target = " ".join(phrase_words)
            if SequenceMatcher(None, candidate, target).ratio() >= _SUGGESTION_THRESHOLD:
                return True
    return False


def classify_profile_skills(
    profile: Any,
    skills: list[Skill] | None = None,
) -> tuple[list[Skill], list[tuple[Skill, str]]]:
    """Return exact positive mentions to link and uncertain mentions to review."""
    text_sources = _profile_text_sources(profile)
    already_linked = {
        getattr(skill, "pk", None)
        for skill in _items(_value(profile, "skills"))
    }
    confirmed: list[Skill] = []
    suggestions: list[tuple[Skill, str]] = []

    for skill in skills if skills is not None else Skill.objects.all():
        if skill.pk in already_linked:
            continue

        phrases = _skill_phrases(skill)
        exact_positive = False
        uncertain_mention = False
        for text in text_sources:
            mentioned, negated = _mentioned_exactly(text, phrases)
            if mentioned:
                if negated:
                    uncertain_mention = True
                else:
                    exact_positive = True
                    break
            elif _has_near_match(text, phrases):
                uncertain_mention = True

        if exact_positive:
            confirmed.append(skill)
        elif uncertain_mention:
            suggestions.append((skill, "Possible skill mention; review before linking."))

    return confirmed, suggestions


def sync_profile_skills_from_evidence(profile: Any) -> list[Skill]:
    """Add explicit experience/project skills and exact positive text mentions."""
    explicit_skills = []
    for relation_name in ("work_experiences", "projects"):
        for related in _items(_value(profile, relation_name)):
            explicit_skills.extend(_items(_value(related, "skills_used")))

    confirmed, _ = classify_profile_skills(profile)
    skills_by_id = {skill.pk: skill for skill in (*explicit_skills, *confirmed)}
    skills = list(skills_by_id.values())
    if skills:
        profile.skills.add(*skills)
    return skills
