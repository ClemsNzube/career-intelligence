from django.test import TestCase

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