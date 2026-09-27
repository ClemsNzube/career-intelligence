from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.jobs.models import Job
from apps.skills.models import Skill
from apps.users.models import CareerProfile


class JobRecommendationsAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="recommendation-user",
            email="recommendation@example.com",
            password="secret123",
        )
        self.profile = CareerProfile.objects.create(
            user=self.user,
            related_name="Python Developer",
            year_of_experience=5,
            preferred_locations=["Remote"],
            preferred_work_type="remote",
        )
        self.python = Skill.objects.create(name="Python", slug="python")
        self.django = Skill.objects.create(name="Django", slug="django")
        self.profile.skills.set([self.python, self.django])

        self.strong_job = self.create_job("Python Backend Developer", "remote", [self.python, self.django])
        self.weak_job = self.create_job("Frontend Designer", "onsite", [])
        self.middle_job = self.create_job("Django Developer", "remote", [self.python])
        self.expired_job = self.create_job("Expired Python Developer", "remote", [self.python, self.django])
        self.expired_job.expires_at = timezone.now() - timedelta(days=1)
        self.expired_job.save(update_fields=["expires_at"])

        self.client.force_authenticate(user=self.user)

    def create_job(self, title, work_type, skills):
        job = Job.objects.create(
            title=title,
            company_name="Example Corp",
            description="Build and maintain software.",
            location="Remote" if work_type == "remote" else "New York",
            work_type=work_type,
            employment_type="full_time",
            application_url=f"https://example.com/jobs/{title.lower().replace(' ', '-')}",
            source="example",
        )
        job.skills.set(skills)
        return job

    def test_recommendations_are_ranked_by_match_score(self):
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        results = response.data["results"]
        self.assertEqual(
            [result["job"]["id"] for result in results],
            [self.strong_job.pk, self.middle_job.pk, self.weak_job.pk],
        )
        self.assertEqual([result["rank"] for result in results], [1, 2, 3])
        self.assertEqual([result["score"] for result in results], sorted((result["score"] for result in results), reverse=True))
        self.assertTrue(all("explanation" in result and "components" in result for result in results))
        self.assertNotIn(self.expired_job.pk, [result["job"]["id"] for result in results])

    def test_default_limit_returns_top_twenty_ranked_jobs(self):
        for index in range(18):
            self.create_job(f"Additional Developer {index}", "remote", [self.python])

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 20)
        results = response.data["results"]
        self.assertEqual([result["rank"] for result in results], list(range(1, 21)))
        scores = [result["score"] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_low_scoring_jobs_are_ranked_without_match_threshold_filter(self):
        react = Skill.objects.create(name="React", slug="react")
        low_scoring_job = self.create_job("React Onsite Specialist", "onsite", [react])
        low_scoring_job.min_years_experience = 50
        low_scoring_job.save(update_fields=["min_years_experience"])

        response = self.client.get("/api/recommendations/?limit=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        low_score_result = next(result for result in response.data["results"] if result["job"]["id"] == low_scoring_job.pk)
        self.assertLess(low_score_result["score"], 0.5)
        self.assertFalse(low_score_result["match"])

    def test_limit_returns_only_the_highest_ranked_jobs(self):
        response = self.client.get("/api/recommendations/?limit=2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            [result["job"]["id"] for result in response.data["results"]],
            [self.strong_job.pk, self.middle_job.pk],
        )

    def test_invalid_limit_is_rejected(self):
        response = self.client.get("/api/recommendations/?limit=abc")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_endpoint_returns_not_found_when_profile_is_missing(self):
        self.profile.delete()

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)