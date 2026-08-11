from datetime import date, datetime

from services.job_matcher import calculate_match_score, get_missing_skills


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _deadline_days(job):
    if job.get("deadline_days") is not None:
        return int(job.get("deadline_days"))

    deadline = _parse_date(job.get("deadline"))
    if deadline:
        return max((deadline - date.today()).days, 0)

    return 30


def _status(job):
    return (
        job.get("status")
        or job.get("application_status")
        or "saved"
    )


def _user_interest(job):
    if job.get("user_interest") is not None:
        return int(job.get("user_interest"))

    priority_score = float(job.get("priority_score") or 0)
    if priority_score >= 75:
        return 5
    if priority_score >= 50:
        return 4
    if priority_score >= 25:
        return 3
    return 2


def _job_id(job, index):
    return job.get("id") or job.get("job_id") or job.get("email_id") or index + 1


def _required_skills(job):
    skills = job.get("required_skills") or []
    if isinstance(skills, str):
        return [skill.strip() for skill in skills.split(",") if skill.strip()]
    return skills


def assign_priority(match_score, deadline_days, user_interest, status):
    status = str(status or "saved").lower()

    if status in {"applied", "follow up", "follow-up"}:
        return "Follow Up"

    if deadline_days <= 2 and match_score >= 70:
        return "Do Now"

    if deadline_days <= 5 and match_score >= 60:
        return "Do Today"

    if match_score >= 80 and user_interest >= 4:
        return "High Value"

    if match_score >= 60:
        return "Do This Week"

    if match_score >= 40:
        return "Tailor First"

    return "Low Priority"


def generate_reason(priority, match_score, deadline_days, missing_skills):
    if priority == "Do Now":
        return f"High match score of {match_score}% and deadline is in {deadline_days} days."

    if priority == "Do Today":
        return f"Good match score of {match_score}% with an approaching deadline."

    if priority == "High Value":
        return f"Strong role fit with {match_score}% match and high user interest."

    if priority == "Follow Up":
        return "You already applied. It may be time to follow up or prepare for next steps."

    if priority == "Tailor First":
        return f"Moderate fit. Missing skills include: {', '.join(missing_skills[:3])}."

    if priority == "Do This Week":
        return f"Decent match score of {match_score}%. Worth applying after minor tailoring."

    return "Low match score. This may not be worth immediate attention."


def suggest_action(priority, job_title, company, missing_skills):
    if priority == "Do Now":
        return f"Apply to {job_title} at {company} today."

    if priority == "Do Today":
        return f"Tailor your resume and apply to {job_title} today."

    if priority == "High Value":
        return f"Prepare a strong application for {job_title}; this is a valuable opportunity."

    if priority == "Follow Up":
        return f"Send a polite follow-up email to {company}."

    if priority == "Tailor First":
        return f"Add relevant keywords such as {', '.join(missing_skills[:3])} before applying."

    if priority == "Do This Week":
        return "Add this job to your weekly application plan."

    return f"Save or skip {job_title} for now."


def generate_priority_tasks(resume_profile, jobs):
    tasks = []

    for index, job in enumerate(jobs):
        required_skills = _required_skills(job)
        deadline_days = _deadline_days(job)
        user_interest = _user_interest(job)
        status = _status(job)

        match_score = calculate_match_score(
            resume_profile["skills"],
            required_skills,
        )

        missing_skills = get_missing_skills(
            resume_profile["skills"],
            required_skills,
        )

        priority = assign_priority(
            match_score,
            deadline_days,
            user_interest,
            status,
        )

        title = job.get("title") or "Unknown role"
        company = job.get("company") or "Unknown company"

        tasks.append(
            {
                "job_id": _job_id(job, index),
                "task_title": f"{priority}: {title} at {company}",
                "priority": priority,
                "reason": generate_reason(priority, match_score, deadline_days, missing_skills),
                "suggested_action": suggest_action(priority, title, company, missing_skills),
                "deadline_days": deadline_days,
                "match_score": match_score,
                "missing_skills": missing_skills,
                "source": job.get("source"),
                "apply_url": job.get("apply_url"),
            }
        )

    priority_order = {
        "Do Now": 1,
        "Do Today": 2,
        "Follow Up": 3,
        "High Value": 4,
        "Do This Week": 5,
        "Tailor First": 6,
        "Low Priority": 7,
    }

    return sorted(tasks, key=lambda task: priority_order.get(task["priority"], 99))
