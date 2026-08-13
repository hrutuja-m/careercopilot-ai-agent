from fastapi import APIRouter, HTTPException

from models.schemas import GoalUpdate
from services.profile_store import get_goals, get_profile_bundle, get_progress, update_goals

router = APIRouter()


@router.get("/")
def get_profile():
    bundle = get_profile_bundle()
    return {
        "message": "Profile loaded successfully",
        "resume_profile": bundle["profile"],
        "goals": bundle["goals"],
        "progress": bundle["progress"],
    }


@router.get("/goals")
def get_profile_goals():
    return {
        "message": "Goals loaded successfully",
        "goals": get_goals(),
        "progress": get_progress(),
    }


@router.patch("/goals")
def patch_profile_goals(payload: GoalUpdate):
    if payload.daily_application_goal < 1:
        raise HTTPException(status_code=400, detail="daily_application_goal must be at least 1")

    return {
        "message": "Goals updated successfully",
        "goals": update_goals(payload.daily_application_goal),
        "progress": get_progress(),
    }
