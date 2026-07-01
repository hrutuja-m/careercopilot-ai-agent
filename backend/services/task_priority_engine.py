from services.job_matcher import calculate_match_score, get_missing_skills


def assign_priority(match_score, deadline_days, user_interest, status):
    status = status.lower()

    if status == "applied":
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

    for job in jobs:
        match_score = calculate_match_score(
            resume_profile["skills"],
            job["required_skills"],
        )

        missing_skills = get_missing_skills(
            resume_profile["skills"],
            job["required_skills"],
        )

        priority = assign_priority(
            match_score,
            job["deadline_days"],
            job["user_interest"],
            job["status"],
        )

        tasks.append(
            {
                "job_id": job["id"],
                "task_title": f"{priority}: {job['title']} at {job['company']}",
                "priority": priority,
                "reason": generate_reason(priority, match_score, job["deadline_days"], missing_skills),
                "suggested_action": suggest_action(priority, job["title"], job["company"], missing_skills),
                "deadline_days": job["deadline_days"],
                "match_score": match_score,
                "missing_skills": missing_skills,
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