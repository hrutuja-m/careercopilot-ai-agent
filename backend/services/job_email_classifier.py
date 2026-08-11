JOB_KEYWORDS = {
    "job",
    "jobs",
    "intern",
    "internship",
    "apply",
    "application",
    "position",
    "role",
    "hiring",
    "engineer",
    "analyst",
}

EVENT_KEYWORDS = {
    "career fair",
    "event",
    "webinar",
    "workshop",
    "rsvp",
    "info session",
}

FOLLOW_UP_KEYWORDS = {
    "recruiter",
    "follow up",
    "following up",
    "interview",
    "application update",
}


def classify_job_email(subject="", body="", sender=""):
    text = f"{subject} {body} {sender}".lower()

    if any(keyword in text for keyword in EVENT_KEYWORDS):
        return "event"

    if any(keyword in text for keyword in FOLLOW_UP_KEYWORDS):
        return "recruiter_message"

    if "internship" in text or "intern " in text:
        return "internship"

    if any(keyword in text for keyword in JOB_KEYWORDS):
        return "job"

    return "career_email"
