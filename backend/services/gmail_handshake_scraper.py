import base64
import html
import re
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

from database.db import database_summary, list_jobs, upsert_job, upsert_raw_email
from services.handshake_email_parser import extract_links, extract_skills, parse_handshake_email


HANDSHAKE_GMAIL_QUERY = (
    '(from:handshake OR from:joinhandshake.com OR from:m.joinhandshake.com '
    'OR from:notifications.joinhandshake.com OR from:g.joinhandshake.com '
    'OR subject:handshake OR "Handshake") '
    '(job OR internship OR intern OR recruiter OR apply OR event OR career OR "career fair" OR rsvp)'
)


def decode_base64url(data):
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    decoded_bytes = base64.urlsafe_b64decode(data + padding)
    return decoded_bytes.decode("utf-8", errors="ignore")


class LinkPreservingHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.current_href = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"br", "p", "div", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")
        if tag == "a":
            self.current_href = attrs.get("href", "").strip()

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href.startswith("http"):
            self.parts.append(f" {self.current_href} ")
            self.current_href = ""
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if data:
            self.parts.append(html.unescape(data))

    def get_text(self):
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def clean_html(html):
    if not html:
        return ""

    html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
    parser = LinkPreservingHTMLParser()
    parser.feed(html)
    return parser.get_text()


def get_header(headers, name):
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def extract_message_body(payload):
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data:
        decoded = decode_base64url(body_data)
        return clean_html(decoded) if mime_type == "text/html" else decoded.strip()

    parts = payload.get("parts", [])
    plain_text_chunks = []
    html_chunks = []

    for part in parts:
        part_mime = part.get("mimeType", "")
        part_body = part.get("body", {}).get("data")

        if part_body:
            decoded = decode_base64url(part_body)
            if part_mime == "text/plain":
                plain_text_chunks.append(decoded.strip())
            elif part_mime == "text/html":
                html_chunks.append(clean_html(decoded))

        if part.get("parts"):
            nested_text = extract_message_body(part)
            if nested_text:
                plain_text_chunks.append(nested_text)

    if plain_text_chunks:
        return "\n".join(plain_text_chunks).strip()
    if html_chunks:
        return "\n".join(html_chunks).strip()
    return ""


def fetch_handshake_emails(max_results=20, query=HANDSHAKE_GMAIL_QUERY):
    from services.gmail_auth import get_gmail_service

    service = get_gmail_service()
    search_result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    messages = search_result.get("messages", [])
    emails = []

    for item in messages:
        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full",
        ).execute()

        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        subject = get_header(headers, "Subject")
        sender = get_header(headers, "From")
        date_raw = get_header(headers, "Date")

        try:
            received_at = parsedate_to_datetime(date_raw).isoformat() if date_raw else None
        except Exception:
            received_at = date_raw

        email = {
            "email_id": message.get("id"),
            "thread_id": message.get("threadId"),
            "subject": subject,
            "sender": sender,
            "received_at": received_at,
            "snippet": message.get("snippet", ""),
            "body": extract_message_body(payload),
            "source": "gmail_handshake",
        }
        emails.append(email)

    return emails


def infer_message_type(email):
    text = f"{email.get('subject', '')} {email.get('body', '')}".lower()

    if any(keyword in text for keyword in ["career fair", "webinar", "workshop", "rsvp", "event"]):
        return "event"
    if any(keyword in text for keyword in ["recruiter", "message", "following up", "follow up"]):
        return "recruiter_message"
    if any(keyword in text for keyword in ["internship", "intern "]):
        return "internship"
    if any(keyword in text for keyword in ["job", "apply", "position", "role", "hiring", "engineer", "analyst"]):
        return "job"
    return "career_email"


def extract_jobs_from_gmail_emails(max_results=20, save_to_database=True, query=HANDSHAKE_GMAIL_QUERY):
    emails = fetch_handshake_emails(max_results=max_results, query=query)
    jobs = []

    for email in emails:
        if save_to_database:
            upsert_raw_email(email)

        parsed_jobs = parse_handshake_email(email)
        if parsed_jobs:
            for job in parsed_jobs:
                jobs.append(job)
                if save_to_database:
                    upsert_job(job)
            continue

        full_text = f"{email.get('subject', '')}\n{email.get('body', '')}"
        links = extract_links(full_text)
        fallback_job = {
            "email_id": email.get("email_id"),
            "title": (email.get("subject") or "Handshake Opportunity")[:90],
            "company": "Handshake",
            "location": "Not specified",
            "salary": "",
            "job_type": "Unknown",
            "work_mode": "Unknown",
            "posted_date": email.get("received_at"),
            "deadline": "",
            "deadline_text": "",
            "apply_url": links[0] if links else None,
            "source": "gmail_handshake",
            "message_type": infer_message_type(email),
            "email_subject": email.get("subject"),
            "received_at": email.get("received_at"),
            "raw_details": email.get("snippet", ""),
            "required_skills": extract_skills(full_text),
            "priority_score": 30,
            "priority_label": "Low",
        }
        jobs.append(fallback_job)
        if save_to_database:
            upsert_job(fallback_job)

    return {
        "emails": emails,
        "jobs": jobs,
        "summary": {
            "emails_found": len(emails),
            "jobs_extracted": len(jobs),
            "source": "personal_gmail_handshake",
            "database": database_summary() if save_to_database else None,
        },
    }


def get_saved_handshake_jobs(limit=None):
    return list_jobs(limit=limit)
