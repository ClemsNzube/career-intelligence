from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.urls import reverse
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.applications.models import JobApplication
from apps.jobs.models import Job


class JobApplicationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="applicant",
            email="applicant@example.com",
            password="test-password",
        )
        self.job = Job.objects.create(
            title="Backend Engineer",
            company_name="Example Corp",
            description="Build backend services.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/backend-engineer",
        )

    def test_application_defaults_to_saved_and_exposes_reverse_relations(self):
        application = JobApplication.objects.create(user=self.user, job=self.job)

        self.assertEqual(application.status, JobApplication.Status.SAVED)
        self.assertIsNone(application.applied_at)
        self.assertIsNone(application.follow_up_at)
        self.assertEqual(self.user.job_applications.get(), application)
        self.assertEqual(self.job.applications.get(), application)

    def test_user_cannot_track_the_same_job_more_than_once(self):
        JobApplication.objects.create(user=self.user, job=self.job)

        with self.assertRaises(IntegrityError), transaction.atomic():
            JobApplication.objects.create(user=self.user, job=self.job)


class JobApplicationAPITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="applicant",
            email="applicant@example.com",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="other",
            email="other@example.com",
            password="test-password",
        )
        self.job = Job.objects.create(
            title="Backend Engineer",
            company_name="Example Corp",
            description="Build backend services.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/backend-engineer",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("application-list")

    def test_list_only_returns_the_authenticated_users_applications(self):
        own_application = JobApplication.objects.create(user=self.user, job=self.job)
        other_job = Job.objects.create(
            title="Data Engineer",
            company_name="Other Corp",
            description="Build data pipelines.",
            location="London",
            work_type="hybrid",
            employment_type="full_time",
            application_url="https://example.com/jobs/data-engineer",
        )
        JobApplication.objects.create(user=self.other_user, job=other_job)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], own_application.pk)
        self.assertEqual(response.data["results"][0]["job"]["id"], self.job.pk)

    def test_create_application_uses_authenticated_user_and_accepts_tracking_fields(self):
        response = self.client.post(
            self.list_url,
            {
                "job_id": self.job.pk,
                "status": JobApplication.Status.APPLIED,
                "applied_at": "2026-10-28T10:00:00Z",
                "follow_up_at": "2026-11-04T10:00:00Z",
                "notes": "Contacted the recruiter.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = JobApplication.objects.get(pk=response.data["id"])
        self.assertEqual(application.user, self.user)
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.status, JobApplication.Status.APPLIED)
        self.assertEqual(application.notes, "Contacted the recruiter.")

    def test_duplicate_job_and_invalid_status_are_rejected(self):
        JobApplication.objects.create(user=self.user, job=self.job)

        duplicate_response = self.client.post(
            self.list_url,
            {"job_id": self.job.pk},
            format="json",
        )
        invalid_status_response = self.client.post(
            self.list_url,
            {"job_id": Job.objects.create(
                title="Data Engineer",
                company_name="Other Corp",
                description="Build data pipelines.",
                location="London",
                work_type="hybrid",
                employment_type="full_time",
                application_url="https://example.com/jobs/data-engineer",
            ).pk, "status": "unknown"},
            format="json",
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_id", duplicate_response.data)
        self.assertEqual(invalid_status_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_update_and_delete_are_limited_to_owner(self):
        own_application = JobApplication.objects.create(user=self.user, job=self.job)
        other_job = Job.objects.create(
            title="Data Engineer",
            company_name="Other Corp",
            description="Build data pipelines.",
            location="London",
            work_type="hybrid",
            employment_type="full_time",
            application_url="https://example.com/jobs/data-engineer",
        )
        other_application = JobApplication.objects.create(
            user=self.other_user,
            job=other_job,
        )

        detail_url = reverse("application-detail", args=[own_application.pk])
        update_response = self.client.patch(
            detail_url,
            {"status": JobApplication.Status.INTERVIEW, "notes": "First interview."},
            format="json",
        )
        inaccessible_response = self.client.get(
            reverse("application-detail", args=[other_application.pk])
        )
        inaccessible_update_response = self.client.patch(
            reverse("application-detail", args=[other_application.pk]),
            {"notes": "Attempt to modify another user's record."},
            format="json",
        )
        inaccessible_delete_response = self.client.delete(
            reverse("application-detail", args=[other_application.pk])
        )
        delete_response = self.client.delete(detail_url)

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["status"], JobApplication.Status.INTERVIEW)
        self.assertEqual(inaccessible_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            inaccessible_update_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            inaccessible_delete_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(JobApplication.objects.filter(pk=other_application.pk).exists())
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(JobApplication.objects.filter(pk=own_application.pk).exists())

    def test_application_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stats_return_zero_counts_when_user_has_no_applications(self):
        response = self.client.get(reverse("application-stats"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "total": 0,
                "saved": 0,
                "applied": 0,
                "interview": 0,
                "offer": 0,
                "rejected": 0,
                "withdrawn": 0,
            },
        )

    def test_stats_count_each_status_for_authenticated_user_in_one_query(self):
        statuses = [
            JobApplication.Status.SAVED,
            JobApplication.Status.APPLIED,
            JobApplication.Status.INTERVIEW,
            JobApplication.Status.OFFER,
            JobApplication.Status.REJECTED,
            JobApplication.Status.WITHDRAWN,
        ]
        for index, application_status in enumerate(statuses):
            job = self.job
            if index:
                job = Job.objects.create(
                    title=f"Engineer {index}",
                    company_name="Example Corp",
                    description="Build software.",
                    location="Remote",
                    work_type="remote",
                    employment_type="full_time",
                    application_url=f"https://example.com/jobs/engineer-{index}",
                )
            JobApplication.objects.create(
                user=self.user,
                job=job,
                status=application_status,
            )

        other_job = Job.objects.create(
            title="Other User Job",
            company_name="Other Corp",
            description="Build other software.",
            location="London",
            work_type="hybrid",
            employment_type="full_time",
            application_url="https://example.com/jobs/other-user",
        )
        JobApplication.objects.create(
            user=self.other_user,
            job=other_job,
            status=JobApplication.Status.OFFER,
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("application-stats"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "total": 6,
                "saved": 1,
                "applied": 1,
                "interview": 1,
                "offer": 1,
                "rejected": 1,
                "withdrawn": 1,
            },
        )
        application_queries = [
            query
            for query in queries
            if "jobapplication" in query["sql"].lower()
        ]
        self.assertEqual(len(application_queries), 1)

    def test_stats_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("application-stats"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_follow_ups_include_due_and_overdue_active_applications_in_date_order(self):
        today = timezone.localdate()
        yesterday_at = timezone.make_aware(
            datetime.combine(today - timedelta(days=1), time(hour=9))
        )
        today_at = timezone.make_aware(datetime.combine(today, time(hour=9)))
        tomorrow_at = timezone.make_aware(
            datetime.combine(today + timedelta(days=1), time(hour=9))
        )
        overdue = JobApplication.objects.create(
            user=self.user,
            job=self.job,
            status=JobApplication.Status.APPLIED,
            follow_up_at=yesterday_at,
        )
        today_job = Job.objects.create(
            title="Today Follow-up",
            company_name="Example Corp",
            description="Build software.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/today-follow-up",
        )
        due_today = JobApplication.objects.create(
            user=self.user,
            job=today_job,
            status=JobApplication.Status.INTERVIEW,
            follow_up_at=today_at,
        )
        for index, app_status in enumerate(
            [JobApplication.Status.OFFER, JobApplication.Status.SAVED]
        ):
            job = Job.objects.create(
                title=f"Future Follow-up {index}",
                company_name="Example Corp",
                description="Build software.",
                location="Remote",
                work_type="remote",
                employment_type="full_time",
                application_url=f"https://example.com/jobs/future-follow-up-{index}",
            )
            JobApplication.objects.create(
                user=self.user,
                job=job,
                status=app_status,
                follow_up_at=tomorrow_at,
            )

        response = self.client.get(reverse("application-follow-ups"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [overdue.pk, due_today.pk],
        )

    def test_follow_ups_exclude_rejected_withdrawn_and_other_users(self):
        today_at = timezone.make_aware(
            datetime.combine(timezone.localdate(), time(hour=9))
        )
        for index, app_status in enumerate(
            [JobApplication.Status.REJECTED, JobApplication.Status.WITHDRAWN]
        ):
            job = Job.objects.create(
                title=f"Closed Application {index}",
                company_name="Example Corp",
                description="Build software.",
                location="Remote",
                work_type="remote",
                employment_type="full_time",
                application_url=f"https://example.com/jobs/closed-{index}",
            )
            JobApplication.objects.create(
                user=self.user,
                job=job,
                status=app_status,
                follow_up_at=today_at,
            )
        other_job = Job.objects.create(
            title="Other User Follow-up",
            company_name="Other Corp",
            description="Build software.",
            location="London",
            work_type="hybrid",
            employment_type="full_time",
            application_url="https://example.com/jobs/other-follow-up",
        )
        JobApplication.objects.create(
            user=self.other_user,
            job=other_job,
            status=JobApplication.Status.APPLIED,
            follow_up_at=today_at,
        )

        response = self.client.get(reverse("application-follow-ups"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_follow_ups_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("application-follow-ups"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
