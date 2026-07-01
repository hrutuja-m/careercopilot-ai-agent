from fastapi import APIRouter
from models.schemas import ChatRequest
from services.chatbot_engine import career_chatbot_response
from api.task_routes import demo_resume, demo_jobs
from services.email_scraper import extract_jobs_from_emails
from services.job_api_client import fetch_sample_api_jobs

router = APIRouter()


@router.post("/")
def chat_with_assistant(request: ChatRequest):
    email_jobs = extract_jobs_from_emails()
    api_jobs = fetch_sample_api_jobs()

    all_jobs = demo_jobs + email_jobs + api_jobs

    response = career_chatbot_response(
        request.message,
        demo_resume,
        all_jobs,
    )

    return {
        "user_message": request.message,
        "jobs_analyzed": len(all_jobs),
        "assistant_response": response,
    }