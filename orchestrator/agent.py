import os

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)

from .prompts import ORCHESTRATOR_INSTRUCTION

_EXAMPLE_SPECIALIST_URL = os.environ.get(
    "EXAMPLE_SPECIALIST_AGENT_CARD_URL",
    f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",
)

_JOB_AGENT_URL = os.environ.get(
    "JOB_AGENT_CARD_URL",
    f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}",
)

_SHOPPING_AGENT_URL = os.environ.get(
    "SHOPPING_AGENT_CARD_URL",
    f"http://localhost:8003{AGENT_CARD_WELL_KNOWN_PATH}",
)

_REMEDY_AGENT_URL = os.environ.get(
    "REMEDY_AGENT_CARD_URL",
    f"http://localhost:8004{AGENT_CARD_WELL_KNOWN_PATH}",
)

# A2A sub-agent: a separate process (see sub_agents/example_specialist/server.py)
# that must already be running at _EXAMPLE_SPECIALIST_URL.
example_specialist = RemoteA2aAgent(
    name="example_specialist",
    description=(
        "TEMPLATE specialist sub-agent reachable over A2A — currently only "
        "acknowledges and echoes back a task, to prove sub-agent wiring "
        "works. Replace with a real specialist."
    ),
    agent_card=_EXAMPLE_SPECIALIST_URL,
    use_legacy=False,
)

# A2A sub-agent: a separate process (see sub_agents/job_agent/server.py)
# that must already be running at _JOB_AGENT_URL.
job_agent = RemoteA2aAgent(
    name="job_agent",
    description=(
        "Searches Handshake for matching software engineering roles and "
        "applies on the user's behalf, with a mandatory human review step "
        "before any application is actually submitted. See "
        "sub_agents/job_agent/ for setup and current limitations."
    ),
    agent_card=_JOB_AGENT_URL,
    use_legacy=False,
)

# A2A sub-agent: a separate process (see sub_agents/shopping_agent/server.py)
# that must already be running at _SHOPPING_AGENT_URL.
shopping_agent = RemoteA2aAgent(
    name="shopping_agent",
    description=(
        "Finds clothing deals and recommends products, remembering the "
        "user's measurements, brand preferences, and purchase history so "
        "they aren't asked repeatedly. Prioritizes quality/ratings over "
        "raw price. Recommends only — never places an order."
    ),
    agent_card=_SHOPPING_AGENT_URL,
    use_legacy=False,
)

# A2A sub-agent: a separate process (see sub_agents/remedy_agent/server.py)
# that must already be running at _REMEDY_AGENT_URL.
remedy_agent = RemoteA2aAgent(
    name="remedy_agent",
    description=(
        "Answers questions about traditional-medicine remedies (Ayurveda "
        "and Traditional Chinese Medicine) for everyday complaints. "
        "Always screens for medical emergencies first and advises seeing "
        "a doctor instead of offering a remedy when one is possible; "
        "every other response ends with a see-a-doctor disclaimer."
    ),
    agent_card=_REMEDY_AGENT_URL,
    use_legacy=False,
)

root_agent = Agent(
    model="gemini-flash-latest",
    name="orchestrator",
    description=(
        "Orchestrator that executes tasks given directly by the user, "
        "strictly limited to its registered tools and sub-agents."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    sub_agents=[example_specialist, job_agent, shopping_agent, remedy_agent],
)
