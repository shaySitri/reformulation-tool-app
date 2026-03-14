"""
test_validators.py
------------------
Group A — Unit tests for backend/validators.py.

These tests call the validator functions directly without involving the HTTP
layer, the intent classifier, or the reformulation pipeline. They verify that
the validation logic itself is correct and covers all specified rules.

The tests do NOT evaluate model quality or NLP correctness — they test the
backend validation layer in isolation.

Run with:
    pytest tests/test_validators.py -v
"""

import pytest

from backend.validators import (
    MIN_OUTPUT_LENGTH,
    has_hebrew_letter,
    is_valid_text,
    validate_input,
    validate_output,
)

# ---------------------------------------------------------------------------
# Known values used across tests
# ---------------------------------------------------------------------------

# The shortest possible template output: call_command fallback (6 chars).
MINIMUM_VALID_OUTPUT = "תתקשרי"  # exactly MIN_OUTPUT_LENGTH characters

# One character shorter than the minimum — must be rejected by Stage 2.
BELOW_MINIMUM_OUTPUT = "תתקשר"   # 5 characters

# Known valid template outputs (camera and flashlight are deterministic).
CAMERA_OUTPUT = "תפתחי מצלמה"
FLASHLIGHT_OUTPUT = "להדליק פנס"


# ===========================================================================
# 1. is_valid_text — character-set check (shared by both stages)
# ===========================================================================

class TestIsValidText:
    """
    Verify that is_valid_text() accepts Hebrew letters and spaces only,
    and rejects any character outside that set.
    """

    def test_valid_hebrew_only(self) -> None:
        """Pure Hebrew consonants with no spaces must be accepted."""
        assert is_valid_text("תצלמי") is True

    def test_valid_hebrew_with_spaces(self) -> None:
        """Hebrew words separated by spaces must be accepted."""
        assert is_valid_text("תצלמי תמונה") is True

    def test_valid_camera_output(self) -> None:
        """Known deterministic camera output must be accepted."""
        assert is_valid_text(CAMERA_OUTPUT) is True

    def test_valid_flashlight_output(self) -> None:
        """Known deterministic flashlight output must be accepted."""
        assert is_valid_text(FLASHLIGHT_OUTPUT) is True

    def test_valid_minimum_template_output(self) -> None:
        """The shortest possible template output must be accepted."""
        assert is_valid_text(MINIMUM_VALID_OUTPUT) is True

    def test_empty_string_is_accepted_by_char_check(self) -> None:
        """
        is_valid_text does not check for emptiness — that is validate_input's job.
        An empty string trivially satisfies 'every char is allowed' (vacuously true).
        """
        assert is_valid_text("") is True

    def test_space_only_is_accepted_by_char_check(self) -> None:
        """
        Spaces are in the allowed set. is_valid_text does not check for
        meaningful content — validate_input / validate_output do that.
        """
        assert is_valid_text("   ") is True

    def test_english_letters_rejected(self) -> None:
        """Latin letters are not in the allowed set."""
        assert is_valid_text("hello") is False

    def test_digits_rejected(self) -> None:
        """Digits are not in the allowed set."""
        assert is_valid_text("123") is False

    def test_hash_rejected(self) -> None:
        """Hash characters are not in the allowed set."""
        assert is_valid_text("####") is False

    def test_mixed_hebrew_and_english_rejected(self) -> None:
        """A string with even one Latin character must be rejected."""
        assert is_valid_text("תשלחי john") is False

    def test_mixed_hebrew_and_digit_rejected(self) -> None:
        """A string with even one digit must be rejected."""
        assert is_valid_text("תשלחי 7") is False

    def test_hyphen_rejected(self) -> None:
        """
        Hyphens do not appear in final template outputs (create_command strips
        them). A hyphen in the input or output is therefore invalid.
        """
        assert is_valid_text("תתקשרי-") is False

    def test_colon_rejected(self) -> None:
        """Colons do not appear in any template output."""
        assert is_valid_text("שלח:") is False

    def test_question_mark_rejected(self) -> None:
        """Question marks are not in the allowed set."""
        assert is_valid_text("מה?") is False

    def test_newline_rejected(self) -> None:
        """Control characters including newline are not in the allowed set."""
        assert is_valid_text("שלום\nעולם") is False

    def test_tab_rejected(self) -> None:
        """Tabs are not in the allowed set."""
        assert is_valid_text("שלום\תמונה") is False


# ===========================================================================
# 2. has_hebrew_letter
# ===========================================================================

class TestHasHebrewLetter:
    """Verify that has_hebrew_letter() detects the presence of Hebrew content."""

    def test_hebrew_string_detected(self) -> None:
        assert has_hebrew_letter("שלום") is True

    def test_single_hebrew_letter_detected(self) -> None:
        assert has_hebrew_letter("א") is True

    def test_empty_string_has_no_hebrew(self) -> None:
        assert has_hebrew_letter("") is False

    def test_spaces_only_has_no_hebrew(self) -> None:
        assert has_hebrew_letter("   ") is False

    def test_english_only_has_no_hebrew(self) -> None:
        assert has_hebrew_letter("hello") is False

    def test_digits_only_has_no_hebrew(self) -> None:
        assert has_hebrew_letter("12345") is False


# ===========================================================================
# 3. validate_input — Stage 1
# ===========================================================================

class TestValidateInput:
    """
    Verify Stage 1 input validation rules:
        1. Must not be empty or whitespace-only.
        2. Every character must be Hebrew or space.
    """

    def test_valid_hebrew_utterance(self) -> None:
        """A typical Hebrew command must pass Stage 1."""
        assert validate_input("תתקשרי לאמא שלי") is True

    def test_valid_single_hebrew_word(self) -> None:
        """A single Hebrew word must pass Stage 1."""
        assert validate_input("שלום") is True

    def test_empty_string_rejected(self) -> None:
        """Empty string must be rejected."""
        assert validate_input("") is False

    def test_whitespace_only_rejected(self) -> None:
        """Whitespace-only string must be rejected."""
        assert validate_input("   ") is False

    def test_english_rejected(self) -> None:
        """English letters must be rejected at Stage 1."""
        assert validate_input("call my mom") is False

    def test_digit_rejected(self) -> None:
        """Digits must be rejected at Stage 1."""
        assert validate_input("שעה 7") is False

    def test_hash_rejected(self) -> None:
        """Hash characters must be rejected at Stage 1."""
        assert validate_input("####") is False

    def test_mixed_hebrew_and_english_rejected(self) -> None:
        """One Latin character contaminates an otherwise valid input."""
        assert validate_input("תשלחי john") is False

    def test_mixed_hebrew_and_digit_rejected(self) -> None:
        """One digit contaminates an otherwise valid input."""
        assert validate_input("שלחי הודעה ל7") is False

    def test_punctuation_rejected(self) -> None:
        """Punctuation characters are not in the allowed set."""
        assert validate_input("שלחי,") is False


# ===========================================================================
# 4. validate_output — Stage 2
# ===========================================================================

class TestValidateOutput:
    """
    Verify Stage 2 output validation rules:
        1. Must not be None.
        2. Must not be empty or whitespace-only after stripping.
        3. Stripped length >= MIN_OUTPUT_LENGTH (6 chars = "תתקשרי").
        4. Must contain at least one Hebrew letter.
        5. Every character must be Hebrew or space.
    """

    def test_valid_camera_output(self) -> None:
        """The deterministic camera output must pass Stage 2."""
        assert validate_output(CAMERA_OUTPUT) is True

    def test_valid_flashlight_output(self) -> None:
        """The deterministic flashlight output must pass Stage 2."""
        assert validate_output(FLASHLIGHT_OUTPUT) is True

    def test_minimum_template_length_passes(self) -> None:
        """
        The shortest valid template output ("תתקשרי", MIN_OUTPUT_LENGTH chars)
        must be accepted. This is the minimum valid threshold — a string of
        exactly this length that satisfies all other rules must pass.
        """
        assert len(MINIMUM_VALID_OUTPUT) == MIN_OUTPUT_LENGTH, (
            f"Test setup error: MINIMUM_VALID_OUTPUT has {len(MINIMUM_VALID_OUTPUT)} chars, "
            f"expected {MIN_OUTPUT_LENGTH}"
        )
        assert validate_output(MINIMUM_VALID_OUTPUT) is True

    def test_below_minimum_template_length_rejected(self) -> None:
        """
        A string shorter than MIN_OUTPUT_LENGTH must be rejected even if it
        contains only valid Hebrew characters. This guards against truncated
        or garbled outputs that happen to contain Hebrew letters.
        """
        assert len(BELOW_MINIMUM_OUTPUT) == MIN_OUTPUT_LENGTH - 1, (
            f"Test setup error: BELOW_MINIMUM_OUTPUT has {len(BELOW_MINIMUM_OUTPUT)} chars, "
            f"expected {MIN_OUTPUT_LENGTH - 1}"
        )
        assert validate_output(BELOW_MINIMUM_OUTPUT) is False

    def test_none_rejected(self) -> None:
        """None must be rejected (rule 1)."""
        assert validate_output(None) is False

    def test_empty_string_rejected(self) -> None:
        """Empty string must be rejected (rule 2)."""
        assert validate_output("") is False

    def test_whitespace_only_rejected(self) -> None:
        """Whitespace-only string must be rejected (rule 2)."""
        assert validate_output("   ") is False

    def test_no_hebrew_rejected(self) -> None:
        """
        A string of spaces long enough to pass the length check but containing
        no Hebrew letters must be rejected (rule 4).
        """
        assert validate_output("      ") is False  # 6 spaces, no Hebrew

    def test_hash_placeholder_rejected(self) -> None:
        """A placeholder-style output must be rejected (rule 5)."""
        assert validate_output("########") is False

    def test_english_in_output_rejected(self) -> None:
        """English letters in the output must be rejected (rule 5)."""
        assert validate_output("call my mom please") is False

    def test_digits_in_output_rejected(self) -> None:
        """Digits in the output must be rejected (rule 5)."""
        assert validate_output("שלח הודעה ב 7:30") is False

    def test_mixed_hebrew_and_english_rejected(self) -> None:
        """One Latin character in an otherwise valid output must be rejected."""
        assert validate_output("תשלחי הודעה John") is False

    def test_typical_sms_output_passes(self) -> None:
        """A realistic SMS reformulation must pass Stage 2."""
        assert validate_output("תשלחי הודעה לדוד") is True

    def test_typical_call_output_passes(self) -> None:
        """A realistic call reformulation must pass Stage 2."""
        assert validate_output("תתקשרי לאמא") is True

    def test_min_output_length_constant_is_correct(self) -> None:
        """
        Verify that MIN_OUTPUT_LENGTH equals the actual length of 'תתקשרי',
        the shortest template output. This guards against accidental changes
        to the constant.
        """
        assert MIN_OUTPUT_LENGTH == len("תתקשרי"), (
            f"MIN_OUTPUT_LENGTH is {MIN_OUTPUT_LENGTH} but len('תתקשרי') is {len('תתקשרי')}"
        )
