from fastapi import APIRouter

from api.task_routes import demo_resume
from services.gmail_auth import get_gmail_service
from services.gmail_handshake_scraper import (
    fetch_handshake_emails,
    extract_jobs_from_gmail_emails,
)
from services.recommendation_engine import recommend_jobs
from services.task_priority_engine import generate_priority_tasks

router = APIRouter()


@router.get("/profile")
def get_gmail_profile():
    service = get_gmail_service()

    profile = service.users().getProfile(userId="me").execute()

    return {
        "message": "Gmail connected successfully",
        "email": profile.get("emailAddress"),
        "total_messages": profile.get("messagesTotal"),
    }


@router.get("/handshake-emails")
def get_handshake_emails(max_results: int = 20):
    emails = fetch_handshake_emails(max_results=max_results)

    return {
        "message": "Handshake emails fetched from Gmail successfully",
        "total_emails": len(emails),
        "emails": emails,
    }


@router.get("/handshake-jobs")
def get_handshake_jobs(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results)

    return {
        "message": "Handshake jobs extracted from Gmail successfully",
        "summary": result["summary"],
        "jobs": result["jobs"],
    }


@router.get("/recommendations")
def get_gmail_recommendations(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results)
    jobs = result["jobs"]

    recommendations = recommend_jobs(demo_resume, jobs)

    return {
        "message": "Gmail-based recommendations generated successfully",
        "summary": result["summary"],
        "top_5_recommendations": recommendations[:5],
    }


@router.get("/priority-tasks")
def get_gmail_priority_tasks(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results)
    jobs = result["jobs"]

    tasks = generate_priority_tasks(demo_resume, jobs)

    return {
        "message": "Gmail-based priority tasks generated successfully",
        "summary": result["summary"],
        "top_5_tasks": tasks[:5],
    }