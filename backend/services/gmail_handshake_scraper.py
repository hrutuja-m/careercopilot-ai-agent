import base64
import hashlib
import re
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from config.settings import GMAIL_LOOKBACK_DAYS, GMAIL_MAX_RESULTS
from services.gmail_auth import get_gmail_service
from services.handshake_email_parser import (
    extract_all_links,
    is_real_apply_url,
    pick_application_link,
    resolve_handshake_tracking_url,
)


HANDSHAKE_GMAIL_QUERY_BASE = (
    '(from:handshake OR from:joinhandshake.com OR from:m.joinhandshake.com '
    'OR from:notifications.joinhandshake.com OR from:g.joinhandshake.com '
    'OR subject:handshake OR "Handshake") '
    '(job OR internship OR intern OR recruiter OR apply OR event OR career OR "career fair" OR rsvp '
    'OR "thank you for applying" OR "application received")'
)


def build_handshake_gmail_query(lookback_days=GMAIL_LOOKBACK_DAYS):
    lookback_days = max(int(lookback_days or GMAIL_LOOKBACK_DAYS), 1)
    return f"{HANDSHAKE_GMAIL_QUERY_BASE} newer_than:{lookback_days}d"


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
            return {"text": clean_html(decoded), "html": decoded}

        return {"text": decoded.strip(), "html": ""}

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
                html_chunks.append(decoded)

        if part.get("parts"):
            nested_body = extract_message_body(part)
            if nested_body.get("text"):
                plain_text_chunks.append(nested_body["text"])
            if nested_body.get("html"):
                html_chunks.append(nested_body["html"])

    if plain_text_chunks:
        text = "\n".join(plain_text_chunks).strip()
        html = "\n".join(html_chunks).strip()
        return {"text": text, "html": html}

    if html_chunks:
        html = "\n".join(html_chunks).strip()
        return {"text": clean_html(html), "html": html}

    return {"text": "", "html": ""}


def fetch_handshake_emails(max_results=GMAIL_MAX_RESULTS, lookback_days=GMAIL_LOOKBACK_DAYS, service=None):
    service = service or get_gmail_service()

    search_result = service.users().messages().list(
        userId="me",
        q=build_handshake_gmail_query(lookback_days),
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
                "body": body["text"],
                "html": body["html"],
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

    confirmation_keywords = [
        "thank you for applying",
        "thanks for applying",
        "application received",
        "we've received your application",
        "we have received your application",
        "your application has been received",
        "you applied",
    ]

    digest_keywords = [
        "your weekly jobs round-up",
        "weekly jobs round-up",
        "new jobs just for you",
        "view more jobs",
        "jobs recommended for you",
        "recommended jobs",
    ]

    candidate_signal_keywords = [
        "sees you as a top applicant",
        "top applicant for",
        "you are a top applicant",
        "you're a top applicant",
    ]

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

    if any(keyword in text for keyword in confirmation_keywords):
        return "application_confirmation"

    if any(keyword in text for keyword in candidate_signal_keywords):
        return "candidate_signal"

    if any(keyword in text for keyword in digest_keywords):
        return "job_digest"

    if any(keyword in text for keyword in event_keywords):
        return "event"

    if any(keyword in text for keyword in internship_keywords):
        return "internship"

    if any(keyword in text for keyword in recruiter_keywords):
        return "recruiter_message"

    if any(keyword in text for keyword in job_keywords):
        return "job"

    return "career_email"


def is_trackable_message_type(message_type):
    return message_type in {"job", "internship", "application_confirmation"}


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


def clean_extracted_label(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    return value.strip(" .,!:-")


def split_email_lines(text):
    lines = []
    for line in re.split(r"[\r\n]+", text or ""):
        cleaned = clean_extracted_label(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def _parse_base_datetime(received_at=None):
    if received_at:
        try:
            return datetime.fromisoformat(received_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _deadline_days_from_date(raw_date, received_at=None):
    normalized = re.sub(r"\s+", " ", raw_date.replace(".", "")).strip()
    normalized = re.sub(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\s+\d{1,2}:\d{2}\s*(am|pm)?\s*[A-Z]{2,4}(?=,?\s+\d{4}$|$)",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            due = datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
            base = _parse_base_datetime(received_at)
            return max((due.date() - base.date()).days, 0)
        except ValueError:
            continue

    for fmt in ("%B %d", "%b %d"):
        try:
            base = _parse_base_datetime(received_at)
            due = datetime.strptime(normalized, fmt).replace(year=base.year, tzinfo=timezone.utc)
            if due.date() < base.date():
                due = due.replace(year=base.year + 1)
            return max((due.date() - base.date()).days, 0)
        except ValueError:
            continue
    return None


def _deadline_text_with_year(raw_date, received_at=None):
    cleaned = clean_extracted_label(raw_date)
    cleaned = re.sub(
        r"\s+\d{1,2}:\d{2}\s*(am|pm)?\s*[A-Z]{2,4}$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if re.search(r"\b\d{4}\b", cleaned):
        return cleaned

    base = _parse_base_datetime(received_at)
    return f"{cleaned}, {base.year}"


def infer_deadline_info(text, received_at=None, message_type="job"):
    text = text or ""
    lower = text.lower()

    in_days = re.search(r"(?:deadline|due|apply by|closes?|closing|expires?).{0,40}\bin\s+(\d{1,3})\s+days?\b", lower)
    if in_days:
        days = max(int(in_days.group(1)), 0)
        return {
            "deadline_days": days,
            "deadline_text": f"in {days} day{'s' if days != 1 else ''}",
            "deadline_source": "relative email text",
        }

    explicit_days = re.search(r"\bdeadline\s*(?:is|:)?\s*(\d{1,3})\s+days?\b", lower)
    if explicit_days:
        days = max(int(explicit_days.group(1)), 0)
        return {
            "deadline_days": days,
            "deadline_text": f"{days} day{'s' if days != 1 else ''}",
            "deadline_source": "deadline text",
        }

    month_names = (
        "January|February|March|April|May|June|July|August|September|October|November|December|"
        "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    )
    weekday_names = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun"
    date_regex = rf"((?:{weekday_names}),?\s+)?({month_names})\.?\s+\d{{1,2}}(?:,?\s+\d{{4}})?(?:\s+\d{{1,2}}:\d{{2}}\s*(?:am|pm)?\s*[A-Z]{{2,4}})?"

    due_context = re.search(
        rf"(?:applications?(?:\s+for\s+.+?)?\s+are due|applications? due|apply by|deadline|due by|closes? on|closing date).{{0,220}}?{date_regex}",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if due_context:
        raw_date = due_context.group(0)
        date_match = re.search(date_regex, raw_date, flags=re.IGNORECASE)
        if date_match:
            deadline_text = _deadline_text_with_year(date_match.group(0), received_at)
            days = _deadline_days_from_date(deadline_text, received_at)
            if days is not None:
                return {
                    "deadline_days": days,
                    "deadline_text": deadline_text,
                    "deadline_source": "applications due date",
                }

    for pattern in (
        r"(?:apply by|deadline|due by|closes? on|closing date:?|applications? due)\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        date_regex,
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        deadline_text = _deadline_text_with_year(match.group(0) if pattern == date_regex else match.group(1), received_at)
        days = _deadline_days_from_date(deadline_text, received_at)
        if days is not None:
            return {
                "deadline_days": days,
                "deadline_text": deadline_text,
                "deadline_source": "date found in email",
            }

    if "happening now" in lower or "today" in lower:
        return {"deadline_days": 0, "deadline_text": "today", "deadline_source": "relative email text"}
    if "tomorrow" in lower:
        return {"deadline_days": 1, "deadline_text": "tomorrow", "deadline_source": "relative email text"}
    if "this week" in lower:
        return {"deadline_days": 5, "deadline_text": "this week", "deadline_source": "relative email text"}
    if message_type == "event":
        return {"deadline_days": 7, "deadline_text": "event follow-up window", "deadline_source": "message type fallback"}
    if message_type == "recruiter_message":
        return {"deadline_days": 3, "deadline_text": "recruiter response window", "deadline_source": "message type fallback"}
    if message_type == "application_confirmation":
        return {"deadline_days": 5, "deadline_text": "follow-up window", "deadline_source": "message type fallback"}

    return {"deadline_days": 14, "deadline_text": "not found", "deadline_source": "default fallback"}


def infer_job_attributes(text):
    lines = split_email_lines(text)
    attributes = {
        "employment_type": None,
        "compensation": None,
        "work_mode": None,
        "extracted_location": None,
        "job_facts_line": None,
    }

    employment_terms = ("full-time", "part-time", "internship", "intern", "contract", "temporary", "co-op")
    work_modes = ("remote", "hybrid", "onsite", "on-site")

    for line in lines:
        lower = line.lower()
        if not any(term in lower for term in employment_terms + work_modes) and "$" not in line:
            continue

        parts = [clean_extracted_label(part) for part in re.split(r"\s*(?:\u2022|\||;)\s*", line) if clean_extracted_label(part)]
        if not parts:
            parts = [line]

        for part in parts:
            part_lower = part.lower()
            if not attributes["compensation"] and (
                "$" in part or "/yr" in part_lower or "/mo" in part_lower or "salary" in part_lower
            ):
                attributes["compensation"] = part
                continue

            if not attributes["employment_type"] and any(term in part_lower for term in employment_terms):
                attributes["employment_type"] = part
                continue

            if not attributes["work_mode"]:
                for mode in work_modes:
                    if mode in part_lower:
                        attributes["work_mode"] = "Onsite" if mode == "on-site" else mode.title()
                        break

            if not attributes["extracted_location"]:
                location_part = re.sub(r"\((Remote|Hybrid|Onsite|On-site)\)", "", part, flags=re.IGNORECASE)
                if re.search(r"\b[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}\b", location_part):
                    attributes["extracted_location"] = clean_extracted_label(location_part)
                elif part_lower in work_modes:
                    attributes["extracted_location"] = "Remote" if part_lower == "remote" else None

        if any(attributes.get(key) for key in ("employment_type", "compensation", "work_mode", "extracted_location")):
            attributes["job_facts_line"] = line
            break

    return attributes


def infer_title_company_from_text(text, fallback_title, fallback_company):
    saved_job = re.search(
        r"your saved job at (?P<company>.+?) is about to close",
        text or "",
        flags=re.IGNORECASE,
    )
    if saved_job:
        company = clean_extracted_label(saved_job.group("company"))
        title_match = re.search(
            r"applications for (?P<title>.+?) are due",
            text or "",
            flags=re.IGNORECASE | re.DOTALL,
        )
        if title_match:
            title = clean_extracted_label(title_match.group("title"))
            return title, company

        lines = split_email_lines(text)
        for index, line in enumerate(lines):
            if line.lower() == company.lower() and index + 1 < len(lines):
                return clean_extracted_label(lines[index + 1]), company

    patterns = [
        r"^new\s+(?P<title>.+?)\s+at\s+(?P<company>[^\n]+)",
        r"(?:thank you|thanks) for applying to (?:the )?(?P<title>.+?) (?:at|with) (?P<company>[^\n]+)",
        r"application (?:received|submitted) for (?:the )?(?P<title>.+?) (?:at|with) (?P<company>[^\n]+)",
        r"you applied to (?:the )?(?P<title>.+?) (?:at|with) (?P<company>[^\n]+)",
        r"your saved job at (?P<company>.+?) is about to close",
        r"(?P<title>[A-Z][A-Za-z0-9 &/,+#.-]{2,90}?) at (?P<company>[A-Z][A-Za-z0-9 &/,+#.-]{2,80})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if not match:
            continue

        title = clean_extracted_label(match.groupdict().get("title") or fallback_title)
        company = clean_extracted_label(match.group("company"))
        if title and company:
            return title, company

    return fallback_title, fallback_company


def infer_location_from_text(text):
    attributes = infer_job_attributes(text)
    if attributes.get("extracted_location"):
        return attributes["extracted_location"]

    location_patterns = [
        r"\b(?:location|located in):\s*(?P<location>[A-Z][A-Za-z .,-]+)",
        r"\bin\s+(?P<location>(?:Remote|Hybrid|[A-Z][A-Za-z .]+,\s*[A-Z]{2}))\b",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if match:
            return clean_extracted_label(match.group("location"))

    if re.search(r"\bremote\b", text or "", flags=re.IGNORECASE):
        return "Remote"

    return "Not specified"


def infer_deadline_days(text, received_at=None, message_type="job"):
    return infer_deadline_info(text, received_at=received_at, message_type=message_type)["deadline_days"]


def build_extraction_evidence(email, title, company, location, deadline_info, attributes, picked_link, apply_url, has_real_apply_url):
    return {
        "subject": email.get("subject"),
        "sender": email.get("sender"),
        "title_source": "email subject/body pattern" if title else "fallback",
        "company_source": "email subject/body pattern" if company else "fallback",
        "location_source": "job facts line" if attributes.get("extracted_location") else "body text/default",
        "deadline_source": deadline_info.get("deadline_source"),
        "job_facts_line": attributes.get("job_facts_line"),
        "apply_url_source": (
            "explicit CTA link"
            if picked_link and picked_link.get("is_cta")
            else ("Handshake posting URL" if has_real_apply_url else "no confirmed link")
        ),
        "link_confidence": "confirmed" if has_real_apply_url else "not found",
        "apply_url": apply_url if has_real_apply_url else None,
    }


def stable_email_job_id(email_id, title=""):
    raw = str(email_id or title or "handshake-email").encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:10], 16)


def extract_jobs_from_gmail_emails(max_results=GMAIL_MAX_RESULTS, lookback_days=GMAIL_LOOKBACK_DAYS, service=None):
    emails = fetch_handshake_emails(
        max_results=max_results,
        lookback_days=lookback_days,
        service=service,
    )
    jobs = []

    for email in emails:
        full_text = f"{email.get('subject', '')}\n{email.get('body', '')}"
        links = extract_all_links(html=email.get("html"), text=full_text)
        skills = extract_skills(full_text)
        message_type = infer_message_type(email)

        title = email.get("subject") or "Handshake Opportunity"
        title = title.replace("Fwd:", "").replace("FW:", "").strip()

        company = "Handshake"
        sender = email.get("sender", "")
        sender_match = re.search(r"<(.+?)>", sender)

        if sender_match:
            sender_email = sender_match.group(1)
        else:
            sender_email = sender

        sender_is_handshake = "@" in sender_email and (
            "handshake" in sender_email.lower() or "joinhandshake.com" in sender_email.lower()
        )

        if not sender_is_handshake and "@" in sender_email:
            company = sender_email.split("@")[-1].split(".")[0].title()

        title, company = infer_title_company_from_text(full_text, title, company)

        if len(title) > 90:
            title = title[:90] + "..."

        if message_type == "event":
            user_interest = 3

        elif message_type == "recruiter_message":
            user_interest = 4

        else:
            user_interest = 4

        deadline_info = infer_deadline_info(
            full_text,
            received_at=email.get("received_at"),
            message_type=message_type,
        )
        deadline_days = deadline_info["deadline_days"]

        status = "applied" if message_type == "application_confirmation" else "not_applied"
        stable_id = stable_email_job_id(email.get("email_id"), title)

        picked_link = pick_application_link(html=email.get("html"), text=full_text)
        apply_url = picked_link["href"] if picked_link else None
        if apply_url:
            resolved_url = resolve_handshake_tracking_url(apply_url)
            if resolved_url:
                apply_url = resolved_url
        has_real_apply_url = is_real_apply_url(
            apply_url,
            trusted_cta=bool(picked_link and picked_link["is_cta"]),
        )
        attributes = infer_job_attributes(full_text)
        location = infer_location_from_text(full_text)
        extraction_evidence = build_extraction_evidence(
            email,
            title,
            company,
            location,
            deadline_info,
            attributes,
            picked_link,
            apply_url,
            has_real_apply_url,
        )

        # The Gmail search query matches on the word "Handshake" appearing
        # anywhere in a message, not just messages actually sent by
        # Handshake (see build_handshake_gmail_query) — so newsletters or
        # unrelated emails that merely mention Handshake can slip through.
        # Only keep something as a tracked "job" if it's actually from
        # Handshake, or if we found a link we're confident enough to call
        # Apply on.
        if not sender_is_handshake and not has_real_apply_url:
            continue

        # Roundups, recommendations, events, and recruiter/profile-signal
        # notices can contain job-like words and links, but they are not one
        # concrete opportunity the user can track or apply to.
        if not is_trackable_message_type(message_type):
            continue

        if message_type in ("job", "internship") and not has_real_apply_url:
            continue

        job = {
            "id": stable_id,
            "title": title or "Handshake Opportunity",
            "company": company or "Unknown company",
            "location": location,
            "employment_type": attributes.get("employment_type"),
            "compensation": attributes.get("compensation"),
            "work_mode": attributes.get("work_mode"),
            "required_skills": skills,
            "description": (email.get("body") or email.get("snippet") or "No description extracted yet.")[:1200],
            "deadline_days": deadline_days,
            "deadline_text": deadline_info.get("deadline_text"),
            "deadline_source": deadline_info.get("deadline_source"),
            "status": status,
            "user_interest": user_interest,
            "source": "gmail_handshake",
            "message_type": message_type,
            "email_subject": email.get("subject"),
            "email_sender": email.get("sender"),
            "email_id": email.get("email_id"),
            "thread_id": email.get("thread_id"),
            "received_at": email.get("received_at"),
            "apply_url": apply_url if has_real_apply_url else None,
            "has_real_apply_url": has_real_apply_url,
            "apply_url_source": extraction_evidence["apply_url_source"],
            "link_confidence": extraction_evidence["link_confidence"],
            "extraction_evidence": extraction_evidence,
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
