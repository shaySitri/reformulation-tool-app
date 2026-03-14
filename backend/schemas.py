"""
schemas.py
----------
Pydantic request and response models for the reformulation API.

All models include field-level documentation so that FastAPI's auto-generated
OpenAPI docs (available at /docs) are self-describing.
"""

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
    Successful response body from the POST /reformulate endpoint.

    Contains the original utterance alongside the pipeline's full output so
    that callers can display both for transparency.
    """

    original: str = Field(
        description="The original utterance exactly as received (stripped of leading/trailing whitespace)."
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
    reformulated: str = Field(
        description="The structured Hebrew command suitable for reading aloud to Siri."
    )


class ErrorResponse(BaseModel):
    """
    Error response body returned on 4xx / 5xx responses.

    FastAPI uses the 'detail' key by default for HTTPException messages,
    so this schema matches that convention.
    """

    detail: str = Field(description="Human-readable error description.")


class HealthResponse(BaseModel):
    """Response body for the GET /health endpoint."""

    status: str = Field(description="'ok' when the server is running normally.")
    models_loaded: bool = Field(
        description="True when the intent classifier has been successfully loaded into memory."
    )
