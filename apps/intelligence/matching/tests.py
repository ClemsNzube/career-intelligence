from unittest.mock import patch

from django.test import SimpleTestCase

from apps.intelligence.matching.hybrid import hybrid_match


class HybridMatchingTests(SimpleTestCase):
    def score_with(self, rule_score, semantic_score):
        with (
            patch(
                "apps.intelligence.matching.hybrid.match_job_to_profile",
                return_value={"score": rule_score},
            ),
            patch(
                "apps.intelligence.matching.hybrid.similarity_for_objects",
                return_value=semantic_score,
            ),
        ):
            return hybrid_match(profile=object(), job=object())

    def test_strong_rule_and_semantic_scores_produce_a_very_high_score(self):
        result = self.score_with(rule_score=0.9, semantic_score=0.95)

        self.assertAlmostEqual(result["final_score"], 0.92)
        self.assertGreater(result["final_score"], 0.9)

    def test_strong_rule_and_weak_semantic_scores_produce_moderate_high_score(self):
        result = self.score_with(rule_score=0.9, semantic_score=0.2)

        self.assertAlmostEqual(result["final_score"], 0.62)

    def test_weak_rule_and_strong_semantic_scores_produce_moderate_score(self):
        result = self.score_with(rule_score=0.2, semantic_score=0.9)

        self.assertAlmostEqual(result["final_score"], 0.48)

    def test_weak_rule_and_weak_semantic_scores_produce_low_score(self):
        result = self.score_with(rule_score=0.2, semantic_score=0.1)

        self.assertAlmostEqual(result["final_score"], 0.16)

    def test_final_score_is_bounded_when_cosine_similarity_is_negative(self):
        result = self.score_with(rule_score=0.0, semantic_score=-0.8)

        self.assertEqual(result["semantic_score"], 0.0)
        self.assertGreaterEqual(result["final_score"], 0.0)
        self.assertLessEqual(result["final_score"], 1.0)

    def test_result_includes_the_blend_weights_and_component_scores(self):
        result = self.score_with(rule_score=0.82, semantic_score=0.94)

        self.assertEqual(result["rule_score"], 0.82)
        self.assertEqual(result["semantic_score"], 0.94)
        self.assertAlmostEqual(result["final_score"], 0.868)
        self.assertEqual(result["weights"], {"rule": 0.6, "semantic": 0.4})

    def test_result_preserves_rule_component_scores_for_explanations(self):
        component_scores = {
            "score": 0.82,
            "skill": 0.75,
            "experience": 1.0,
            "work_type": 1.0,
            "location": 0.5,
            "title": 0.6,
        }
        with patch(
            "apps.intelligence.matching.hybrid.match_job_to_profile",
            return_value=component_scores,
        ):
            with patch(
                "apps.intelligence.matching.hybrid.similarity_for_objects",
                return_value=0.94,
            ):
                result = hybrid_match(profile=object(), job=object())

        self.assertEqual(
            result["rule_details"],
            {
                "skill": 0.75,
                "experience": 1.0,
                "work_type": 1.0,
                "location": 0.5,
                "title": 0.6,
            },
        )

    def test_out_of_range_rule_score_is_rejected(self):
        with patch(
            "apps.intelligence.matching.hybrid.match_job_to_profile",
            return_value={"score": 1.1},
        ):
            with patch("apps.intelligence.matching.hybrid.similarity_for_objects", return_value=0.5):
                with self.assertRaises(ValueError):
                    hybrid_match(profile=object(), job=object())
