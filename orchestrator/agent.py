from google.adk.agents import Agent

from .prompts import ORCHESTRATOR_INSTRUCTION
from .tools.calendar_tool import list_calendar_events

root_agent = Agent(
    model="gemini-flash-latest",
    name="orchestrator",
    description=(
        "Orchestrator that executes tasks given directly by the user or "
        "found on the user's Google Calendar, strictly limited to its "
        "registered tools and sub-agents."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[list_calendar_events],
)
