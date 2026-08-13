from datetime import date, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.task_priority_engine import generate_priority_tasks


def _job_by_id(jobs):
    return {job.get("id"): job for job in jobs}


def _task_card(task, job_lookup):
    job = job_lookup.get(task["job_id"], {})
    # Trust the job's own has_real_apply_url — it's computed once, with
    # full context (e.g. whether the link's email text was an explicit
    # "Apply" CTA), by database/jobs_store.py. No fallback search URL is
    # fabricated here: if there's no confirmed-real link, apply_url is
    # honestly null, same as every other endpoint. A chat surface that
    # quietly sends someone to a generic search page instead of saying "no
    # link found yet" is exactly the kind of misleading "it looks like
    # Apply but isn't" button this was meant to fix.
    has_real_link = bool(job.get("has_real_apply_url"))
    return {
        "job_id": task["job_id"],
        "title": job.get("title", task["task_title"]),
        "company": job.get("company", "Unknown company"),
        "priority": task["priority"],
        "reason": task["reason"],
        "suggested_action": task["suggested_action"],
        "deadline_days": task["deadline_days"],
        "match_score": task["match_score"],
        "missing_skills": task.get("missing_skills", []),
        "apply_url": job.get("apply_url") if has_real_link else None,
        "has_real_apply_url": has_real_link,
        "status": job.get("status", "not_applied"),
    }


def _next_weekdays():
    today = date.today()
    return [today + timedelta(days=offset) for offset in range(7)]


def _clip_text(value, limit=220):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _profile_document(resume_profile):
    if not resume_profile:
        return None

    parts = [
        resume_profile.get("name"),
        " ".join(resume_profile.get("target_roles", []) or []),
        " ".join(resume_profile.get("skills", []) or []),
        resume_profile.get("summary"),
    ]
    text = " ".join(str(part or "") for part in parts).strip()
    if not text:
        return None

    return {
        "type": "profile",
        "title": "Resume profile",
        "text": text,
        "snippet": _clip_text(text),
    }


def _retrieval_documents(resume_profile, jobs, tasks):
    documents = []
    profile_doc = _profile_document(resume_profile)
    if profile_doc:
        documents.append(profile_doc)

    job_lookup = _job_by_id(jobs)
    for task in tasks:
        job = job_lookup.get(task["job_id"], {})
        text = " ".join(
            str(part or "")
            for part in (
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("status"),
                job.get("message_type"),
                " ".join(job.get("required_skills", []) or []),
                job.get("description"),
                task.get("priority"),
                task.get("reason"),
                task.get("suggested_action"),
                " ".join(task.get("missing_skills", []) or []),
            )
        ).strip()
        if not text:
            continue

        documents.append(
            {
                "type": "job",
                "job_id": task["job_id"],
                "title": job.get("title", task.get("task_title")),
                "company": job.get("company", "Unknown company"),
                "priority": task.get("priority"),
                "match_score": task.get("match_score"),
                "text": text,
                "snippet": _clip_text(
                    f"{job.get('company', 'Unknown company')} - {job.get('title', task.get('task_title'))}: {task.get('reason') or job.get('description')}"
                ),
            }
        )

    return documents


def retrieve_relevant_context(user_message, resume_profile, jobs, tasks, limit=4):
    documents = _retrieval_documents(resume_profile, jobs, tasks)
    query = (user_message or "").strip()
    if not query or not documents:
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([query] + [doc["text"] for doc in documents])
        scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    except ValueError:
        return []

    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    results = []
    for idx, score in ranked[:limit]:
        if score <= 0:
            continue
        doc = dict(documents[idx])
        doc.pop("text", None)
        doc["score"] = round(float(score), 4)
        results.append(doc)

    return results


def build_weekly_plan(tasks, job_lookup, daily_goal):
    open_tasks = [task for task in tasks if task["priority"] not in ("Closed", "Follow Up")]
    followups = [task for task in tasks if task["priority"] == "Follow Up"]
    plan = []
    cursor = 0

    for day in _next_weekdays():
        actions = []
        for _ in range(max(int(daily_goal or 1), 1)):
            if cursor >= len(open_tasks):
                break
            actions.append(_task_card(open_tasks[cursor], job_lookup))
            cursor += 1

        if not actions and followups:
            actions.append(_task_card(followups.pop(0), job_lookup))

        plan.append(
            {
                "date": day.isoformat(),
                "day_name": day.strftime("%A"),
                "display_date": day.strftime("%B %-d, %Y"),
                "goal": daily_goal,
                "actions": actions,
            }
        )

    return plan


def career_chatbot_response(user_message, resume_profile, jobs, goals=None):
    goals = goals or {}
    daily_goal = int(goals.get("daily_application_goal", 3))
    message = user_message.lower()
    tasks = generate_priority_tasks(resume_profile, jobs)
    job_lookup = _job_by_id(jobs)
    top_tasks = [_task_card(task, job_lookup) for task in tasks[:5]]
    weekly_plan = build_weekly_plan(tasks, job_lookup, daily_goal)
    retrieved_context = retrieve_relevant_context(user_message, resume_profile, jobs, tasks)
    retrieved_job_ids = [
        item["job_id"]
        for item in retrieved_context
        if item.get("type") == "job" and item.get("job_id") is not None
    ]
    retrieved_jobs = [
        _task_card(task, job_lookup)
        for task in tasks
        if task["job_id"] in retrieved_job_ids
    ]

    response = {
        "summary": "I looked at your tracked opportunities, deadlines, match scores, and application statuses.",
        "sections": [],
        "jobs": (retrieved_jobs or top_tasks)[:3],
        "weekly_plan": [],
        "retrieved_context": retrieved_context,
        "quick_actions": [
            {"label": "Open tracker", "action": "tracker"},
            {"label": "Review profile goal", "action": "profile-goals"},
        ],
    }

    if "week" in message or "plan" in message:
        response["summary"] = f"Here is a 7-day plan using your daily goal of {daily_goal} application{'s' if daily_goal != 1 else ''}."
        response["weekly_plan"] = weekly_plan
        response["sections"].append(
            {
                "title": "How to work the plan",
                "items": [
                    "Start with the earliest deadlines inside each priority bucket.",
                    "Use the Apply link when one is shown; if a job has no link yet, find the posting yourself and update its status once you've applied.",
                    "Mark jobs Applied as you finish them so the progress tracker updates.",
                ],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if "best job" in message or "highest match" in message or "best match" in message:
        best = max(top_tasks, key=lambda item: item["match_score"]) if top_tasks else None
        response["summary"] = "Your strongest match is the role with the best profile fit among active tracked jobs."
        response["jobs"] = [best] if best else []
        response["sections"].append(
            {
                "title": "Why this is strong",
                "items": [best["reason"]] if best else ["No tracked jobs are loaded yet."],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if "missing skills" in message or "skills am i missing" in message:
        items = []
        for card in top_tasks:
            missing = card.get("missing_skills", [])
            if missing:
                items.append(f"{card['company']} - {card['title']}: {', '.join(missing[:5])}")
        response["summary"] = "Here are the most important skill gaps from your current priority jobs."
        response["sections"].append(
            {
                "title": "Skill gaps",
                "items": items or ["No major missing skills were detected in the current top jobs."],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if "follow up" in message or "follow-up" in message:
        followups = [_task_card(task, job_lookup) for task in tasks if task["priority"] == "Follow Up"]
        response["summary"] = "These are the applications that may need follow-up or interview prep."
        response["jobs"] = followups[:5]
        response["sections"].append(
            {
                "title": "Next move",
                "items": [item["suggested_action"] for item in followups[:5]] or ["No follow-ups are due right now."],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if "today" in message or "do first" in message or "priority" in message:
        response["summary"] = f"Today, aim for {daily_goal} application{'s' if daily_goal != 1 else ''}; start with these highest-priority actions."
        response["jobs"] = top_tasks[:daily_goal]
        response["sections"].append(
            {
                "title": "Today",
                "items": [item["suggested_action"] for item in top_tasks[:daily_goal]] or ["No priority tasks are loaded yet."],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if "explain" in message or "why" in message:
        top = top_tasks[0] if top_tasks else None
        response["summary"] = "The priority engine weighs deadline urgency, match score, application status, and interest."
        response["jobs"] = [top] if top else []
        response["sections"].append(
            {
                "title": "Top priority reasoning",
                "items": [top["reason"]] if top else ["No priority tasks are loaded yet."],
            }
        )
        if retrieved_context:
            response["sections"].append(
                {
                    "title": "Evidence used",
                    "items": [item["snippet"] for item in retrieved_context[:3]],
                }
            )
        return response

    if retrieved_context:
        response["summary"] = "I found the most relevant tracker context for your question."
        response["sections"].append(
            {
                "title": "Evidence used",
                "items": [item["snippet"] for item in retrieved_context[:4]],
            }
        )
    else:
        response["summary"] = "I can help you decide what to apply to, what to follow up on, and how to plan your week."
        response["sections"].append(
            {
                "title": "Try asking",
                "items": [
                    "What should I do today?",
                    "Make me a weekly plan.",
                    "Which job is my best match?",
                    "What skills am I missing?",
                ],
            }
        )
    return response
