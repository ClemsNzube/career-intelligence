import re

from apps.skills.models import Skill


_EXPERIENCE_PATTERNS = (
    re.compile(r"\b(?:minimum|min\.?|at\s+least)\s+(\d+)\s*\+?\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*\+\s*years?\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s+years?\s+(?:of\s+)?(?:relevant\s+)?experience\b", re.IGNORECASE),
)
_TITLE_PATTERNS = (
    re.compile(r"\b(?:job\s+title|position|role)\s*[:\-]\s*([^\n.;]+)", re.IGNORECASE),
    re.compile(
        r"\b(?:we\s+are\s+)?(?:looking\s+for|seeking|hiring)\s+(?:an?\s+)?(.+?)"
        r"(?=\s+(?:with|who|to|that)\b|[,.;\n]|$)",
        re.IGNORECASE,
    ),
)
_EDUCATION_PATTERNS = (
    (re.compile(r"\bbachelor(?:'s)?(?:\s+degree)?\b", re.IGNORECASE), "Bachelor's degree"),
    (re.compile(r"\bB\.?Sc\.?\b", re.IGNORECASE), "BSc"),
    (re.compile(r"\bmaster(?:'s)?(?:\s+degree)?\b", re.IGNORECASE), "Master's degree"),
    (re.compile(r"\bM\.?Sc\.?\b", re.IGNORECASE), "MSc"),
)
_WORK_TYPE_PATTERN = re.compile(r"\bremote\b|\bhybrid\b|\bon[ -]?site\b", re.IGNORECASE)
_RESPONSIBILITIES_HEADING = re.compile(
    r"^\s*(?:key\s+)?responsibilities\s*:?\s*$|^\s*what\s+you\s+(?:will|'ll)\s+do\s*:?\s*$",
    re.IGNORECASE,
)
_SECTION_HEADING = re.compile(r"^\s*[A-Za-z][A-Za-z /&'-]{1,50}\s*:\s*$")
_BULLET = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$")


def _extract_title(text: str) -> str | None:
    for pattern in _TITLE_PATTERNS:
        match = pattern.search(text)
        if match:
            title = match.group(1).strip()
            if title:
                return title
    return None


def _extract_min_years_experience(text: str) -> int | None:
    for pattern in _EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def _extract_skills(text: str) -> list[str]:
    matches = []
    for skill in Skill.objects.only("name"):
        pattern = re.compile(rf"(?<![\w]){re.escape(skill.name)}(?![\w])", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            matches.append((match.start(), -len(skill.name), skill.name))
    return [name for _, _, name in sorted(matches)]


def _extract_work_type(text: str) -> str | None:
    match = _WORK_TYPE_PATTERN.search(text)
    if match is None:
        return None
    work_type = match.group(0).lower().replace(" ", "-")
    return "onsite" if work_type == "on-site" else work_type


def _extract_education(text: str) -> list[str]:
    matches = []
    for pattern, label in _EDUCATION_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append((match.start(), label))
    return list(dict.fromkeys(label for _, label in sorted(matches)))


def _extract_responsibilities(text: str) -> list[str]:
    in_section = False
    responsibilities = []

    for line in text.splitlines():
        stripped = line.strip()
        if _RESPONSIBILITIES_HEADING.match(stripped):
            in_section = True
            continue
        if in_section and _SECTION_HEADING.match(stripped):
            break
        if in_section:
            match = _BULLET.match(line)
            if match:
                responsibilities.append(match.group(1).strip())

    return responsibilities


def extract_job_data(job_description: str | None) -> dict[str, object]:
    """Extract structured job information using deterministic text rules."""
    text = job_description if isinstance(job_description, str) else ""
    return {
        "title": _extract_title(text),
        "skills": _extract_skills(text),
        "min_years_experience": _extract_min_years_experience(text),
        "work_type": _extract_work_type(text),
        "education": _extract_education(text),
        "responsibilities": _extract_responsibilities(text),
    }