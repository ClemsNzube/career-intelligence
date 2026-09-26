from abc import ABC, abstractmethod
from typing import Any


class BaseJobSourceAdapter(ABC):
    slug = "base"

    def __init__(self, source: str | None = None):
        self.source = source or self.slug

    @abstractmethod
    def fetch_jobs(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class LinkedInJobAdapter(BaseJobSourceAdapter):
    slug = "linkedin"

    def fetch_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "external_id": "linkedin-demo-1",
                "title": "Senior Python Developer",
                "company_name": "Example Corp",
                "description": "Build backend services and APIs.",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/linkedIn-demo",
                "source": self.source,
                "skills": ["Python", "Django"],
            }
        ]
