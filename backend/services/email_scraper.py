def get_sample_job_emails():
    """
    This function simulates career-related emails.

    Later, this will connect to Gmail API and search emails from:
    - LinkedIn
    - Handshake
    - company career pages
    - recruiters
    - job alerts
    """

    return [
        {
            "email_id": 1,
            "sender": "careers@deepmeasures.com",
            "subject": "AI Agent Engineer Intern Opportunity",
            "body": "We are hiring an AI Agent Engineer Intern in Cambridge, MA. Skills include Python, LLM, APIs, prompt engineering, and workflow automation. Apply by May 21, 2026.",
            "source": "email",
        },
        {
            "email_id": 2,
            "sender": "jobs@healthtechlabs.com",
            "subject": "Data Analyst Intern Role",
            "body": "HealthTech Labs is looking for a Data Analyst Intern. Skills include SQL, Python, Tableau, and Excel. Deadline in 8 days.",
            "source": "email",
        },
        {
            "email_id": 3,
            "sender": "recruiting@smartsystems.ai",
            "subject": "Machine Learning Intern Application Update",
            "body": "Thank you for applying to our Machine Learning Intern role. We will review your application soon.",
            "source": "email",
        },
    ]


def extract_job_from_email(email):
    """
    Converts one job-related email into a normalized job dictionary.
    This is simple rule-based extraction for MVP.
    Later, an LLM can extract this more intelligently.
    """

    subject = email["subject"].lower()
    body = email["body"].lower()

    if "ai agent engineer" in subject or "ai agent engineer" in body:
        return {
            "id": 101,
            "title": "AI Agent Engineer Intern",
            "company": "DEEP Measures",
            "location": "Cambridge, MA",
            "required_skills": ["python", "llm", "api", "prompt engineering", "workflow automation"],
            "description": email["body"],
            "deadline_days": 3,
            "status": "not_applied",
            "user_interest": 5,
            "source": "email",
            "apply_url": None,
        }

    if "data analyst" in subject or "data analyst" in body:
        return {
            "id": 102,
            "title": "Data Analyst Intern",
            "company": "HealthTech Labs",
            "location": "Boston, MA",
            "required_skills": ["sql", "python", "tableau", "excel"],
            "description": email["body"],
            "deadline_days": 8,
            "status": "not_applied",
            "user_interest": 3,
            "source": "email",
            "apply_url": None,
        }

    if "machine learning intern" in subject or "machine learning intern" in body:
        return {
            "id": 103,
            "title": "Machine Learning Intern",
            "company": "Smart Systems AI",
            "location": "Remote",
            "required_skills": ["python", "machine learning", "deep learning", "aws"],
            "description": email["body"],
            "deadline_days": 5,
            "status": "applied",
            "user_interest": 4,
            "source": "email",
            "apply_url": None,
        }

    return None


def extract_jobs_from_emails():
    emails = get_sample_job_emails()
    jobs = []

    for email in emails:
        job = extract_job_from_email(email)

        if job:
            jobs.append(job)

    return jobs
