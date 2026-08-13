from fastapi import APIRouter, HTTPException
from database.jobs_store import get_all_jobs, get_job, update_job_status, VALID_STATUSES
from models.schemas import JobStatusUpdate
from services.gmail_labels import label_job_applied

router = APIRouter()


@router.get("/")
def get_jobs():
    return {
        "message": "Jobs loaded successfully",
        "jobs": get_all_jobs(),
    }


@router.get("/{job_id}")
def get_single_job(job_id: int):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "message": "Job loaded successfully",
        "job": job,
    }


@router.patch("/{job_id}")
def patch_job_status(job_id: int, payload: JobStatusUpdate):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {VALID_STATUSES}",
        )

    job = update_job_status(job_id, payload.status)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    gmail_label = label_job_applied(job) if job.get("status") == "applied" else None

    return {
        "message": "Job status updated successfully",
        "job": job,
        "gmail_label": gmail_label,
    }


@router.post("/{job_id}/apply")
def apply_to_job(job_id: int):
    """Convenience endpoint for the "Easy Apply" button: equivalent to
    PATCHing status to "applied", but doesn't require the caller to build
    a request body."""
    job = update_job_status(job_id, "applied")

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    gmail_label = label_job_applied(job)

    return {
        "message": "Marked as applied",
        "job": job,
        "gmail_label": gmail_label,
    }
