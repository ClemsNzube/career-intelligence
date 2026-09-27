from __future__ import annotations

from collections.abc import Iterable


def _normalize_skill(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


class SkillMatcher:
    def __init__(self, min_score: float = 0.5):
        self.min_score = min_score

    def score(self, candidate_skills: Iterable[str] | None, job_skills: Iterable[str] | None) -> float:
        candidate = {_normalize_skill(skill) for skill in (candidate_skills or []) if _normalize_skill(skill)}
        job = {_normalize_skill(skill) for skill in (job_skills or []) if _normalize_skill(skill)}

        if not job:
            return 1.0
        if not candidate:
            return 0.0

        overlap = candidate & job
        if not overlap:
            return 0.0

        return len(overlap) / len(job)

    def matches(self, candidate_skills: Iterable[str] | None, job_skills: Iterable[str] | None) -> bool:
        return self.score(candidate_skills, job_skills) >= self.min_score
