from google.adk.agents import Agent
from google.adk.tools import google_search

from .prompts import SHOPPING_AGENT_INSTRUCTION
from .tools.profile_store import get_profile, save_profile_fields
from .tools.purchase_store import (
    get_brand_affinity,
    get_purchase_history,
    record_purchase,
)
from .tools.slickdeals_tool import search_slickdeals

root_agent = Agent(
    model="gemini-flash-latest",
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
        google_search,
        get_profile,
        save_profile_fields,
        record_purchase,
        get_purchase_history,
        get_brand_affinity,
        search_slickdeals,
    ],
)
