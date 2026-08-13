import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token_gmail.json")


def get_gmail_service(allow_interactive=True):
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            token_info = json.load(token_file)
        token_scopes = set(token_info.get("scopes", []))

        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if (token_scopes and not set(SCOPES).issubset(token_scopes)) or not creds.has_scopes(SCOPES):
            creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:
        if not allow_interactive:
            raise RuntimeError("Gmail modify token is not available. Reconnect Gmail to enable labeling.")

        if not os.path.exists(CLIENT_SECRET_FILE):
            raise FileNotFoundError(
                "client_secret.json not found. Place it inside the backend folder."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    return service
