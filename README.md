# CareerCopilot AI

CareerCopilot AI is a personal job search assistant that helps users turn career-related emails into organized, actionable job opportunities.

Instead of manually going through job alerts, internship emails, reminders, and application updates, the system collects relevant data, extracts useful job information, matches opportunities with the user’s resume, and helps identify what needs attention first.

## What this project does

CareerCopilot AI is being built as a job action assistant, not just a job tracker.

The goal is to help a user:

- collect job-related information from email sources
- separate useful emails from noise
- extract structured job details
- match jobs with resume content
- recommend what needs action first
- support reminders, follow-ups, and planning

## Current features

At its current stage, the project includes:

- Backend API built with FastAPI
- Modular route structure for:
  - tasks
  - chatbot
  - jobs
  - resume
  - data sources
  - Gmail integration
- Streamlit-based frontend experiments
- Email dataset ingestion and preprocessing
- Job extraction and filtering pipeline
- Resume-related matching direction
- Action-based job recommendation direction
- GitHub development workflow using branches

## Project structure

```text
careercopilot-ai/
├── backend/
│   ├── api/
│   ├── config/
│   ├── database/
│   ├── models/
│   ├── services/
│   ├── utils/
│   ├── main.py
│   ├── requirements.txt
│   └── test_gmail_auth.py
├── frontend/
├── learning_notes/
└── .gitignore
