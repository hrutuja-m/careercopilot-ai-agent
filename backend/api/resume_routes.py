from fastapi import APIRouter
from api.task_routes import demo_resume

router = APIRouter()


@router.get("/")
def get_resume_profile():
    return {
        "message": "Resume profile loaded successfully",
        "resume_profile": demo_resume,
    }