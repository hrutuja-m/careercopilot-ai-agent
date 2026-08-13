"""Job extraction helpers for CareerCopilot's email ingestion pipeline."""

from services.gmail_handshake_scraper import (
    extract_jobs_from_gmail_emails,
    extract_links,
    extract_skills,
    infer_deadline_days,
    infer_location_from_text,
    infer_title_company_from_text,
    stable_email_job_id,
)

__all__ = [
    "extract_jobs_from_gmail_emails",
    "extract_links",
    "extract_skills",
    "infer_deadline_days",
    "infer_location_from_text",
    "infer_title_company_from_text",
    "stable_email_job_id",
]
