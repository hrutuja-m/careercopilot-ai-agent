from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from api.task_routes import router as task_router
from api.chatbot_routes import router as chatbot_router
from api.job_routes import router as job_router
from api.resume_routes import router as resume_router
from api.data_routes import router as data_router
from api.gmail_routes import router as gmail_router
from api.profile_routes import router as profile_router

app = FastAPI(
    title="CareerCopilot AI",
    description="Personal AI Assistant for Job Search Tasks, Priorities, and Application Tracking",
    version="1.0.0",
)

# Allow the static frontend (opened via file:// or a local dev server on any
# port) to call this API during local development. Locked down to "*" only
# because this is a local prototype with no auth/cookies involved.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Chrome's Private Network Access checks block a page on file:// or a
    non-localhost origin from calling http://localhost:8002 unless this
    header is present. Harmless no-op for browsers that don't check it."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(PrivateNetworkAccessMiddleware)

app.include_router(task_router, prefix="/tasks", tags=["Tasks"])
app.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(job_router, prefix="/jobs", tags=["Jobs"])
app.include_router(resume_router, prefix="/resume", tags=["Resume"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])
app.include_router(data_router, prefix="/data", tags=["Data Sources"])
app.include_router(gmail_router, prefix="/gmail", tags=["Gmail Scraper"])


@app.get("/")
def root():
    return {
        "message": "CareerCopilot AI backend is running",
        "status": "success",
    }
