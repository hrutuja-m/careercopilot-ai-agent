import re


DEFAULT_TARGET_ROLES = [
    "AI Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Data Analyst",
    "Software Engineer",
]

KNOWN_SKILLS = [
    "python",
    "sql",
    "fastapi",
    "rag",
    "llm",
    "openai api",
    "faiss",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "aws",
    "azure",
    "tableau",
    "excel",
    "data pipelines",
    "prompt engineering",
]

EXPERIENCE_KEYWORDS = [
    "ai agents",
    "workflow automation",
    "model evaluation",
    "resume parsing",
    "job matching",
    "data analysis",
    "dashboard",
    "api",
]


def _clean_text(text):
    text = str(text or "").replace("\xa0", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_name(text):
    lines = [line.strip() for line in _clean_text(text).split("\n") if line.strip()]
    if not lines:
        return "Unknown"

    first_line = lines[0]
    if "@" in first_line or len(first_line.split()) > 5:
        return "Unknown"

    return first_line


def extract_skills(text):
    lower = _clean_text(text).lower()
    return [skill for skill in KNOWN_SKILLS if skill in lower]


def extract_target_roles(text):
    lower = _clean_text(text).lower()
    roles = [role for role in DEFAULT_TARGET_ROLES if role.lower() in lower]
    return roles or DEFAULT_TARGET_ROLES[:3]


def extract_experience_keywords(text):
    lower = _clean_text(text).lower()
    return [keyword for keyword in EXPERIENCE_KEYWORDS if keyword in lower]


def parse_resume_text(text):
    return {
        "name": extract_name(text),
        "target_roles": extract_target_roles(text),
        "skills": extract_skills(text),
        "experience_keywords": extract_experience_keywords(text),
    }
