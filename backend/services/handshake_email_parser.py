import re
from datetime import datetime
from email.utils import parsedate_to_datetime


DETAIL_KEYWORDS = (
    "full-time",
    "part-time",
    "internship",
    "contract",
    "temporary",
    "co-op",
    "remote",
    "hybrid",
    "onsite",
    "on-site",
    "/yr",
    "/hr",
)

TARGET_SKILLS = [
    "python",
    "sql",
    "machine learning",
    "ai",
    "data analyst",
    "data science",
    "software engineer",
    "analytics",
    "tableau",
    "aws",
    "azure",
]


def clean_text(value):
    value = str(value or "").replace("\xa0", " ")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def lines_from_text(text):
    return [line.strip() for line in clean_text(text).split("\n") if line.strip()]


def normalize_date(value):
    value = str(value or "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return value


def posted_date_from_received(received_at):
    if not received_at:
        return ""
    try:
        return parsedate_to_datetime(received_at).strftime("%Y-%m-%d")
    except Exception:
        try:
            return datetime.fromisoformat(received_at).strftime("%Y-%m-%d")
        except Exception:
            return str(received_at)


def parse_deadline(text):
    patterns = [
        r"Applications? are due\s+(.+?)(?:\.|\n|$)",
        r"Apply by\s+(.+?)(?:\.|\n|$)",
        r"Application deadline[:\s]+(.+?)(?:\.|\n|$)",
        r"Deadline[:\s]+(.+?)(?:\.|\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if not match:
            continue
        raw = re.sub(r"\s+", " ", match.group(1)).strip()
        date_match = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", raw)
        return normalize_date(date_match.group(1)) if date_match else raw, raw
    return "", ""


def parse_subject(subject):
    subject = subject or ""
    match = re.search(r"^New\s+(.+?)\s+at\s+(.+)$", subject, re.IGNORECASE)
    if match:
        return match.group(2).strip(), match.group(1).strip()

    match = re.search(
        r",\s*(.+?)\s+sees you as a top applicant for\s+(.+?)(?:\s+and more)?$",
        subject,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return "", ""


def is_detail_line(line):
    lower = line.lower()
    return "•" in line and any(keyword in lower for keyword in DETAIL_KEYWORDS)


def parse_detail_line(line):
    result = {
        "salary": "",
        "job_type": "Unknown",
        "location": "Not specified",
        "work_mode": "Unknown",
    }
    tokens = [token.strip() for token in re.split(r"\s*•\s*", line or "") if token.strip()]

    for token in tokens:
        lower = token.lower()
        if lower == "promoted":
            continue
        if "$" in token or "/yr" in lower or "/hr" in lower:
            result["salary"] = token
        elif any(kind in lower for kind in ["full-time", "part-time", "internship", "contract", "co-op"]):
            result["job_type"] = token
        else:
            result["location"] = token

    mode_match = re.search(r"\((Remote|Hybrid|Onsite|On-site)\)", result["location"], re.IGNORECASE)
    if mode_match:
        result["work_mode"] = mode_match.group(1).replace("On-site", "Onsite").title()
        result["location"] = re.sub(
            r"\((Remote|Hybrid|Onsite|On-site)\)",
            "",
            result["location"],
            flags=re.IGNORECASE,
        ).strip()
    elif "remote" in result["location"].lower():
        result["work_mode"] = "Remote"
    elif "hybrid" in result["location"].lower():
        result["work_mode"] = "Hybrid"
    elif "onsite" in result["location"].lower() or "on-site" in result["location"].lower():
        result["work_mode"] = "Onsite"

    return result


def extract_skills(text):
    lower = (text or "").lower()
    return [skill for skill in TARGET_SKILLS if skill in lower]


def extract_links(text):
    links = re.findall(r"https?://[^\s\"'>]+", text or "")
    cleaned = []
    for link in links:
        link = link.rstrip(".,)]}").replace("&amp;", "&")
        if link not in cleaned:
            cleaned.append(link)
    return cleaned


def is_probable_job_link(link):
    lower = (link or "").lower()
    if not lower.startswith("http"):
        return False
    blocked = [
        "unsubscribe",
        "preferences",
        "notification",
        "privacy",
        "terms",
        "help",
        "support",
        "mailto:",
    ]
    if any(token in lower for token in blocked):
        return False
    if "joinhandshake.com" in lower and any(token in lower for token in ["job", "jobs", "posting", "postings", "stu"]):
        return True
    if "joinhandshake.com" in lower:
        return True
    return False


def job_links_from_text(text):
    links = extract_links(text)
    job_links = [link for link in links if is_probable_job_link(link)]
    return job_links or links


def score_job(job):
    score = 0
    title = (job.get("title") or "").lower()
    subject = (job.get("email_subject") or "").lower()

    if any(term in title for term in ["data", "analyst", "ai", "machine learning", "software", "contract analyst"]):
        score += 30
    else:
        score += 14

    if job.get("deadline"):
        score += 20
    if job.get("apply_url"):
        score += 15
    if job.get("salary"):
        score += 10
    if job.get("location") and job.get("location") != "Not specified":
        score += 8
    if job.get("work_mode") in {"Remote", "Hybrid"}:
        score += 7
    if "top applicant" in subject:
        score += 10

    score = min(score, 100)
    if score >= 75:
        label = "High"
    elif score >= 50:
        label = "Medium"
    else:
        label = "Low"
    return score, label


def parse_handshake_email(email):
    subject = email.get("subject") or ""
    body = clean_text(email.get("body") or "")
    email_id = email.get("email_id")
    received_at = email.get("received_at")
    lines = lines_from_text(body)
    deadline, deadline_text = parse_deadline(body)
    posted_date = posted_date_from_received(received_at)
    links = job_links_from_text(body)
    jobs = []

    is_roundup = "round-up" in subject.lower() or "and more" in subject.lower() or "weekly jobs" in body.lower()

    if is_roundup:
        for index, line in enumerate(lines):
            if not is_detail_line(line) or index < 2:
                continue
            company = lines[index - 2].strip()
            title = lines[index - 1].strip()
            if company.lower().startswith("your weekly") or title.lower().startswith("new jobs"):
                continue
            details = parse_detail_line(line)
            job = {
                "email_id": email_id,
                "title": title,
                "company": company,
                "location": details["location"],
                "salary": details["salary"],
                "job_type": details["job_type"],
                "work_mode": details["work_mode"],
                "posted_date": posted_date,
                "deadline": deadline,
                "deadline_text": deadline_text,
                "apply_url": links[min(len(jobs), len(links) - 1)] if links else None,
                "source": "gmail_handshake",
                "message_type": "job",
                "email_subject": subject,
                "received_at": received_at,
                "raw_details": line,
                "required_skills": extract_skills(f"{title} {body}"),
            }
            job["priority_score"], job["priority_label"] = score_job(job)
            jobs.append(job)
        return jobs

    company, title = parse_subject(subject)
    detail_line = ""
    for index, line in enumerate(lines):
        if title and line.lower() == title.lower() and index + 1 < len(lines):
            detail_line = lines[index + 1]
            break
    if not detail_line:
        detail_line = next((line for line in lines if is_detail_line(line)), "")
    if (not company or not title) and detail_line in lines:
        idx = lines.index(detail_line)
        if idx >= 2:
            company = company or lines[idx - 2]
            title = title or lines[idx - 1]
    if not company or not title:
        return []

    details = parse_detail_line(detail_line)
    job = {
        "email_id": email_id,
        "title": title,
        "company": company,
        "location": details["location"],
        "salary": details["salary"],
        "job_type": details["job_type"],
        "work_mode": details["work_mode"],
        "posted_date": posted_date,
        "deadline": deadline,
        "deadline_text": deadline_text,
        "apply_url": links[0] if links else None,
        "source": "gmail_handshake",
        "message_type": "job",
        "email_subject": subject,
        "received_at": received_at,
        "raw_details": detail_line,
        "required_skills": extract_skills(f"{title} {body}"),
    }
    job["priority_score"], job["priority_label"] = score_job(job)
    return [job]
