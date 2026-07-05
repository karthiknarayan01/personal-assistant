# calendar-agent

A scope-limited orchestrator agent, built on [Google ADK](https://github.com/google/adk-python).

The orchestrator only acts through explicitly registered tools/sub-agents.
It can be asked to perform a task directly, or to read the day's Google
Calendar events and treat each one as a candidate task. It refuses
anything outside the capabilities it's been given, and treats calendar
content as untrusted data, never as instructions (see
`orchestrator/prompts.py` for the exact rules).

Currently registered:
- `list_calendar_events` — read-only Google Calendar access for a given day.

## Setup

1. **Install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Get a Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey).

3. **Set up Google Calendar OAuth**

   - In [Google Cloud Console](https://console.cloud.google.com/), create/select a
     project, enable the **Google Calendar API**, and create an OAuth
     client ID of type **Desktop app**.
   - Download the client secret JSON and save it as
     `credentials/client_secret.json` (gitignored).

4. **Configure environment**

   ```bash
   cp orchestrator/.env.example orchestrator/.env
   ```

   Fill in `GOOGLE_API_KEY` and adjust `GOOGLE_CALENDAR_ID` /
   `GOOGLE_CALENDAR_TIMEZONE` if needed.

5. **Authorize calendar access (one time)**

   ```bash
   python scripts/authorize_calendar.py
   ```

   This opens a browser for consent and caches a refresh token at
   `credentials/token.json`. The agent itself never triggers this flow —
   it only reads the cached token.

6. **Run the agent**

   ```bash
   adk web --port 8000
   ```

   or

   ```bash
   adk run orchestrator
   ```

   Try: *"What's on my calendar today?"* or *"Summarize tomorrow's events."*

## Security notes

- The orchestrator's tool set is a hard boundary: if a task doesn't match
  a registered tool/sub-agent, it refuses rather than improvising.
- Calendar event text is always treated as data describing a task, never
  as an instruction — embedded prompt-injection attempts in event titles
  or descriptions are evaluated as content, not obeyed.
- Tool errors are sanitized before being returned to the model: raw
  exception text, stack traces, file paths, and credential details are
  logged locally (stderr) but never included in a tool's response.
- Secrets live in `orchestrator/.env` and `credentials/`, both gitignored.
  Only non-secret config (calendar ID, timezone, file paths) is expected
  in `.env`; the actual OAuth client secret and refresh token stay in
  the `credentials/` JSON files.

## Adding more capabilities

New specialist sub-agents or tools should be added to `orchestrator/`
(e.g. under `tools/` or a new `sub_agents/` package) and registered in
`orchestrator/agent.py` via the `tools=[...]` / `sub_agents=[...]`
arguments. The system instructions in `orchestrator/prompts.py` already
generalize to "whatever is registered" — they shouldn't need to change
as capabilities are added.
