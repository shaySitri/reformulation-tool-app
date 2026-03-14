"""
test_api.py
-----------
Groups B–E — Integration tests for the POST /reformulate API endpoint.

All tests run against the real backend, the real intent classifier model,
and the real reformulation pipeline. No mocking.

Test focus
----------
These tests verify BACKEND BEHAVIOR, not model quality:
  - The API response schema is always well-formed.
  - The 'status' field is always "success" or "failed".
  - Invalid input is rejected with HTTP 400 (Stage 1 validation).
  - Valid Hebrew input always produces a well-structured HTTP 200 response.
  - The 'reformulated' field is null when and only when status is "failed".
  - 'original', 'intent_id', and 'intent_label' are always present and typed correctly.
  - Deterministic intents (camera, flashlight) produce exact known outputs.
  - Malformed requests produce HTTP 4xx responses.

What these tests deliberately do NOT assert:
  - Whether the classifier predicted the "correct" intent.
  - Whether the reformulated string is linguistically optimal.
  - The exact content of 'reformulated' for non-deterministic intents.

Run with:
    pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All valid intent labels — used to verify the 'intent_label' field.
VALID_INTENT_LABELS = frozenset({
    "call", "alarm", "sms", "search_query", "navigation",
    "calendar", "camera", "weather", "notes", "flashlight",
})

# Exact outputs for the two deterministic intents (no NER, no extraction).
CAMERA_OUTPUT = "תפתחי מצלמה"
FLASHLIGHT_OUTPUT = "להדליק פנס"


# ---------------------------------------------------------------------------
# Session-scoped client fixture (models load once for the full test session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Session-scoped TestClient. FastAPI's lifespan context manager is triggered
    once for the entire pytest session:
      - Startup: IntentClassifier.load() + NER models already in memory.
      - Shutdown: resources released after all tests complete.

    Using session scope prevents reloading 3+ BERT models for every test,
    reducing total runtime from hours to ~30 seconds.
    """
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def post(client: TestClient, utterance: str):
    """POST /reformulate with the given utterance. Returns the response object."""
    return client.post("/reformulate", json={"utterance": utterance})


def assert_success_schema(body: dict) -> None:
    """
    Assert that a body with status='success' has all required fields with
    correct types and that 'reformulated' is a non-null Hebrew-containing string.

    Does NOT assert the content of 'reformulated' (not a model-quality test).
    """
    assert body["status"] == "success"
    assert isinstance(body["reformulated"], str), "'reformulated' must be a string on success"
    assert len(body["reformulated"].strip()) > 0, "'reformulated' must not be empty on success"
    # Must contain at least one Hebrew character (U+05D0-U+05EA)
    has_hebrew = any("\u05D0" <= ch <= "\u05EA" for ch in body["reformulated"])
    assert has_hebrew, f"'reformulated' must contain Hebrew: {body['reformulated']!r}"


def assert_common_schema(body: dict) -> None:
    """
    Assert the fields that must be present and correctly typed in every
    HTTP 200 response, regardless of status.
    """
    assert "status" in body
    assert "original" in body
    assert "intent_id" in body
    assert "intent_label" in body
    assert "reformulated" in body  # field must exist (value may be null)

    assert body["status"] in ("success", "failed"), (
        f"'status' must be 'success' or 'failed', got {body['status']!r}"
    )
    assert isinstance(body["original"], str)
    assert isinstance(body["intent_id"], int)
    assert isinstance(body["intent_label"], str)
    assert 0 <= body["intent_id"] <= 9, f"'intent_id' out of range: {body['intent_id']}"
    assert body["intent_label"] in VALID_INTENT_LABELS, (
        f"'intent_label' is not a known label: {body['intent_label']!r}"
    )


# ===========================================================================
# Group B — Input rejection tests (Stage 1 validation via HTTP)
# ===========================================================================

class TestInputRejection:
    """
    Verify that Stage 1 input validation rejects invalid input at the HTTP layer.
    All cases expect HTTP 400 with a generic error body.
    The specific failure reason (empty vs invalid chars) is not revealed.
    """

    def test_empty_string_returns_400(self, client: TestClient) -> None:
        """Empty string must be rejected before reaching the pipeline."""
        response = post(client, "")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_whitespace_only_returns_400(self, client: TestClient) -> None:
        """Whitespace-only input must be rejected before reaching the pipeline."""
        response = post(client, "   \t\n  ")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_english_only_returns_400(self, client: TestClient) -> None:
        """Pure English input must be rejected by Stage 1 validation."""
        response = post(client, "call my mom")
        assert response.status_code == 400

    def test_hebrew_with_digit_returns_400(self, client: TestClient) -> None:
        """Hebrew with a digit must be rejected — digits are not in the allowed set."""
        response = post(client, "תשלחי הודעה ל7")
        assert response.status_code == 400

    def test_hebrew_with_english_returns_400(self, client: TestClient) -> None:
        """Hebrew mixed with a Latin word must be rejected."""
        response = post(client, "תתקשרי John")
        assert response.status_code == 400

    def test_hash_characters_return_400(self, client: TestClient) -> None:
        """Hash placeholder characters must be rejected."""
        response = post(client, "####")
        assert response.status_code == 400

    def test_time_with_colon_returns_400(self, client: TestClient) -> None:
        """Time format with colon (e.g. '7:30') must be rejected."""
        response = post(client, "תעירי אותי ב7:30")
        assert response.status_code == 400

    def test_error_detail_is_generic(self, client: TestClient) -> None:
        """
        The error message must not expose which validation rule failed.
        It must be the same for all Stage 1 rejections.
        """
        response_empty = post(client, "")
        response_english = post(client, "hello")
        assert response_empty.status_code == 400
        assert response_english.status_code == 400
        # Both must have the same generic detail message
        assert response_empty.json()["detail"] == response_english.json()["detail"]


# ===========================================================================
# Group C — API structure tests (real pipeline, valid Hebrew inputs)
# ===========================================================================

class TestAPIStructure:
    """
    Verify that for valid Hebrew inputs the API always returns a well-formed
    HTTP 200 response with all required fields correctly typed.

    These tests do NOT assert which intent was predicted or what the
    reformulated string contains — only that the structure is correct.
    """

    def test_health_check_passes(self, client: TestClient) -> None:
        """GET /health must return 200 with models_loaded=True."""
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["models_loaded"] is True

    def test_valid_input_returns_200(self, client: TestClient) -> None:
        """A valid Hebrew utterance must produce HTTP 200."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200

    def test_response_has_all_required_fields(self, client: TestClient) -> None:
        """HTTP 200 response must contain status, original, intent_id, intent_label, reformulated."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        assert_common_schema(response.json())

    def test_status_field_is_valid_enum(self, client: TestClient) -> None:
        """'status' must be exactly 'success' or 'failed'."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        assert response.json()["status"] in ("success", "failed")

    def test_original_matches_stripped_input(self, client: TestClient) -> None:
        """'original' must equal the utterance after stripping whitespace."""
        response = post(client, "  תתקשרי לאמא שלי  ")
        assert response.status_code == 200
        assert response.json()["original"] == "תתקשרי לאמא שלי"

    def test_intent_id_is_integer_in_range(self, client: TestClient) -> None:
        """'intent_id' must be a Python int in 0–9."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        assert type(body["intent_id"]) is int
        assert 0 <= body["intent_id"] <= 9

    def test_intent_label_is_known_label(self, client: TestClient) -> None:
        """'intent_label' must be one of the 10 registered intent names."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        assert response.json()["intent_label"] in VALID_INTENT_LABELS

    def test_intent_id_and_label_are_consistent(self, client: TestClient) -> None:
        """
        'intent_label' must be the canonical label for 'intent_id'.
        The two fields must be consistent — not independently set.
        """
        from backend.model_loader import IntentClassifier
        # Read the id2label mapping from the loaded classifier
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        # The label for the returned id must match the returned label
        # We verify via the known mapping rather than hitting the model again
        from backend.pipeline import _INTENT_LABELS
        expected_label = _INTENT_LABELS[body["intent_id"]]
        assert body["intent_label"] == expected_label

    def test_success_status_implies_non_null_reformulated(self, client: TestClient) -> None:
        """When status='success', 'reformulated' must be a non-null string."""
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        if body["status"] == "success":
            assert_success_schema(body)

    def test_failed_status_implies_null_reformulated(self, client: TestClient) -> None:
        """
        When status='failed', 'reformulated' must be null.
        This test verifies the invariant. If the pipeline succeeds on this
        input (status='success'), the test passes vacuously — we are not
        testing model quality, only the schema invariant.
        """
        response = post(client, "שלום")  # minimal input, may succeed or fail
        assert response.status_code == 200
        body = response.json()
        if body["status"] == "failed":
            assert body["reformulated"] is None, (
                "When status='failed', 'reformulated' must be null"
            )

    def test_reformulated_is_null_or_hebrew_string(self, client: TestClient) -> None:
        """
        'reformulated' must be either null (status='failed') or a non-empty
        string containing at least one Hebrew character (status='success').
        """
        response = post(client, "תתקשרי לאמא שלי")
        assert response.status_code == 200
        body = response.json()
        if body["reformulated"] is None:
            assert body["status"] == "failed"
        else:
            assert isinstance(body["reformulated"], str)
            has_hebrew = any("\u05D0" <= ch <= "\u05EA" for ch in body["reformulated"])
            assert has_hebrew

    def test_content_type_is_json(self, client: TestClient) -> None:
        """Response Content-Type must be application/json."""
        response = post(client, "תתקשרי לאמא שלי")
        assert "application/json" in response.headers["content-type"]

    def test_classifier_is_deterministic(self, client: TestClient) -> None:
        """
        The same utterance submitted twice must produce the same intent_id.
        The model is in eval mode with dropout disabled — results are deterministic.
        """
        utterance = "תצלמי תמונה"
        r1 = post(client, utterance)
        r2 = post(client, utterance)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["intent_id"] == r2.json()["intent_id"]

    def test_multiple_valid_inputs_all_return_200(self, client: TestClient) -> None:
        """
        A set of diverse valid Hebrew utterances must all return HTTP 200.
        This is a smoke test — it does not assert intent or output content.
        """
        utterances = [
            "תתקשרי לאמא שלי",
            "תעירי אותי בבוקר",
            "תשלחי הודעה לדוד",
            "תחפשי מידע על סוכרת",
            "תנווטי אותי לתל אביב",
            "תצרי פגישה ביומן",
            "תצלמי תמונה",
            "מה מזג האוויר היום",
            "תכתבי לי פתק",
            "תדליקי את הפנס",
        ]
        for utterance in utterances:
            response = post(client, utterance)
            assert response.status_code == 200, (
                f"Expected 200 for {utterance!r}, got {response.status_code}"
            )
            assert_common_schema(response.json())


# ===========================================================================
# Group D — Deterministic integration tests (camera and flashlight)
# ===========================================================================

class TestDeterministicIntents:
    """
    Camera (intent 6) and flashlight (intent 9) handlers take no arguments
    and return fixed Hebrew strings unconditionally. Their output is known
    in advance and does not depend on NER or entity extraction.

    These are the only tests that assert exact reformulated content, because
    that content is a constant — not a model prediction.
    """

    def test_camera_returns_correct_output(self, client: TestClient) -> None:
        """
        Camera command must produce the exact hard-coded output "תפתחי מצלמה".
        status must be "success" (the output passes all validation rules).
        """
        response = post(client, "תצלמי תמונה")
        assert response.status_code == 200
        body = response.json()
        assert_common_schema(body)
        assert body["status"] == "success"
        assert body["reformulated"] == CAMERA_OUTPUT, (
            f"Camera output must be {CAMERA_OUTPUT!r}, got {body['reformulated']!r}"
        )

    def test_flashlight_returns_correct_output(self, client: TestClient) -> None:
        """
        Flashlight command must produce the exact hard-coded output "להדליק פנס".
        status must be "success" (the output passes all validation rules).
        """
        response = post(client, "תדליקי את הפנס")
        assert response.status_code == 200
        body = response.json()
        assert_common_schema(body)
        assert body["status"] == "success"
        assert body["reformulated"] == FLASHLIGHT_OUTPUT, (
            f"Flashlight output must be {FLASHLIGHT_OUTPUT!r}, got {body['reformulated']!r}"
        )

    def test_camera_output_passes_validator(self, client: TestClient) -> None:
        """
        The camera output must be accepted by the Stage 2 validator.
        This is an end-to-end verification that the validator and the
        deterministic output are consistent with each other.
        """
        from backend.validators import validate_output
        assert validate_output(CAMERA_OUTPUT) is True

    def test_flashlight_output_passes_validator(self, client: TestClient) -> None:
        """
        The flashlight output must be accepted by the Stage 2 validator.
        """
        from backend.validators import validate_output
        assert validate_output(FLASHLIGHT_OUTPUT) is True


# ===========================================================================
# Group E — HTTP error / protocol tests
# ===========================================================================

class TestHTTPErrors:
    """
    Verify correct HTTP status codes for malformed requests and wrong methods.
    These tests do not involve the NLP pipeline.
    """

    def test_missing_utterance_field_returns_422(self, client: TestClient) -> None:
        """A request body missing 'utterance' must return HTTP 422 (Pydantic validation)."""
        response = client.post("/reformulate", json={})
        assert response.status_code == 422

    def test_wrong_field_name_returns_422(self, client: TestClient) -> None:
        """'text' instead of 'utterance' means the required field is missing → 422."""
        response = client.post("/reformulate", json={"text": "תתקשרי לאמא"})
        assert response.status_code == 422

    def test_null_utterance_returns_422(self, client: TestClient) -> None:
        """JSON null for 'utterance' must return 422 (Pydantic requires str)."""
        response = client.post("/reformulate", json={"utterance": None})
        assert response.status_code == 422

    def test_get_on_reformulate_returns_405(self, client: TestClient) -> None:
        """GET on /reformulate (POST-only) must return HTTP 405 Method Not Allowed."""
        response = client.get("/reformulate")
        assert response.status_code == 405

    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        """A request to an undefined route must return HTTP 404 Not Found."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_wrong_content_type_returns_error(self, client: TestClient) -> None:
        """Sending plain text instead of JSON must return 400 or 422."""
        response = client.post(
            "/reformulate",
            content="תתקשרי לאמא שלי",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code in (400, 422)

    def test_400_error_body_uses_detail_key(self, client: TestClient) -> None:
        """HTTP 400 error bodies must use FastAPI's standard 'detail' key."""
        response = post(client, "")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_400_detail_is_generic_string(self, client: TestClient) -> None:
        """The 400 detail message must be a plain string (not a nested object)."""
        response = post(client, "hello world")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)
