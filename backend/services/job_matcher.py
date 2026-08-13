def calculate_match_score(resume_skills, job_required_skills):
    resume_set = {skill.lower() for skill in resume_skills}
    job_set = {skill.lower() for skill in job_required_skills}

    if not job_set:
        return 0.0

    matched_skills = resume_set.intersection(job_set)
    score = (len(matched_skills) / len(job_set)) * 100

    return round(score, 2)


def get_missing_skills(resume_skills, job_required_skills):
    resume_set = {skill.lower() for skill in resume_skills}
    job_set = {skill.lower() for skill in job_required_skills}

    return list(job_set.difference(resume_set))