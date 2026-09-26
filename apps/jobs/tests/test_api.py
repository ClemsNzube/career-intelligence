from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.jobs.models import Job
from apps.skills.models import Skill


class JobAPITest(APITestCase):
    def setUp(self):
        self.skill_python = Skill.objects.create(name="Python", slug="python")
        self.skill_django = Skill.objects.create(name="Django", slug="django")

        self.job = Job.objects.create(
            title="Senior Python Developer",
            company_name="Example Corp",
            description="Build backend services and APIs.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/1",
            source="linkedin",
        )
        self.job.skills.set([self.skill_python, self.skill_django])

    def test_list_endpoint_supports_search_filters_and_ordering(self):
        response = self.client.get(
            "/api/jobs/?search=python&work_type=remote&employment_type=full_time&skills=Python&ordering=-created_at"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Senior Python Developer")

    def test_create_job_requires_valid_data(self):
        payload = {
            "title": "Data Engineer",
            "company_name": "Acme Labs",
            "description": "Build analytics pipelines.",
            "location": "New York",
            "work_type": "onsite",
            "employment_type": "full_time",
            "application_url": "https://example.com/jobs/data-engineer",
            "source": "greenhouse",
            "skills": ["Python", "Django"],
        }

        response = self.client.post("/api/jobs/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company_name"], "Acme Labs")
        self.assertIn("Python", response.data["skills"])

        invalid_response = self.client.post(
            "/api/jobs/",
            {"title": "Bad job"},
            format="json",
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_job_detail_supports_update_and_delete(self):
        detail_url = reverse("job-detail", args=[self.job.pk])

        patch_response = self.client.patch(
            detail_url,
            {"title": "Updated Job Title"},
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["title"], "Updated Job Title")

        delete_response = self.client.delete(detail_url)

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
