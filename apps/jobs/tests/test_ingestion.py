from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.jobs.models import Job, JobIngestionLog, JobSource, JobSourceListing
from apps.jobs.services.ingestion import JobIngestionService


class JobIngestionServiceTest(TestCase):
    def setUp(self):
        self.source = JobSource.objects.create(
            name="LinkedIn",
            slug="linkedin",
            base_url="https://linkedin.com/jobs",
        )

    def test_ingestion_creates_and_updates_jobs(self):
        service = JobIngestionService(source=self.source)

        payloads = [
            {
                "external_id": "linkedin-001",
                "title": "  senior   python   developer  ",
                "company_name": "Example Corp",
                "description": "<p>Build backend services and APIs.</p>",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/1",
                "source": "linkedin",
                "skills": ["Python", "Django"],
            }
        ]

        result = service.ingest(payloads)

        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["updated_count"], 0)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(Job.objects.get().title, "Senior Python Developer")

        payloads[0]["description"] = "Build backend services and APIs."
        payloads[0]["skills"] = ["Python", "Django", "PostgreSQL"]

        result = service.ingest(payloads)

        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(result["created_count"], 0)
        self.assertEqual(Job.objects.get().skills.count(), 3)

    def test_ingestion_logs_failed_records(self):
        service = JobIngestionService(source=self.source)

        result = service.ingest([
            {
                "title": "",
                "company_name": "Example Corp",
                "description": "Missing title",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/bad",
                "source": "linkedin",
            }
        ])

        self.assertEqual(result["failed_count"], 1)
        self.assertTrue(JobIngestionLog.objects.filter(status="failed").exists())
        self.assertEqual(Job.objects.count(), 0)

    def test_management_command_runs_for_source(self):
        call_command("ingest_jobs", source="linkedin", jobs=[
            {
                "external_id": "linkedin-002",
                "title": "Backend Engineer",
                "company_name": "Pilot Co",
                "description": "Build APIs.",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/2",
                "source": "linkedin",
                "skills": ["Python"],
            }
        ])

        self.assertEqual(Job.objects.filter(title__icontains="Backend Engineer").count(), 1)

    def test_ingestion_endpoint_accepts_payload(self):
        url = reverse("job-ingest")
        payload = {
            "source": "linkedin",
            "jobs": [{
                "external_id": "linkedin-003",
                "title": "Platform Engineer",
                "company_name": "Launch Labs",
                "description": "Ship backend infrastructure.",
                "location": "Remote",
                "work_type": "remote",
                "employment_type": "full_time",
                "application_url": "https://example.com/jobs/3",
                "source": "linkedin",
                "skills": ["Python", "Kubernetes"],
            }],
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(Job.objects.filter(company_name="Launch Labs").count(), 1)

    def test_same_job_from_multiple_sources_preserves_each_listing_and_application_url(self):
        first_payload = {
            "external_id": "alpha-001",
            "title": "Senior Python Developer",
            "company_name": "Example Corp",
            "description": "Build backend services and APIs.",
            "location": "Remote",
            "work_type": "remote",
            "employment_type": "full_time",
            "application_url": "https://alpha.example/jobs/alpha-001",
            "source_url": "https://alpha.example/listings/alpha-001",
            "source": "alpha",
            "skills": ["Python"],
        }
        first_result = JobIngestionService(source=self.source).ingest([first_payload])
        first_job = Job.objects.get()
        second_source = JobSource.objects.create(
            name="Beta",
            slug="beta",
            base_url="https://beta.example",
        )
        second_payload = {
            **first_payload,
            "external_id": "beta-001",
            "application_url": "https://beta.example/jobs/beta-001",
            "source_url": "https://beta.example/listings/beta-001",
            "source": "beta",
        }

        second_result = JobIngestionService(source=second_source).ingest([second_payload])

        self.assertEqual(first_result["created_count"], 1)
        self.assertEqual(second_result["updated_count"], 1)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(
            set(
                JobSourceListing.objects.filter(job=first_job).values_list(
                    "application_url", flat=True
                )
            ),
            {
                "https://alpha.example/jobs/alpha-001",
                "https://beta.example/jobs/beta-001",
            },
        )
        self.assertEqual(
            set(
                JobSourceListing.objects.filter(job=first_job).values_list(
                    "source_listing_id", flat=True
                )
            ),
            {"alpha-001", "beta-001"},
        )
        response = self.client.get(f"/api/jobs/{first_job.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["source_listings"]), 2)
        self.assertEqual(
            {listing["source"] for listing in response.data["source_listings"]},
            {"linkedin", "beta"},
        )

    def test_same_external_id_is_allowed_for_different_sources(self):
        first = {
            "external_id": "shared-id",
            "title": "Python Engineer",
            "company_name": "Alpha Corp",
            "description": "Build alpha systems.",
            "location": "Remote",
            "work_type": "remote",
            "employment_type": "full_time",
            "application_url": "https://alpha.example/jobs/shared-id",
        }
        JobIngestionService(source=self.source).ingest([first])
        second_source = JobSource.objects.create(
            name="Beta",
            slug="beta",
            base_url="https://beta.example",
        )
        second = {
            **first,
            "title": "Data Engineer",
            "company_name": "Beta Corp",
            "description": "Build beta systems.",
            "application_url": "https://beta.example/jobs/shared-id",
        }

        result = JobIngestionService(source=second_source).ingest([second])

        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(Job.objects.count(), 2)
