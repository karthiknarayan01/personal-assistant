import logging
import os

_logger = logging.getLogger(__name__)


def read_cv(path: str) -> dict:
    """Extracts plain text from a CV/resume file so it can be read as context.

    Supports .pdf, .docx, and .txt. The extracted text is not stored
    automatically — after reading it, use save_profile_fields (or
    save_candidate_summary in profile_store) to persist whatever
    structured facts (companies, skills, education) you derive from it,
    once the user confirms they're accurate.

    Args:
        path: Absolute path to the CV file on disk.

    Returns:
        dict: {"status": "success", "text": "<extracted plain text>"} or
        {"status": "error", "error_message": "<short, sanitized description>"}.
    """
    if not os.path.isfile(path):
        return {"status": "error", "error_message": f"No file found at '{path}'."}

    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".pdf":
            text = _read_pdf(path)
        elif ext == ".docx":
            text = _read_docx(path)
        elif ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            return {
                "status": "error",
                "error_message": f"Unsupported file type '{ext}'. Use .pdf, .docx, or .txt.",
            }
    except Exception:
        _logger.exception("Failed to extract text from CV at %s", path)
        return {
            "status": "error",
            "error_message": "Could not read that file. It may be corrupted or password-protected.",
        }

    if not text.strip():
        return {
            "status": "error",
            "error_message": "No extractable text found in that file (it may be a scanned image).",
        }

    return {"status": "success", "text": text}


def _read_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: str) -> str:
    import docx

    document = docx.Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
