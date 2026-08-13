"""High-level career email ingestion pipeline.

Today the only live provider is Gmail/Handshake. This module gives the
application a stable pipeline entrypoint while keeping provider-specific
details in gmail_handshake_scraper.
"""

from services.gmail_handshake_scraper import (
    extract_jobs_from_gmail_emails,
    fetch_handshake_emails,
)


def run_gmail_handshake_pipeline(max_results=None, lookback_days=None):
    kwargs = {}
    if max_results is not None:
        kwargs["max_results"] = max_results
    if lookback_days is not None:
        kwargs["lookback_days"] = lookback_days
    return extract_jobs_from_gmail_emails(**kwargs)


__all__ = [
    "extract_jobs_from_gmail_emails",
    "fetch_handshake_emails",
    "run_gmail_handshake_pipeline",
]
