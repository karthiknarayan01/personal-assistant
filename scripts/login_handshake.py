"""One-time manual login to Handshake, saved to a persistent browser profile.

Run this once (and again whenever the session expires):

    python scripts/login_handshake.py

It opens a real, visible Chromium window against the persistent profile at
sub_agents/job_agent/browser_profiles/handshake/. Log in yourself
(including any school SSO or 2FA) in that window, then come back to the
terminal and press Enter. The agent's tools reuse this same saved session
— it never automates the login itself.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sub_agents.job_agent.tools.browser import get_context

if __name__ == "__main__":
    context = get_context("handshake", headless=False)
    page = context.new_page()
    page.goto("https://app.joinhandshake.com/login")
    input(
        "Log in to Handshake in the opened browser window, then press "
        "Enter here once you're on your dashboard...\n"
    )
    context.close()
    print("Session saved. You can now use the Handshake job search/apply tools.")
