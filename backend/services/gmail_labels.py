from config.settings import GMAIL_APPLIED_LABEL
from services.gmail_auth import get_gmail_service


def get_or_create_label_id(service, label_name):
    labels_result = service.users().labels().list(userId="me").execute()
    for label in labels_result.get("labels", []):
        if label.get("name") == label_name:
            return label.get("id")

    label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=label).execute()
    return created.get("id")


def label_job_applied(job, service=None):
    """Best-effort Gmail label sync for jobs sourced from Gmail."""
    thread_id = job.get("thread_id")
    message_id = job.get("email_id")

    if not thread_id and not message_id:
        return {"labeled": False, "reason": "No Gmail thread/message id on job"}

    try:
        service = service or get_gmail_service(allow_interactive=False)
        label_id = get_or_create_label_id(service, GMAIL_APPLIED_LABEL)
        body = {"addLabelIds": [label_id], "removeLabelIds": []}

        if thread_id:
            service.users().threads().modify(
                userId="me",
                id=thread_id,
                body=body,
            ).execute()
        else:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body=body,
            ).execute()

        return {"labeled": True, "label": GMAIL_APPLIED_LABEL}

    except Exception as exc:
        return {"labeled": False, "reason": str(exc)}
