from fastapi import APIRouter
from api.task_routes import demo_jobs

router = APIRouter()


@router.get("/")
def get_jobs():
    return {
        "message": "Jobs loaded successfully",
        "jobs": demo_jobs,
    }