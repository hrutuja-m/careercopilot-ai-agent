from fastapi import APIRouter
from models.schemas import ChatRequest
from services.chatbot_engine import career_chatbot_response
from database.jobs_store import get_all_jobs
from services.profile_store import get_goals, get_profile

router = APIRouter()


@router.post("/")
def chat_with_assistant(request: ChatRequest):
    all_jobs = get_all_jobs()

    response = career_chatbot_response(
        request.message,
        get_profile(),
        all_jobs,
        get_goals(),
    )

    return {
        "user_message": request.message,
        "jobs_analyzed": len(all_jobs),
        "assistant_response": response,
    }
