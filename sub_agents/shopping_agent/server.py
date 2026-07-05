"""Exposes shopping_agent over A2A.

Run before starting the orchestrator:

    uvicorn sub_agents.shopping_agent.server:a2a_app --host localhost --port 8003

Agent card ends up at http://localhost:8003/.well-known/agent-card.json,
which orchestrator/agent.py points its RemoteA2aAgent at.
"""

import os

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(__file__), "..", "..", "orchestrator", ".env")
)

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import root_agent

_PORT = int(os.environ.get("SHOPPING_AGENT_PORT", "8003"))

a2a_app = to_a2a(root_agent, port=_PORT)
