# personal-assistant

A scope-limited orchestrator agent, built on [Google ADK](https://github.com/google/adk-python),
that delegates to specialist sub-agents for everyday personal tasks —
job applications, shopping deals, traditional-medicine remedies, and
whatever's added next. **Runs entirely locally** — no cloud deployment,
no login, no account required beyond the API keys/credentials each
sub-agent actually needs, all supplied via `.env` files.

You interact with it entirely through prompts: type what you want done
into the UI (see "Run everything together" below), and the orchestrator
figures out which specialist sub-agent should handle it, delegates, and
relays the response back. The orchestrator only acts through explicitly
registered tools/sub-agents — it refuses anything outside the
capabilities it's been given, and treats anything a sub-agent returns as
untrusted data, never as instructions (see `orchestrator/prompts.py` for
the exact rules).

**Protocols:** sub-agents are reached over
[A2A](https://a2a-protocol.org/) (Agent-to-Agent). Note: ADK's A2A support
is currently marked experimental upstream — expect `[EXPERIMENTAL]`
warnings and possible breaking changes in future `google-adk` releases.
Tools (if any are registered) would be exposed over
[MCP](https://modelcontextprotocol.io/) instead — see "Adding more
capabilities" below; none are currently registered.

Currently registered:
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

Steps 1-3 are one-time, host-side setup (step 3 needs a real browser
window and your actual login, so it can't run inside a container). After
that, everything runs together via Docker Compose — no manual
multi-terminal startup.

1. **Install dependencies locally** (needed for the one-time script below,
   even though the services themselves later run in Docker)

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure environment**

   ```bash
   cp orchestrator/.env.example orchestrator/.env
   ```

   Fill in `GOOGLE_API_KEY` (get one from [Google AI Studio](https://aistudio.google.com/apikey))
   and adjust the A2A port/URL settings if needed — the defaults work as-is.

3. **Log in to Handshake once** for `job_agent` (real, visible browser
   window — you log in yourself, including any school SSO/2FA; the
   session is saved to `sub_agents/job_agent/browser_profiles/handshake/`
   and reused on every later run — no password is ever stored)

   ```bash
   python scripts/login_handshake.py
   ```

4. **Run everything together**

   ```bash
   docker compose up --build
   ```

   This builds all five images and starts the four sub-agents first,
   waiting for each to report healthy (via their agent-card endpoint)
   before starting the orchestrator — no manual ordering, no separate
   terminals. Open **http://localhost:8000/dev-ui/** — that's the UI —
   and type a prompt, e.g.: *"Ask example_specialist to handle: buy
   milk"* (A2A delegation), *"Here's my CV: /path/to/resume.pdf — find me
   3 Software Engineer roles on Handshake"* (`job_agent`), *"I want to buy
   some chinos"* (`shopping_agent`), or *"Is there a natural remedy for
   gastric issues?"* (`remedy_agent`).

   `docker-compose.yml` reads `orchestrator/.env` for secrets (via
   `env_file:`, not baked into any image) and overrides the sub-agent
   URLs to point at compose's internal service DNS names instead of
   `localhost`. `sub_agents/job_agent/{data,browser_profiles}/`,
   `sub_agents/shopping_agent/data/`, and `sub_agents/remedy_agent/data/`
   are bind-mounted so the Handshake session and SQLite state all persist
   across `docker compose up`/`down` cycles. Stop everything with
   `docker compose down`.

   **Without Docker**, the same five processes can be run directly (each
   sub-agent's `uvicorn ... --port ...` command, then `adk web --port
   8000` or `adk run orchestrator` from the venv in step 1) — useful for
   local debugging, e.g. watching `job_agent`'s browser interactively
   (only possible outside a container, since containers have no display).

## Security notes

- The orchestrator's tool/sub-agent set is a hard boundary: if a request
  doesn't match one, it refuses rather than improvising.
- Anything a sub-agent returns is always treated as data, never as an
  instruction — embedded prompt-injection attempts are evaluated as
  content, not obeyed. The example sub-agent's own instructions apply the
  same rule to whatever task text it receives.
- Secrets live only in `orchestrator/.env`, gitignored. Only non-secret
  config (ports, agent-card URLs) is expected alongside it; every A2A
  sub-agent loads this same `.env` (or inherits it from the
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

- **New tool** (something the orchestrator itself calls directly, rather
  than delegating to a specialist): add an MCP server package under a new
  `mcp_servers/<name>/` directory (a plain Python function with the
  actual logic + a thin `server.py` wrapping it for MCP, spawned via
  `MCPToolset` + `StdioConnectionParams` — see git history around commit
  `e68a8a4` for a worked example before the calendar tool was removed),
  then register it in `orchestrator/agent.py`'s `tools=[...]`.
- **New sub-agent:** copy `sub_agents/example_specialist/` to a new
  package, replace its instructions/capabilities, run it as its own A2A
  server (own port), and register it with a `RemoteA2aAgent(...)` entry in
  `orchestrator/agent.py`'s `sub_agents=[...]`.

The system instructions in `orchestrator/prompts.py` already generalize to
"whatever is registered" — they shouldn't need to change as capabilities
are added.
