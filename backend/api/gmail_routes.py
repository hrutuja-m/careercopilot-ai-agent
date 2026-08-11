from fastapi import APIRouter, HTTPException

from api.task_routes import demo_resume
from database.db import database_summary, list_jobs, update_job_status
from models.schemas import ApplicationStatusUpdate
from services.application_tracker import get_next_tracker_action, normalize_status
from services.gmail_auth import get_gmail_service
from services.gmail_handshake_scraper import (
    extract_jobs_from_gmail_emails,
    fetch_handshake_emails,
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


@router.post("/sync-handshake-jobs")
def sync_handshake_jobs(max_results: int = 50):
    result = extract_jobs_from_gmail_emails(max_results=max_results, save_to_database=True)
    return {
        "message": "Handshake jobs synced to SQLite successfully",
        "summary": result["summary"],
        "database": database_summary(),
    }


@router.get("/stored-handshake-jobs")
def get_stored_handshake_jobs(limit: int | None = None):
    jobs = list_jobs(limit=limit)
    return {
        "message": "Stored Handshake jobs loaded successfully",
        "total_jobs": len(jobs),
        "jobs": jobs,
    }


@router.patch("/stored-handshake-jobs/{job_id}/status")
def update_stored_handshake_job_status(job_id: int, request: ApplicationStatusUpdate):
    status = normalize_status(request.status)
    updated = update_job_status(job_id, status)

    if not updated:
        raise HTTPException(status_code=404, detail="Stored job not found")

    return {
        "message": "Application status updated successfully",
        "job_id": job_id,
        "application_status": status,
        "next_action": get_next_tracker_action(status),
    }


@router.get("/database-summary")
def get_database_summary():
    return database_summary()


@router.get("/handshake-jobs")
def get_handshake_jobs(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results, save_to_database=True)
    return {
        "message": "Handshake jobs extracted from Gmail successfully",
        "summary": result["summary"],
        "jobs": result["jobs"],
    }


@router.get("/recommendations")
def get_gmail_recommendations(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results, save_to_database=True)
    recommendations = recommend_jobs(demo_resume, result["jobs"])
    return {
        "message": "Gmail-based recommendations generated successfully",
        "summary": result["summary"],
        "top_5_recommendations": recommendations[:5],
    }


@router.get("/priority-tasks")
def get_gmail_priority_tasks(max_results: int = 20):
    result = extract_jobs_from_gmail_emails(max_results=max_results, save_to_database=True)
    tasks = generate_priority_tasks(demo_resume, result["jobs"])
    return {
        "message": "Gmail-based priority tasks generated successfully",
        "summary": result["summary"],
        "top_5_tasks": tasks[:5],
    }
