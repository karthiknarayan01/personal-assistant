import os

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .prompts import ORCHESTRATOR_INSTRUCTION

_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
_OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

_SHOPPING_AGENT_URL = os.environ.get(
    "SHOPPING_AGENT_CARD_URL",
    f"http://localhost:8003{AGENT_CARD_WELL_KNOWN_PATH}",
)

_REMEDY_AGENT_URL = os.environ.get(
    "REMEDY_AGENT_CARD_URL",
    f"http://localhost:8004{AGENT_CARD_WELL_KNOWN_PATH}",
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
    model=LiteLlm(model=f"ollama_chat/{_OLLAMA_MODEL}", api_base=_OLLAMA_API_BASE),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    name="orchestrator",
    description=(
        "Orchestrator that executes tasks given directly by the user, "
        "strictly limited to its registered tools and sub-agents."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    sub_agents=[shopping_agent, remedy_agent],
)
