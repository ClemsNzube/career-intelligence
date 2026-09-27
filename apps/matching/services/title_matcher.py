from __future__ import annotations

import re


class TitleMatcher:
    def __init__(self, min_score: float = 0.5):
        self.min_score = min_score

    def _normalize(self, value: str | None) -> set[str]:
        text = (value or "").lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return {token for token in text.split() if token}

    def score(self, candidate_title: str | None, job_title: str | None) -> float:
        candidate_tokens = self._normalize(candidate_title)
        job_tokens = self._normalize(job_title)

        if not job_tokens:
            return 1.0
        if not candidate_tokens:
            return 1.0

        overlap = candidate_tokens & job_tokens
        if not overlap:
            return 0.0

        return len(overlap) / max(len(job_tokens), 1)

    def matches(self, candidate_title: str | None, job_title: str | None) -> bool:
        return self.score(candidate_title, job_title) >= self.min_score
