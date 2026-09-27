from __future__ import annotations


class WorkTypeMatcher:
    def __init__(self, min_score: float = 1.0):
        self.min_score = min_score

    def score(self, candidate_work_type: str | None, job_work_type: str | None) -> float:
        candidate = (candidate_work_type or "").strip().lower()
        job = (job_work_type or "").strip().lower()

        if not job:
            return 1.0
        if not candidate:
            return 0.0
        if candidate == job:
            return 1.0
        if candidate == "any" or job == "any":
            return 1.0

        return 0.0

    def matches(self, candidate_work_type: str | None, job_work_type: str | None) -> bool:
        return self.score(candidate_work_type, job_work_type) >= self.min_score
