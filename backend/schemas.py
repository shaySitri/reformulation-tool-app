"""
schemas.py
----------
Pydantic request and response models for the reformulation API.

All models include field-level documentation so that FastAPI's auto-generated
OpenAPI docs (available at /docs) are self-describing.

Response design
---------------
POST /reformulate always returns HTTP 200 when the pipeline runs (regardless
of whether the output passed validation). The 'status' field distinguishes
the two outcomes:

    status = "success"  — output passed validation; 'reformulated' is a string.
    status = "failed"   — output failed validation; 'reformulated' is null.

HTTP 4xx / 5xx codes are reserved for true request or server errors (empty
input, malformed request body, internal crash), not for pipeline-level
quality judgements.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReformulateRequest(BaseModel):
    """
    Request body for the POST /reformulate endpoint.

    The caller supplies only the raw Hebrew utterance. Intent classification
    is performed server-side by the AlephBERT model.
    """

    utterance: str = Field(
        ...,
        description="The raw Hebrew text utterance to be reformulated.",
        examples=["תשלחי הודעה לישראל שאני מאחרת"],
    )


class ReformulateResponse(BaseModel):
    """
    Response body from the POST /reformulate endpoint (HTTP 200).

    Always returned when the pipeline executes — regardless of whether the
    output passed Stage 2 validation. The 'status' field tells callers which
    outcome occurred.

    When status == "failed", 'reformulated' is null and the client should
    not attempt to use the pipeline result. The failure reason is intentionally
    not exposed.
    """

    status: Literal["success", "failed"] = Field(
        description=(
            "'success' when the reformulated output passed all validation checks. "
            "'failed' when the pipeline produced an unusable result — in this case "
            "'reformulated' is null."
        )
    )
    original: str = Field(
        description="The input utterance exactly as received (stripped of leading/trailing whitespace)."
    )
    intent_id: int = Field(
        description="Predicted intent class index (0–9)."
    )
    intent_label: str = Field(
        description=(
            "Human-readable intent label corresponding to intent_id. "
            "One of: call, alarm, sms, search_query, navigation, calendar, "
            "camera, weather, notes, flashlight."
        )
    )
    reformulated: Optional[str] = Field(
        default=None,
        description=(
            "The structured Hebrew command suitable for reading aloud to Siri. "
            "null when status is 'failed'."
        ),
    )


class ErrorResponse(BaseModel):
    """
    Error response body returned on 4xx / 5xx responses.

    FastAPI uses the 'detail' key by default for HTTPException messages,
    so this schema matches that convention.

    Error messages are intentionally generic — internal failure reasons
    (model errors, validation details) are never exposed to the client.
    """

    detail: str = Field(description="Generic error description.")


class HealthResponse(BaseModel):
    """Response body for the GET /health endpoint."""

    status: str = Field(description="'ok' when the server is running normally.")
    models_loaded: bool = Field(
        description="True when the intent classifier has been successfully loaded into memory."
    )
