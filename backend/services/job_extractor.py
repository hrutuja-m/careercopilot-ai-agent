import re

from services.job_email_classifier import classify_job_email


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


def extract_skills_from_text(text):
    lower = str(text or "").lower()
    return [skill for skill in KNOWN_SKILLS if skill in lower]


def extract_apply_url(text):
    links = re.findall(r"https?://[^\s\"'>]+", str(text or ""))
    if not links:
        return None
    return links[0].rstrip(".,)]}")


def extract_deadline_text(text):
    patterns = [
        r"apply by\s+(.+?)(?:\.|\n|$)",
        r"deadline(?: is|:)?\s+(.+?)(?:\.|\n|$)",
        r"applications? are due\s+(.+?)(?:\.|\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def extract_company_from_sender(sender):
    email_match = re.search(r"@([^>\s]+)", str(sender or ""))
    if not email_match:
        return "Unknown company"

    domain = email_match.group(1).split(".")[0]
    return domain.replace("-", " ").title()


def extract_job_from_text(subject="", body="", sender="", source="email"):
    full_text = f"{subject}\n{body}"
    message_type = classify_job_email(subject, body, sender)

    title = str(subject or "Career Opportunity").strip()
    title = re.sub(r"^(new|job alert|opportunity):\s*", "", title, flags=re.IGNORECASE)

    company = extract_company_from_sender(sender)
    required_skills = extract_skills_from_text(full_text)

    return {
        "title": title[:90],
        "company": company,
        "location": "Not specified",
        "required_skills": required_skills,
        "description": str(body or "").strip(),
        "deadline_text": extract_deadline_text(full_text),
        "status": "saved",
        "user_interest": 3,
        "source": source,
        "message_type": message_type,
        "apply_url": extract_apply_url(full_text),
    }
