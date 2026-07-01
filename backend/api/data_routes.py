from fastapi import APIRouter
from api.task_routes import demo_jobs
from services.email_scraper import extract_jobs_from_emails
from services.job_api_client import fetch_sample_api_jobs

router = APIRouter()


@router.get("/combined-jobs")
def get_combined_jobs():
    email_jobs = extract_jobs_from_emails()
    api_jobs = fetch_sample_api_jobs()

    combined_jobs = demo_jobs + email_jobs + api_jobs

    return {
        "message": "Combined jobs loaded successfully",
        "total_jobs": len(combined_jobs),
        "sources": {
            "manual_demo_jobs": len(demo_jobs),
            "email_jobs": len(email_jobs),
            "api_jobs": len(api_jobs),
        },
        "jobs": combined_jobs,
    }