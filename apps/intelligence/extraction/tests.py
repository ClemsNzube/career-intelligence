from django.test import TestCase

from apps.intelligence.extraction.services import extract_job_data
from apps.skills.models import Skill


class JobDescriptionExtractionTests(TestCase):
    def setUp(self):
        self.skills = {
            name: Skill.objects.create(name=name, slug=name.lower().replace(" ", "-"))
            for name in ("Python", "Django", "PostgreSQL", "Docker")
        }

    def test_extracts_skills_experience_title_and_work_type(self):
        description = (
            "We are looking for a Python Developer with 3+ years of experience. "
            "Strong knowledge of Django, PostgreSQL and Docker is required. "
            "This is a fully remote position."
        )

        extracted = extract_job_data(description)

        self.assertEqual(extracted["title"], "Python Developer")
        self.assertEqual(extracted["skills"], ["Python", "Django", "PostgreSQL", "Docker"])
        self.assertEqual(extracted["min_years_experience"], 3)
        self.assertEqual(extracted["work_type"], "remote")

    def test_extracts_years_from_minimum_and_at_least_phrases(self):
        for description, expected in (
            ("Minimum 2 years of experience required.", 2),
            ("At least 5 years' experience is preferred.", 5),
        ):
            with self.subTest(description=description):
                self.assertEqual(extract_job_data(description)["min_years_experience"], expected)

    def test_extracts_education_and_responsibility_bullets(self):
        description = """Education:
Bachelor's degree in Computer Science or MSc preferred.

Responsibilities:
- Build REST APIs
- Maintain backend services

Requirements:
- 3+ years of experience
"""

        extracted = extract_job_data(description)

        self.assertEqual(extracted["education"], ["Bachelor's degree", "MSc"])
        self.assertEqual(
            extracted["responsibilities"],
            ["Build REST APIs", "Maintain backend services"],
        )

    def test_extracts_education_abbreviations_and_work_type_variants(self):
        extracted_education = extract_job_data("BSc or Master's degree required; MSc also accepted.")
        self.assertEqual(extracted_education["education"], ["BSc", "Master's degree", "MSc"])

        for phrase, expected in (("hybrid role", "hybrid"), ("on-site position", "onsite"), ("onsite role", "onsite")):
            with self.subTest(phrase=phrase):
                self.assertEqual(extract_job_data(phrase)["work_type"], expected)

    def test_missing_information_returns_empty_values(self):
        extracted = extract_job_data("A great opportunity to join our growing team.")

        self.assertEqual(extracted, {
            "title": None,
            "skills": [],
            "min_years_experience": None,
            "work_type": None,
            "education": [],
            "responsibilities": [],
        })

    def test_skill_matching_uses_word_boundaries(self):
        extracted = extract_job_data("We are looking for someone with ongoing project experience.")

        self.assertEqual(extracted["skills"], [])