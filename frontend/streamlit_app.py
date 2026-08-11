import sys
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.task_routes import demo_resume
from database.db import database_summary, init_db, list_jobs, update_job_status
from services.application_tracker import VALID_STATUSES, get_next_tracker_action, normalize_status
from services.chatbot_engine import career_chatbot_response
from services.task_priority_engine import generate_priority_tasks


st.set_page_config(
    page_title="CareerCopilot AI",
    page_icon="CC",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_jobs_df():
    init_db()
    jobs = list_jobs()
    if not jobs:
        return pd.DataFrame()
    return pd.DataFrame(jobs)


def clean_jobs(df):
    if df.empty:
        return df

    jobs = df.copy()
    fill_values = {
        "company": "Unknown",
        "title": "Unknown role",
        "location": "Not specified",
        "salary": "",
        "job_type": "Unknown",
        "work_mode": "Unknown",
        "deadline": "",
        "deadline_text": "",
        "apply_url": "",
        "priority_label": "Low",
        "application_status": "Not Applied",
        "source": "gmail_handshake",
        "raw_details": "",
        "email_subject": "",
        "posted_date": "",
    }
    for column, value in fill_values.items():
        if column not in jobs.columns:
            jobs[column] = value
        jobs[column] = jobs[column].fillna(value)

    jobs["priority_score"] = jobs.get("priority_score", 0).fillna(0).astype(float)
    return jobs


def filter_jobs(df, search, priority, status, source):
    if df.empty:
        return df

    jobs = df.copy()
    if priority:
        jobs = jobs[jobs["priority_label"].isin(priority)]
    if status:
        jobs = jobs[jobs["application_status"].isin(status)]
    if source:
        jobs = jobs[jobs["source"].isin(source)]
    if search:
        text = search.lower().strip()
        haystack = (
            jobs["company"].astype(str)
            + " "
            + jobs["title"].astype(str)
            + " "
            + jobs["location"].astype(str)
            + " "
            + jobs["salary"].astype(str)
        ).str.lower()
        jobs = jobs[haystack.str.contains(text, na=False)]

    return jobs.sort_values(["priority_score", "company"], ascending=[False, True])


def parse_date(value):
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def upcoming_deadlines(df, days=14):
    if df.empty or "deadline" not in df:
        return pd.DataFrame()

    jobs = df.copy()
    jobs["deadline_date"] = jobs["deadline"].apply(parse_date)
    jobs = jobs[jobs["deadline_date"].notna()]
    today = date.today()
    jobs = jobs[
        (jobs["deadline_date"] >= today)
        & (jobs["deadline_date"] <= today + timedelta(days=days))
    ]
    return jobs.sort_values(["deadline_date", "priority_score"], ascending=[True, False])


def focus_jobs(df, focus):
    if df.empty:
        return df

    if focus == "High priority":
        return df[df["priority_label"] == "High"]
    if focus == "Not applied":
        return df[df["application_status"].str.lower() != "applied"]
    if focus == "Applied":
        return df[df["application_status"].str.lower() == "applied"]
    if focus == "Remote / hybrid":
        return df[df["work_mode"].isin(["Remote", "Hybrid"])]
    return df


def html_text(value):
    return escape(str(value or ""))


def job_details(row):
    parts = [
        row.get("salary"),
        row.get("job_type"),
        row.get("location"),
        row.get("work_mode"),
    ]
    return " · ".join(
        html_text(part)
        for part in parts
        if part and part != "Unknown" and part != "Not specified"
    ) or "Details not found yet"


def priority_class(label):
    label = str(label or "").lower()
    if label == "high":
        return "priority-high"
    if label == "medium":
        return "priority-medium"
    return "priority-low"


def render_metric(label, value, helper=""):
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">{html_text(label)}</div>
    <div class="metric-value">{html_text(value)}</div>
    <div class="metric-helper">{html_text(helper)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_job_card(row):
    priority_label = html_text(row.get("priority_label") or "Low")
    status = html_text(row.get("application_status") or "Not Applied")
    deadline = html_text(row.get("deadline") or "No deadline found")
    score = float(row.get("priority_score") or 0)
    st.markdown(
        f"""
<div class="job-card">
    <div class="job-card-top">
        <div>
            <div class="job-company">{html_text(row.get("company"))}</div>
            <div class="job-title">{html_text(row.get("title"))}</div>
        </div>
        <div class="score-pill">{score:.0f}</div>
    </div>
    <div class="job-meta">{job_details(row)}</div>
    <div class="job-footer">
        <span class="status-pill {priority_class(priority_label)}">{priority_label}</span>
        <span>{status}</span>
        <span>Deadline: {deadline}</span>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if row.get("apply_url"):
        st.link_button("Apply", row["apply_url"], width="stretch")


def render_selected_job(row):
    st.markdown(
        f"""
<div class="job-card">
    <div class="job-company">{html_text(row.get("company"))}</div>
    <div class="job-title">{html_text(row.get("title"))}</div>
    <div class="job-meta">{job_details(row)}</div>
    <div class="job-footer">
        <span class="status-pill {priority_class(row.get("priority_label"))}">{html_text(row.get("priority_label"))}</span>
        <span>{html_text(row.get("application_status"))}</span>
        <span>Score: {float(row.get("priority_score") or 0):.0f}</span>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def export_jobs_csv(df):
    if df.empty:
        return ""
    return df.to_csv(index=False).encode("utf-8")


st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700;800&display=swap');

    :root {
        --sea-salt: #F1E6DF;
        --bitter: #503130;
        --bitter-hover: #3F2726;
        --card: #FBF6F2;
        --surface: #F7EEE8;
        --soft: #E7D5CC;
        --line: #D8C2B9;
        --muted: #7B6260;
        --quiet: #A78C88;
    }

    .stApp {
        background: var(--sea-salt);
        color: var(--bitter);
        font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, p, label, span, div, button, input, textarea {
        font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0;
    }

    h1, h2, h3, .app-title, .metric-value, .section-title, .job-title {
        color: var(--bitter);
        font-family: "Playfair Display", Georgia, serif;
    }

    p, label, span, div {
        color: inherit;
    }

    div[data-testid="stTabs"] {
        background: rgba(251, 246, 242, .48);
        border: 1px solid rgba(216, 194, 185, .75);
        border-radius: 8px;
        padding: .35rem .45rem .1rem;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: .25rem;
    }

    div[data-testid="stTabs"] button p {
        font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-weight: 750;
        color: var(--muted);
    }

    div[data-testid="stTabs"] button[aria-selected="true"] p {
        color: var(--bitter);
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: var(--card);
        border-radius: 8px;
    }

    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 1rem;
        margin-bottom: 1rem;
        padding-bottom: .85rem;
        border-bottom: 1px solid var(--line);
    }

    .app-title {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.08;
    }

    .app-subtitle {
        margin-top: .28rem;
        color: var(--muted);
        font-size: .98rem;
    }

    .sync-state {
        text-align: right;
        color: var(--muted);
        font-size: .86rem;
        line-height: 1.45;
    }

    .metric-card, .job-card, .assistant-panel {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 1px 0 rgba(80, 49, 48, .04);
    }

    .metric-card {
        padding: .9rem 1rem;
        min-height: 112px;
    }

    .metric-label {
        color: var(--muted);
        font-size: .78rem;
        font-weight: 750;
        text-transform: uppercase;
    }

    .metric-value {
        font-size: 1.9rem;
        font-weight: 700;
        margin-top: .35rem;
        line-height: 1;
    }

    .metric-helper {
        color: var(--muted);
        font-size: .82rem;
        margin-top: .24rem;
    }

    .section-title {
        font-size: 1.18rem;
        font-weight: 700;
        margin: 1.25rem 0 .65rem;
    }

    .job-card {
        padding: .95rem;
        min-height: 188px;
        margin-bottom: .6rem;
        transition: border-color .15s ease, transform .15s ease, box-shadow .15s ease;
    }

    .job-card:hover {
        border-color: var(--bitter);
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(80, 49, 48, .08);
    }

    .job-card-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: .75rem;
    }

    .job-company {
        color: var(--muted);
        font-size: .86rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .job-title {
        font-size: 1.16rem;
        font-weight: 700;
        margin-top: .15rem;
        line-height: 1.25;
    }

    .job-meta {
        color: var(--muted);
        font-size: .86rem;
        margin-top: .55rem;
        line-height: 1.45;
    }

    .job-footer {
        display: flex;
        flex-wrap: wrap;
        gap: .45rem .7rem;
        color: var(--muted);
        font-size: .78rem;
        margin-top: .78rem;
        align-items: center;
    }

    .score-pill, .status-pill {
        border-radius: 999px;
        font-size: .78rem;
        font-weight: 800;
        white-space: nowrap;
    }

    .score-pill {
        background: var(--bitter);
        color: var(--sea-salt);
        padding: .28rem .5rem;
    }

    .status-pill {
        padding: .22rem .5rem;
        border: 1px solid var(--line);
        color: var(--bitter);
        background: var(--surface);
    }

    .priority-high {
        background: var(--bitter);
        border-color: var(--bitter);
        color: var(--sea-salt);
    }

    .priority-medium {
        background: var(--soft);
        border-color: var(--line);
        color: var(--bitter);
    }

    .priority-low {
        background: var(--surface);
        border-color: var(--line);
        color: var(--muted);
    }

    .assistant-panel {
        padding: 1rem;
    }

    .assistant-answer {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem;
        color: var(--bitter);
        white-space: pre-wrap;
        line-height: 1.5;
    }

    div.stButton > button, div.stDownloadButton > button, div[data-testid="stLinkButton"] > a {
        border-radius: 8px;
        border: 1px solid var(--bitter);
        background: var(--bitter);
        color: var(--sea-salt);
        font-weight: 800;
    }

    div.stButton > button:hover, div[data-testid="stLinkButton"] > a:hover {
        border-color: var(--bitter);
        background: var(--bitter-hover);
        color: var(--sea-salt);
    }

    div.stDownloadButton > button {
        background: transparent;
        color: var(--bitter);
    }

    div.stDownloadButton > button:hover {
        background: var(--surface);
        color: var(--bitter);
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] {
        background: var(--card);
        border-color: var(--line);
        color: var(--bitter);
        border-radius: 8px;
    }

    div[data-testid="stSlider"] [data-baseweb="slider"] div {
        color: var(--bitter);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        background: var(--card);
    }

    .stAlert {
        background: var(--card);
        border-color: var(--line);
        color: var(--bitter);
    }
</style>
""",
    unsafe_allow_html=True,
)


init_db()
summary = database_summary()
jobs_df = clean_jobs(load_jobs_df())
filtered_default = filter_jobs(jobs_df, "", [], [], [])
priority_tasks = generate_priority_tasks(demo_resume, jobs_df.to_dict("records")) if not jobs_df.empty else []
deadline_df = upcoming_deadlines(jobs_df)
last_sync = summary["latest_email"] or "No sync yet"

st.markdown(
    f"""
<div class="app-header">
    <div>
        <h1 class="app-title">CareerCopilot AI</h1>
        <div class="app-subtitle">Here are the jobs you should care about today.</div>
    </div>
    <div class="sync-state">
        <div>Last Gmail sync</div>
        <strong>{html_text(last_sync)}</strong>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Filters")
    search = st.text_input("Search", placeholder="Company, role, location")
    priority = st.multiselect("Priority", sorted(jobs_df["priority_label"].unique()) if not jobs_df.empty else [])
    status = st.multiselect("Status", sorted(jobs_df["application_status"].unique()) if not jobs_df.empty else [])
    source = st.multiselect("Source", sorted(jobs_df["source"].unique()) if not jobs_df.empty else [])

filtered_df = filter_jobs(jobs_df, search, priority, status, source)

tab_dashboard, tab_jobs, tab_assistant = st.tabs(["Dashboard", "Jobs", "Assistant"])

with tab_dashboard:
    control_cols = st.columns([1.4, 1, 1])
    with control_cols[0]:
        focus = st.segmented_control(
            "Focus",
            ["All", "High priority", "Not applied", "Applied", "Remote / hybrid"],
            default="Not applied",
        )
    with control_cols[1]:
        deadline_window = st.slider("Deadline window", min_value=7, max_value=60, value=14, step=7)
    with control_cols[2]:
        top_count = st.number_input("Top jobs", min_value=3, max_value=12, value=3, step=1)

    focused_df = focus_jobs(filtered_default, focus)
    deadline_df = upcoming_deadlines(focused_df, days=int(deadline_window))

    metric_cols = st.columns(4)
    high_count = int((focused_df["priority_label"] == "High").sum()) if not focused_df.empty else 0
    upcoming_count = len(deadline_df)

    with metric_cols[0]:
        render_metric("In View", len(focused_df), "After dashboard focus")
    with metric_cols[1]:
        render_metric("High Priority", high_count, "Best immediate matches")
    with metric_cols[2]:
        render_metric("Upcoming Deadlines", upcoming_count, f"Next {deadline_window} days")
    with metric_cols[3]:
        render_metric("Saved Jobs", summary["jobs"], "All tracked jobs")

    st.markdown("<div class='section-title'>Jobs to care about today</div>", unsafe_allow_html=True)
    if focused_df.empty:
        st.info("No jobs match this focus. Try a different filter.")
    else:
        top_cols = st.columns(3)
        for index, (_, row) in enumerate(focused_df.head(int(top_count)).iterrows()):
            with top_cols[index % 3]:
                render_job_card(row)

    st.markdown("<div class='section-title'>Inspect and update</div>", unsafe_allow_html=True)
    if focused_df.empty:
        st.caption("Pick a focus with available jobs to inspect details.")
    else:
        inspect_cols = st.columns([2, 1])
        job_options = {
            f"{int(row['id'])} - {row['company']} - {row['title']}": index
            for index, row in focused_df.reset_index(drop=True).iterrows()
        }
        with inspect_cols[0]:
            selected_label = st.selectbox("Job", list(job_options.keys()))
            selected_row = focused_df.reset_index(drop=True).iloc[job_options[selected_label]]
            render_selected_job(selected_row)
            if selected_row.get("raw_details"):
                with st.expander("Email details"):
                    st.write(selected_row.get("raw_details"))
            if selected_row.get("apply_url"):
                st.link_button("Open application", selected_row["apply_url"], width="stretch")
        with inspect_cols[1]:
            selected_status = st.selectbox(
                "Status",
                [status.title() for status in VALID_STATUSES],
                key="dashboard_status",
            )
            if st.button("Save Status", width="stretch"):
                normalized_status = normalize_status(selected_status)
                update_job_status(int(selected_row["id"]), normalized_status)
                st.success(get_next_tracker_action(normalized_status))
                st.rerun()

    st.markdown("<div class='section-title'>Upcoming deadlines</div>", unsafe_allow_html=True)
    if deadline_df.empty:
        st.info(f"No upcoming deadlines found in the next {deadline_window} days.")
    else:
        deadline_view = deadline_df[
            ["company", "title", "deadline", "priority_score", "application_status", "apply_url"]
        ].rename(
            columns={
                "company": "Company",
                "title": "Role",
                "deadline": "Deadline",
                "priority_score": "Score",
                "application_status": "Status",
                "apply_url": "Apply",
            }
        )
        st.dataframe(
            deadline_view.head(8),
            hide_index=True,
            width="stretch",
            column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "Apply": st.column_config.LinkColumn("Apply", display_text="Open"),
            },
        )

with tab_jobs:
    action_cols = st.columns([3, 1])
    with action_cols[0]:
        st.markdown("<div class='section-title'>Saved jobs</div>", unsafe_allow_html=True)
    with action_cols[1]:
        st.download_button(
            "Export CSV",
            data=export_jobs_csv(filtered_df),
            file_name="careercopilot_jobs.csv",
            mime="text/csv",
            disabled=filtered_df.empty,
            width="stretch",
        )

    if filtered_df.empty:
        st.info("No saved jobs match the current filters.")
    else:
        display_df = filtered_df[
            [
                "id",
                "company",
                "title",
                "location",
                "work_mode",
                "salary",
                "deadline",
                "job_type",
                "priority_score",
                "priority_label",
                "application_status",
                "apply_url",
            ]
        ].rename(
            columns={
                "id": "ID",
                "company": "Company",
                "title": "Role",
                "location": "Location",
                "work_mode": "Mode",
                "salary": "Salary",
                "deadline": "Deadline",
                "job_type": "Type",
                "priority_score": "Score",
                "priority_label": "Priority",
                "application_status": "Status",
                "apply_url": "Apply",
            }
        )
        st.dataframe(
            display_df,
            hide_index=True,
            width="stretch",
            column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "Apply": st.column_config.LinkColumn("Apply", display_text="Open"),
            },
        )

        st.markdown("<div class='section-title'>Update application status</div>", unsafe_allow_html=True)
        status_cols = st.columns([2.5, 1.5, 1])
        job_options = {
            f"{int(row['id'])} - {row['company']} - {row['title']}": int(row["id"])
            for _, row in filtered_df.iterrows()
        }
        with status_cols[0]:
            selected_job = st.selectbox("Job", list(job_options.keys()))
        with status_cols[1]:
            selected_status = st.selectbox("Status", [status.title() for status in VALID_STATUSES])
        with status_cols[2]:
            st.write("")
            st.write("")
            if st.button("Update", width="stretch"):
                normalized_status = normalize_status(selected_status)
                update_job_status(job_options[selected_job], normalized_status)
                st.success(get_next_tracker_action(normalized_status))
                st.rerun()

        with st.expander("Raw email details"):
            detail_df = filtered_df[
                ["id", "company", "title", "deadline_text", "posted_date", "raw_details", "email_subject"]
            ].rename(
                columns={
                    "id": "ID",
                    "company": "Company",
                    "title": "Role",
                    "deadline_text": "Original Deadline Text",
                    "posted_date": "Posted Date",
                    "raw_details": "Raw Details",
                    "email_subject": "Email Subject",
                }
            )
            st.dataframe(detail_df, hide_index=True, width="stretch")

with tab_assistant:
    st.markdown("<div class='section-title'>Assistant</div>", unsafe_allow_html=True)
    st.markdown("<div class='assistant-panel'>", unsafe_allow_html=True)

    suggested_questions = [
        "What should I apply to first?",
        "Which job is my best match?",
        "What skills am I missing?",
        "Make me a weekly plan.",
    ]
    prompt_cols = st.columns(4)
    for index, question in enumerate(suggested_questions):
        with prompt_cols[index]:
            if st.button(question, width="stretch", key=f"suggested_{index}"):
                st.session_state["assistant_question"] = question

    user_question = st.text_input(
        "Ask CareerCopilot",
        value=st.session_state.get("assistant_question", ""),
        placeholder="What should I apply to first?",
    )
    if st.button("Ask", width="stretch") and user_question.strip():
        st.session_state["assistant_answer"] = career_chatbot_response(
            user_question,
            demo_resume,
            jobs_df.to_dict("records"),
        )

    answer = st.session_state.get("assistant_answer")
    if answer:
        st.markdown(
            f"<div class='assistant-answer'>{html_text(answer)}</div>",
            unsafe_allow_html=True,
        )
    elif priority_tasks:
        top_task = priority_tasks[0]
        st.markdown(
            f"""
<div class="assistant-answer">Start here:

{html_text(top_task["task_title"])}

{html_text(top_task["suggested_action"])}</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.info("Sync jobs first, then the assistant can help you choose what to do next.")

    st.markdown("</div>", unsafe_allow_html=True)
