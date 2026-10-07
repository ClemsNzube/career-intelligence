from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.intelligence.embeddings.providers.fastembed import FastEmbedProvider
from apps.intelligence.embeddings.services import EmbeddingService
from apps.intelligence.similarity.services import calculate_similarity, similarity_for_objects
from apps.jobs.models import Job
from apps.users.models import CareerProfile


class SemanticSimilarityTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="similarity-user",
            email="similarity@example.com",
            password="secret123",
        )
        self.profile = CareerProfile.objects.create(
            user=user,
            related_name="Backend Engineer",
            bio="Backend Python Engineer with Django, PostgreSQL and REST APIs.",
            year_of_experience=5,
        )
        self.service = EmbeddingService(provider=FastEmbedProvider())

        self.profile_text = "Backend Python Engineer with Django, PostgreSQL and REST APIs."
        self.job_a_text = "Python Backend Developer working with Django, PostgreSQL and REST APIs."
        self.job_b_text = "Frontend React Developer working with TypeScript, Next.js and CSS."

        self.service.save_for_object(self.profile, self.profile_text)

        self.job_a = Job.objects.create(
            title="Python Backend Developer",
            company_name="Example Corp",
            description="We build Django services with PostgreSQL and REST APIs.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/python-backend",
        )
        self.service.save_for_object(self.job_a, self.job_a_text)

        self.job_b = Job.objects.create(
            title="Frontend React Developer",
            company_name="Another Corp",
            description="We build TypeScript apps with Next.js and CSS.",
            location="Remote",
            work_type="remote",
            employment_type="full_time",
            application_url="https://example.com/jobs/frontend-react",
        )
        self.service.save_for_object(self.job_b, self.job_b_text)

    def test_related_jobs_have_higher_similarity_than_unrelated_jobs(self):
        profile_to_job_a = similarity_for_objects(self.profile, self.job_a)
        profile_to_job_b = similarity_for_objects(self.profile, self.job_b)

        self.assertGreater(profile_to_job_a, 0.5)
        self.assertLess(profile_to_job_b, profile_to_job_a)

    def test_identical_text_has_similarity_close_to_one(self):
        score = calculate_similarity(
            self.service.embed(self.profile_text),
            self.service.embed(self.profile_text),
        )

        self.assertAlmostEqual(score, 1.0, places=3)

    def test_unrelated_vectors_have_low_similarity(self):
        score = calculate_similarity(
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        )

        self.assertLess(score, 0.5)
        self.assertGreaterEqual(score, -1.0)

    def test_missing_embedding_raises_value_error(self):
        orphan_profile = CareerProfile.objects.create(
            user=get_user_model().objects.create_user(
                username="orphan-profile",
                email="orphan@example.com",
                password="secret123",
            ),
            related_name="Designer",
            bio="Designs UI systems.",
            year_of_experience=2,
        )

        with self.assertRaises(ValueError):
            similarity_for_objects(orphan_profile, self.job_a)

    def test_zero_or_invalid_vectors_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_similarity([0.0, 0.0], [1.0, 0.0])

        with self.assertRaises(ValueError):
            calculate_similarity([1.0, float("nan")], [1.0, 0.0])

    def test_similarity_stays_in_expected_range(self):
        score = similarity_for_objects(self.profile, self.job_a)
        self.assertGreaterEqual(score, -1.0)
        self.assertLessEqual(score, 1.0)
