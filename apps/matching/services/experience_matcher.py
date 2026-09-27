from __future__ import annotations


class ExperienceMatcher:
    def __init__(self, min_score: float = 0.0):
        self.min_score = min_score

    def score(self, candidate_years: int | float | None, required_years: int | float | None) -> float:
        candidate_years = float(candidate_years or 0)
        required_years = float(required_years or 0)

        if required_years <= 0:
            return 1.0

        if candidate_years >= required_years:
            return 1.0

        return max(0.0, min(1.0, candidate_years / required_years))

    def matches(self, candidate_years: int | float | None, required_years: int | float | None) -> bool:
        return self.score(candidate_years, required_years) >= self.min_score
