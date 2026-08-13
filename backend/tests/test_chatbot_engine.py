import unittest

from services.chatbot_engine import career_chatbot_response, retrieve_relevant_context


RESUME = {
    "name": "Rutuja",
    "target_roles": ["Data Analyst", "AI Engineer"],
    "skills": ["python", "sql", "machine learning"],
}

JOBS = [
    {
        "id": 1,
        "title": "Transit Data Analyst",
        "company": "Green Mountain Transit",
        "location": "Burlington, VT",
        "required_skills": ["sql", "tableau"],
        "description": "Analyze transit ridership data and publish operational dashboards.",
        "deadline_days": 5,
        "status": "not_applied",
        "user_interest": 4,
        "apply_url": "https://app.joinhandshake.com/job-search/1",
        "has_real_apply_url": True,
    },
    {
        "id": 2,
        "title": "AI Engineer",
        "company": "Schneider",
        "location": "Remote",
        "required_skills": ["python", "machine learning"],
        "description": "Build AI workflows for logistics automation.",
        "deadline_days": 10,
        "status": "applied",
        "user_interest": 5,
        "apply_url": "https://app.joinhandshake.com/job-search/2",
        "has_real_apply_url": True,
    },
]

TASKS = [
    {
        "job_id": 1,
        "task_title": "Apply to Transit Data Analyst",
        "priority": "Do Today",
        "reason": "Strong SQL and analytics match with an urgent deadline.",
        "suggested_action": "Tailor your resume around dashboard and ridership analytics work.",
        "deadline_days": 5,
        "match_score": 82,
        "missing_skills": ["tableau"],
    },
    {
        "job_id": 2,
        "task_title": "Follow up with Schneider",
        "priority": "Follow Up",
        "reason": "Already applied to a strong AI workflow role.",
        "suggested_action": "Send a concise follow-up.",
        "deadline_days": 10,
        "match_score": 91,
        "missing_skills": [],
    },
]


class ChatbotRetrievalTest(unittest.TestCase):
    def test_retrieves_relevant_job_context_for_query(self):
        context = retrieve_relevant_context(
            "Which role uses ridership dashboards?",
            RESUME,
            JOBS,
            TASKS,
        )

        self.assertGreaterEqual(len(context), 1)
        self.assertEqual(context[0]["type"], "job")
        self.assertEqual(context[0]["job_id"], 1)

    def test_response_includes_retrieved_context_and_evidence_section(self):
        response = career_chatbot_response(
            "Tell me about the ridership dashboard role",
            RESUME,
            JOBS,
            goals={"daily_application_goal": 2},
        )

        self.assertTrue(response["retrieved_context"])
        self.assertEqual(response["jobs"][0]["job_id"], 1)
        self.assertTrue(
            any(section["title"] == "Evidence used" for section in response["sections"])
        )


if __name__ == "__main__":
    unittest.main()
