import os

from mcp import StdioServerParameters

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

from .prompts import ORCHESTRATOR_INSTRUCTION

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_EXAMPLE_SPECIALIST_URL = os.environ.get(
    "EXAMPLE_SPECIALIST_AGENT_CARD_URL",
    f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",
)

_JOB_AGENT_URL = os.environ.get(
    "JOB_AGENT_CARD_URL",
    f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}",
)

# MCP tool: spawned automatically over stdio, no separate process to start.
calendar_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            args=["-m", "mcp_servers.calendar.server"],
            cwd=_PROJECT_ROOT,
            env=dict(os.environ),
        ),
    ),
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

root_agent = Agent(
    model="gemini-flash-latest",
    name="orchestrator",
    description=(
        "Orchestrator that executes tasks given directly by the user or "
        "found on the user's Google Calendar, strictly limited to its "
        "registered tools and sub-agents."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[calendar_toolset],
    sub_agents=[example_specialist, job_agent],
)
