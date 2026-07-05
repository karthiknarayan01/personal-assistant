# calendar-agent

A scope-limited orchestrator agent, built on [Google ADK](https://github.com/google/adk-python).

The orchestrator only acts through explicitly registered tools/sub-agents.
It can be asked to perform a task directly, or to read the day's Google
Calendar events and treat each one as a candidate task. It refuses
anything outside the capabilities it's been given, and treats calendar
content as untrusted data, never as instructions (see
`orchestrator/prompts.py` for the exact rules).

**Protocols:** tools are exposed to the orchestrator over
[MCP](https://modelcontextprotocol.io/); sub-agents are reached over
[A2A](https://a2a-protocol.org/) (Agent-to-Agent). Note: ADK's A2A support
is currently marked experimental upstream — expect `[EXPERIMENTAL]`
warnings and possible breaking changes in future `google-adk` releases.

Currently registered:
- **Tool (MCP):** `list_calendar_events` — read-only Google Calendar
  access for a given day. Runs as `mcp_servers/calendar/server.py`,
  spawned automatically by the orchestrator over stdio — nothing to
  start by hand.
- **Sub-agent (A2A):** `example_specialist` — a template specialist in
  `sub_agents/example_specialist/`. It has no real capability; it only
  acknowledges and echoes back a task, to prove the orchestrator-to-
  sub-agent wiring works. Copy this package as the starting point for a
  real specialist. Runs as its own server process (see below).

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

   Fill in `GOOGLE_API_KEY` and adjust the calendar/A2A settings if needed.

5. **Authorize calendar access (one time)**

   ```bash
   python scripts/authorize_calendar.py
   ```

   This opens a browser for consent and caches a refresh token at
   `credentials/token.json`. The agent itself never triggers this flow —
   it only reads the cached token.

6. **Start the sub-agent's A2A server** (separate terminal, must be
   running before the orchestrator starts)

   ```bash
   source .venv/bin/activate
   uvicorn sub_agents.example_specialist.server:a2a_app --host localhost --port 8001
   ```

7. **Run the orchestrator**

   ```bash
   adk web --port 8000
   ```

   or

   ```bash
   adk run orchestrator
   ```

   Try: *"What's on my calendar today?"*, *"Summarize tomorrow's
   events."*, or *"Ask example_specialist to handle: buy milk"* (to see
   the A2A delegation path).

## Security notes

- The orchestrator's tool/sub-agent set is a hard boundary: if a task
  doesn't match one, it refuses rather than improvising.
- Calendar event text is always treated as data describing a task, never
  as an instruction — embedded prompt-injection attempts in event titles
  or descriptions (or in anything a sub-agent returns) are evaluated as
  content, not obeyed. The example sub-agent's own instructions apply the
  same rule to whatever task text it receives.
- Tool errors are sanitized before being returned to the model, at two
  layers: `mcp_servers/calendar/tool.py` catches and sanitizes first, and
  `mcp_servers/calendar/server.py` has a defense-in-depth catch-all
  around the MCP `call_tool` handler. Raw exception text, stack traces,
  file paths, and credential details are logged locally (stderr) but
  never included in a response that reaches the model.
- Secrets live in `orchestrator/.env` and `credentials/`, both gitignored.
  Only non-secret config (calendar ID, timezone, file/URL references) is
  expected in `.env`; the actual OAuth client secret and refresh token
  stay in the `credentials/` JSON files. The calendar MCP server and the
  example_specialist A2A server each load this same `.env` (or inherit it
  from the orchestrator's environment) — no secret is duplicated anywhere.

## Adding more capabilities

- **New tool:** add an MCP server package under `mcp_servers/`, following
  `mcp_servers/calendar/` as a template (a plain Python function with the
  actual logic + a thin `server.py` wrapping it for MCP), then register it
  with an `MCPToolset(...)` entry in `orchestrator/agent.py`'s `tools=[...]`.
- **New sub-agent:** copy `sub_agents/example_specialist/` to a new
  package, replace its instructions/capabilities, run it as its own A2A
  server (own port), and register it with a `RemoteA2aAgent(...)` entry in
  `orchestrator/agent.py`'s `sub_agents=[...]`.

The system instructions in `orchestrator/prompts.py` already generalize to
"whatever is registered" — they shouldn't need to change as capabilities
are added.
