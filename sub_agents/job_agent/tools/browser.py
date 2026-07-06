"""Shared Playwright persistent-profile browser management.

Each job source gets its own on-disk browser profile directory, so a
one-time manual login (see scripts/login_handshake.py) is reused as a
normal returning-user session on every later run — no stored passwords,
no fresh automated-login pattern for bot detection to flag.

Contexts are cached at module level and kept open for the lifetime of
this process, so a page opened by one tool call (e.g. prepare_application)
is still open and interactable in a later tool call (e.g.
submit_application) within the same run.
"""

import os
import threading

from playwright.sync_api import sync_playwright

_PROFILES_ROOT = os.environ.get(
    "BROWSER_PROFILES_DIR",
    os.path.join(os.path.dirname(__file__), "..", "browser_profiles"),
)

# Defaults to visible so a human can watch/intervene during local, interactive
# use (e.g. scripts/login_handshake.py). Containers have no display, so
# deployment must set PLAYWRIGHT_HEADLESS=true — the login step itself still
# only ever runs locally beforehand, never inside a headless container.
_DEFAULT_HEADLESS = os.environ.get("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

_lock = threading.Lock()
_playwright = None
_contexts: dict[str, "playwright.sync_api.BrowserContext"] = {}
_pages: dict[str, "playwright.sync_api.Page"] = {}


def profile_dir(source: str) -> str:
    path = os.path.join(_PROFILES_ROOT, source)
    os.makedirs(path, exist_ok=True)
    return path


def get_context(source: str, headless: bool | None = None):
    """Returns the persistent BrowserContext for a job source, launching it
    on first use. Defaults to PLAYWRIGHT_HEADLESS (see above) when not
    given explicitly."""
    global _playwright
    if headless is None:
        headless = _DEFAULT_HEADLESS
    with _lock:
        if _playwright is None:
            _playwright = sync_playwright().start()
        if source not in _contexts:
            _contexts[source] = _playwright.chromium.launch_persistent_context(
                profile_dir(source),
                headless=headless,
            )
        return _contexts[source]


def get_page(source: str, page_key: str):
    """Returns a named page within a source's context, reused across tool
    calls (e.g. the same job's tab between prepare_application and
    submit_application). Creates a new tab if page_key hasn't been seen."""
    context = get_context(source)  # uses PLAYWRIGHT_HEADLESS default
    cache_key = f"{source}:{page_key}"
    with _lock:
        page = _pages.get(cache_key)
        if page is None or page.is_closed():
            page = context.new_page()
            _pages[cache_key] = page
        return page


def close_all() -> None:
    global _playwright
    with _lock:
        for context in _contexts.values():
            context.close()
        _contexts.clear()
        _pages.clear()
        if _playwright is not None:
            _playwright.stop()
            _playwright = None
