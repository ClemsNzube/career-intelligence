from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import (
    CareerPreferences,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Project,
)

User = get_user_model()


class CareerProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        self.profile = CareerProfile.objects.create(
            user=self.user,
            related_name="Software Engineer",
            bio="Builds platform services.",
            year_of_experience=5,
            preferred_locations=["Remote", "New York"],
            preferred_work_type="remote",
        )

    def test_profile_can_have_preferences(self):
        preferences = CareerPreferences.objects.create(
            career_profile=self.profile,
            target_job_titles=["Senior Python Developer", "Platform Engineer"],
            target_industries=["SaaS", "FinTech"],
            preferred_locations=["Remote", "London"],
            preferred_work_types=["remote", "hybrid"],
            min_years_of_experience=3,
            max_years_of_experience=8,
        )

        self.assertEqual(preferences.career_profile, self.profile)
        self.assertEqual(self.profile.preferences, preferences)

    def test_profile_can_have_multiple_education_records(self):
        Education.objects.create(
            career_profile=self.profile,
            institution="University of Michigan",
            degree="B.S.",
            field_of_study="Computer Science",
            start_date=date(2014, 9, 1),
            end_date=date(2018, 5, 1),
            description="Studied systems and software engineering.",
        )
        Education.objects.create(
            career_profile=self.profile,
            institution="University of Washington",
            degree="M.S.",
            field_of_study="Data Science",
            start_date=date(2018, 9, 1),
            currently_studying=True,
            description="Researching ML systems.",
        )

        self.assertEqual(self.profile.education_records.count(), 2)

    def test_profile_can_have_multiple_work_experiences(self):
        first = Experience.objects.create(
            career_profile=self.profile,
            job_title="Backend Engineer",
            company="Example Corp",
            employment_type="full_time",
            location="Remote",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
            description="Built APIs and services.",
        )
        second = Experience.objects.create(
            career_profile=self.profile,
            job_title="Senior Platform Engineer",
            company="Launch Labs",
            employment_type="full_time",
            location="New York",
            start_date=date(2023, 1, 1),
            currently_working=True,
            description="Designed deployment platform.",
        )

        self.assertEqual(self.profile.work_experiences.count(), 2)
        self.assertIn(first, self.profile.work_experiences.all())
        self.assertIn(second, self.profile.work_experiences.all())

    def test_profile_can_have_multiple_certifications(self):
        cert_1 = Certification.objects.create(
            career_profile=self.profile,
            name="AWS Certified Developer - Associate",
            issuing_organization="Amazon Web Services",
            issue_date=date(2022, 5, 1),
            expiration_date=date(2025, 5, 1),
            credential_id="AWS-12345",
            credential_url="https://example.com/certs/aws-12345",
        )
        cert_2 = Certification.objects.create(
            career_profile=self.profile,
            name="CKAD",
            issuing_organization="The Linux Foundation",
            issue_date=date(2023, 9, 1),
            credential_id="CKAD-987",
            credential_url="https://example.com/certs/ckad-987",
        )

        self.assertEqual(self.profile.certifications.count(), 2)
        self.assertIn(cert_1, self.profile.certifications.all())
        self.assertIn(cert_2, self.profile.certifications.all())

    def test_profile_can_have_multiple_projects(self):
        project_1 = Project.objects.create(
            career_profile=self.profile,
            name="Career Intelligence API",
            description="Built a platform to match jobs and users.",
            role="Lead Engineer",
            project_url="https://example.com/projects/career-intelligence",
            repository_url="https://github.com/example/career-intelligence",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )
        project_2 = Project.objects.create(
            career_profile=self.profile,
            name="Skill Graph Explorer",
            description="Created a visualization for skill clusters.",
            role="Backend Developer",
            project_url="https://example.com/projects/skill-graph",
            repository_url="https://github.com/example/skill-graph",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 12, 1),
        )

        self.assertEqual(self.profile.projects.count(), 2)
        self.assertIn(project_1, self.profile.projects.all())
        self.assertIn(project_2, self.profile.projects.all())
