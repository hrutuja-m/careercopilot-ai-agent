from pydantic import BaseModel
from typing import List


class ChatRequest(BaseModel):
    message: str


class ResumeProfile(BaseModel):
    name: str
    target_roles: List[str]
    skills: List[str]
    experience_keywords: List[str]


class Job(BaseModel):
    id: int
    title: str
    company: str
    location: str
    required_skills: List[str]
    description: str
    deadline_days: int
    status: str
    user_interest: int