import json
import sqlite3
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
DB_PATH = BACKEND_DIR / "careercopilot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_emails (
                email_id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                received_at TEXT,
                snippet TEXT,
                body TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                salary TEXT,
                job_type TEXT,
                work_mode TEXT,
                posted_date TEXT,
                deadline TEXT,
                deadline_text TEXT,
                apply_url TEXT,
                source TEXT,
                message_type TEXT,
                email_subject TEXT,
                received_at TEXT,
                raw_details TEXT,
                required_skills TEXT,
                priority_score REAL DEFAULT 0,
                priority_label TEXT DEFAULT 'Low',
                application_status TEXT DEFAULT 'Not Applied',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email_id, company, title)
            )
            """
        )
        conn.commit()


def upsert_raw_email(email):
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_emails (
                email_id, thread_id, subject, sender, received_at,
                snippet, body, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email_id) DO UPDATE SET
                thread_id = excluded.thread_id,
                subject = excluded.subject,
                sender = excluded.sender,
                received_at = excluded.received_at,
                snippet = excluded.snippet,
                body = excluded.body,
                source = excluded.source
            """,
            (
                email.get("email_id"),
                email.get("thread_id"),
                email.get("subject"),
                email.get("sender"),
                email.get("received_at"),
                email.get("snippet"),
                email.get("body"),
                email.get("source", "gmail_handshake"),
            ),
        )
        conn.commit()


def upsert_job(job):
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO job_opportunities (
                email_id, title, company, location, salary, job_type,
                work_mode, posted_date, deadline, deadline_text, apply_url,
                source, message_type, email_subject, received_at, raw_details,
                required_skills, priority_score, priority_label,
                application_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email_id, company, title) DO UPDATE SET
                location = excluded.location,
                salary = excluded.salary,
                job_type = excluded.job_type,
                work_mode = excluded.work_mode,
                posted_date = excluded.posted_date,
                deadline = excluded.deadline,
                deadline_text = excluded.deadline_text,
                apply_url = excluded.apply_url,
                source = excluded.source,
                message_type = excluded.message_type,
                email_subject = excluded.email_subject,
                received_at = excluded.received_at,
                raw_details = excluded.raw_details,
                required_skills = excluded.required_skills,
                priority_score = excluded.priority_score,
                priority_label = excluded.priority_label,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job.get("email_id"),
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("salary"),
                job.get("job_type"),
                job.get("work_mode"),
                job.get("posted_date"),
                job.get("deadline"),
                job.get("deadline_text"),
                job.get("apply_url"),
                job.get("source", "gmail_handshake"),
                job.get("message_type", "job"),
                job.get("email_subject"),
                job.get("received_at"),
                job.get("raw_details"),
                json.dumps(job.get("required_skills", [])),
                job.get("priority_score", 0),
                job.get("priority_label", "Low"),
                job.get("application_status", "Not Applied"),
            ),
        )
        conn.commit()


def list_jobs(limit=None):
    init_db()
    query = """
        SELECT *
        FROM job_opportunities
        ORDER BY priority_score DESC, deadline IS NULL, deadline ASC, company ASC
    """
    params = ()
    if limit:
        query += " LIMIT ?"
        params = (limit,)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        jobs = [dict(row) for row in rows]

    for job in jobs:
        try:
            job["required_skills"] = json.loads(job.get("required_skills") or "[]")
        except json.JSONDecodeError:
            job["required_skills"] = []
    return jobs


def update_job_status(job_id, status):
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE job_opportunities
            SET application_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, job_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def database_summary():
    init_db()
    with get_connection() as conn:
        raw_count = conn.execute("SELECT COUNT(*) FROM raw_emails").fetchone()[0]
        job_count = conn.execute("SELECT COUNT(*) FROM job_opportunities").fetchone()[0]
        handshake_count = conn.execute(
            "SELECT COUNT(*) FROM job_opportunities WHERE source = 'gmail_handshake'"
        ).fetchone()[0]
        latest_email = conn.execute("SELECT MAX(received_at) FROM raw_emails").fetchone()[0]

    return {
        "database_path": str(DB_PATH),
        "raw_emails": raw_count,
        "jobs": job_count,
        "handshake_jobs": handshake_count,
        "latest_email": latest_email,
    }
