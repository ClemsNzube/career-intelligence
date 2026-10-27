from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.skills.models import Skill
from apps.users.models import (
    CareerPreferences,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Project,
)

User = get_user_model()


class CareerProfileAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser",
            email="apiuser@example.com",
            password="password123",
        )
        self.profile = CareerProfile.objects.create(
            user=self.user,
            related_name="Platform Engineer",
            bio="Builds systems.",
            year_of_experience=4,
            preferred_locations=["Remote"],
            preferred_work_type="remote",
        )

    def test_profile_endpoint_list_and_detail(self):
        list_url = reverse("profile-list")
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

        detail_url = reverse("profile-detail", args=[self.profile.pk])
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["user"], self.user.pk)

    def test_profile_endpoint_persists_explicitly_selected_skills(self):
        python = Skill.objects.create(name="Python", slug="python")

        response = self.client.patch(
            reverse("profile-detail", args=[self.profile.pk]),
            {"skills": [python.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(self.profile.skills.values_list("name", flat=True)),
            ["Python"],
        )

    def test_profile_save_links_exact_skill_mentions_from_bio(self):
        python = Skill.objects.create(name="Python", slug="python")
        profile = CareerProfile.objects.create(
            user=User.objects.create_user(
                username="python-profile",
                email="python-profile@example.com",
            ),
            bio="Experienced Python developer.",
        )

        self.assertEqual(list(profile.skills.all()), [python])

    def test_experience_skill_selection_is_linked_to_parent_profile(self):
        python = Skill.objects.create(name="Python", slug="python")
        experience = Experience.objects.create(
            career_profile=self.profile,
            job_title="Backend Engineer",
            company="Example Corp",
        )

        experience.skills_used.add(python)

        self.assertEqual(list(self.profile.skills.all()), [python])

    def test_profile_skill_suggestions_endpoint_returns_ambiguous_mentions(self):
        Skill.objects.create(name="Python", slug="python")
        Skill.objects.create(name="Docker", slug="docker")
        self.profile.bio = "Pyhton developer; no experience with Docker."
        self.profile.save(update_fields=["bio"])

        response = self.client.get(
            reverse("profile-skill-suggestions", args=[self.profile.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["name"] for item in response.data["suggestions"]},
            {"Python", "Docker"},
        )
        self.assertEqual(
            list(self.profile.skills.values_list("name", flat=True)),
            [],
        )

    def test_preferences_endpoint_create_and_list(self):
        url = reverse("career-preferences-list")
        payload = {
            "career_profile": self.profile.pk,
            "target_job_titles": ["Senior Python Developer"],
            "target_industries": ["SaaS"],
            "preferred_locations": ["Remote", "Berlin"],
            "preferred_work_types": ["remote", "hybrid"],
            "min_years_of_experience": 3,
            "max_years_of_experience": 8,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CareerPreferences.objects.count(), 1)

    def test_education_endpoint_create_and_list(self):
        url = reverse("education-list")
        payload = {
            "career_profile": self.profile.pk,
            "institution": "University of Michigan",
            "degree": "B.S.",
            "field_of_study": "Computer Science",
            "start_date": "2014-09-01",
            "end_date": "2018-05-01",
            "currently_studying": False,
            "description": "Studied computer engineering.",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Education.objects.count(), 1)

    def test_experience_endpoint_create_and_list(self):
        url = reverse("experience-list")
        payload = {
            "career_profile": self.profile.pk,
            "job_title": "Backend Engineer",
            "company": "Example Corp",
            "employment_type": "full_time",
            "location": "Remote",
            "start_date": "2020-01-01",
            "end_date": "2022-12-31",
            "currently_working": False,
            "description": "Built APIs.",
            "skills_used": [],
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Experience.objects.count(), 1)

    def test_certification_endpoint_create_and_list(self):
        url = reverse("certification-list")
        payload = {
            "career_profile": self.profile.pk,
            "name": "AWS Certified Developer",
            "issuing_organization": "Amazon Web Services",
            "issue_date": "2022-05-01",
            "expiration_date": "2025-05-01",
            "credential_id": "AWS-123",
            "credential_url": "https://example.com/cert/aws-123",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Certification.objects.count(), 1)

    def test_project_endpoint_create_and_list(self):
        url = reverse("project-list")
        payload = {
            "career_profile": self.profile.pk,
            "name": "Career Intelligence",
            "description": "Built a job matching platform.",
            "role": "Lead Engineer",
            "project_url": "https://example.com/projects/career-intelligence",
            "repository_url": "https://github.com/example/career-intelligence",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "skills_used": [],
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 1)
