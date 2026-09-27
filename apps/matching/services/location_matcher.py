from __future__ import annotations


class LocationMatcher:
    def __init__(self, min_score: float = 1.0):
        self.min_score = min_score

    @staticmethod
    def _normalize(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            values = []
            for item in value:
                if item is not None:
                    values.append(str(item).strip().lower())
            return [item for item in values if item]
        return [str(value).strip().lower()] if str(value).strip() else []

    def score(self, candidate_location: str | list | tuple | set | None, job_location: str | None) -> float:
        candidate_values = self._normalize(candidate_location)
        job = (job_location or "").strip().lower()

        if not job:
            return 1.0
        if "remote" in job:
            return 1.0
        if not candidate_values:
            return 0.0

        for candidate in candidate_values:
            if candidate == job:
                return 1.0
            if "remote" in candidate and "remote" in job:
                return 1.0
            if "remote" in candidate and job in {"hybrid", "onsite"}:
                return 0.0
            if "remote" in job and candidate in {"hybrid", "onsite"}:
                return 0.0

        return 0.0

    def matches(self, candidate_location: str | None, job_location: str | None) -> bool:
        return self.score(candidate_location, job_location) >= self.min_score
