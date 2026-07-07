"""Google-signed ID token auth for calling private Cloud Run sub-agents.

On Cloud Run, each sub-agent is deployed with --no-allow-unauthenticated
(see gcp/deploy.sh) — only the orchestrator's own Cloud Run service
identity is granted roles/run.invoker on them. A plain httpx call would
get a 401; this attaches a fresh, correctly-scoped ID token to every
request instead, using the ambient service identity Cloud Run already
provides (no credentials to manage).

Locally / in Docker Compose, USE_GCP_ID_TOKEN_AUTH is unset, so
authed_httpx_client() returns None and RemoteA2aAgent falls back to its
default client — sub-agents aren't locked down there, there's nothing to
attach.
"""

import os

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token

_ENABLED = os.environ.get("USE_GCP_ID_TOKEN_AUTH", "false").lower() == "true"


def _service_base_url(agent_card_url: str) -> str:
    return agent_card_url.split("/.well-known/", 1)[0]


def authed_httpx_client(agent_card_url: str) -> httpx.AsyncClient | None:
    """Returns an httpx.AsyncClient that attaches a Google-signed ID token
    (audience = the sub-agent's own Cloud Run URL) to every outbound
    request, or None when GCP ID-token auth isn't enabled."""
    if not _ENABLED:
        return None

    audience = _service_base_url(agent_card_url)

    async def add_id_token(request: httpx.Request) -> None:
        token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
        request.headers["Authorization"] = f"Bearer {token}"

    return httpx.AsyncClient(event_hooks={"request": [add_id_token]})
