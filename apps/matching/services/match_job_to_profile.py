from __future__ import annotations

from typing import Any

from .experience_matcher import ExperienceMatcher
from .location_matcher import LocationMatcher
from .skill_matcher import SkillMatcher
from .title_matcher import TitleMatcher
from .work_type_matcher import WorkTypeMatcher


class WeightedScorer:
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = self._normalize(weights or {})

    @staticmethod
    def _normalize(weights: dict[str, float]) -> dict[str, float]:
        cleaned = {key: float(value) for key, value in weights.items() if value is not None}
        total = sum(cleaned.values())
        if total <= 0:
            return {}
        return {key: value / total for key, value in cleaned.items()}

    def score(self, component_scores: dict[str, float]) -> float:
        if not self.weights:
            return 0.0

        total = 0.0
        for name, weight in self.weights.items():
            total += float(component_scores.get(name, 0.0)) * weight
        return total


class JobProfileMatcher:
    def __init__(self, weights: dict[str, float] | None = None, match_threshold: float = 0.5):
        self.weights = {
            "skill": 0.35,
            "experience": 0.2,
            "work_type": 0.15,
            "location": 0.15,
            "title": 0.15,
        }
        if weights:
            self.weights.update(weights)
        self.scorer = WeightedScorer(self.weights)
        self.match_threshold = match_threshold
        self.skill_matcher = SkillMatcher(min_score=0.0)
        self.experience_matcher = ExperienceMatcher(min_score=0.0)
        self.work_type_matcher = WorkTypeMatcher(min_score=0.0)
        self.location_matcher = LocationMatcher(min_score=0.0)
        self.title_matcher = TitleMatcher(min_score=0.0)

    def _get_value(self, obj: Any, *keys: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            for key in keys:
                if key in obj:
                    return obj[key]
            return default
        for key in keys:
            value = getattr(obj, key, None)
            if value is not None:
                return value
        return default

    def _job_skills(self, job: Any) -> list[str]:
        skills = self._get_value(job, "skills", default=[])
        if hasattr(skills, "all"):
            return [str(skill.name if hasattr(skill, "name") else skill) for skill in skills.all()]
        if isinstance(skills, (list, tuple, set)):
            return [str(skill.name if hasattr(skill, "name") else skill) for skill in skills]
        return [str(skills)] if skills else []

    def _profile_skills(self, profile: Any) -> list[str]:
        skills = self._get_value(profile, "skills", "skill_names", "preferred_skills", default=[])
        if hasattr(skills, "all"):
            return [str(skill.name if hasattr(skill, "name") else skill) for skill in skills.all()]
        if isinstance(skills, (list, tuple, set)):
            return [str(skill.name if hasattr(skill, "name") else skill) for skill in skills]
        return [str(skills)] if skills else []

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _component_explanation(self, name: str, score: float, weight: float, matched: bool, reason: str) -> dict[str, Any]:
        return {
            "name": name,
            "score": score,
            "weight": weight,
            "matched": matched,
            "reason": reason,
        }

    def score(self, profile: Any, job: Any) -> dict[str, Any]:
        profile_title = self._get_value(profile, "title", "job_title", "desired_title", "target_title", default="")
        job_title = self._get_value(job, "title", "job_title", default="")

        profile_location = self._get_value(profile, "location", "preferred_location", "preferred_locations", default="")
        if isinstance(profile_location, (list, tuple, set)):
            profile_location = next((item for item in profile_location if item), "")
        job_location = self._get_value(job, "location", default="")

        profile_work_type = self._get_value(profile, "work_type", "preferred_work_type", default="")
        if isinstance(profile_work_type, (list, tuple, set)):
            profile_work_type = next((item for item in profile_work_type if item), "")
        job_work_type = self._get_value(job, "work_type", default="")

        profile_years = self._get_value(profile, "years_of_experience", "year_of_experience", "experience_years", default=0)
        job_required_years = self._get_value(job, "min_years_experience", "minimum_years_experience", default=0)

        candidate_skills = self._profile_skills(profile)
        job_skills = self._job_skills(job)

        skill_score = self.skill_matcher.score(candidate_skills, job_skills)
        experience_score = self.experience_matcher.score(profile_years, job_required_years)
        work_type_score = self.work_type_matcher.score(profile_work_type, job_work_type)
        location_score = self.location_matcher.score(profile_location, job_location)
        title_score = self.title_matcher.score(profile_title, job_title)

        component_scores = {
            "skill": skill_score,
            "experience": experience_score,
            "work_type": work_type_score,
            "location": location_score,
            "title": title_score,
        }

        total = self.scorer.score(component_scores)
        matched = total >= self.match_threshold

        skill_overlap = set(str(skill).strip().lower() for skill in candidate_skills) & set(str(skill).strip().lower() for skill in job_skills)
        if job_skills:
            if skill_overlap:
                skill_reason = f"Matched {len(skill_overlap)} of {len(job_skills)} required skills: {', '.join(sorted(skill_overlap))}."
            else:
                skill_reason = f"Matched 0 of {len(job_skills)} required skills: none."
        else:
            skill_reason = "No required skills were specified for this job."
        experience_reason = (
            f"Candidate has {profile_years} years of experience; the role requires {job_required_years}." if job_required_years else "No minimum experience requirement was specified for this role."
        )
        work_type_reason = (
            f"Candidate prefers {profile_work_type or 'unspecified'} work type; the role is {job_work_type or 'unspecified'}."
        )
        if profile_location and job_location and ("remote" in str(profile_location).lower() or "remote" in str(job_location).lower()):
            location_reason = "Remote preference aligns with a remote job." if "remote" in str(profile_location).lower() and "remote" in str(job_location).lower() else f"Candidate prefers {profile_location or 'unspecified'}; the role is in {job_location or 'unspecified'}."
        else:
            location_reason = f"Candidate prefers {profile_location or 'unspecified'}; the role is in {job_location or 'unspecified'}."
        if not profile_title or not str(profile_title).strip():
            title_reason = "No preferred job title was specified."
        else:
            title_reason = f"Candidate title '{profile_title}' overlaps with job title '{job_title or 'unspecified'}'."

        explanation = {
            "overall": {
                "total": total,
                "threshold": self.match_threshold,
                "matched": matched,
                "summary": (
                    f"Weighted match score is {total:.2f} out of 1.0; the profile {'meets' if matched else 'does not meet'} the threshold."
                ),
            },
            "components": [
                self._component_explanation("skill", skill_score, self.weights.get("skill", 0.0), skill_score > 0, skill_reason),
                self._component_explanation("experience", experience_score, self.weights.get("experience", 0.0), experience_score >= 0.5, experience_reason),
                self._component_explanation("work_type", work_type_score, self.weights.get("work_type", 0.0), work_type_score >= 0.5, work_type_reason),
                self._component_explanation("location", location_score, self.weights.get("location", 0.0), location_score >= 0.5, location_reason),
                self._component_explanation("title", title_score, self.weights.get("title", 0.0), title_score >= 0.5, title_reason),
            ],
        }

        return {
            **component_scores,
            "score": total,
            "total": total,
            "weighted_score": total,
            "match": matched,
            "threshold": self.match_threshold,
            "weights": self.weights,
            "explanation": explanation,
        }


def match_job_to_profile(profile: Any, job: Any, weights: dict[str, float] | None = None, match_threshold: float = 0.5) -> dict[str, Any]:
    matcher = JobProfileMatcher(weights=weights, match_threshold=match_threshold)
    return matcher.score(profile, job)
