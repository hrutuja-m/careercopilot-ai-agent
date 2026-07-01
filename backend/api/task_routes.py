from fastapi import APIRouter
from services.task_priority_engine import generate_priority_tasks
from services.email_scraper import extract_jobs_from_emails
from services.job_api_client import fetch_sample_api_jobs

router = APIRouter()


demo_resume = {
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


demo_jobs = [
    {
        "id": 1,
        "title": "AI Agent Engineer Intern",
        "company": "DEEP Measures",
        "location": "Cambridge, MA",
        "required_skills": ["python", "llm", "fastapi", "rag", "api", "prompt engineering"],
        "description": "Build AI agents, workflows, and enterprise automation tools.",
        "deadline_days": 2,
        "status": "saved",
        "user_interest": 5,
    },
    {
        "id": 2,
        "title": "Data Analyst Intern",
        "company": "HealthTech Labs",
        "location": "Boston, MA",
        "required_skills": ["sql", "python", "tableau", "excel"],
        "description": "Analyze healthcare data and build dashboards.",
        "deadline_days": 8,
        "status": "saved",
        "user_interest": 3,
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
    },
]


@router.get("/")
def get_priority_tasks():
    email_jobs = extract_jobs_from_emails()
    api_jobs = fetch_sample_api_jobs()

    all_jobs = demo_jobs + email_jobs + api_jobs

    tasks = generate_priority_tasks(demo_resume, all_jobs)

    return {
        "message": "Priority tasks generated successfully",
        "total_jobs_analyzed": len(all_jobs),
        "tasks": tasks,
    }