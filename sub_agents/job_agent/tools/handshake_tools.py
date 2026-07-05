"""Handshake job search + apply automation.

IMPORTANT — first-pass implementation, not yet validated live:
The selectors and flow below are written from general knowledge of
Handshake's UI (search results, an in-app "Apply" flow with custom
question fields, and an external "Apply on company site" redirect for
many postings). They have not been exercised against a real Handshake
account/session, and Handshake's markup changes over time. Treat this as
a first draft to validate and adjust — in a live session, run
scripts/login_handshake.py, then call search_handshake_jobs with
headless left off, watch what actually renders, and adjust the locator
lines marked "VERIFY:" below.

Only postings with an in-app ("Apply on Handshake") flow are supported by
prepare_application/submit_application — postings that redirect to an
external ATS (Greenhouse, Lever, Workday, etc.) are reported as
`application_type: "external"` and are out of scope for this pass; they'd
need per-ATS handling.
"""

import logging
import os

from . import browser

_logger = logging.getLogger(__name__)
_SEARCH_URL = "https://app.joinhandshake.com/stu/postings"


def search_handshake_jobs(role_titles: list[str], limit: int = 25) -> dict:
    """Searches Handshake for postings matching the given role titles.

    This is the ONLY way job listings should be discovered from Handshake
    — never use general web search to find job postings, only this tool.

    Args:
        role_titles: Role titles/keywords to search for, e.g.
            ["Software Engineer", "Forward Deployed Engineer"].
        limit: Maximum number of unique postings to return across all
            role titles combined.

    Returns:
        dict: {"status": "success", "jobs": [{"external_job_id", "title",
        "company", "location", "url", "posted_at"}, ...]} or
        {"status": "error", "error_message": "..."}.
    """
    try:
        page = browser.get_page("handshake", "search")
        seen_ids: set[str] = set()
        jobs: list[dict] = []

        for role_title in role_titles:
            if len(jobs) >= limit:
                break

            page.goto(f"{_SEARCH_URL}?query={role_title}&sort=default")
            # VERIFY: confirm this is really how result cards are marked up.
            cards = page.get_by_role("link", name=role_title).all()
            if not cards:
                cards = page.locator("[data-hook='postings-list'] a").all()

            for card in cards:
                if len(jobs) >= limit:
                    break
                href = card.get_attribute("href") or ""
                external_job_id = href.rstrip("/").split("/")[-1]
                if not external_job_id or external_job_id in seen_ids:
                    continue
                seen_ids.add(external_job_id)
                jobs.append(
                    {
                        "external_job_id": external_job_id,
                        "title": card.inner_text().strip().split("\n")[0],
                        "company": "",  # VERIFY: extract from card structure
                        "location": "",  # VERIFY: extract from card structure
                        "url": f"{_SEARCH_URL}/{external_job_id}",
                        "posted_at": "",
                    }
                )

        return {"status": "success", "jobs": jobs}
    except Exception:
        _logger.exception("Handshake search failed.")
        return {
            "status": "error",
            "error_message": (
                "Could not search Handshake right now. The session may "
                "have expired — try running scripts/login_handshake.py again."
            ),
        }


def get_application_questions(external_job_id: str) -> dict:
    """Opens a Handshake posting's apply flow and reads its question fields.

    Call this before drafting answers, so answers are written for the
    questions the posting actually asks rather than guessed generically.

    Args:
        external_job_id: The posting's Handshake ID, as returned by
            search_handshake_jobs.

    Returns:
        dict: {"status": "success", "application_type": "internal" or
        "external", "questions": [{"label", "field_type"}, ...]}. When
        application_type is "external", the posting redirects off
        Handshake to the employer's own site and is not supported by
        prepare_application/submit_application yet.
    """
    try:
        page = browser.get_page("handshake", external_job_id)
        page.goto(f"{_SEARCH_URL}/{external_job_id}")
        # VERIFY: the actual label/selector Handshake uses for its apply CTA.
        apply_button = page.get_by_role("button", name="Apply")
        if apply_button.count() == 0:
            apply_button = page.get_by_role("link", name="Apply")
        apply_button.first.click()
        page.wait_for_load_state("networkidle")

        if "joinhandshake.com" not in page.url:
            return {
                "status": "success",
                "application_type": "external",
                "questions": [],
            }

        # VERIFY: how custom questions are actually marked up (label + input pairs).
        labels = page.locator("form label").all()
        questions = []
        for label in labels:
            text = label.inner_text().strip()
            if text:
                questions.append({"label": text, "field_type": "text"})

        return {"status": "success", "application_type": "internal", "questions": questions}
    except Exception:
        _logger.exception("Reading Handshake application questions failed for %s", external_job_id)
        return {
            "status": "error",
            "error_message": "Could not open that posting's application form.",
        }


def prepare_application(
    external_job_id: str,
    cv_path: str,
    standard_answers: dict,
    question_answers: dict,
) -> dict:
    """Fills out a Handshake application WITHOUT submitting it.

    Attaches the CV, fills standard fields, and fills each custom
    question. Takes a screenshot so the draft can be reviewed by the
    user before submit_application is ever called.

    Args:
        external_job_id: The posting's Handshake ID.
        cv_path: Absolute path to the CV file to attach.
        standard_answers: Common fields, e.g. {"first_name": "...",
            "last_name": "...", "email": "...", "phone": "...",
            "visa_sponsorship_required": "No"}.
        question_answers: Mapping of question label -> drafted answer
            text, for the labels returned by get_application_questions.

    Returns:
        dict: {"status": "success", "screenshot_path": "...",
        "draft_summary": {...}} or {"status": "error", "error_message": "..."}.
        Never calls submit — a separate, explicit submit_application call
        is required after the user reviews this draft.
    """
    try:
        page = browser.get_page("handshake", external_job_id)

        for field, value in standard_answers.items():
            # VERIFY: real field labels on Handshake's application form.
            locator = page.get_by_label(field.replace("_", " "), exact=False)
            if locator.count() > 0:
                locator.first.fill(str(value))

        file_input = page.locator("input[type='file']")
        if file_input.count() > 0:
            file_input.first.set_input_files(cv_path)

        for label, answer in question_answers.items():
            locator = page.get_by_label(label, exact=False)
            if locator.count() > 0:
                locator.first.fill(answer)

        screenshot_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "screenshots"
        )
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"{external_job_id}.png")
        page.screenshot(path=screenshot_path, full_page=True)

        draft_summary = {**standard_answers, **question_answers}

        from .. import db

        db.init_db()
        with db.lock(), db.connect() as conn:
            conn.execute(
                "INSERT INTO pending_drafts "
                "(job_id, source, company, role_title, job_url, draft_summary, screenshot_path, created_at) "
                "VALUES (?, 'handshake', '', '', ?, ?, ?, ?) "
                "ON CONFLICT(job_id) DO UPDATE SET draft_summary = excluded.draft_summary, "
                "screenshot_path = excluded.screenshot_path, created_at = excluded.created_at",
                (
                    external_job_id,
                    f"{_SEARCH_URL}/{external_job_id}",
                    str(draft_summary),
                    screenshot_path,
                    db.now_iso(),
                ),
            )

        return {
            "status": "success",
            "screenshot_path": screenshot_path,
            "draft_summary": draft_summary,
        }
    except Exception:
        _logger.exception("Preparing Handshake application failed for %s", external_job_id)
        return {
            "status": "error",
            "error_message": "Could not fill out that application.",
        }


def submit_application(external_job_id: str) -> dict:
    """Clicks final Submit on a previously prepared Handshake application.

    Only call this after the user has explicitly reviewed and approved
    the draft from prepare_application — never as part of the same step
    that prepared it.

    Args:
        external_job_id: The posting's Handshake ID.

    Returns:
        dict: {"status": "success"} or {"status": "error", "error_message": "..."}.
        On success, the caller must still record the application via
        applied_jobs_store.record_application — this tool only submits.
    """
    try:
        page = browser.get_page("handshake", external_job_id)
        # VERIFY: the actual final submit control's accessible name.
        submit_button = page.get_by_role("button", name="Submit Application")
        if submit_button.count() == 0:
            submit_button = page.get_by_role("button", name="Submit")
        submit_button.first.click()
        page.wait_for_load_state("networkidle")
        return {"status": "success"}
    except Exception:
        _logger.exception("Submitting Handshake application failed for %s", external_job_id)
        return {
            "status": "error",
            "error_message": "Could not submit that application.",
        }
