import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job, JobIngestionLog, JobSource
from apps.skills.models import Skill

logger = logging.getLogger(__name__)


@dataclass
class ParsedJob:
    external_id: str | None
    title: str
    company_name: str
    description: str
    location: str
    work_type: str
    employment_type: str
    application_url: str
    source: str
    skills: list[str]
    posted_at: str | None = None
    expires_at: str | None = None


class JobParser:
    @staticmethod
    def parse(raw_job: dict[str, Any]) -> ParsedJob:
        return ParsedJob(
            external_id=(raw_job.get("external_id") or "").strip() or None,
            title=(raw_job.get("title") or "").strip(),
            company_name=(raw_job.get("company_name") or "").strip(),
            description=(raw_job.get("description") or "").strip(),
            location=(raw_job.get("location") or "").strip(),
            work_type=(raw_job.get("work_type") or "").strip(),
            employment_type=(raw_job.get("employment_type") or "").strip(),
            application_url=(raw_job.get("application_url") or "").strip(),
            source=(raw_job.get("source") or "").strip(),
            skills=[str(item).strip() for item in (raw_job.get("skills") or []) if str(item).strip()],
            posted_at=raw_job.get("posted_at"),
            expires_at=raw_job.get("expires_at"),
        )


class JobIngestionService:
    def __init__(self, source: JobSource):
        self.source = source

    def ingest(self, payloads: list[dict[str, Any]]) -> dict[str, int]:
        created_count = 0
        updated_count = 0
        failed_count = 0

        for raw_job in payloads:
            try:
                parsed = JobParser.parse(raw_job)
                logger.info("Processing job source=%s external_id=%s", self.source.slug, parsed.external_id)

                if not parsed.title or not parsed.company_name or not parsed.application_url:
                    raise ValueError("Title, company_name, and application_url are required.")

                job = self._get_existing_job(parsed)
                serializer = JobSerializer(instance=job, data=self._build_payload(parsed), partial=bool(job))
                serializer.is_valid(raise_exception=True)

                with transaction.atomic():
                    saved_job = serializer.save()
                    self._sync_skill_names(saved_job, parsed.skills)

                if job is None:
                    created_count += 1
                    status = "created"
                else:
                    updated_count += 1
                    status = "updated"

                JobIngestionLog.objects.create(
                    source=self.source,
                    job=saved_job,
                    external_id=parsed.external_id,
                    status=status,
                    payload=raw_job,
                )
            except Exception as exc:  # pragma: no cover - broad path for real ingestion failures
                failed_count += 1
                logger.exception("Job ingestion failed for source=%s payload=%s", self.source.slug, raw_job)
                JobIngestionLog.objects.create(
                    source=self.source,
                    external_id=(raw_job or {}).get("external_id") or None,
                    status="failed",
                    payload=raw_job,
                    error_message=str(exc),
                )

        return {
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
        }

    def _get_existing_job(self, parsed: ParsedJob):
        if parsed.external_id:
            existing = Job.objects.filter(external_id=parsed.external_id, source=self.source.slug).first()
            if existing:
                return existing

        return Job.objects.filter(
            title__iexact=Job.normalize_title(parsed.title),
            company_name__iexact=parsed.company_name,
            application_url__iexact=parsed.application_url,
        ).first()

    def _build_payload(self, parsed: ParsedJob) -> dict[str, Any]:
        return {
            "title": parsed.title,
            "company_name": parsed.company_name,
            "description": parsed.description,
            "location": parsed.location,
            "work_type": parsed.work_type,
            "employment_type": parsed.employment_type,
            "application_url": parsed.application_url,
            "source": self.source.slug,
            "external_id": parsed.external_id,
            "posted_at": parsed.posted_at,
            "expires_at": parsed.expires_at,
            "skills": parsed.skills,
        }

    def _sync_skill_names(self, job: Job, skill_names: list[str]):
        skill_objects = []
        for name in skill_names:
            skill = Skill.objects.filter(name__iexact=name).first()
            if skill is None:
                skill = Skill.objects.create(name=name, slug=name.lower().replace(" ", "-")[:120])
            skill_objects.append(skill)
        job.skills.set(skill_objects)
