from fastapi import APIRouter
from database.jobs_store import get_all_jobs
from services.profile_store import get_profile
from services.task_priority_engine import generate_priority_tasks

router = APIRouter()


@router.get("/")
def get_priority_tasks():
    all_jobs = get_all_jobs()

    tasks = generate_priority_tasks(get_profile(), all_jobs)

    return {
        "message": "Priority tasks generated successfully",
        "total_jobs_analyzed": len(all_jobs),
        "tasks": tasks,
    }
