# CareerCopilot AI

CareerCopilot AI is a local job-search assistant that syncs Handshake job emails from Gmail, extracts real application links, tracks application status, and prioritizes opportunities by deadline and fit.

## Features

- Gmail to job tracker sync for Handshake opportunities
- Real Handshake apply-link extraction
- Persistent application status tracking
- Applied-status sync from Gmail confirmation emails
- Resume/profile parsing
- Priority task generation
- Job details, upcoming deadlines, weekly digest, and chatbot views

## Project Structure

```text
backend/    FastAPI backend, Gmail sync, parsing, scoring, and storage
frontend/   Single-page HTML/CSS/JS interface
```

## Run Locally

Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Start the API:

```bash
python run.py
```

Open the frontend:

```text
frontend/index.html
```

The frontend expects the backend at:

```text
http://localhost:8002
```

## Gmail Setup

Gmail OAuth files are intentionally not committed.

To enable Gmail sync locally:

1. Add your Google OAuth client file as `backend/client_secret.json`.
2. Start the backend.
3. Click `Sync Gmail` in the app and complete the Google consent flow.
4. A local `backend/token_gmail.json` file will be created automatically.

Optional backend environment values can be placed in `backend/.env`:

```env
USER_EMAIL=your.email@gmail.com
GMAIL_LOOKBACK_DAYS=30
GMAIL_MAX_RESULTS=20
GMAIL_APPLIED_LABEL=CareerCopilot/Applied
```

## Tests

Run backend tests from the backend folder:

```bash
cd backend
python -m pytest tests
```

## Privacy Note

The repository ignores Gmail tokens, OAuth client secrets, local `.env` files, and local JSON stores so personal data is not pushed to GitHub.
