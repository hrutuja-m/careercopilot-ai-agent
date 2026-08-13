from fastapi import APIRouter, HTTPException

from services.gmail_auth import get_gmail_service
from services.gmail_handshake_scraper import (
    fetch_handshake_emails,
    extract_jobs_from_gmail_emails,
)
from services.gmail_labels import label_job_applied
from services.recommendation_engine import recommend_jobs
from services.task_priority_engine import generate_priority_tasks
from services.profile_store import get_profile
from database.jobs_store import merge_jobs_detailed
from config.settings import GMAIL_LOOKBACK_DAYS, GMAIL_MAX_RESULTS, USER_EMAIL

router = APIRouter()


def _assert_expected_gmail_account(service):
    profile = service.users().getProfile(userId="me").execute()
    actual = (profile.get("emailAddress") or "").lower()
    expected = (USER_EMAIL or "").lower()
    if expected and actual and actual != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Connected Gmail is {actual}, but CareerCopilot is configured for {expected}. Delete token_gmail.json and reconnect with the correct account.",
        )
    return profile


@router.get("/profile")
def get_gmail_profile():
    service = get_gmail_service()

    profile = _assert_expected_gmail_account(service)

    return {
        "message": "Gmail connected successfully",
        "email": profile.get("emailAddress"),
        "expected_email": USER_EMAIL,
        "total_messages": profile.get("messagesTotal"),
    }


@router.get("/status")
def get_gmail_status():
    try:
        service = get_gmail_service(allow_interactive=False)
        profile = _assert_expected_gmail_account(service)
    except HTTPException as exc:
        return {
            "connected": False,
            "error": exc.detail,
            "expected_email": USER_EMAIL,
        }
    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
            "expected_email": USER_EMAIL,
        }

    return {
        "connected": True,
        "email": profile.get("emailAddress"),
        "expected_email": USER_EMAIL,
        "total_messages": profile.get("messagesTotal"),
    }


@router.get("/handshake-emails")
def get_handshake_emails(
    max_results: int = GMAIL_MAX_RESULTS,
    lookback_days: int = GMAIL_LOOKBACK_DAYS,
):
    emails = fetch_handshake_emails(max_results=max_results, lookback_days=lookback_days)

    return {
        "message": "Handshake emails fetched from Gmail successfully",
        "total_emails": len(emails),
        "emails": emails,
    }


@router.get("/handshake-jobs")
def get_handshake_jobs(
    max_results: int = GMAIL_MAX_RESULTS,
    lookback_days: int = GMAIL_LOOKBACK_DAYS,
):
    result = extract_jobs_from_gmail_emails(
        max_results=max_results,
        lookback_days=lookback_days,
    )

    return {
        "message": "Handshake jobs extracted from Gmail successfully",
        "summary": result["summary"],
        "jobs": result["jobs"],
    }


@router.post("/sync")
def sync_gmail_jobs(
    max_results: int = GMAIL_MAX_RESULTS,
    lookback_days: int = GMAIL_LOOKBACK_DAYS,
):
    service = get_gmail_service()
    gmail_profile = _assert_expected_gmail_account(service)
    result = extract_jobs_from_gmail_emails(
        max_results=max_results,
        lookback_days=lookback_days,
        service=service,
    )

    # Persist newly-found jobs into the tracker so they show up in
    # /jobs/, /tasks/, and /data/combined-jobs on subsequent calls.
    # Existing tracked jobs keep their user-set status unless Gmail contains
    # an application-confirmation message for that opportunity.
    merge_result = merge_jobs_detailed(result["jobs"])
    label_results = [
        label_job_applied(job, service=service)
        for job in result["jobs"]
        if job.get("status") == "applied"
    ]
    jobs_preview = [
        {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "apply_url": job.get("apply_url"),
            "has_real_apply_url": job.get("has_real_apply_url"),
        }
        for job in result["jobs"][:5]
    ]

    return {
        "message": "Gmail synced successfully",
        "email": gmail_profile.get("emailAddress"),
        "expected_email": USER_EMAIL,
        "total_messages": gmail_profile.get("messagesTotal"),
        "summary": result["summary"],
        "newly_added_to_tracker": merge_result["added"],
        "statuses_updated_to_applied": merge_result["status_updated"],
        "gmail_labels_applied": sum(1 for item in label_results if item.get("labeled")),
        "jobs_preview": jobs_preview,
    }


@router.get("/recommendations")
def get_gmail_recommendations(max_results: int = GMAIL_MAX_RESULTS):
    result = extract_jobs_from_gmail_emails(max_results=max_results)
    jobs = result["jobs"]

    recommendations = recommend_jobs(get_profile(), jobs)

    return {
        "message": "Gmail-based recommendations generated successfully",
        "summary": result["summary"],
        "top_5_recommendations": recommendations[:5],
    }


@router.get("/priority-tasks")
def get_gmail_priority_tasks(max_results: int = GMAIL_MAX_RESULTS):
    result = extract_jobs_from_gmail_emails(max_results=max_results)
    jobs = result["jobs"]

    tasks = generate_priority_tasks(get_profile(), jobs)

    return {
        "message": "Gmail-based priority tasks generated successfully",
        "summary": result["summary"],
        "top_5_tasks": tasks[:5],
    }
