from fastapi import FastAPI
from api.task_routes import router as task_router
from api.chatbot_routes import router as chatbot_router
from api.job_routes import router as job_router
from api.resume_routes import router as resume_router
from api.data_routes import router as data_router
from api.gmail_routes import router as gmail_router

app = FastAPI(
    title="CareerCopilot AI",
    description="Personal AI Assistant for Job Search Tasks, Priorities, and Application Tracking",
    version="1.0.0",
)

app.include_router(task_router, prefix="/tasks", tags=["Tasks"])
app.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(job_router, prefix="/jobs", tags=["Jobs"])
app.include_router(resume_router, prefix="/resume", tags=["Resume"])
app.include_router(data_router, prefix="/data", tags=["Data Sources"])
app.include_router(gmail_router, prefix="/gmail", tags=["Gmail Scraper"])


@app.get("/")
def root():
    return {
        "message": "CareerCopilot AI backend is running",
        "status": "success",
    }