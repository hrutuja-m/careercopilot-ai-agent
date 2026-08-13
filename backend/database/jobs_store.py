"""A tiny JSON-file-backed store for tracked jobs.

Why this exists: CareerCopilot needs a durable place to record "I applied
to this" or "mark this as rejected." Every route reads/writes through this
store so status changes survive across requests and server restarts.

This is intentionally simple (a single JSON file, a threading.Lock, and a
process-local cache) rather than a real database — it's sized for a single
user running this locally, not concurrent multi-user traffic.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone

from services.profile_store import record_application
from services.handshake_email_parser import is_placeholder_url, is_real_apply_url

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_FILE = os.path.join(BASE_DIR, "database", "jobs_store.json")

VALID_STATUSES = ["not_applied", "applied", "interviewing", "rejected"]

# Older/incoming data may still use different words for the same idea
# (e.g. older saved records used "saved"). Map those onto the four
# canonical statuses instead of dropping the information.
_LEGACY_STATUS_MAP = {
    "saved": "not_applied",
    "event": "not_applied",
    "follow up": "not_applied",
    "not applied": "not_applied",
}

_lock = threading.Lock()
_cache = None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_status(raw_status):
    raw = (raw_status or "").strip().lower()
    if raw in VALID_STATUSES:
        return raw
    return _LEGACY_STATUS_MAP.get(raw, "not_applied")


def _stamp(job):
    """Return a copy of job with the fields the store needs, filled in."""
    job = dict(job)
    job.setdefault("apply_url", None)
    job = _sanitize_job(job)
    job["status"] = normalize_status(job.get("status"))
    job["status_history"] = [{"status": job["status"], "at": _now_iso()}]
    job["applied_at"] = _now_iso() if job["status"] == "applied" else None
    return job


def _build_seed():
    return []


def _is_visible_mail_job(job):
    return (
        job.get("source") == "gmail_handshake"
        and job.get("message_type") in ("job", "internship")
        and bool(job.get("has_real_apply_url"))
        and bool(job.get("apply_url"))
    )


def _load_from_disk():
    if not os.path.exists(STORE_FILE):
        return None
    with open(STORE_FILE, "r") as f:
        return json.load(f)


def _save_to_disk(jobs):
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
    tmp_file = STORE_FILE + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(jobs, f, indent=2)
    os.replace(tmp_file, STORE_FILE)


def _sanitize_job(job):
    """Normalize apply_url/has_real_apply_url using the single shared
    classifier in handshake_email_parser.py, instead of a separate
    reimplementation here.

    Extraction (gmail_handshake_scraper.py) already computes
    has_real_apply_url with context this function doesn't have — namely
    whether the link's visible text was an explicit "Apply"/"View Job" CTA,
    which makes a non-Handshake link (e.g. the employer's own career page)
    trustworthy too. So an already-set boolean is respected as-is rather
    than being re-derived and potentially downgraded. Only missing/legacy
    data (no has_real_apply_url at all) falls back to a fresh URL-only
    check here.
    """
    job = dict(job)
    job.pop("all_links", None)
    job.pop("tracking_apply_url", None)
    apply_url = job.get("apply_url")

    if is_placeholder_url(apply_url):
        job["apply_url"] = None
        job["has_real_apply_url"] = False
        return job

    if job.get("has_real_apply_url") is None:
        job["has_real_apply_url"] = is_real_apply_url(apply_url)

    if not job["has_real_apply_url"]:
        job["apply_url"] = None

    return job


def _ensure_loaded():
    global _cache
    if _cache is not None:
        return
    with _lock:
        if _cache is not None:
            return
        existing = _load_from_disk()
        if existing is None:
            existing = _build_seed()
            _save_to_disk(existing)
        else:
            sanitized = [_sanitize_job(job) for job in existing]
            if sanitized != existing:
                existing = sanitized
                _save_to_disk(existing)
        _cache = existing


def get_all_jobs():
    _ensure_loaded()
    return [dict(job) for job in _cache if _is_visible_mail_job(job)]


def get_job(job_id):
    _ensure_loaded()
    for job in _cache:
        if job.get("id") == job_id:
            return dict(job)
    return None


def update_job_status(job_id, new_status):
    """Set job_id's status, recording history. Returns the updated job, or
    None if no job with that id exists."""
    _ensure_loaded()
    normalized = normalize_status(new_status)
    with _lock:
        for job in _cache:
            if job.get("id") == job_id:
                previous_status = job.get("status")
                job["status"] = normalized
                job.setdefault("status_history", [])
                job["status_history"].append({"status": normalized, "at": _now_iso()})
                if normalized == "applied":
                    job["applied_at"] = _now_iso()
                    if previous_status != "applied":
                        record_application()
                _save_to_disk(_cache)
                return dict(job)
    return None


def _normalize_match_text(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _matching_job(existing_jobs, incoming_job):
    incoming_id = incoming_job.get("id")
    incoming_email_id = incoming_job.get("email_id")
    incoming_apply_url = incoming_job.get("apply_url")
    incoming_title = _normalize_match_text(incoming_job.get("title"))
    incoming_company = _normalize_match_text(incoming_job.get("company"))

    for job in existing_jobs:
        if incoming_id is not None and job.get("id") == incoming_id:
            return job

        if incoming_email_id and job.get("email_id") == incoming_email_id:
            return job

        if incoming_apply_url and job.get("apply_url") == incoming_apply_url:
            return job

        if (
            incoming_title
            and incoming_company
            and _normalize_match_text(job.get("title")) == incoming_title
            and _normalize_match_text(job.get("company")) == incoming_company
        ):
            return job

    return None


def _merge_job_metadata(existing_job, incoming_job):
    changed = False
    incoming_apply_url = incoming_job.get("apply_url")
    incoming_is_real = bool(incoming_job.get("has_real_apply_url"))
    existing_is_real = bool(existing_job.get("has_real_apply_url"))

    # Only ever adopt an incoming apply_url when the incoming job was
    # already confirmed real at extraction time (which has context this
    # merge step doesn't, like CTA link text) — never promote
    # has_real_apply_url to True here based on a ranking heuristic alone.
    # That was the bug: a merely-better-than-nothing link could get
    # mislabeled as a confirmed Apply target.
    if incoming_apply_url and incoming_is_real and (
        not existing_is_real or incoming_apply_url != existing_job.get("apply_url")
    ):
        existing_job["apply_url"] = incoming_apply_url
        existing_job["has_real_apply_url"] = True
        changed = True

    for field in (
        "email_id",
        "thread_id",
        "email_subject",
        "email_sender",
        "received_at",
        "message_type",
        "location",
        "employment_type",
        "compensation",
        "work_mode",
        "deadline_text",
        "deadline_source",
        "apply_url_source",
        "link_confidence",
        "extraction_evidence",
    ):
        if incoming_job.get(field) and not existing_job.get(field):
            existing_job[field] = incoming_job[field]
            changed = True
    return changed


def merge_jobs_detailed(new_jobs):
    """Merge externally-sourced jobs (e.g. a fresh Gmail sync) into the
    store. De-duplicated by id; a job that's already tracked keeps whatever
    status the user already set for it rather than being overwritten, except
    for application-confirmation emails, which may promote a matching job to
    "applied" automatically.
    Returns added and status-updated counts."""
    _ensure_loaded()
    with _lock:
        added = 0
        status_updated = 0
        changed = False
        for job in new_jobs:
            existing = _matching_job(_cache, job)
            incoming_status = normalize_status(job.get("status"))

            if existing is not None:
                if _merge_job_metadata(existing, job):
                    changed = True
                if incoming_status == "applied" and existing.get("status") != "applied":
                    existing["status"] = "applied"
                    existing.setdefault("status_history", [])
                    existing["status_history"].append({"status": "applied", "at": _now_iso()})
                    existing["applied_at"] = _now_iso()
                    record_application()
                    status_updated += 1
                    changed = True
                continue

            if not _is_visible_mail_job(job):
                continue

            stamped = _stamp(job)
            _cache.append(stamped)
            added += 1
            changed = True
        if changed:
            _save_to_disk(_cache)
        return {"added": added, "status_updated": status_updated}


def merge_jobs(new_jobs):
    return merge_jobs_detailed(new_jobs)["added"]
