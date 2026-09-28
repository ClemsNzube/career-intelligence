from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.intelligence.embeddings.services import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    build_job_text,
    build_profile_text,
    generate_embedding,
    similarity,
)
from apps.jobs.models import Job
from apps.skills.models import Skill
from apps.users.models import CareerProfile, Experience, Project


class FixedEmbeddingProvider:
    def __init__(self, vector):
        self.vector = vector
        self.received_text = None

    def embed(self, text):
        self.received_text = text
        return self.vector


class EmbeddingServiceTests(TestCase):
    def test_generates_embedding_through_injected_provider(self):
        provider = FixedEmbeddingProvider((0.25, 0.75))

        vector = generate_embedding("Backend Python Engineer", provider=provider)

        self.assertEqual(vector, [0.25, 0.75])
        self.assertEqual(provider.received_text, "Backend Python Engineer")
        self.assertEqual(DEFAULT_EMBEDDING_MODEL, "BAAI/bge-small-en-v1.5")
        self.assertEqual(DEFAULT_EMBEDDING_DIMENSIONS, 384)

    def test_rejects_blank_text(self):
        with self.assertRaises(ValueError):
            generate_embedding("  ", provider=FixedEmbeddingProvider([]))

    def test_cosine_similarity(self):
        self.assertAlmostEqual(similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(similarity([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(similarity([1, 1], [-1, -1]), -1.0)
        self.assertEqual(similarity([0, 0], [1, 0]), 0.0)

    def test_similarity_rejects_vectors_with_different_dimensions(self):
        with self.assertRaises(ValueError):
            similarity([1, 0], [1])

    def test_job_text_contains_title_description_skills_and_responsibilities(self):
        python = Skill.objects.create(name="Python", slug="python")
        job = Job.objects.create(
            title="Backend Python Engineer",
            company_name="Example Corp",
            description="Responsibilities:\n- Build REST APIs\n- Maintain backend services",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/backend-python",
        )
        job.skills.add(python)

        text = build_job_text(job)

        self.assertIn("Backend Python Engineer", text)
        self.assertIn("Build REST APIs", text)
        self.assertIn("Maintain backend services", text)
        self.assertIn("Python", text)

    def test_profile_text_contains_headline_bio_skills_experience_and_projects(self):
        user = get_user_model().objects.create_user(username="embedding-user")
        python = Skill.objects.create(name="Python", slug="python")
        profile = CareerProfile.objects.create(
            user=user,
            related_name="Backend Engineer",
            bio="Builds Python services.",
        )
        profile.skills.add(python)
        experience = Experience.objects.create(
            career_profile=profile,
            job_title="API Engineer",
            company="Example Corp",
            description="Designed web APIs.",
        )
        experience.skills_used.add(python)
        project = Project.objects.create(
            career_profile=profile,
            name="Service Platform",
            role="Developer",
            description="Built a service platform.",
        )
        project.skills_used.add(python)

        text = build_profile_text(profile)

        for expected in (
            "Backend Engineer",
            "Builds Python services.",
            "Python",
            "API Engineer",
            "Designed web APIs.",
            "Service Platform",
            "Built a service platform.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)