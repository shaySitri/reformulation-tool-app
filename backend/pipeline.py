"""
pipeline.py
-----------
Orchestrates the full two-stage Hebrew command reformulation pipeline,
including both input and output validation.

Pipeline stages
---------------
    Stage 1 — Input validation (validators.validate_input)
        Runs before any model inference. Rejects inputs that contain
        characters outside the allowed set (Hebrew letters + space).
        Invalid input raises ValueError → caught by the route handler → HTTP 400.

    Stage 2a — Intent classification (IntentClassifier.predict)
        AlephBERT fine-tuned on 10 Hebrew command intents.

    Stage 2b — Reformulation (command_reformulatuin_script.reformulate)
        NER-based entity extraction + template filling.
        The two NER models (heBERT_NER, dictabert-ner) are loaded at import
        time as module-level globals in command_reformulatuin_script.py.

    Stage 3 — Output validation (validators.validate_output)
        Runs after reformulate() returns. Checks the result for None,
        emptiness, minimum length, Hebrew content, and allowed characters.
        Invalid output does NOT raise an exception — instead, the pipeline
        returns status="failed" with reformulated=None.

Return value
------------
run_pipeline() always returns a dict with five keys:
    status       "success" | "failed"
    original     str
    intent_id    int
    intent_label str
    reformulated str | None   (None when status == "failed")

Path resolution
---------------
The repository root is added to sys.path so that
`import command_reformulatuin_script` works regardless of the CWD when
uvicorn or pytest is launched.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Add repository root to sys.path so the reformulation script is importable
# regardless of the working directory at runtime.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Importing this module triggers loading of the two NER models
# (avichr/heBERT_NER and dicta-il/dictabert-ner) as module-level globals.
# This happens once when pipeline.py is first imported by main.py.
import command_reformulatuin_script as _reformulation  # noqa: E402

from backend.validators import validate_input, validate_output  # noqa: E402

logger = logging.getLogger(__name__)

# Human-readable labels for logging (mirrors model config.json id2label).
_INTENT_LABELS: Dict[int, str] = {
    0: "call",
    1: "alarm",
    2: "sms",
    3: "search_query",
    4: "navigation",
    5: "calendar",
    6: "camera",
    7: "weather",
    8: "notes",
    9: "flashlight",
}


def run_pipeline(utterance: str, classifier: Any) -> Dict[str, Any]:
    """
    Execute the full validated reformulation pipeline on a Hebrew utterance.

    The function returns a result dict in all non-error cases. It raises
    only for true input errors (ValueError) or internal crashes (RuntimeError).
    Output quality failures are encoded as status="failed" in the return dict,
    not as exceptions.

    Args:
        utterance:  Raw Hebrew text from the API request body. May contain
                    leading/trailing whitespace — it is stripped here.
        classifier: A loaded IntentClassifier instance (must have had
                    .load() called before this function is invoked).

    Returns:
        A dict with keys:
            status       (str)  "success" or "failed"
            original     (str)  The stripped input utterance.
            intent_id    (int)  Predicted intent index (0–9).
            intent_label (str)  Human-readable intent name.
            reformulated (str | None)  Command string, or None on failure.

    Raises:
        ValueError:   Stage 1 input validation failed (empty or invalid chars).
                      The route handler maps this to HTTP 400 with a generic message.
        RuntimeError: The reformulation module raised an unexpected exception.
                      The route handler maps this to HTTP 500.
    """
    utterance = utterance.strip()

    # ------------------------------------------------------------------
    # Stage 1 — Input validation
    # Reject before any model inference to avoid wasting compute on
    # inputs that contain English letters, digits, or other disallowed chars.
    # ------------------------------------------------------------------
    if not validate_input(utterance):
        logger.debug("Stage 1 failed for utterance %r", utterance[:60])
        raise ValueError("Invalid input.")

    # ------------------------------------------------------------------
    # Stage 2a — Intent classification
    # ------------------------------------------------------------------
    logger.debug("Classifying utterance (length=%d): %r", len(utterance), utterance[:60])
    intent_id, intent_label = classifier.predict(utterance)
    logger.info("Intent predicted: %d (%s) for %r", intent_id, intent_label, utterance[:40])

    # ------------------------------------------------------------------
    # Stage 2b — Reformulation
    # Wrap in try/except to surface NER / template errors as RuntimeError
    # rather than leaking raw tracebacks to the route handler.
    # ------------------------------------------------------------------
    try:
        reformulated: str = _reformulation.reformulate(utterance, intent_id)
    except Exception as exc:
        logger.exception(
            "Reformulation raised an exception — utterance=%r, intent_id=%d",
            utterance,
            intent_id,
        )
        raise RuntimeError(
            f"Reformulation step failed for intent '{intent_label}': {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # Stage 3 — Output validation
    # A failed output is NOT an exception; it is a normal application-level
    # outcome. The status field encodes the result for the client.
    # ------------------------------------------------------------------
    if validate_output(reformulated):
        status = "success"
        logger.info(
            "Pipeline OK: %r → intent=%s → %r",
            utterance[:40],
            intent_label,
            reformulated[:60],
        )
    else:
        status = "failed"
        # Log the actual output internally (for debugging) but do not expose
        # it to the client — the response will contain reformulated=None.
        logger.warning(
            "Stage 3 output validation failed — utterance=%r, intent=%s, raw_output=%r",
            utterance[:40],
            intent_label,
            (reformulated or "")[:60],
        )
        reformulated = None  # type: ignore[assignment]

    return {
        "status": status,
        "original": utterance,
        "intent_id": intent_id,
        "intent_label": intent_label,
        "reformulated": reformulated,
    }
