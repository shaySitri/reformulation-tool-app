"""
validators.py
-------------
Shared validation logic for both input utterances (Stage 1) and pipeline
output strings (Stage 2).

Allowed character set
---------------------
Derived by reading every template literal in command_reformulatuin_script.py
and tracing the create_command() normalisation function:

    create_command() joins the template list with spaces, then calls
    .replace("- ", "") which strips all "ל-", "מ-", "ב-" connector hyphens
    before they reach the final output.

After that transformation, every possible output contains exactly:
  - Hebrew consonants and final forms  (Unicode block U+05D0 – U+05EA)
  - ASCII space                        (U+0020)

Nothing else — no digits, no Latin letters, no punctuation — survives into
any template output. The same character set is therefore applied to both
Stage 1 (input) and Stage 2 (output) validation.

Minimum output length
---------------------
The shortest string any template handler can produce is the call_command()
fallback:  "תתקשרי"  (6 characters, returned when no person name is found).
Any reformulated output shorter than this cannot correspond to a valid
template result and is treated as unusable.

Usage
-----
    from backend.validators import validate_input, validate_output

    # Stage 1 — before the pipeline runs
    if not validate_input(utterance):
        raise ValueError("Invalid input.")

    # Stage 2 — after reformulate() returns
    if not validate_output(reformulated):
        # treat as failed — do not return to client
        ...
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Compiled regular expressions
# ---------------------------------------------------------------------------

# Matches a full string that contains only Hebrew letters and/or spaces.
# re.fullmatch ensures every character — not just the prefix — is checked.
_ALL_ALLOWED_RE = re.compile(r"[\u05D0-\u05EA ]*")

# Matches at least one Hebrew consonant or final form anywhere in the string.
_HAS_HEBREW_RE = re.compile(r"[\u05D0-\u05EA]")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Length of the shortest valid template output ("תתקשרי", the call fallback).
# Outputs shorter than this cannot originate from a valid template.
MIN_OUTPUT_LENGTH: int = 6


# ---------------------------------------------------------------------------
# Core character-set check (shared by both stages)
# ---------------------------------------------------------------------------

def is_valid_text(text: str) -> bool:
    """
    Return True if every character in *text* is either a Hebrew letter
    (U+05D0–U+05EA, including all final forms) or an ASCII space.

    This is the shared rule applied identically to input and output.
    It does not check for emptiness — callers handle that separately.

    Args:
        text: Any string to inspect.

    Returns:
        True  — all characters are in the allowed set.
        False — at least one character is outside the allowed set
                (e.g. a digit, Latin letter, '#', punctuation, etc.).
    """
    return bool(_ALL_ALLOWED_RE.fullmatch(text))


def has_hebrew_letter(text: str) -> bool:
    """
    Return True if *text* contains at least one Hebrew letter.

    Used in Stage 2 to catch outputs that consist only of spaces or that
    were somehow emptied of all content after stripping.

    Args:
        text: Any string to inspect.

    Returns:
        True  — at least one Hebrew letter found.
        False — no Hebrew letter present.
    """
    return bool(_HAS_HEBREW_RE.search(text))


# ---------------------------------------------------------------------------
# Stage 1 — Input validation
# ---------------------------------------------------------------------------

def validate_input(text: str) -> bool:
    """
    Stage 1 validation: run before the intent classifier and reformulation
    pipeline execute.

    Rules (applied in order):
        1. Must not be empty or whitespace-only.
        2. Every character must be a Hebrew letter or ASCII space
           (delegates to is_valid_text).

    Args:
        text: The stripped utterance string from the API request body.
              Callers must strip whitespace before passing it here.

    Returns:
        True  — input is safe to pass to the pipeline.
        False — input should be rejected; return HTTP 400 to the client.
    """
    # Rule 1: non-empty after stripping
    if not text or not text.strip():
        return False

    # Rule 2: allowed characters only
    return is_valid_text(text)


# ---------------------------------------------------------------------------
# Stage 2 — Output validation
# ---------------------------------------------------------------------------

def validate_output(text: Optional[str]) -> bool:
    """
    Stage 2 validation: run after reformulate() returns, before the result
    is sent to the client.

    Guards against None, empty strings, suspiciously short outputs, outputs
    with no Hebrew content, and outputs containing invalid characters (e.g.
    placeholders, garbled NER extractions with Latin letters or digits).

    Rules (applied in order):
        1. Must not be None.
        2. Must not be empty or whitespace-only after stripping.
        3. Stripped length must be >= MIN_OUTPUT_LENGTH (6 chars = "תתקשרי").
        4. Must contain at least one Hebrew letter.
        5. Every character must be a Hebrew letter or ASCII space
           (delegates to is_valid_text — same rule as Stage 1).

    Args:
        text: The string returned by the reformulation script, or None if
              the script returned None unexpectedly.

    Returns:
        True  — output is valid and can be sent to the client.
        False — output is unusable; the API should return status="failed".
    """
    # Rule 1: not None
    if text is None:
        return False

    stripped = text.strip()

    # Rule 2: non-empty after stripping
    if not stripped:
        return False

    # Rule 3: minimum template length
    if len(stripped) < MIN_OUTPUT_LENGTH:
        return False

    # Rule 4: contains at least one Hebrew letter
    if not has_hebrew_letter(stripped):
        return False

    # Rule 5: allowed characters only (use full text, not stripped, so leading/
    # trailing spaces are also checked — spaces are allowed, but not other
    # whitespace such as tabs or newlines)
    return is_valid_text(text)
