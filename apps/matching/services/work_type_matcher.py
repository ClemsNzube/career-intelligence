from __future__ import annotations


class WorkTypeMatcher:
    def __init__(self, min_score: float = 1.0):
        self.min_score = min_score

    def score(
        self,
        candidate_work_type: str | list[str] | tuple[str, ...] | set[str] | None,
        job_work_type: str | None,
    ) -> float:
        if isinstance(candidate_work_type, str):
            candidates = {candidate_work_type.strip().lower()}
        else:
            candidates = {
                value.strip().lower()
                for value in candidate_work_type or ()
                if isinstance(value, str) and value.strip()
            }
        job = (job_work_type or "").strip().lower()

        if not job or not candidates:
            return 0.0
        if job in candidates or "any" in candidates or job == "any":
            return 1.0

        return 0.0

    def matches(
        self,
        candidate_work_type: str | list[str] | tuple[str, ...] | set[str] | None,
        job_work_type: str | None,
    ) -> bool:
        return self.score(candidate_work_type, job_work_type) >= self.min_score
