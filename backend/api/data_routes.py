from fastapi import APIRouter
from database.jobs_store import get_all_jobs

router = APIRouter()


@router.get("/combined-jobs")
def get_combined_jobs():
    jobs = get_all_jobs()

    sources = {}
    for job in jobs:
        src = job.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    return {
        "message": "Combined jobs loaded successfully",
        "total_jobs": len(jobs),
        "sources": sources,
        "jobs": jobs,
    }
