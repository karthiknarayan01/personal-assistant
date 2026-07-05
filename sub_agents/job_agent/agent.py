from google.adk.agents import Agent
from google.adk.tools import google_search

from .prompts import JOB_AGENT_INSTRUCTION
from .tools.applied_jobs_store import (
    check_cooldown,
    list_recent_applications,
    record_application,
)
from .tools.cv_tools import read_cv
from .tools.handshake_tools import (
    get_application_questions,
    prepare_application,
    search_handshake_jobs,
    submit_application,
)
from .tools.profile_store import get_profile, save_profile_fields

root_agent = Agent(
    model="gemini-flash-latest",
    name="job_agent",
    description=(
        "Specialist that searches Handshake for matching software "
        "engineering roles, drafts tailored application answers, and "
        "applies on the user's behalf after explicit review/approval."
    ),
    instruction=JOB_AGENT_INSTRUCTION,
    tools=[
        google_search,
        read_cv,
        get_profile,
        save_profile_fields,
        check_cooldown,
        record_application,
        list_recent_applications,
        search_handshake_jobs,
        get_application_questions,
        prepare_application,
        submit_application,
    ],
)
