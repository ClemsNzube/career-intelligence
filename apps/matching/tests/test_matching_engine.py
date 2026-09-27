from django.test import SimpleTestCase

from apps.matching.services.match_job_to_profile import match_job_to_profile


class JobProfileMatchingEngineTests(SimpleTestCase):
    def test_matching_engine_returns_high_score_for_good_fit(self):
        profile = {
            "title": "Senior Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "years_of_experience": 5,
            "skills": ["Python", "Django", "PostgreSQL"],
        }
        job = {
            "title": "Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "min_years_experience": 3,
            "skills": ["Python", "Django"],
        }

        result = match_job_to_profile(profile, job)

        self.assertGreater(result["total"], 0.8)
        self.assertTrue(result["match"])
        self.assertEqual(result["explanation"]["overall"]["matched"], True)
        self.assertIn("skill", result["explanation"]["components"][0]["name"])

    def test_matching_engine_returns_low_score_for_poor_fit(self):
        profile = {
            "title": "Frontend Engineer",
            "location": "New York",
            "work_type": "onsite",
            "years_of_experience": 1,
            "skills": ["JavaScript", "React"],
        }
        job = {
            "title": "Senior Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "min_years_experience": 5,
            "skills": ["Python", "Django", "PostgreSQL"],
        }

        result = match_job_to_profile(profile, job)

        self.assertLess(result["total"], 0.5)
        self.assertFalse(result["match"])
        self.assertIn("overall", result["explanation"])
        self.assertEqual(len(result["explanation"]["components"]), 5)

    def test_matching_engine_supports_custom_weight_configuration(self):
        profile = {
            "title": "Senior Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "years_of_experience": 5,
            "skills": ["Python", "Django"],
        }
        job = {
            "title": "Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "min_years_experience": 3,
            "skills": ["Python", "Django"],
        }

        result = match_job_to_profile(profile, job, weights={"skill": 0.5, "experience": 0.2, "title": 0.3})

        self.assertEqual(result["weights"]["skill"], 0.5)
        self.assertEqual(result["weights"]["experience"], 0.2)
        self.assertEqual(result["weights"]["title"], 0.3)
        self.assertIn("weighted_score", result)
        self.assertTrue(result["match"])

    def test_matching_engine_handles_zero_skill_overlap_and_no_title_preference(self):
        profile = {
            "title": "",
            "location": "Remote",
            "work_type": "remote",
            "years_of_experience": 7,
            "skills": ["JavaScript", "React"],
        }
        job = {
            "title": "Senior Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "min_years_experience": 5,
            "skills": ["Python", "Django"],
        }

        result = match_job_to_profile(profile, job)

        self.assertEqual(result["title"], 1.0)
        self.assertEqual(result["explanation"]["components"][4]["reason"], "No preferred job title was specified.")
        self.assertIn("none", result["explanation"]["components"][0]["reason"])

    def test_matching_engine_does_not_penalize_remote_jobs_when_remote_is_preferred(self):
        profile = {
            "title": "Python Engineer",
            "location": ["Remote"],
            "work_type": "remote",
            "years_of_experience": 3,
            "skills": ["Python"],
        }
        job = {
            "title": "Python Developer",
            "location": "Remote",
            "work_type": "remote",
            "min_years_experience": 1,
            "skills": ["Python"],
        }

        result = match_job_to_profile(profile, job)

        self.assertEqual(result["location"], 1.0)
        self.assertTrue(result["match"])
