import base64
import re
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from services.gmail_auth import get_gmail_service


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


def clean_html(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


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

        if mime_type == "text/html":
            return clean_html(decoded)

        return decoded.strip()

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


def fetch_handshake_emails(max_results=20):
    service = get_gmail_service()

    search_result = service.users().messages().list(
        userId="me",
        q=HANDSHAKE_GMAIL_QUERY,
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

        body = extract_message_body(payload)

        emails.append(
            {
                "email_id": message.get("id"),
                "thread_id": message.get("threadId"),
                "subject": subject,
                "sender": sender,
                "received_at": received_at,
                "snippet": message.get("snippet", ""),
                "body": body,
                "source": "gmail_handshake",
            }
        )

    return emails


def extract_links(text):
    links = re.findall(r"https?://[^\s\"'>]+", text or "")

    cleaned = []

    for link in links:
        link = link.rstrip(".,)]}")
        if link not in cleaned:
            cleaned.append(link)

    return cleaned


def infer_message_type(email):
    text = f"{email.get('subject', '')} {email.get('body', '')}".lower()

    event_keywords = [
        "event",
        "career fair",
        "fair",
        "rsvp",
        "register",
        "registration",
        "session",
        "webinar",
        "workshop",
        "network",
        "networking",
        "happening now",
        "marketplace",
    ]

    internship_keywords = [
        "internship",
        "intern ",
        "summer intern",
        "co-op",
    ]

    recruiter_keywords = [
        "recruiter",
        "following up",
        "follow up",
        "message",
        "invited you",
        "reach out",
    ]

    job_keywords = [
        "job",
        "apply",
        "position",
        "role",
        "hiring",
        "opportunity",
        "software developer",
        "data analyst",
        "data scientist",
        "engineer",
    ]

    if any(keyword in text for keyword in event_keywords):
        return "event"

    if any(keyword in text for keyword in internship_keywords):
        return "internship"

    if any(keyword in text for keyword in recruiter_keywords):
        return "recruiter_message"

    if any(keyword in text for keyword in job_keywords):
        return "job"

    return "career_email"


def extract_skills(text):
    known_skills = [
        "python",
        "sql",
        "machine learning",
        "deep learning",
        "generative ai",
        "gen ai",
        "llm",
        "rag",
        "api",
        "fastapi",
        "aws",
        "azure",
        "tableau",
        "excel",
        "nlp",
        "computer vision",
        "prompt engineering",
        "data analytics",
        "data science",
        "workflow automation",
        "model evaluation",
    ]

    text_lower = (text or "").lower()

    found = []

    for skill in known_skills:
        if skill in text_lower and skill not in found:
            found.append(skill)

    return found


def extract_jobs_from_gmail_emails(max_results=20):
    emails = fetch_handshake_emails(max_results=max_results)
    jobs = []

    for email in emails:
        full_text = f"{email.get('subject', '')}\n{email.get('body', '')}"
        links = extract_links(full_text)
        skills = extract_skills(full_text)
        message_type = infer_message_type(email)

        title = email.get("subject") or "Handshake Opportunity"
        title = title.replace("Fwd:", "").replace("FW:", "").strip()

        if len(title) > 90:
            title = title[:90] + "..."

        company = "Handshake"
        sender = email.get("sender", "")
        sender_match = re.search(r"<(.+?)>", sender)

        if sender_match:
            sender_email = sender_match.group(1)
        else:
            sender_email = sender

        if "handshake" not in sender_email.lower() and "@" in sender_email:
            company = sender_email.split("@")[-1].split(".")[0].title()

        if message_type == "event":
            status = "event"
            user_interest = 3
            deadline_days = 1 if "happening now" in full_text.lower() else 7

        elif message_type == "recruiter_message":
            status = "follow up"
            user_interest = 4
            deadline_days = 3

        else:
            status = "saved"
            user_interest = 4
            deadline_days = 7

        job = {
            "id": abs(hash(email.get("email_id", title))) % 100000,
            "title": title,
            "company": company,
            "location": "Not specified",
            "required_skills": skills,
            "description": email.get("body", "")[:1200],
            "deadline_days": deadline_days,
            "status": status,
            "user_interest": user_interest,
            "source": "gmail_handshake",
            "message_type": message_type,
            "email_subject": email.get("subject"),
            "email_sender": email.get("sender"),
            "received_at": email.get("received_at"),
            "apply_url": links[0] if links else None,
            "all_links": links,
        }

        jobs.append(job)

    return {
        "emails": emails,
        "jobs": jobs,
        "summary": {
            "emails_found": len(emails),
            "jobs_extracted": len(jobs),
            "source": "personal_gmail_handshake",
        },
    }