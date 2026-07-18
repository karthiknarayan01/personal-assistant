import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .prompts import REMEDY_AGENT_INSTRUCTION
from .tools.emergency_check import check_emergency_symptoms
from .tools.knowledge_base import save_remedy, search_remedy_knowledge_base
from .tools.web_search import web_search

_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
_OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

root_agent = Agent(
    model=LiteLlm(model=f"ollama_chat/{_OLLAMA_MODEL}", api_base=_OLLAMA_API_BASE),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    name="remedy_agent",
    description=(
        "Specialist that answers questions about traditional-medicine "
        "remedies (Ayurveda and Traditional Chinese Medicine) for "
        "everyday complaints, always screening for medical emergencies "
        "first and always closing with a see-a-doctor disclaimer."
    ),
    instruction=REMEDY_AGENT_INSTRUCTION,
    tools=[
        web_search,
        check_emergency_symptoms,
        search_remedy_knowledge_base,
        save_remedy,
    ],
)
