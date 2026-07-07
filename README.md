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
- **Sub-agent (A2A):** `job_agent` — in `sub_agents/job_agent/`. Searches
  Handshake for matching software engineering roles and applies on the
  user's behalf, with a mandatory human review-and-approve step before
  any application is actually submitted. See "job_agent details" below.
- **Sub-agent (A2A):** `shopping_agent` — in `sub_agents/shopping_agent/`.
  Finds clothing deals (Slickdeals + web search) and recommends products,
  remembering measurements, brand preferences, and purchase history so
  they aren't asked repeatedly. Recommends only — never places an order.
  See "shopping_agent details" below.
- **Sub-agent (A2A):** `remedy_agent` — in `sub_agents/remedy_agent/`.
  Answers questions about traditional-medicine remedies (Ayurveda and
  TCM) for everyday complaints. Screens every query for possible medical
  emergencies first and advises seeing a doctor instead of offering a
  remedy when one is possible. See "remedy_agent details" below.

## Setup

Steps 1-6 are one-time, host-side setup (they need a real browser window
and your actual login, so they can't run inside a container). After that,
everything runs together via Docker Compose — no manual multi-terminal
startup.

1. **Install dependencies locally** (needed for the one-time scripts below,
   even though the services themselves later run in Docker)

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
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

6. **Log in to Handshake once** for `job_agent` (real, visible browser
   window — you log in yourself, including any school SSO/2FA; the
   session is saved to `sub_agents/job_agent/browser_profiles/handshake/`
   and reused on every later run — no password is ever stored)

   ```bash
   python scripts/login_handshake.py
   ```

7. **Run everything together**

   ```bash
   docker compose up --build
   ```

   This builds all five images and starts the four sub-agents first,
   waiting for each to report healthy (via their agent-card endpoint)
   before starting the orchestrator — no manual ordering, no separate
   terminals. Open **http://localhost:8000/dev-ui/** and try: *"What's on
   my calendar today?"*, *"Ask example_specialist to handle: buy milk"*
   (A2A delegation), *"Here's my CV: /path/to/resume.pdf — find me 3
   Software Engineer roles on Handshake"* (`job_agent`), *"I want to buy
   some chinos"* (`shopping_agent`), or *"Is there a natural remedy for
   gastric issues?"* (`remedy_agent`).

   `docker-compose.yml` reads `orchestrator/.env` for secrets (via
   `env_file:`, not baked into any image) and overrides the sub-agent
   URLs to point at compose's internal service DNS names instead of
   `localhost`. `credentials/`, `sub_agents/job_agent/{data,browser_profiles}/`,
   `sub_agents/shopping_agent/data/`, and `sub_agents/remedy_agent/data/`
   are bind-mounted so the OAuth token, Handshake session, and SQLite
   state all persist across `docker compose up`/`down` cycles. Stop
   everything with `docker compose down`.

   **Without Docker**, the same five processes can be run directly (each
   sub-agent's `uvicorn ... --port ...` command, then `adk web --port
   8000` or `adk run orchestrator` from the venv in step 1) — useful for
   local debugging, e.g. watching `job_agent`'s browser interactively
   (only possible outside a container, since containers have no display).

## Deploying to Cloud Run (GCP)

`gcp/deploy.sh` deploys the same two images to five Cloud Run services.
**This creates real, billable cloud resources and a real internet-facing
URL — it has not been run for you; read this section before running it
yourself.** Cloud Run's pay-per-use pricing should be small for personal,
low-traffic use, but the GCS bucket, Artifact Registry storage, and any
`--min-instances` you set later all have an ongoing cost regardless of
traffic.

**Access model:** only the orchestrator gets a public URL, and it's
gated by [Identity-Aware Proxy](https://cloud.google.com/iap) — you sign
in with your normal Google account in a plain browser tab; nobody else
gets through. The four sub-agents are deployed with
`--no-allow-unauthenticated` and are only callable by the orchestrator's
own Cloud Run service identity (`orchestrator/gcp_auth.py` attaches a
Google-signed ID token to each request when `USE_GCP_ID_TOKEN_AUTH=true`)
— they have no public URL of their own.

**Persistence:** a single GCS bucket is mounted into `job-agent`,
`shopping-agent`, `remedy-agent`, and `orchestrator` at `/mnt/state`, so
purchase history, the 90-day applied-jobs cooldown, saved measurements/
preferences, the curated remedy knowledge base, the calendar OAuth
token, and the logged-in Handshake session all survive redeploys — the
script seeds it from your local `credentials/`,
`sub_agents/job_agent/{data,browser_profiles}/`,
`sub_agents/shopping_agent/data/`, and `sub_agents/remedy_agent/data/`
on first run. One caveat worth knowing: SQLite's default WAL journal
mode needs file-locking that GCS FUSE mounts don't reliably support, so
the deploy sets `SQLITE_JOURNAL_MODE=DELETE` for these services on Cloud
Run instead — fine for a single low-traffic personal instance, but if
this ever sees real concurrent load, migrating that state to Firestore
would be the more correct fix.

**One-time prerequisites** (not scripted — account-type-dependent):
1. `gcloud auth login`, and a GCP project with billing enabled.
2. Configure an OAuth consent screen for the project — IAP needs one to
   exist. In the console: APIs & Services → OAuth consent screen →
   External → add yourself as a test user.
3. Complete the local one-time setup already described above (steps 1-6)
   — the calendar token and Handshake session need to exist locally
   before the script can seed the bucket with them.

**Deploy:**

```bash
export PROJECT_ID=your-gcp-project
export BUCKET_NAME=your-bucket-name
export IAP_USER_EMAIL=you@gmail.com
./gcp/deploy.sh
```

Prints the orchestrator's URL at the end — open `<url>/dev-ui/` and sign
in. **Tear down** with `./gcp/teardown.sh` (add `--delete-bucket` to also
remove your persisted data, otherwise it's left in place).

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
  stay in the `credentials/` JSON files. The calendar MCP server and every
  A2A sub-agent load this same `.env` (or inherit it from the
  orchestrator's environment) — no secret is duplicated anywhere.
- `job_agent` never stores a Handshake password: `browser_profiles/`
  holds a logged-in session instead (see `job_agent` details below), and
  it never submits an application without an explicit human approval of
  that specific drafted answer set first.
- `shopping_agent` has no purchase/checkout capability at all — it only
  searches and recommends. Slickdeals is queried through their own
  documented public RSS search feed (no scraping, no account needed).
- `remedy_agent` screens every query for possible medical emergencies
  (keyword safety net + the model's own judgment) before offering any
  home remedy, and never omits known contraindications/interactions.
  It does not diagnose, prescribe dosages, or otherwise substitute for
  professional care — see "remedy_agent details" below.

## `job_agent` details

- **Persistent state** lives in `sub_agents/job_agent/data/job_agent.db`
  (gitignored, contains PII), independent of chat/session memory:
  `applications` (every submission, for a 90-day per-company-per-role
  cooldown), `profile_fields` (CV summary, target roles, roles-per-run,
  and recurring answers — asked once, reused forever), `pending_drafts`
  (last prepared-but-unsubmitted draft per job).
- **Job discovery is hard-locked** to `search_handshake_jobs` — the
  agent's `google_search` tool may only be used to research a company for
  drafting answers, never to find or verify job listings.
- **Status:** Handshake search/apply automation
  (`sub_agents/job_agent/tools/handshake_tools.py`) is a first-pass
  implementation from general knowledge of Handshake's UI, not yet
  validated against a live account/session (selectors marked `VERIFY:` in
  the code) — plan on a live debugging pass with a headed browser.
  External-ATS-redirect postings (Greenhouse/Lever/Workday via Handshake)
  aren't handled yet. LinkedIn and jobright.ai sources aren't built yet.

## `shopping_agent` details

- **Persistent state** lives in
  `sub_agents/shopping_agent/data/shopping_agent.db` (gitignored, contains
  PII), independent of chat/session memory: `purchases` (every purchase
  the user reports, for brand-affinity signal and to avoid re-asking) and
  `profile_fields` (a flexible key/value store for
  `measurements:<category>`, `preferred_brands:<category>`,
  `notes:<category>` — asked once per category, reused forever).
  `get_brand_affinity` derives brand signal straight from purchase history
  when there's no explicit stored preference yet.
- **Deal search:** `search_slickdeals` uses Slickdeals' own documented
  public RSS search feed (`newsearch.php?q=...&rss=1`) — first-party,
  no scraping, no login required — ranked by their community "thumb
  score". `google_search` is used alongside it for reviews, ratings, and
  price context. Slickdeals' actual partner API requires requesting a
  token from their team and wasn't pursued for this first pass, since the
  RSS feed already covers the need without an approval process.
- **No purchase/checkout automation** — this agent only searches,
  compares, and recommends; the user buys things themselves and reports
  back what they bought via `record_purchase`.
- Quality/ratings are explicitly prioritized over raw price when they
  trade off, and when there's no purchase history yet the agent is
  instructed to lead with well-reviewed, popularly-bought items rather
  than the steepest discount.

## `remedy_agent` details

- **Persistent state** lives in
  `sub_agents/remedy_agent/data/remedy_agent.db` (gitignored, treated as
  a runtime artifact even though it isn't personal data): a curated
  `remedies` table seeded on first use with ~12 well-known Ayurveda/TCM/
  general remedies for common complaints (cold & cough, sore throat,
  gastric/indigestion, nausea, headache, mild insomnia, joint pain, minor
  cuts) — deliberately no specific dosages, only general traditional-use
  descriptions plus real, commonly-cited cautions. `save_remedy` grows it
  over time from vetted live search results.
- **Emergency screening is the first thing that happens on every query**
  (`orchestrator/prompts.py`-style priority-ordered rules in
  `sub_agents/remedy_agent/prompts.py`): a deterministic keyword check
  (`check_emergency_symptoms`) plus the model's own judgment — either can
  trigger it. On a possible emergency (chest pain, trouble breathing,
  stroke signs, severe allergic reaction, suicidal ideation, poisoning,
  etc.), it advises immediate medical attention instead of a remedy, full
  stop, no exceptions.
- **Sources:** checks the local knowledge base first, then `google_search`
  weighted toward NCCIH (nccih.nih.gov), MedlinePlus (medlineplus.gov),
  India's Ministry of AYUSH (ayush.gov.in / namayush.gov.in), Mayo
  Clinic, PubMed/NCBI, and examine.com — no MCP tool or structured API
  exists for TCM/Ayurveda specifically (checked; nothing reliable
  found), so this is instruction-level source weighting rather than a
  hard-locked tool boundary the way `job_agent`'s Handshake-only search
  is.
- **Every non-emergency response ends with a disclaimer**: these are
  traditional/home remedies, not a substitute for professional medical
  advice, see a doctor if symptoms are severe, persist, or don't improve.

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
