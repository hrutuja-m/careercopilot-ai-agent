from services.task_priority_engine import generate_priority_tasks


def format_task(task):
    return (
        f"{task['task_title']}\n"
        f"Priority: {task['priority']}\n"
        f"Match Score: {task['match_score']}%\n"
        f"Reason: {task['reason']}\n"
        f"Action: {task['suggested_action']}"
    )


def get_today_plan(tasks):
    if not tasks:
        return "No career tasks are available yet. Sync jobs or add opportunities first, then I can build a focused plan."

    top_tasks = tasks[:3]

    response = "Today, focus on these career actions:\n\n"

    for index, task in enumerate(top_tasks, start=1):
        response += (
            f"{index}. {format_task(task)}\n\n"
        )

    response += (
        "My recommendation: finish the first task before opening new job boards. "
        "That keeps your search focused instead of chaotic."
    )

    return response


def get_best_match(tasks):
    if not tasks:
        return "No jobs are available yet, so I cannot choose a best match. Sync jobs or add opportunities first."

    best_task = max(tasks, key=lambda task: task["match_score"])

    return (
        f"Your strongest opportunity right now is:\n\n"
        f"{format_task(best_task)}\n\n"
        f"Why this matters: this role already matches your current profile well, "
        f"so it has better application ROI than a low-match role."
    )


def get_missing_skills_summary(tasks):
    if not tasks:
        return "No jobs are available yet, so there are no missing skills to summarize."

    response = "Here are missing skills by opportunity:\n\n"
    found_missing_skills = False

    for task in tasks:
        missing = task.get("missing_skills", [])

        if missing:
            found_missing_skills = True
            response += (
                f"- Job ID {task['job_id']}: "
                f"{', '.join(missing[:5])}\n"
            )

    if not found_missing_skills:
        return "No missing skills were found for the current jobs."

    response += (
        "\nUse this to update your resume keywords or decide what to learn next."
    )

    return response


def get_follow_up_plan(tasks):
    follow_up_tasks = [
        task for task in tasks
        if task["priority"] == "Follow Up"
    ]

    if not follow_up_tasks:
        return "No follow-up tasks right now. Keep applying and tracking new opportunities."

    response = "These applications may need follow-up:\n\n"

    for task in follow_up_tasks:
        response += (
            f"- {task['task_title']}\n"
            f"Action: {task['suggested_action']}\n\n"
        )

    return response


def get_weekly_plan(tasks):
    if not tasks:
        return "No career tasks are available yet. Sync jobs or add opportunities first, then I can make a weekly plan."

    response = "Here is your career task plan for this week:\n\n"

    buckets = {
        "Do Now": [],
        "Do Today": [],
        "Follow Up": [],
        "High Value": [],
        "Do This Week": [],
        "Tailor First": [],
        "Low Priority": [],
    }

    for task in tasks:
        buckets[task["priority"]].append(task)

    for priority, priority_tasks in buckets.items():
        if priority_tasks:
            response += f"{priority}:\n"
            for task in priority_tasks:
                response += f"- {task['task_title']}\n"
            response += "\n"

    response += (
        "Smart move: complete urgent applications first, then improve weak-match roles only if they align with your target roles."
    )

    return response


def explain_top_priority(tasks):
    if not tasks:
        return "No top priority is available yet because there are no jobs to rank."

    top_task = tasks[0]

    return (
        f"I ranked this first:\n\n"
        f"{format_task(top_task)}\n\n"
        f"Why: the priority engine considers deadline urgency, match score, "
        f"application status, and your interest level. This task gives the highest immediate career value."
    )


def career_chatbot_response(user_message, resume_profile, jobs):
    message = user_message.lower()
    tasks = generate_priority_tasks(resume_profile, jobs)

    if "today" in message or "do first" in message or "priority" in message:
        return get_today_plan(tasks)

    if "week" in message or "plan" in message:
        return get_weekly_plan(tasks)

    if "best job" in message or "highest match" in message or "best match" in message:
        return get_best_match(tasks)

    if "follow up" in message or "follow-up" in message:
        return get_follow_up_plan(tasks)

    if "missing skills" in message or "skills am i missing" in message:
        return get_missing_skills_summary(tasks)

    if "explain" in message or "why" in message:
        return explain_top_priority(tasks)

    return (
        "I can help with your job search priorities. Try asking:\n"
        "- What should I do today?\n"
        "- Which job is my best match?\n"
        "- What skills am I missing?\n"
        "- Make me a weekly plan.\n"
        "- Explain my top priority."
    )
