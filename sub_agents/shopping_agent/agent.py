import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .prompts import SHOPPING_AGENT_INSTRUCTION
from .tools.profile_store import get_profile, save_profile_fields
from .tools.purchase_store import (
    get_brand_affinity,
    get_purchase_history,
    record_purchase,
)
from .tools.slickdeals_tool import search_slickdeals
from .tools.web_search import web_search

_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
_OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

root_agent = Agent(
    model=LiteLlm(model=f"ollama_chat/{_OLLAMA_MODEL}", api_base=_OLLAMA_API_BASE),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    name="shopping_agent",
    description=(
        "Specialist that finds clothing deals and recommends products, "
        "remembering the user's measurements, brand preferences, and "
        "purchase history so they aren't asked repeatedly. Prioritizes "
        "quality/ratings over raw price. Recommends only — never places "
        "an order."
    ),
    instruction=SHOPPING_AGENT_INSTRUCTION,
    tools=[
        web_search,
        get_profile,
        save_profile_fields,
        record_purchase,
        get_purchase_history,
        get_brand_affinity,
        search_slickdeals,
    ],
)
