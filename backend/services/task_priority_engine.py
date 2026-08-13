import re
from datetime import datetime, timezone

from services.job_matcher import calculate_match_score, get_missing_skills


ROLE_SIGNAL_SKILLS = {
    "data scientist": {"data science", "machine learning", "python", "sql", "model evaluation"},
    "data analyst": {"data analytics", "sql", "excel", "tableau"},
    "analytical": {"data analytics", "sql", "excel"},
    "analyst": {"data analytics", "sql", "excel"},
    "data engineer": {"data pipelines", "sql", "python", "aws"},
    "machine learning engineer": {"machine learning", "python", "deep learning"},
    "machine learning": {"machine learning", "python"},
    "ml engineer": {"machine learning", "python", "deep learning"},
    "ai engineer": {"generative ai", "llm", "machine learning", "python"},
    "ai ": {"generative ai", "llm", "machine learning", "python"},
    "agentic ai": {"generative ai", "llm", "prompt engineering", "python"},
    "systems research engineer": {"python", "machine learning", "model evaluation"},
    "modeling and simulation": {"python", "model evaluation", "machine learning"},
}

STOP_WORDS = {"new", "senior", "principal", "lead", "associate", "program", "the", "and", "at"}

GENERIC_TITLES = {"handshake opportunity", "opportunity", "job", "internship"}
GENERIC_COMPANIES = {"handshake", "unknown company", "unknown"}


def _normalize_text(value):
    return " ".join(str(value or "").lower().replace("&", " ").split())


def _tokenize(value):
    cleaned = "".join(char if char.isalnum() else " " for char in _normalize_text(value))
    return {token for token in cleaned.split() if token and token not in STOP_WORDS}


def _normalize_skills(skills):
    return {_normalize_text(skill) for skill in (skills or []) if _normalize_text(skill)}


def _whole_score(value):
    return int(round(float(value or 0)))


def _parse_deadline_date(deadline_text):
    text = re.sub(r"\s+", " ", str(deadline_text or "")).strip()
    if not text or text.lower() == "not found":
        return None

    text = re.sub(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s+\d{1,2}:\d{2}\s*(am|pm)?\s*[A-Z]{2,4}(?=,?\s+\d{4}$|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text.replace(".", ""), fmt).date()
        except ValueError:
            continue

    return None


def effective_deadline_days(job, today=None):
    due = _parse_deadline_date(job.get("deadline_text"))
    if due:
        base = today or datetime.now(timezone.utc).date()
        return (due - base).days

    try:
        return int(job.get("deadline_days"))
    except (TypeError, ValueError):
        return 9999


def _job_text(job):
    return _normalize_text(
        " ".join(
            str(part or "")
            for part in (
                job.get("title"),
                job.get("company"),
                job.get("description"),
                " ".join(job.get("required_skills", []) or []),
            )
        )
    )


def _inferred_role_skills(job):
    text = _job_text(job)
    inferred = set()
    for phrase, skills in ROLE_SIGNAL_SKILLS.items():
        if phrase in text:
            inferred.update(skills)
    return inferred


def _matched_and_missing(resume_skills, required_skills):
    resume_set = _normalize_skills(resume_skills)
    required_set = _normalize_skills(required_skills)
    return sorted(resume_set.intersection(required_set)), sorted(required_set.difference(resume_set))


def _target_role_score(resume_profile, job):
    title_tokens = _tokenize(job.get("title"))
    if not title_tokens:
        return 0.0

    best = 0.0
    for role in resume_profile.get("target_roles", []) or []:
        role_tokens = _tokenize(role)
        if not role_tokens:
            continue
        overlap = len(role_tokens.intersection(title_tokens)) / len(role_tokens)
        best = max(best, overlap * 100)
    return _whole_score(best)


def _experience_score(resume_profile, job):
    keywords = resume_profile.get("experience_keywords", []) or []
    if not keywords:
        return 0, []

    text = _job_text(job)
    matched = []
    normalized_keywords = sorted({normalized for keyword in keywords if (normalized := _normalize_text(keyword))})
    for keyword in keywords:
        normalized = _normalize_text(keyword)
        if normalized and normalized in text:
            matched.append(normalized)

    if not normalized_keywords:
        return 0, []

    return _whole_score((len(set(matched)) / len(normalized_keywords)) * 100), sorted(set(matched))


def _context_confidence_score(job):
    signals = []
    missing = []

    title = _normalize_text(job.get("title"))
    company = _normalize_text(job.get("company"))
    description = _normalize_text(job.get("description"))
    location = _normalize_text(job.get("location"))

    checks = [
        ("real apply link", bool(job.get("has_real_apply_url") and job.get("apply_url"))),
        ("specific title", bool(title and title not in GENERIC_TITLES and len(title) > 5)),
        ("specific company", bool(company and company not in GENERIC_COMPANIES)),
        ("location", bool(location and location != "not specified")),
        ("useful description", bool(description and description != "no description extracted yet." and len(description) >= 80)),
    ]

    for label, present in checks:
        if present:
            signals.append(label)
        else:
            missing.append(label)

    score = _whole_score((len(signals) / len(checks)) * 100)
    return score, signals, missing


def explain_job_match(resume_profile, job):
    """Return a fit score and the evidence behind it.

    Match score is intentionally about resume/profile fit only. Deadlines
    and application status are handled by assign_priority(), because urgency
    should not make a weak-fit job look like a strong fit.
    """
    resume_skills = resume_profile.get("skills", []) or []
    required_skills = job.get("required_skills", []) or []
    inferred_skills = sorted(_inferred_role_skills(job))

    matched_required, missing_required = _matched_and_missing(resume_skills, required_skills)
    matched_inferred, missing_inferred = _matched_and_missing(resume_skills, inferred_skills)

    explicit_skill_score = _whole_score(calculate_match_score(resume_skills, required_skills)) if required_skills else None
    inferred_skill_score = (
        _whole_score((len(matched_inferred) / len(inferred_skills)) * 100)
        if inferred_skills
        else 0
    )
    role_score = _target_role_score(resume_profile, job)
    experience_score, matched_experience = _experience_score(resume_profile, job)
    context_score, context_signals, context_missing = _context_confidence_score(job)

    if required_skills:
        components = [
            {
                "name": "Required skill match",
                "score": explicit_skill_score,
                "weight": 45,
                "reason": "Direct overlap between resume skills and skills explicitly found in the job email.",
                "matched": matched_required,
                "missing": missing_required,
            },
            {
                "name": "Target role fit",
                "score": role_score,
                "weight": 25,
                "reason": "Overlap between the job title and the target roles saved in the profile.",
                "matched": [],
                "missing": [],
            },
            {
                "name": "Inferred role signals",
                "score": inferred_skill_score,
                "weight": 15,
                "reason": "Skills inferred from role phrases such as Data Scientist, AI Engineer, or Machine Learning.",
                "matched": matched_inferred,
                "missing": missing_inferred,
            },
            {
                "name": "Experience keyword fit",
                "score": experience_score,
                "weight": 10,
                "reason": "Overlap between job text and experience keywords from the profile.",
                "matched": matched_experience,
                "missing": [],
            },
            {
                "name": "Job info quality",
                "score": context_score,
                "weight": 5,
                "reason": "Checks that the card has real title, company, link, location, and description.",
                "matched": context_signals,
                "missing": context_missing,
            },
        ]
    else:
        components = [
            {
                "name": "Target role fit",
                "score": role_score,
                "weight": 35,
                "reason": "No explicit skills were extracted, so title-to-target-role alignment carries more weight.",
                "matched": [],
                "missing": [],
            },
            {
                "name": "Inferred role signals",
                "score": inferred_skill_score,
                "weight": 40,
                "reason": "Skills inferred from the role title and description stand in for missing explicit requirements.",
                "matched": matched_inferred,
                "missing": missing_inferred,
            },
            {
                "name": "Experience keyword fit",
                "score": experience_score,
                "weight": 10,
                "reason": "Overlap between job text and experience keywords from the profile.",
                "matched": matched_experience,
                "missing": [],
            },
            {
                "name": "Job info quality",
                "score": context_score,
                "weight": 15,
                "reason": "Checks that the card has real title, company, link, location, and description.",
                "matched": context_signals,
                "missing": context_missing,
            },
        ]

    score = _whole_score(sum((component["score"] * component["weight"]) / 100 for component in components))
    strongest = max(components, key=lambda component: component["score"])
    weakest = min(components, key=lambda component: component["score"])

    return {
        "score": score,
        "components": components,
        "matched_skills": sorted(set(matched_required + matched_inferred)),
        "missing_skills": sorted(set(missing_required + missing_inferred)),
        "inferred_skills": inferred_skills,
        "summary": (
            f"{score}% fit. Best signal: {strongest['name'].lower()} "
            f"({strongest['score']}%). Main gap: {weakest['name'].lower()} "
            f"({weakest['score']}%)."
        ),
    }


def calculate_job_match_score(resume_profile, job):
    return explain_job_match(resume_profile, job)["score"]


def calculate_job_missing_skills(resume_profile, job):
    return explain_job_match(resume_profile, job)["missing_skills"]


def assign_priority(match_score, deadline_days, user_interest, status):
    status = (status or "").lower()

    if status == "rejected":
        return "Closed"

    if status == "interviewing":
        return "Prepare for Interview"

    if status == "applied":
        return "Follow Up"

    if status == "not_applied" and deadline_days <= 7:
        return "Do Today"

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


def generate_reason(priority, match_score, deadline_days, missing_skills, match_summary=None):
    fit_note = match_summary or f"{match_score}% profile fit."

    if priority == "Prepare for Interview":
        return f"You're interviewing for this role. {fit_note}"

    if priority == "Closed":
        return "This application was marked rejected, so it's no longer an active priority."

    if priority == "Do Now":
        return f"{fit_note} Deadline is in {deadline_days} days, so it needs immediate action."

    if priority == "Do Today":
        return f"{fit_note} Deadline is in {deadline_days} days, so this belongs in today's queue."

    if priority == "High Value":
        return f"{fit_note} This is high value because it has strong fit and high user interest."

    if priority == "Follow Up":
        return f"You already applied. {fit_note}"

    if priority == "Tailor First":
        return f"Moderate fit. Missing skills include: {', '.join(missing_skills[:3])}."

    if priority == "Do This Week":
        return f"Decent match score of {match_score}%. Worth applying after minor tailoring."

    return "Low match score. This may not be worth immediate attention."


def suggest_action(priority, job_title, company, missing_skills):
    if priority == "Prepare for Interview":
        return f"Prepare for your {job_title} interview at {company}: research common questions and review the job description."

    if priority == "Closed":
        return "No action needed. If you received feedback, it may be worth noting for next time."

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

    for job in jobs:
        match_breakdown = explain_job_match(resume_profile, job)
        match_score = match_breakdown["score"]
        missing_skills = match_breakdown["missing_skills"]

        deadline_days = effective_deadline_days(job)

        priority = assign_priority(
            match_score,
            deadline_days,
            job["user_interest"],
            job["status"],
        )

        tasks.append(
            {
                "job_id": job["id"],
                "task_title": f"{priority}: {job['title']} at {job['company']}",
                "priority": priority,
                "reason": generate_reason(
                    priority,
                    match_score,
                    deadline_days,
                    missing_skills,
                    match_breakdown["summary"],
                ),
                "suggested_action": suggest_action(priority, job["title"], job["company"], missing_skills),
                "deadline_days": deadline_days,
                "match_score": match_score,
                "match_breakdown": match_breakdown,
                "missing_skills": missing_skills,
            }
        )

    priority_order = {
        "Prepare for Interview": 0,
        "Do Now": 1,
        "Do Today": 2,
        "High Value": 3,
        "Do This Week": 4,
        "Tailor First": 5,
        "Follow Up": 6,
        "Low Priority": 7,
        "Closed": 8,
    }

    return sorted(
        tasks,
        key=lambda task: (
            priority_order.get(task["priority"], 99),
            task["deadline_days"],
            -task["match_score"],
        ),
    )
