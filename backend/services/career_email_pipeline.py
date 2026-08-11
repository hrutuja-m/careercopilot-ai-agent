from services.email_cleaner import clean_email_text
from services.job_email_classifier import classify_job_email
from services.job_extractor import extract_job_from_text


def process_career_email(email):
    subject = email.get("subject", "")
    body = clean_email_text(email.get("body", ""))
    sender = email.get("sender", "")

    job = extract_job_from_text(
        subject=subject,
        body=body,
        sender=sender,
        source=email.get("source", "email"),
    )
    job["email_id"] = email.get("email_id")
    job["message_type"] = classify_job_email(subject, body, sender)

    return job


def process_career_emails(emails):
    return [process_career_email(email) for email in emails]
