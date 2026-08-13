from services.job_matcher import calculate_match_score, get_missing_skills


EVENT_TYPES = {"event", "career_email"}
JOB_TYPES = {"job", "internship"}
FOLLOW_UP_TYPES = {"recruiter_message"}


def get_recommendation_label(match_score, message_type):
    if message_type in EVENT_TYPES:
        return "Career Event"

    if message_type in FOLLOW_UP_TYPES:
        return "Follow Up"

    if match_score >= 80:
        return "Highly Recommended"

    if match_score >= 60:
        return "Recommended"

    if match_score >= 40:
        return "Consider After Tailoring"

    return "Low Fit"


def build_recommendation_reason(job, match_score, missing_skills, message_type):
    if message_type in EVENT_TYPES:
        return "This is a career event or informational opportunity, so it is ranked as a networking/action item instead of a resume-match job."

    if message_type in FOLLOW_UP_TYPES:
        return "This appears to be a recruiter or follow-up message, so the next action is to respond or review the opportunity."

    if not job.get("required_skills"):
        return "No clear required skills were extracted from this email, so the match score is kept low until more job details are available."

    if missing_skills:
        return f"This role has a {round(match_score / 10, 1)}/10 profile match. Missing skills include: {', '.join(missing_skills[:3])}."

    return f"This role has a {round(match_score / 10, 1)}/10 profile match based on your resume skills."


def recommend_jobs(resume_profile, jobs):
    recommendations = []

    for job in jobs:
        message_type = job.get("message_type", "job")
        required_skills = job.get("required_skills", [])

        if message_type in EVENT_TYPES:
            match_score = 0
            missing_skills = []

        elif message_type in FOLLOW_UP_TYPES:
            match_score = 50
            missing_skills = []

        elif not required_skills:
            match_score = 20
            missing_skills = []

        else:
            match_score = calculate_match_score(
                resume_profile["skills"],
                required_skills,
            )

            missing_skills = get_missing_skills(
                resume_profile["skills"],
                required_skills,
            )

        recommendations.append(
            {
                "job_id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "source": job.get("source"),
                "message_type": message_type,
                "apply_url": job.get("apply_url"),
                "match_score": match_score,
                "match_score_out_of_10": round(match_score / 10, 1),
                "missing_skills": missing_skills,
                "recommendation": get_recommendation_label(match_score, message_type),
                "reason": build_recommendation_reason(
                    job,
                    match_score,
                    missing_skills,
                    message_type,
                ),
            }
        )

    return sorted(
        recommendations,
        key=lambda item: (
            0 if item["message_type"] in JOB_TYPES else 1,
            -item["match_score"],
        ),
    )