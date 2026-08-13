import unittest
from datetime import date

from services.task_priority_engine import (
    assign_priority,
    calculate_job_match_score,
    effective_deadline_days,
    explain_job_match,
    generate_priority_tasks,
)


class TaskPriorityEngineTest(unittest.TestCase):
    def test_not_applied_due_this_week_is_do_today(self):
        self.assertEqual(
            assign_priority(
                match_score=0,
                deadline_days=7,
                user_interest=4,
                status="not_applied",
            ),
            "Do Today",
        )

    def test_effective_deadline_days_uses_actual_deadline_date(self):
        self.assertEqual(
            effective_deadline_days(
                {"deadline_text": "Wednesday, August 12, 2026", "deadline_days": 3},
                today=date(2026, 8, 13),
            ),
            -1,
        )

    def test_not_applied_do_today_sorts_before_applied_follow_up(self):
        resume = {"skills": ["python"]}
        jobs = [
            {
                "id": 1,
                "title": "Applied AI Engineer",
                "company": "Schneider",
                "required_skills": ["python"],
                "deadline_days": 7,
                "user_interest": 5,
                "status": "applied",
            },
            {
                "id": 2,
                "title": "Open Data Analyst",
                "company": "Google",
                "required_skills": [],
                "deadline_days": 7,
                "user_interest": 4,
                "status": "not_applied",
            },
        ]

        tasks = generate_priority_tasks(resume, jobs)

        self.assertEqual(tasks[0]["job_id"], 2)
        self.assertEqual(tasks[0]["priority"], "Do Today")

    def test_high_value_open_job_sorts_before_applied_follow_up(self):
        resume = {
            "skills": ["python", "sql", "machine learning", "data science"],
            "target_roles": ["Data Scientist"],
        }
        jobs = [
            {
                "id": 1,
                "title": "Applied AI Engineer",
                "company": "Schneider",
                "required_skills": ["python"],
                "deadline_days": 7,
                "user_interest": 5,
                "status": "applied",
            },
            {
                "id": 2,
                "title": "Data Scientist",
                "company": "Open Lab",
                "required_skills": ["python", "sql", "machine learning", "data science"],
                "deadline_days": 45,
                "user_interest": 5,
                "status": "not_applied",
                "apply_url": "https://app.joinhandshake.com/job-search/2",
                "has_real_apply_url": True,
            },
        ]

        tasks = generate_priority_tasks(resume, jobs)

        self.assertEqual(tasks[0]["job_id"], 2)
        self.assertEqual(tasks[0]["priority"], "High Value")

    def test_scores_title_context_when_required_skills_are_missing(self):
        resume = {
            "skills": ["python", "sql", "machine learning", "data science"],
            "target_roles": ["Data Scientist"],
        }
        job = {
            "title": "New Data Scientist",
            "company": "Health Agency",
            "description": "Applications are due soon.",
            "required_skills": [],
        }

        self.assertGreaterEqual(calculate_job_match_score(resume, job), 70)

    def test_score_breakdown_explains_component_weights(self):
        resume = {
            "skills": ["python", "sql", "machine learning", "llm"],
            "target_roles": ["AI Engineer", "Data Scientist"],
            "experience_keywords": ["model evaluation", "cloud"],
        }
        job = {
            "title": "AI Engineer",
            "company": "BeaconFire",
            "location": "Remote",
            "description": "Build LLM features with Python and model evaluation.",
            "required_skills": ["python", "llm", "aws"],
            "deadline_days": 4,
            "user_interest": 4,
            "status": "not_applied",
            "apply_url": "https://app.joinhandshake.com/job-search/123",
            "has_real_apply_url": True,
        }

        breakdown = explain_job_match(resume, job)

        self.assertIn("score", breakdown)
        self.assertIn("summary", breakdown)
        self.assertEqual(sum(component["weight"] for component in breakdown["components"]), 100)
        self.assertIn("python", breakdown["matched_skills"])
        self.assertIn("aws", breakdown["missing_skills"])

    def test_priority_uses_status_without_auto_applying_job(self):
        resume = {"skills": ["python"], "target_roles": ["AI Engineer"]}
        jobs = [
            {
                "id": 3,
                "title": "AI Engineer",
                "company": "Acme",
                "required_skills": ["python"],
                "deadline_days": 2,
                "user_interest": 4,
                "status": "not_applied",
                "apply_url": "https://app.joinhandshake.com/job-search/3",
                "has_real_apply_url": True,
            }
        ]

        tasks = generate_priority_tasks(resume, jobs)

        self.assertEqual(jobs[0]["status"], "not_applied")
        self.assertEqual(tasks[0]["priority"], "Do Today")
        self.assertNotIn("status", tasks[0])


if __name__ == "__main__":
    unittest.main()
