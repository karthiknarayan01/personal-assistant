"""One-time interactive Google Calendar authorization.

Run this once from the project root:

    python scripts/authorize_calendar.py

It opens a browser for OAuth consent and caches a refresh token at the
path in GOOGLE_TOKEN_FILE. The orchestrator agent never runs this
interactive flow itself, so a calendar tool call during a conversation
can't unexpectedly open a browser window.
"""

import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, "orchestrator", ".env"))

from orchestrator.auth.google_oauth import run_interactive_authorization

if __name__ == "__main__":
    run_interactive_authorization()
    print("Google Calendar authorization complete.")
