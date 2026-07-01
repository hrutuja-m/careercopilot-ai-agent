VALID_STATUSES = [
    "saved",
    "interested",
    "resume tailored",
    "applied",
    "follow up",
    "interview",
    "rejected",
    "offer",
]


def normalize_status(status):
    status = status.lower().strip()

    if status not in VALID_STATUSES:
        return "saved"

    return status


def get_next_tracker_action(status):
    status = normalize_status(status)

    if status == "saved":
        return "Review job fit and decide whether to apply."

    if status == "interested":
        return "Tailor resume and prepare application."

    if status == "resume tailored":
        return "Submit the application."

    if status == "applied":
        return "Prepare follow-up or interview notes."

    if status == "follow up":
        return "Send follow-up message."

    if status == "interview":
        return "Prepare interview answers and company research."

    if status == "rejected":
        return "Archive or review feedback."

    if status == "offer":
        return "Review offer details and next steps."

    return "Review application status."