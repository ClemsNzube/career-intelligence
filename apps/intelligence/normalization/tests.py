from django.test import TestCase

from apps.intelligence.normalization.profile_skills import classify_profile_skills
from apps.intelligence.normalization.skills import normalize_skills
from apps.skills.models import Skill


class SkillNormalizationTests(TestCase):
    def setUp(self):
        for name in ("Python", "Django REST Framework", "PostgreSQL", "Docker"):
            Skill.objects.create(name=name, slug=name.lower().replace(" ", "-"))

    def test_matches_existing_skills_and_aliases(self):
        self.assertEqual(
            normalize_skills(["Python", "DRF", "postgres", "Docker"]),
            ["Python", "Django REST Framework", "PostgreSQL", "Docker"],
        )

    def test_normalizes_case_and_whitespace(self):
        self.assertEqual(
            normalize_skills(["  pYtHoN  ", "  dJaNgO   rEsT  "]),
            ["Python", "Django REST Framework"],
        )

    def test_removes_duplicates_after_alias_resolution(self):
        self.assertEqual(
            normalize_skills(["DRF", "Django REST", "Django REST Framework", "drf"]),
            ["Django REST Framework"],
        )

    def test_preserves_cleaned_unknown_skills(self):
        self.assertEqual(
            normalize_skills(["  Quantum   Widgets ", "Unknown Framework"]),
            ["Quantum Widgets", "Unknown Framework"],
        )

    def test_does_not_replace_alias_when_canonical_skill_is_missing(self):
        Skill.objects.filter(name="Django REST Framework").delete()

        self.assertEqual(normalize_skills(["DRF"]), ["DRF"])

    def test_profile_skill_classification_links_exact_and_known_alias_mentions(self):
        confirmed, suggestions = classify_profile_skills(
            {
                "bio": "Experienced with Python and PostgreSQL; built APIs with DRF.",
                "work_experiences": [],
                "projects": [],
                "skills": [],
            }
        )

        self.assertEqual(
            {skill.name for skill in confirmed},
            {"Python", "PostgreSQL", "Django REST Framework"},
        )
        self.assertEqual(suggestions, [])

    def test_profile_skill_classification_suggests_typos_and_negated_mentions(self):
        confirmed, suggestions = classify_profile_skills(
            {
                "bio": "Pyhton developer; no experience with Docker.",
                "work_experiences": [],
                "projects": [],
                "skills": [],
            }
        )

        self.assertEqual(confirmed, [])
        self.assertEqual(
            {skill.name for skill, _ in suggestions},
            {"Python", "Docker"},
        )

    def test_profile_skill_classification_does_not_suggest_already_linked_skills(self):
        python = Skill.objects.get(name="Python")
        confirmed, suggestions = classify_profile_skills(
            {
                "bio": "Python developer",
                "work_experiences": [],
                "projects": [],
                "skills": [python],
            }
        )

        self.assertEqual(confirmed, [])
        self.assertEqual(suggestions, [])