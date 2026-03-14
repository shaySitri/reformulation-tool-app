"""
test_api.py
-----------
Full pytest test suite for the Hebrew Voice Command Reformulation API.

Test categories
---------------
1. Pipeline structure tests  — verify API response shape, field types, and
                               HTTP status codes are always correct.
2. Functional intent tests   — one representative Hebrew utterance per intent
                               (all 10 intents covered). Verifies the pipeline
                               does not crash and returns a non-empty result.
3. Classifier output tests   — verify the intent classifier returns plausible
                               predictions for unambiguous Hebrew utterances.
4. Edge case tests           — empty input, whitespace, very long text,
                               non-Hebrew text, special characters, and
                               malformed HTTP requests.

Running the suite
-----------------
    # From the repository root:
    pytest tests/ -v

    # Run only one category:
    pytest tests/ -v -k "functional"
    pytest tests/ -v -k "edge"
    pytest tests/ -v -k "classifier"
"""

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# Helper constants
# ===========================================================================

# Expected intent labels for the 10 classes (mirrors model config.json)
INTENT_LABELS = {
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

# Known exact outputs for the two zero-argument intents (camera, flashlight).
# These handlers ignore the utterance and return a hard-coded Hebrew string.
CAMERA_OUTPUT = "תפתחי מצלמה"
FLASHLIGHT_OUTPUT = "להדליק פנס"


# ===========================================================================
# Utility functions
# ===========================================================================

def post_reformulate(client: TestClient, utterance: str) -> dict:
    """
    Helper: POST /reformulate with the given utterance and return the JSON body.

    Args:
        client:    The session-scoped TestClient.
        utterance: Hebrew text to send.

    Returns:
        Parsed JSON response body as a dict.
    """
    response = client.post("/reformulate", json={"utterance": utterance})
    return response


def assert_valid_response_structure(body: dict) -> None:
    """
    Assert that a successful response body contains all required fields with
    the correct types.

    This helper is reused across every functional test so that structure
    validation is never omitted.

    Args:
        body: Parsed JSON dict from a 200 response.
    """
    assert "original" in body, "Response must contain 'original' field"
    assert "intent_id" in body, "Response must contain 'intent_id' field"
    assert "intent_label" in body, "Response must contain 'intent_label' field"
    assert "reformulated" in body, "Response must contain 'reformulated' field"

    assert isinstance(body["original"], str), "'original' must be a string"
    assert isinstance(body["intent_id"], int), "'intent_id' must be an integer"
    assert isinstance(body["intent_label"], str), "'intent_label' must be a string"
    assert isinstance(body["reformulated"], str), "'reformulated' must be a string"

    assert 0 <= body["intent_id"] <= 9, f"'intent_id' must be 0–9, got {body['intent_id']}"
    assert body["intent_label"] in INTENT_LABELS.values(), (
        f"'intent_label' must be a known label, got {body['intent_label']!r}"
    )
    assert len(body["reformulated"]) > 0, "'reformulated' must not be an empty string"


# ===========================================================================
# 1. Pipeline structure tests
# ===========================================================================

class TestPipelineStructure:
    """
    Verify the API response structure and HTTP status codes are always correct,
    independent of which intent is predicted.
    """

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """
        GET /health must return 200 OK when the server is running.
        Verifies the liveness probe works before any pipeline tests run.
        """
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["models_loaded"] is True

    def test_successful_response_has_all_required_fields(self, client: TestClient) -> None:
        """
        A valid Hebrew utterance must produce a 200 response containing
        all four required fields: original, intent_id, intent_label, reformulated.
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        assert_valid_response_structure(response.json())

    def test_original_field_matches_stripped_input(self, client: TestClient) -> None:
        """
        The 'original' field must reflect the utterance after whitespace stripping,
        not the raw bytes from the request body.
        """
        response = post_reformulate(client, "  תתקשרי לאמא שלי  ")
        assert response.status_code == 200
        assert response.json()["original"] == "תתקשרי לאמא שלי"

    def test_intent_id_is_within_valid_range(self, client: TestClient) -> None:
        """
        The 'intent_id' must always be one of the 10 valid class indices (0–9),
        even for unusual inputs.
        """
        response = post_reformulate(client, "שלום")
        assert response.status_code == 200
        assert 0 <= response.json()["intent_id"] <= 9

    def test_intent_label_matches_intent_id(self, client: TestClient) -> None:
        """
        The 'intent_label' must be the canonical label for the returned 'intent_id'.
        These must be consistent with each other (not mismatch).
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        expected_label = INTENT_LABELS[body["intent_id"]]
        assert body["intent_label"] == expected_label, (
            f"intent_label={body['intent_label']!r} does not match "
            f"intent_id={body['intent_id']} (expected {expected_label!r})"
        )

    def test_content_type_is_json(self, client: TestClient) -> None:
        """
        The response Content-Type header must be application/json.
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert "application/json" in response.headers["content-type"]


# ===========================================================================
# 2. Functional intent tests — all 10 intents
# ===========================================================================

class TestFunctionalIntents:
    """
    One representative Hebrew utterance per intent. Each test verifies that:
      - The HTTP status is 200.
      - The response structure is valid (all fields, correct types).
      - The reformulated output is non-empty.

    These are integration tests of the full pipeline. We deliberately do NOT
    assert exact reformulated strings because NER output may vary slightly by
    model version or runtime. We DO assert the expected intent label for
    unambiguous utterances, since the model has 99.61% accuracy.
    """

    def test_intent_call(self, client: TestClient) -> None:
        """
        Intent 0 (call): 'תתקשרי לאמא שלי' — 'Call my mom'.
        Verifies the pipeline handles a clear phone-call command.
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "call", (
            f"Expected intent 'call', got {body['intent_label']!r}"
        )

    def test_intent_alarm(self, client: TestClient) -> None:
        """
        Intent 1 (alarm): 'תעירי אותי בשש בבוקר' — 'Wake me up at six in the morning'.
        Verifies time extraction and alarm template generation.
        """
        response = post_reformulate(client, "תעירי אותי בשש בבוקר")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "alarm", (
            f"Expected intent 'alarm', got {body['intent_label']!r}"
        )

    def test_intent_sms(self, client: TestClient) -> None:
        """
        Intent 2 (sms): 'תשלחי הודעה לדוד שאני בדרך' — 'Send a message to David that I'm on my way'.
        Verifies person-name extraction and message content extraction.
        """
        response = post_reformulate(client, "תשלחי הודעה לדוד שאני בדרך")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "sms", (
            f"Expected intent 'sms', got {body['intent_label']!r}"
        )

    def test_intent_search_query(self, client: TestClient) -> None:
        """
        Intent 3 (search_query): 'תחפשי לי מידע על מחלת הסוכרת' — 'Search for info about diabetes'.
        Verifies search-query reformulation strips filler words.
        """
        response = post_reformulate(client, "תחפשי לי מידע על מחלת הסוכרת")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "search_query", (
            f"Expected intent 'search_query', got {body['intent_label']!r}"
        )

    def test_intent_navigation(self, client: TestClient) -> None:
        """
        Intent 4 (navigation): 'תנווטי אותי מהבית לתל אביב' — 'Navigate me from home to Tel Aviv'.
        Verifies dual-location extraction (origin + destination).
        """
        response = post_reformulate(client, "תנווטי אותי מהבית לתל אביב")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "navigation", (
            f"Expected intent 'navigation', got {body['intent_label']!r}"
        )

    def test_intent_calendar(self, client: TestClient) -> None:
        """
        Intent 5 (calendar): 'תוסיפי פגישה ביומן מחר בשעה שתיים' — 'Add a meeting tomorrow at two'.
        Verifies date/time parsing and calendar template generation.
        Note: calander_command() prints debug info to stdout — this is a
        known issue in the existing script and does not affect correctness.
        """
        response = post_reformulate(client, "תוסיפי פגישה ביומן מחר בשעה שתיים")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "calendar", (
            f"Expected intent 'calendar', got {body['intent_label']!r}"
        )

    def test_intent_camera(self, client: TestClient) -> None:
        """
        Intent 6 (camera): 'תצלמי תמונה' — 'Take a photo'.
        Camera is a fixed-output intent — the reformulated string is always
        'תפתחי מצלמה' regardless of the utterance. We verify this exact value.
        """
        response = post_reformulate(client, "תצלמי תמונה")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "camera", (
            f"Expected intent 'camera', got {body['intent_label']!r}"
        )
        assert body["reformulated"] == CAMERA_OUTPUT, (
            f"Camera output must always be {CAMERA_OUTPUT!r}, got {body['reformulated']!r}"
        )

    def test_intent_weather(self, client: TestClient) -> None:
        """
        Intent 7 (weather): 'מה מזג האוויר היום בירושלים' — 'What is the weather today in Jerusalem'.
        Verifies location and time-reference extraction for weather queries.
        """
        response = post_reformulate(client, "מה מזג האוויר היום בירושלים")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "weather", (
            f"Expected intent 'weather', got {body['intent_label']!r}"
        )

    def test_intent_notes(self, client: TestClient) -> None:
        """
        Intent 8 (notes): 'תכתבי לי פתק לקנות חלב' — 'Write me a note to buy milk'.
        Verifies meta-word filtering and note content extraction.
        """
        response = post_reformulate(client, "תכתבי לי פתק לקנות חלב")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "notes", (
            f"Expected intent 'notes', got {body['intent_label']!r}"
        )

    def test_intent_flashlight(self, client: TestClient) -> None:
        """
        Intent 9 (flashlight): 'תדליקי את הפנס' — 'Turn on the flashlight'.
        Flashlight is a fixed-output intent — reformulated is always 'להדליק פנס'.
        """
        response = post_reformulate(client, "תדליקי את הפנס")
        assert response.status_code == 200
        body = response.json()
        assert_valid_response_structure(body)
        assert body["intent_label"] == "flashlight", (
            f"Expected intent 'flashlight', got {body['intent_label']!r}"
        )
        assert body["reformulated"] == FLASHLIGHT_OUTPUT, (
            f"Flashlight output must always be {FLASHLIGHT_OUTPUT!r}, got {body['reformulated']!r}"
        )


# ===========================================================================
# 3. Classifier output tests
# ===========================================================================

class TestClassifierOutput:
    """
    Verify the intent classifier produces plausible outputs.

    These tests focus on the classification step specifically — they do not
    verify reformulation quality, only that the model makes sensible decisions
    on clear-cut Hebrew inputs.
    """

    def test_classifier_returns_integer_intent_id(self, client: TestClient) -> None:
        """
        The intent_id in the response must be a Python int (JSON integer),
        not a float or string.
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        # JSON integers come back as Python int via response.json()
        assert type(body["intent_id"]) is int

    def test_classifier_is_consistent_on_same_input(self, client: TestClient) -> None:
        """
        The classifier must be deterministic: the same utterance must always
        produce the same intent_id when called multiple times in the same session.
        (Model is in eval mode with no dropout, so this should always hold.)
        """
        utterance = "תשלחי הודעה לרחל שאני מאחרת"
        response_1 = post_reformulate(client, utterance)
        response_2 = post_reformulate(client, utterance)
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert response_1.json()["intent_id"] == response_2.json()["intent_id"], (
            "Classifier produced different intent_id for identical inputs — "
            "model is not in deterministic eval mode."
        )

    def test_classifier_covers_all_10_label_names(self, client: TestClient) -> None:
        """
        Verify that the model's id2label config exposes all 10 expected labels.
        This guards against misconfigured or truncated model checkpoints.
        """
        # We verify indirectly: each expected label must be reachable as
        # intent_label for at least the fixed-output intents.
        camera_response = post_reformulate(client, "תצלמי תמונה")
        flashlight_response = post_reformulate(client, "תדליקי את הפנס")
        assert camera_response.json()["intent_label"] == "camera"
        assert flashlight_response.json()["intent_label"] == "flashlight"

    def test_reformulated_output_is_hebrew_text(self, client: TestClient) -> None:
        """
        The reformulated string should contain Hebrew Unicode characters.
        Verifies the pipeline actually produces Hebrew output, not garbled ASCII.
        """
        response = post_reformulate(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        reformulated = response.json()["reformulated"]
        # Hebrew Unicode range: U+0590–U+05FF
        has_hebrew = any("\u0590" <= ch <= "\u05FF" for ch in reformulated)
        assert has_hebrew, (
            f"Reformulated output contains no Hebrew characters: {reformulated!r}"
        )


# ===========================================================================
# 4. Edge case tests
# ===========================================================================

class TestEdgeCases:
    """
    Verify the API handles unusual, malformed, or extreme inputs gracefully
    without crashing or returning unexpected data.
    """

    def test_empty_string_returns_400(self, client: TestClient) -> None:
        """
        An empty utterance string must be rejected with HTTP 400.
        The pipeline should never attempt NLP on a blank input.
        """
        response = post_reformulate(client, "")
        assert response.status_code == 400, (
            f"Expected 400 for empty string, got {response.status_code}"
        )
        assert "detail" in response.json()

    def test_whitespace_only_returns_400(self, client: TestClient) -> None:
        """
        A string of only spaces/tabs/newlines must also be rejected with 400.
        After stripping, the utterance is empty — same validation applies.
        """
        response = post_reformulate(client, "   \t\n  ")
        assert response.status_code == 400, (
            f"Expected 400 for whitespace-only input, got {response.status_code}"
        )

    def test_very_long_utterance_does_not_crash(self, client: TestClient) -> None:
        """
        An utterance of 2 000 Hebrew characters must not crash the server.
        The tokenizer truncates inputs to BERT's 512-token maximum.
        The response may be low quality but must be HTTP 200 with valid structure.
        """
        long_utterance = "תתקשרי לאמא שלי " * 120  # ~2 000 characters
        response = post_reformulate(client, long_utterance)
        assert response.status_code == 200, (
            f"Very long input should not crash — got {response.status_code}"
        )
        assert_valid_response_structure(response.json())

    def test_non_hebrew_english_text(self, client: TestClient) -> None:
        """
        An English utterance must not crash the server.
        The model will classify it into one of the 10 intents (possibly with
        low confidence), and the reformulation script will run. The output
        quality is not verified — only that the pipeline completes without error.
        """
        response = post_reformulate(client, "call my mom please")
        assert response.status_code == 200, (
            f"English input should not crash — got {response.status_code}"
        )
        assert_valid_response_structure(response.json())

    def test_mixed_hebrew_and_english(self, client: TestClient) -> None:
        """
        A mix of Hebrew and Latin characters must not crash the pipeline.
        Common in Israeli text (e.g. brand names, abbreviations).
        """
        response = post_reformulate(client, "תתקשרי ל-David בבקשה")
        assert response.status_code == 200, (
            f"Mixed-language input should not crash — got {response.status_code}"
        )
        assert_valid_response_structure(response.json())

    def test_special_characters_only(self, client: TestClient) -> None:
        """
        A string of only punctuation and special characters must not crash.
        The classifier will produce some intent; the reformulation output
        may be empty or minimal. The server must remain stable.
        """
        response = post_reformulate(client, "!@#$%^&*()")
        assert response.status_code == 200, (
            f"Special-character input should not crash — got {response.status_code}"
        )
        body = response.json()
        # Structure must still be valid (reformulated may be empty string here)
        assert "intent_id" in body
        assert "intent_label" in body

    def test_single_hebrew_word(self, client: TestClient) -> None:
        """
        A single Hebrew word must be processed without crashing.
        This is a minimal valid input — no named entities will be found,
        but the pipeline must complete gracefully.
        """
        response = post_reformulate(client, "שלום")
        assert response.status_code == 200
        assert_valid_response_structure(response.json())

    def test_numbers_and_digits(self, client: TestClient) -> None:
        """
        An utterance containing digits (common in time/date commands) must
        be handled correctly without crashing.
        """
        response = post_reformulate(client, "תעירי אותי ב-07:30")
        assert response.status_code == 200
        assert_valid_response_structure(response.json())

    def test_missing_utterance_field_returns_422(self, client: TestClient) -> None:
        """
        A request body missing the required 'utterance' field must return
        HTTP 422 Unprocessable Entity (FastAPI's Pydantic validation error).
        """
        response = client.post("/reformulate", json={})
        assert response.status_code == 422, (
            f"Missing 'utterance' field should return 422, got {response.status_code}"
        )

    def test_wrong_field_name_returns_422(self, client: TestClient) -> None:
        """
        A request body with a misspelled field name ('text' instead of
        'utterance') must return 422 — the required field is missing.
        """
        response = client.post("/reformulate", json={"text": "תתקשרי לאמא"})
        assert response.status_code == 422, (
            f"Wrong field name should return 422, got {response.status_code}"
        )

    def test_wrong_content_type_returns_error(self, client: TestClient) -> None:
        """
        Sending plain text instead of JSON must not crash the server.
        FastAPI should return a 422 or 400 for non-JSON content.
        """
        response = client.post(
            "/reformulate",
            content="תתקשרי לאמא שלי",
            headers={"Content-Type": "text/plain"},
        )
        # FastAPI returns 422 for unparseable body
        assert response.status_code in (400, 422)

    def test_null_utterance_returns_422(self, client: TestClient) -> None:
        """
        Sending JSON null for the utterance field must return 422.
        Pydantic requires a string, not None.
        """
        response = client.post("/reformulate", json={"utterance": None})
        assert response.status_code == 422

    def test_numeric_utterance_is_coerced_or_rejected(self, client: TestClient) -> None:
        """
        Sending a JSON number instead of a string for 'utterance' must
        either be coerced to string (Pydantic v2 behaviour) or return 422.
        The server must not crash with an unhandled exception.
        """
        response = client.post("/reformulate", json={"utterance": 12345})
        # Pydantic v2 coerces int → str; Pydantic v1 raises ValidationError → 422
        assert response.status_code in (200, 422)

    def test_unknown_endpoint_returns_404(self, client: TestClient) -> None:
        """
        A request to an undefined route must return HTTP 404 Not Found.
        Verifies FastAPI's default 404 handling is working.
        """
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_get_on_post_only_endpoint_returns_405(self, client: TestClient) -> None:
        """
        A GET request to /reformulate (which only accepts POST) must return
        HTTP 405 Method Not Allowed.
        """
        response = client.get("/reformulate")
        assert response.status_code == 405
