from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.intelligence.embeddings.models import Embedding
from apps.intelligence.embeddings.services import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingService,
    build_job_text,
    build_profile_text,
    generate_embedding,
    similarity,
)
from apps.intelligence.embeddings.providers.fake import FakeEmbeddingProvider
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
    def test_service_uses_an_injected_provider(self):
        provider = FixedEmbeddingProvider((0.25, 0.75))

        vector = EmbeddingService(provider=provider).embed("Backend Python Engineer")

        self.assertEqual(vector, [0.25, 0.75])
        self.assertEqual(provider.received_text, "Backend Python Engineer")

    def test_generates_embedding_through_injected_provider(self):
        provider = FixedEmbeddingProvider((0.25, 0.75))

        vector = generate_embedding("Backend Python Engineer", provider=provider)

        self.assertEqual(vector, [0.25, 0.75])
        self.assertEqual(provider.received_text, "Backend Python Engineer")
        self.assertEqual(DEFAULT_EMBEDDING_MODEL, "BAAI/bge-small-en-v1.5")
        self.assertEqual(DEFAULT_EMBEDDING_DIMENSIONS, 384)

    def test_fake_provider_is_deterministic_and_has_consistent_dimensions(self):
        provider = FakeEmbeddingProvider(dimensions=16)

        first_vector = provider.embed("Backend Python Engineer")
        second_vector = provider.embed("Backend Python Engineer")

        self.assertEqual(first_vector, second_vector)
        self.assertEqual(len(first_vector), 16)

    def test_default_provider_returns_a_vector_without_loading_a_model(self):
        vector = generate_embedding("Backend Python Engineer")

        self.assertEqual(len(vector), DEFAULT_EMBEDDING_DIMENSIONS)

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


class EmbeddingPersistenceTests(TestCase):
    def test_embedding_model_can_store_metadata_and_vector(self):
        user = get_user_model().objects.create_user(username="vector-user")
        profile = CareerProfile.objects.create(
            user=user,
            related_name="Backend Engineer",
            bio="Builds Python services.",
        )

        saved = EmbeddingService(provider=FakeEmbeddingProvider(dimensions=DEFAULT_EMBEDDING_DIMENSIONS)).save_for_object(
            profile,
            "Backend Python Engineer with Django and PostgreSQL",
            model_name="fake-provider-tests",
        )

        self.assertEqual(saved.source_text, "Backend Python Engineer with Django and PostgreSQL")
        self.assertEqual(saved.model_name, "fake-provider-tests")
        self.assertEqual(len(saved.embedding), DEFAULT_EMBEDDING_DIMENSIONS)
        self.assertTrue(saved.pk)

        persisted = Embedding.objects.get(content_type__app_label="users", content_type__model="careerprofile", object_id=profile.pk)
        self.assertEqual(persisted.source_text, saved.source_text)
        self.assertEqual(len(list(persisted.embedding)), DEFAULT_EMBEDDING_DIMENSIONS)
        self.assertEqual(persisted.model_name, "fake-provider-tests")

    def test_embedding_model_updates_existing_record(self):
        user = get_user_model().objects.create_user(username="vector-update-user")
        profile = CareerProfile.objects.create(
            user=user,
            related_name="Data Engineer",
            bio="Works with data pipelines.",
        )

        service = EmbeddingService(provider=FakeEmbeddingProvider(dimensions=DEFAULT_EMBEDDING_DIMENSIONS))
        first = service.save_for_object(profile, "Python data engineering", model_name="fake-provider-tests")
        second = service.save_for_object(profile, "Updated Python data engineering", model_name="fake-provider-tests")

        self.assertEqual(Embedding.objects.filter(object_id=profile.pk).count(), 1)
        self.assertEqual(first.pk, second.pk)
        self.assertNotEqual(first.source_text, second.source_text)
        self.assertEqual(second.source_text, "Updated Python data engineering")