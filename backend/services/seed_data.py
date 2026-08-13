"""Static seed data for the demo/prototype dataset.

This module has no internal dependencies on other backend modules so it can
be safely imported by both api/task_routes.py (for backward compatibility)
and database/jobs_store.py (which seeds the persistent job store from it)
without creating an import cycle.
"""

DEMO_RESUME = {
    "name": "Rutuja More",
    "target_roles": ["AI Engineer", "Data Scientist", "Machine Learning Engineer"],
    "skills": [
        "python",
        "sql",
        "fastapi",
        "rag",
        "llm",
        "openai api",
        "faiss",
        "machine learning",
        "deep learning",
        "nlp",
        "computer vision",
        "aws",
        "data pipelines",
        "prompt engineering",
    ],
    "experience_keywords": [
        "ai agents",
        "workflow automation",
        "model evaluation",
        "resume parsing",
        "job matching",
    ],
}


# These are fictional demo companies, so they intentionally do not carry
# apply_url values. The frontend will show a search fallback instead of
# pretending an example.com URL is a real application page.
DEMO_JOBS = [
    {
        "id": 1,
        "title": "AI Agent Engineer Intern",
        "company": "DEEP Measures",
        "location": "Cambridge, MA",
        "required_skills": ["python", "llm", "fastapi", "rag", "api", "prompt engineering"],
        "description": "Build AI agents, workflows, and enterprise automation tools.",
        "deadline_days": 2,
        "status": "not_applied",
        "user_interest": 5,
        "source": "demo",
        "apply_url": None,
    },
    {
        "id": 2,
        "title": "Data Analyst Intern",
        "company": "HealthTech Labs",
        "location": "Boston, MA",
        "required_skills": ["sql", "python", "tableau", "excel"],
        "description": "Analyze healthcare data and build dashboards.",
        "deadline_days": 8,
        "status": "not_applied",
        "user_interest": 3,
        "source": "demo",
        "apply_url": None,
    },
    {
        "id": 3,
        "title": "Machine Learning Intern",
        "company": "Smart Systems AI",
        "location": "Remote",
        "required_skills": ["python", "machine learning", "deep learning", "aws"],
        "description": "Build predictive models and deploy machine learning workflows.",
        "deadline_days": 5,
        "status": "applied",
        "user_interest": 4,
        "source": "demo",
        "apply_url": None,
    },
]
