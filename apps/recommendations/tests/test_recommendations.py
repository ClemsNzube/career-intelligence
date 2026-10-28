from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applications.models import JobApplication
from apps.intelligence.embeddings.providers.fake import FakeEmbeddingProvider
from apps.intelligence.embeddings.services import (
    EmbeddingService,
    build_job_text,
    build_profile_text,
)
from apps.jobs.models import Job
from apps.skills.models import Skill
from apps.users.models import CareerPreferences, CareerProfile, Experience


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
            year_of_experience=5,
            preferred_locations=["Remote"],
            preferred_work_type="remote",
        )
        self.python = Skill.objects.create(name="Python", slug="python")
        self.django = Skill.objects.create(name="Django", slug="django")
        self.profile.skills.set([self.python, self.django])
        self.experience = Experience.objects.create(
            career_profile=self.profile,
            job_title="Backend Engineer",
            company="Example Corp",
            employment_type="full_time",
            location="Remote",
            start_date=date(2020, 1, 1),
            currently_working=True,
            description="Builds Python services.",
        )
        self.experience.skills_used.set([self.python, self.django])
        self.preferences = CareerPreferences.objects.create(
            career_profile=self.profile,
            target_job_titles=["Python Developer", "Backend Engineer"],
            preferred_locations=["Remote"],
            preferred_work_types=["remote"],
            min_years_of_experience=3,
        )

        self.strong_job = self.create_job("Python Backend Developer", "remote", [self.python, self.django])
        self.weak_job = self.create_job("Frontend Designer", "onsite", [])
        self.middle_job = self.create_job("Django Developer", "remote", [self.python])
        self.expired_job = self.create_job("Expired Python Developer", "remote", [self.python, self.django])
        self.expired_job.expires_at = timezone.now() - timedelta(days=1)
        self.expired_job.save(update_fields=["expires_at"])

        self.client.force_authenticate(user=self.user)

    def test_profile_data_is_saved_and_linked(self):
        profile = CareerProfile.objects.get(user=self.user)

        self.assertEqual(set(profile.skills.all()), {self.python, self.django})
        self.assertEqual(profile.year_of_experience, 5)
        self.assertEqual(profile.preferred_work_type, "remote")
        self.assertEqual(profile.preferred_locations, ["Remote"])
        self.assertEqual(profile.work_experiences.get(), self.experience)
        self.assertEqual(set(self.experience.skills_used.all()), {self.python, self.django})
        self.assertEqual(profile.preferences, self.preferences)
        self.assertEqual(
            profile.preferences.target_job_titles,
            ["Python Developer", "Backend Engineer"],
        )
        self.assertEqual(profile.preferences.career_profile, profile)

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

    def test_recommendations_include_current_users_application_status(self):
        JobApplication.objects.create(
            user=self.user,
            job=self.strong_job,
            status=JobApplication.Status.APPLIED,
        )
        other_user = get_user_model().objects.create_user(
            username="other-recommendation-user",
            email="other-recommendation@example.com",
            password="test-password",
        )
        JobApplication.objects.create(
            user=other_user,
            job=self.middle_job,
            status=JobApplication.Status.INTERVIEW,
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/api/recommendations/?limit=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application_queries = [
            query
            for query in queries
            if "jobapplication" in query["sql"].lower()
        ]
        self.assertEqual(len(application_queries), 1)
        statuses = {
            result["job"]["id"]: result["application_status"]
            for result in response.data["results"]
        }
        self.assertEqual(statuses[self.strong_job.pk], JobApplication.Status.APPLIED)
        self.assertEqual(statuses[self.middle_job.pk], "not_tracked")
        self.assertEqual(statuses[self.weak_job.pk], "not_tracked")

    def test_recommended_job_can_be_saved_directly_to_application_tracker(self):
        response = self.client.post(
            "/api/applications/",
            {"job_id": self.strong_job.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["job"]["id"], self.strong_job.pk)
        recommendations = self.client.get("/api/recommendations/?limit=50")
        strong_recommendation = next(
            item
            for item in recommendations.data["results"]
            if item["job"]["id"] == self.strong_job.pk
        )
        self.assertEqual(strong_recommendation["application_status"], "saved")

    def test_experience_skills_and_career_preferences_drive_recommendations(self):
        self.profile.skills.clear()
        self.experience.skills_used.set([self.python, self.django])
        self.profile.related_name = "Unrelated Title"
        self.profile.preferred_locations = ["New York"]
        self.profile.preferred_work_type = "onsite"
        self.profile.save(
            update_fields=["related_name", "preferred_locations", "preferred_work_type"]
        )
        self.preferences.target_job_titles = ["Python Backend Developer"]
        self.preferences.preferred_locations = ["Remote"]
        self.preferences.preferred_work_types = ["remote", "hybrid"]
        self.preferences.save(
            update_fields=[
                "target_job_titles",
                "preferred_locations",
                "preferred_work_types",
            ]
        )

        response = self.client.get("/api/recommendations/?limit=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = next(
            item
            for item in response.data["results"]
            if item["job"]["id"] == self.strong_job.pk
        )
        self.assertEqual(result["components"]["skill"], 1.0)
        self.assertEqual(result["components"]["location"], 1.0)
        self.assertEqual(result["components"]["work_type"], 1.0)
        self.assertEqual(result["components"]["title"], 1.0)
        self.assertEqual(result["explanation"]["matched_skills"], ["Python", "Django"])
        self.assertEqual(result["explanation"]["missing_skills"], [])
        self.assertIn("Your location preference matches", result["explanation"]["strengths"])
        self.assertIn("Your work type preference matches", result["explanation"]["strengths"])
        self.assertIn("Your preferred title aligns with this role", result["explanation"]["strengths"])

    def test_browsable_api_renders_recommendations(self):
        response = self.client.get("/api/recommendations/", HTTP_ACCEPT="text/html")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Python Backend Developer")

    def test_hybrid_scores_rank_jobs_and_explanations_match_each_job(self):
        rule_scores = {
            self.strong_job.pk: 0.8,
            self.middle_job.pk: 0.6,
            self.weak_job.pk: 0.1,
        }

        def rule_result(profile, job):
            return {
                "score": rule_scores[job.pk],
                "skill": 0.5,
                "experience": 0.5,
                "work_type": 0.5,
                "location": 0.5,
                "title": 0.5,
            }

        def semantic_score(profile, job):
            return 1.0 if job.pk == self.middle_job.pk else 0.0

        with patch(
            "apps.intelligence.matching.hybrid.match_job_to_profile",
            side_effect=rule_result,
        ), patch(
            "apps.intelligence.matching.hybrid.similarity_for_objects",
            side_effect=semantic_score,
        ):
            response = self.client.get("/api/recommendations/?limit=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        middle_result = next(item for item in results if item["job"]["id"] == self.middle_job.pk)
        self.assertEqual(results[0]["job"]["id"], self.middle_job.pk)
        self.assertEqual(middle_result["scores"]["semantic"], 1.0)
        self.assertGreater(middle_result["scores"]["final"], middle_result["scores"]["rule"])
        self.assertEqual(middle_result["score"], middle_result["scores"]["final"])
        self.assertEqual(middle_result["explanation"]["missing_skills"], [])
        self.assertEqual(middle_result["explanation"]["matched_skills"], ["Python"])
        self.assertEqual(
            [item["scores"]["final"] for item in results],
            sorted((item["scores"]["final"] for item in results), reverse=True),
        )
        self.assertTrue(middle_result["scores"]["semantic_available"])

    def test_missing_embeddings_use_rule_score_and_are_reported(self):
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertIsNone(result["scores"]["semantic"])
        self.assertFalse(result["scores"]["semantic_available"])
        self.assertEqual(result["scores"]["final"], result["scores"]["rule"])
        self.assertEqual(result["score"], result["scores"]["rule"])
        self.assertIn(
            "Semantic similarity unavailable; ranking uses the rule-based score only",
            result["explanation"]["gaps"],
        )

    def test_recommendation_uses_persisted_embeddings_for_the_same_objects(self):
        embedding_service = EmbeddingService(provider=FakeEmbeddingProvider())
        embedding_service.save_for_object(self.profile, build_profile_text(self.profile))
        embedding_service.save_for_object(
            self.strong_job,
            build_job_text(self.strong_job),
        )

        with patch(
            "apps.recommendations.services.recommend_jobs.get_available_jobs",
            return_value=[self.strong_job],
        ):
            response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertTrue(result["scores"]["semantic_available"])
        self.assertIsInstance(result["scores"]["semantic"], float)

    def test_empty_job_list_returns_empty_paginated_results(self):
        with patch(
            "apps.recommendations.services.recommend_jobs.get_available_jobs",
            return_value=[],
        ):
            response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_equal_scores_are_ordered_by_posted_at_then_id_descending(self):
        older_job = self.create_job("Python Developer", "remote", [self.python])
        same_date_earlier_id = self.create_job("Python Developer", "remote", [self.python])
        same_date_later_id = self.create_job("Python Developer", "remote", [self.python])
        latest = timezone.now()
        older = latest - timedelta(days=1)

        older_job.posted_at = older
        older_job.save(update_fields=["posted_at"])
        same_date_earlier_id.posted_at = latest
        same_date_earlier_id.save(update_fields=["posted_at"])
        same_date_later_id.posted_at = latest
        same_date_later_id.save(update_fields=["posted_at"])

        response = self.client.get("/api/recommendations/?limit=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ranked_ids = [item["job"]["id"] for item in response.data["results"]]
        self.assertLess(ranked_ids.index(same_date_later_id.pk), ranked_ids.index(same_date_earlier_id.pk))
        self.assertLess(ranked_ids.index(same_date_earlier_id.pk), ranked_ids.index(older_job.pk))

    def test_jobs_without_application_url_are_excluded(self):
        missing_url_job = self.create_job("Unavailable Role", "remote", [self.python])
        missing_url_job.application_url = ""
        missing_url_job.save(update_fields=["application_url"])

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertNotIn(missing_url_job.pk, [result["job"]["id"] for result in response.data["results"]])

    def test_default_limit_returns_top_twenty_ranked_jobs(self):
        for index in range(18):
            self.create_job(f"Additional Developer {index}", "remote", [self.python])

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 21)
        results = response.data["results"]
        self.assertEqual(len(results), 20)
        self.assertEqual([result["rank"] for result in results], list(range(1, 21)))
        scores = [result["score"] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

        second_page = self.client.get("/api/recommendations/?page=2")

        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(second_page.data["count"], 21)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(second_page.data["results"][0]["rank"], 21)
        self.assertIsNotNone(second_page.data["previous"])

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
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
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