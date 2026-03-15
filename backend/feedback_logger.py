"""
feedback_logger.py
------------------
Single shared service for appending feedback records to a JSONL log file.

Each call to append_feedback() writes one JSON object (one line) to:
    <repo_root>/logs/feedback.jsonl

The logs/ directory is created automatically on first write.
Hebrew characters are preserved as-is (ensure_ascii=False).
"""

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOG_PATH = _REPO_ROOT / "logs" / "feedback.jsonl"


def append_feedback(record: dict) -> None:
    """
    Append a single feedback record to the JSONL log file.

    Args:
        record: Dict containing all feedback fields. Must be JSON-serialisable.
    """
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
