import json
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone

from services.seed_data import DEMO_RESUME

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_FILE = os.path.join(BASE_DIR, "database", "profile_store.json")

KNOWN_SKILLS = [
    "python",
    "sql",
    "fastapi",
    "rag",
    "llm",
    "openai api",
    "faiss",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "aws",
    "azure",
    "tableau",
    "excel",
    "data pipelines",
    "prompt engineering",
    "workflow automation",
    "model evaluation",
    "data science",
    "data analytics",
    "generative ai",
    "api",
]

ROLE_KEYWORDS = [
    "AI Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Data Analyst",
    "Software Engineer",
    "ML Engineer",
    "AI Agent Engineer",
]

_lock = threading.Lock()
_cache = None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _today():
    return date.today().isoformat()


def _week_start(day=None):
    day = day or date.today()
    return (day - timedelta(days=day.weekday())).isoformat()


def _default_store():
    return {
        "profile": dict(DEMO_RESUME),
        "goals": {
            "daily_application_goal": 3,
            "week_start": _week_start(),
            "updated_at": _now_iso(),
        },
        "progress": {},
    }


def _load_from_disk():
    if not os.path.exists(STORE_FILE):
        return None
    with open(STORE_FILE, "r") as f:
        return json.load(f)


def _save_to_disk(data):
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
    tmp_file = STORE_FILE + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_file, STORE_FILE)


def _ensure_loaded():
    global _cache
    if _cache is not None:
        return
    with _lock:
        if _cache is not None:
            return
        existing = _load_from_disk()
        if existing is None:
            existing = _default_store()
            _save_to_disk(existing)
        existing.setdefault("profile", dict(DEMO_RESUME))
        existing.setdefault("goals", _default_store()["goals"])
        existing.setdefault("progress", {})
        profile = existing["profile"]
        if profile.get("resume_filename") and not profile.get("resume_files"):
            profile["resume_files"] = [
                {
                    "filename": profile["resume_filename"],
                    "uploaded_at": profile.get("resume_updated_at"),
                }
            ]
            _save_to_disk(existing)
        _cache = existing


def get_profile():
    _ensure_loaded()
    return dict(_cache["profile"])


def get_goals():
    _ensure_loaded()
    goals = dict(_cache["goals"])
    goals["week_start"] = goals.get("week_start") or _week_start()
    return goals


def get_progress(days=28):
    _ensure_loaded()
    today = date.today()
    daily_goal = int(get_goals().get("daily_application_goal", 3))
    days = max(int(days or 28), 7)
    items = []

    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        count = int(_cache["progress"].get(key, 0))
        if count <= 0:
            level = 0
        elif count >= daily_goal:
            level = 4
        else:
            level = max(1, min(3, round((count / max(daily_goal, 1)) * 4)))
        items.append(
            {
                "date": key,
                "count": count,
                "goal": daily_goal,
                "level": level,
            }
        )

    return items


def get_profile_bundle():
    return {
        "profile": get_profile(),
        "goals": get_goals(),
        "progress": get_progress(),
    }


def update_goals(daily_application_goal):
    goal = max(int(daily_application_goal), 1)
    _ensure_loaded()
    with _lock:
        _cache["goals"]["daily_application_goal"] = goal
        _cache["goals"]["week_start"] = _week_start()
        _cache["goals"]["updated_at"] = _now_iso()
        _save_to_disk(_cache)
        return get_goals()


def record_application(day=None, amount=1):
    _ensure_loaded()
    key = day or _today()
    with _lock:
        _cache["progress"][key] = int(_cache["progress"].get(key, 0)) + amount
        _save_to_disk(_cache)
        return {
            "date": key,
            "count": _cache["progress"][key],
            "goal": int(_cache["goals"].get("daily_application_goal", 3)),
        }


def extract_pdf_text(file_bytes):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to parse uploaded resumes.") from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def parse_resume_text(text, filename=None):
    normalized = re.sub(r"\s+", " ", text or " ").strip()
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    current = get_profile()

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text or "")
    email = email_match.group(0) if email_match else current.get("email")

    name = current.get("name") or "Profile"
    for line in lines[:8]:
        if "@" not in line and not re.search(r"\d{3}", line) and len(line.split()) <= 5:
            name = line
            break

    lower = normalized.lower()
    skills = [skill for skill in KNOWN_SKILLS if skill in lower]
    if not skills:
        skills = current.get("skills", [])

    target_roles = [role for role in ROLE_KEYWORDS if role.lower() in lower]
    if not target_roles:
        target_roles = current.get("target_roles", [])

    experience_keywords = []
    for phrase in (
        "ai agents",
        "workflow automation",
        "model evaluation",
        "resume parsing",
        "job matching",
        "dashboards",
        "data visualization",
        "predictive models",
        "etl",
        "cloud",
    ):
        if phrase in lower:
            experience_keywords.append(phrase)

    if not experience_keywords:
        experience_keywords = current.get("experience_keywords", [])

    return {
        "name": name,
        "email": email,
        "target_roles": target_roles,
        "skills": skills,
        "experience_keywords": experience_keywords,
        "resume_filename": filename,
        "resume_updated_at": _now_iso(),
    }


def update_profile_from_resume(file_bytes, filename):
    text = extract_pdf_text(file_bytes)
    parsed = parse_resume_text(text, filename=filename)
    _ensure_loaded()
    with _lock:
        existing_files = list(_cache["profile"].get("resume_files", []))
        existing_files = [
            file if isinstance(file, dict) else {"filename": str(file), "uploaded_at": None}
            for file in existing_files
        ]
        existing_files = [
            file for file in existing_files if file.get("filename") != filename
        ]
        existing_files.append(
            {
                "filename": filename,
                "uploaded_at": parsed["resume_updated_at"],
            }
        )
        parsed["resume_files"] = existing_files
        _cache["profile"].update(parsed)
        _save_to_disk(_cache)
        return dict(_cache["profile"])
