import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

_logger = logging.getLogger(__name__)


def _paths() -> tuple[str, str]:
    client_secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE")
    token_file = os.environ.get("GOOGLE_TOKEN_FILE")
    if not client_secrets or not token_file:
        raise RuntimeError(
            "GOOGLE_CLIENT_SECRETS_FILE and GOOGLE_TOKEN_FILE must be set "
            "in the environment."
        )
    return client_secrets, token_file


def get_calendar_credentials() -> Credentials:
    """Loads cached Google Calendar credentials, refreshing if expired.

    Never runs the interactive consent flow itself — that only happens
    once, via scripts/authorize_calendar.py — so a tool call made during
    a conversation can't unexpectedly pop open a browser window.
    """
    _, token_file = _paths()

    if not os.path.exists(token_file):
        raise FileNotFoundError(token_file)

    creds = Credentials.from_authorized_user_file(token_file, _SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def run_interactive_authorization() -> None:
    """One-time interactive OAuth consent flow.

    Run via `python scripts/authorize_calendar.py`, not from within the
    agent process.
    """
    client_secrets, token_file = _paths()
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, _SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    _logger.info("Saved Google Calendar credentials to %s", token_file)
