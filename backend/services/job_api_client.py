def fetch_sample_api_jobs():
    """
    This simulates jobs coming from an external job API.

    Later, this file can connect to:
    - LinkedIn job scraper API
    - RapidAPI job search APIs
    - Adzuna API
    - SerpApi Google Jobs
    - company career pages
    """

    return [
        {
            "id": 201,
            "title": "AI Engineer Intern",
            "company": "Enterprise AI Labs",
            "location": "Cambridge, MA",
            "required_skills": ["python", "llm", "rag", "fastapi", "rest api"],
            "description": "Build AI assistants and workflow automation tools for internal business teams.",
            "deadline_days": 6,
            "status": "not_applied",
            "user_interest": 5,
            "source": "job_api",
            "apply_url": None,
        },
        {
            "id": 202,
            "title": "Machine Learning Engineer Intern",
            "company": "VisionEdge AI",
            "location": "Boston, MA",
            "required_skills": ["python", "machine learning", "computer vision", "deep learning"],
            "description": "Develop computer vision models and evaluate machine learning pipelines.",
            "deadline_days": 10,
            "status": "not_applied",
            "user_interest": 4,
            "source": "job_api",
            "apply_url": None,
        },
        {
            "id": 203,
            "title": "Data Science Intern",
            "company": "CloudMetrics",
            "location": "Remote",
            "required_skills": ["python", "sql", "aws", "data pipelines", "machine learning"],
            "description": "Analyze datasets, build models, and create data science workflows.",
            "deadline_days": 4,
            "status": "not_applied",
            "user_interest": 4,
            "source": "job_api",
            "apply_url": None,
        },
    ]
