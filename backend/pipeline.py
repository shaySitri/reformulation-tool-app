"""
pipeline.py
-----------
Orchestrates the full two-stage Hebrew command reformulation pipeline:

    Stage 1 — Intent classification
        The IntentClassifier (AlephBERT fine-tuned on 10 Hebrew command
        intents) predicts which intent the utterance belongs to.

    Stage 2 — Reformulation
        The existing command_reformulatuin_script.py is imported as a Python
        module and its `reformulate(utter, intent)` function is called. That
        function uses two NER pipelines (heBERT_NER and dictabert-ner) to
        extract entities and fill intent-specific templates.

NER model loading side-effect
------------------------------
Importing command_reformulatuin_script triggers module-level code in that
file that downloads and loads:
  - avichr/heBERT_NER        (primary Hebrew NER model)
  - dicta-il/dictabert-ner   (fallback / oracle Hebrew NER model)

Both models are kept alive as module globals for the lifetime of the process.
This import therefore takes ~10–30 seconds on first run (or if not cached in
~/.cache/huggingface/). After the first import, subsequent calls to
run_pipeline() are fast.

Path resolution
---------------
This module appends the repository root to sys.path so that
`import command_reformulatuin_script` succeeds regardless of the working
directory from which uvicorn or pytest is launched.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure the repository root (parent of this file's parent directory) is on
# sys.path so `command_reformulatuin_script` can be found via a plain import,
# regardless of the CWD at runtime.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# This import triggers loading of the two NER models as module-level globals.
# It happens exactly once, when pipeline.py is first imported by main.py.
import command_reformulatuin_script as _reformulation  # noqa: E402

logger = logging.getLogger(__name__)

# Intent label lookup — mirrors the model's config.json id2label.
# Used for logging and as a fallback if the classifier's id2label is empty.
INTENT_LABELS: dict[int, str] = {
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


def run_pipeline(utterance: str, classifier: Any) -> dict[str, Any]:
    """
    Execute the full reformulation pipeline on a single Hebrew utterance.

    Steps
    -----
    1. Strip and validate the utterance.
    2. Classify the intent using the provided IntentClassifier.
    3. Call reformulate(utterance, intent_id) from the reformulation module.
    4. Return a structured dict with all outputs.

    Args:
        utterance:  Raw Hebrew text from the user (may include leading/
                    trailing whitespace — it will be stripped here).
        classifier: A loaded IntentClassifier instance. Must have already
                    had .load() called before this function is invoked.

    Returns:
        A dict with the following keys:
            original     (str) — The utterance after stripping whitespace.
            intent_id    (int) — Predicted intent index (0–9).
            intent_label (str) — Human-readable intent name.
            reformulated (str) — The structured Hebrew command string.

    Raises:
        ValueError:   If the utterance is empty or whitespace-only.
        RuntimeError: If the reformulation module raises an unexpected error.
    """
    utterance = utterance.strip()

    if not utterance:
        raise ValueError("Utterance must not be empty.")

    # --- Stage 1: intent classification ---
    logger.debug("Classifying utterance (length=%d): %r", len(utterance), utterance[:60])
    intent_id, intent_label = classifier.predict(utterance)
    logger.info("Intent predicted: %d (%s) for %r", intent_id, intent_label, utterance[:40])

    # --- Stage 2: reformulation ---
    # The reformulation module's global functions always return a str (never
    # None). We still wrap in try/except to surface any internal NER errors
    # as a clean RuntimeError rather than a raw traceback.
    logger.debug("Reformulating with intent_id=%d", intent_id)
    try:
        reformulated: str = _reformulation.reformulate(utterance, intent_id)
    except Exception as exc:
        logger.exception(
            "Reformulation failed — utterance=%r, intent_id=%d", utterance, intent_id
        )
        raise RuntimeError(
            f"Reformulation step failed for intent '{intent_label}': {exc}"
        ) from exc

    logger.info(
        "Pipeline complete: %r → intent=%s → %r",
        utterance[:40],
        intent_label,
        reformulated[:60],
    )

    return {
        "original": utterance,
        "intent_id": intent_id,
        "intent_label": intent_label,
        "reformulated": reformulated,
    }
