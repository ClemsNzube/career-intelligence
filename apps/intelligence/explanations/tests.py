from django.test import SimpleTestCase

from apps.intelligence.explanations.services import explain_match


class MatchExplanationTests(SimpleTestCase):
    def setUp(self):
        self.profile = {
            "title": "Backend Python Engineer",
            "skills": ["python", "Django"],
            "year_of_experience": 5,
            "preferred_work_type": "remote",
            "preferred_locations": ["Remote"],
        }
        self.job = {
            "title": "Python Backend Developer",
            "skills": ["Python", "Django", "PostgreSQL"],
            "min_years_experience": 3,
            "work_type": "remote",
            "location": "Remote",
        }
        self.rule_details = {
            "skill": 2 / 3,
            "experience": 1.0,
            "work_type": 1.0,
            "location": 1.0,
            "title": 2 / 3,
        }

    def make_result(self, final_score, rule_score, semantic_score):
        return {
            "rule_score": rule_score,
            "semantic_score": semantic_score,
            "final_score": final_score,
            "weights": {"rule": 0.6, "semantic": 0.4},
            "rule_details": self.rule_details,
        }

    def test_strong_match_explains_strengths_and_skill_gap(self):
        explanation = explain_match(
            self.profile,
            self.job,
            self.make_result(final_score=0.9, rule_score=0.9, semantic_score=0.9),
        )

        self.assertEqual(explanation["summary"], "Strong match for this role.")
        self.assertEqual(explanation["recommendation"], "Apply")
        self.assertIn("Strong semantic similarity", explanation["strengths"])
        self.assertIn("Your work type preference matches", explanation["strengths"])
        self.assertIn("You meet the required experience", explanation["strengths"])
        self.assertEqual(explanation["matched_skills"], ["Python", "Django"])
        self.assertEqual(explanation["missing_skills"], ["PostgreSQL"])
        self.assertIn("You are missing 1 required skill: PostgreSQL", explanation["gaps"])

    def test_moderate_match_gets_good_band_and_consider_recommendation(self):
        explanation = explain_match(
            self.profile,
            self.job,
            self.make_result(final_score=0.65, rule_score=0.7, semantic_score=0.6),
        )

        self.assertEqual(explanation["score_band"], "Good match")
        self.assertEqual(explanation["recommendation"], "Apply")
        self.assertIn("Good semantic similarity", explanation["strengths"])

    def test_weak_match_highlights_experience_work_type_location_and_title_gaps(self):
        profile = {
            "title": "Frontend Engineer",
            "skills": ["React"],
            "year_of_experience": 1,
            "preferred_work_type": "onsite",
            "preferred_locations": ["New York"],
        }
        job = {
            "title": "Senior Python Developer",
            "skills": ["Python", "Django"],
            "min_years_experience": 5,
            "work_type": "remote",
            "location": "San Francisco",
        }
        rule_details = {
            "skill": 0.0,
            "experience": 0.2,
            "work_type": 0.0,
            "location": 0.0,
            "title": 0.0,
        }

        explanation = explain_match(
            profile,
            job,
            {
                "rule_score": 0.2,
                "semantic_score": 0.1,
                "final_score": 0.25,
                "rule_details": rule_details,
            },
        )

        self.assertEqual(explanation["summary"], "Weak match for this role.")
        self.assertEqual(explanation["recommendation"], "Look for a closer match")
        self.assertIn("Low semantic similarity", explanation["gaps"])
        self.assertIn("You are missing 2 required skills: Python, Django", explanation["gaps"])
        self.assertIn("The job's work type differs from your preference", explanation["gaps"])
        self.assertIn("The job location does not match your preference", explanation["gaps"])
        self.assertIn("The role title differs from your preference", explanation["gaps"])
        self.assertTrue(any("the role requires 5" in gap for gap in explanation["gaps"]))

    def test_score_band_boundaries_are_deterministic(self):
        cases = (
            (0.80, "Strong match"),
            (0.60, "Good match"),
            (0.40, "Partial match"),
            (0.39, "Weak match"),
        )
        for score, expected_band in cases:
            with self.subTest(score=score):
                explanation = explain_match(
                    self.profile,
                    self.job,
                    self.make_result(score, rule_score=0.5, semantic_score=0.5),
                )
                self.assertEqual(explanation["score_band"], expected_band)

    def test_invalid_final_score_is_rejected(self):
        with self.assertRaises(ValueError):
            explain_match(
                self.profile,
                self.job,
                self.make_result(final_score=1.2, rule_score=0.5, semantic_score=0.5),
            )
