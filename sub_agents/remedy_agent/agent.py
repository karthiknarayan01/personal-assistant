from google.adk.agents import Agent
from google.adk.tools import google_search

from .prompts import REMEDY_AGENT_INSTRUCTION
from .tools.emergency_check import check_emergency_symptoms
from .tools.knowledge_base import save_remedy, search_remedy_knowledge_base

root_agent = Agent(
    model="gemini-flash-latest",
    name="remedy_agent",
    description=(
        "Specialist that answers questions about traditional-medicine "
        "remedies (Ayurveda and Traditional Chinese Medicine) for "
        "everyday complaints, always screening for medical emergencies "
        "first and always closing with a see-a-doctor disclaimer."
    ),
    instruction=REMEDY_AGENT_INSTRUCTION,
    tools=[
        google_search,
        check_emergency_symptoms,
        search_remedy_knowledge_base,
        save_remedy,
    ],
)
