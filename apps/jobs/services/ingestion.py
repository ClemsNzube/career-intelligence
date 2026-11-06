import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job, JobIngestionLog, JobSource, JobSourceListing
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
    industry: str
    min_years_experience: int
    application_url: str
    source: str
    skills: list[str]
    posted_at: str | None = None
    expires_at: str | None = None
    source_url: str = ""


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
            industry=(raw_job.get("industry") or "").strip(),
            min_years_experience=int(raw_job.get("min_years_experience") or 0),
            application_url=(raw_job.get("application_url") or "").strip(),
            source=(raw_job.get("source") or "").strip(),
            skills=[str(item).strip() for item in (raw_job.get("skills") or []) if str(item).strip()],
            posted_at=raw_job.get("posted_at"),
            expires_at=raw_job.get("expires_at"),
            source_url=(raw_job.get("source_url") or raw_job.get("application_url") or "").strip(),
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
                payload = self._build_payload(parsed)
                if job is not None:
                    payload.update(
                        source=job.source,
                        external_id=job.external_id,
                        application_url=job.application_url,
                    )
                serializer = JobSerializer(instance=job, data=payload, partial=bool(job))
                serializer.is_valid(raise_exception=True)

                with transaction.atomic():
                    saved_job = serializer.save()
                    self._sync_skill_names(saved_job, parsed.skills)
                    self._record_source_listing(saved_job, parsed, raw_job)

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
        listing_lookup = JobSourceListing.objects.filter(source=self.source)
        if parsed.external_id:
            listing = listing_lookup.filter(source_listing_id=parsed.external_id).select_related("job").first()
            if listing:
                return listing.job

            existing = Job.objects.filter(
                external_id=parsed.external_id,
                source=self.source.slug,
            ).first()
            if existing:
                return existing

        source_url = parsed.source_url or parsed.application_url
        existing_listing = listing_lookup.filter(
            source_url=source_url,
        ).select_related("job").first()
        if existing_listing:
            return existing_listing.job

        exact_duplicate = Job.objects.filter(
            title__iexact=Job.normalize_title(parsed.title),
            company_name__iexact=parsed.company_name.strip(),
            location__iexact=parsed.location.strip(),
            work_type=parsed.work_type,
            employment_type=parsed.employment_type,
            description=Job.clean_description(parsed.description),
        ).first()
        if exact_duplicate:
            return exact_duplicate

        return Job.objects.filter(
            source=self.source.slug,
            application_url__iexact=parsed.application_url,
        ).first()

    def _record_source_listing(self, job: Job, parsed: ParsedJob, raw_job: dict[str, Any]):
        lookup = {"source": self.source}
        if parsed.external_id:
            lookup["source_listing_id"] = parsed.external_id
        else:
            lookup["source_url"] = parsed.source_url or parsed.application_url
        JobSourceListing.objects.update_or_create(
            **lookup,
            defaults={
                "job": job,
                "source_listing_id": parsed.external_id or "",
                "source_url": parsed.source_url or parsed.application_url,
                "application_url": parsed.application_url,
                "raw_payload": raw_job,
            },
        )

    def _build_payload(self, parsed: ParsedJob) -> dict[str, Any]:
        return {
            "title": parsed.title,
            "company_name": parsed.company_name,
            "description": parsed.description,
            "location": parsed.location,
            "work_type": parsed.work_type,
            "employment_type": parsed.employment_type,
            "industry": parsed.industry,
            "min_years_experience": parsed.min_years_experience,
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
