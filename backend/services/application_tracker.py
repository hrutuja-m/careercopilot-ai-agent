# NOTE (unused / deprecated): nothing in this codebase imports this module.
# The application status vocabulary actually in use is the 4-value one
# defined in database/jobs_store.py (VALID_STATUSES = not_applied, applied,
# interviewing, rejected) — the frontend's status dropdown, the priority
# engine, and every API route all use that one. The 8-value vocabulary
# below predates it and conflicts with it (e.g. "saved" vs "not_applied",
# "interview" vs "interviewing"). Left in place rather than deleted since
# it may be part of the original project scaffolding, but don't wire this
# up without reconciling it with jobs_store.VALID_STATUSES first — having
# two different status vocabularies live at once is exactly what caused
# confusion here.

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