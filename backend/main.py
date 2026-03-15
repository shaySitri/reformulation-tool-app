"""
main.py
-------
FastAPI application for the Hebrew Voice Command Reformulation API.

This module defines:
  - The FastAPI app instance with metadata for auto-generated OpenAPI docs.
  - A lifespan context manager that loads all NLP models once at startup.
  - CORS middleware configured to allow the React dev server (any origin
    during development; restrict to specific origins in production).
  - GET  /health      — liveness probe, returns model-loaded status.
  - POST /reformulate — the main pipeline endpoint.

Model loading strategy
----------------------
All three NLP models are loaded exactly once at server startup via the
`lifespan` context manager and stored in `app.state`:

  1. Intent classifier (AlephBERT, local weights in intent_model/)
     → loaded by IntentClassifier.load()

  2. NER model avichr/heBERT_NER        } loaded as module-level globals
  3. NER model dicta-il/dictabert-ner   } when pipeline.py is first imported

Because models live in app.state (shared across all requests), every request
is served without any per-call cold-start overhead after the initial startup.

Error message policy
--------------------
HTTP error responses (400, 500) use intentionally generic messages.
Internal failure reasons — validation rule details, model outputs, exception
messages — are logged server-side but never sent to the client.

Running the server locally
--------------------------
    # From the repository root:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

    # Interactive API docs (auto-generated):
    http://localhost:8000/docs

Environment variables
---------------------
    MODEL_DIR   Path to the intent model directory.
                Default: <repo_root>/intent_model
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from backend.model_loader import IntentClassifier
from backend.pipeline import run_pipeline
from backend.feedback_logger import append_feedback
from backend.schemas import (
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    ReformulateRequest,
    ReformulateResponse,
)

# ---------------------------------------------------------------------------
# Logging — structured format makes it easy to grep by level or module name.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve the intent model directory.
# Default: <repo_root>/intent_model  (the directory already in the repository)
# Override: set the MODEL_DIR environment variable before starting the server.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MODEL_DIR = _REPO_ROOT / "intent_model"
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(_DEFAULT_MODEL_DIR)))


# ---------------------------------------------------------------------------
# Lifespan context manager — runs startup logic before the first request and
# shutdown logic after the last request.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan: load models on startup, release on shutdown.

    Everything before `yield` runs at startup; everything after runs at
    shutdown. Models are stored in `app.state` so route handlers can access
    them via `request.app.state.classifier`.

    Note: importing `backend.pipeline` already triggered loading of the two
    NER models (heBERT_NER, dictabert-ner) as module-level globals in
    command_reformulatuin_script.py. By the time we reach this function those
    models are already in memory.
    """
    logger.info("=== Startup: loading intent classifier from %s ===", MODEL_DIR)
    classifier = IntentClassifier(model_dir=MODEL_DIR)
    classifier.load()
    app.state.classifier = classifier
    logger.info("=== All models ready. Server accepting requests. ===")

    yield  # Server is live — handle incoming requests.

    logger.info("=== Shutdown: releasing resources. ===")
    app.state.classifier = None


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Hebrew Voice Command Reformulation API",
    description=(
        "Transforms natural-language Hebrew utterances into structured commands "
        "suitable for reading aloud to Siri. "
        "Designed for elderly Israeli smartphone users.\n\n"
        "**Pipeline:** AlephBERT intent classifier → heBERT NER → template filling "
        "→ output validation.\n\n"
        "**Input rules:** Hebrew letters and spaces only. "
        "English letters, digits, and special characters are rejected.\n\n"
        "**Response status field:** `success` when the output passed validation; "
        "`failed` when the pipeline produced an unusable result."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins during development.
# In production, replace allow_origins=["*"] with the deployed frontend URL.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health / liveness check",
    tags=["Monitoring"],
)
def health_check(request: Request) -> HealthResponse:
    """
    Lightweight liveness probe.

    Returns 200 OK with models_loaded=True once the intent classifier has
    been loaded into memory at startup.
    """
    models_ready = (
        hasattr(request.app.state, "classifier")
        and request.app.state.classifier is not None
        and request.app.state.classifier._loaded
    )
    return HealthResponse(status="ok", models_loaded=models_ready)


@app.post(
    "/reformulate",
    response_model=ReformulateResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Input is empty, whitespace-only, or contains invalid characters.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal pipeline error.",
        },
    },
    summary="Reformulate a Hebrew utterance",
    description=(
        "Accepts a raw Hebrew voice command. Validates the input character set, "
        "classifies the intent, extracts entities, and returns a structured command.\n\n"
        "A successful HTTP 200 response may carry `status: failed` if the pipeline "
        "produced an unusable output — in that case `reformulated` is null."
    ),
    tags=["Pipeline"],
)
def reformulate_utterance(
    body: ReformulateRequest,
    request: Request,
) -> ReformulateResponse:
    """
    Full pipeline endpoint: validate input → classify intent → extract entities
    → build command → validate output → return structured response.

    The route handler is a regular (non-async) function because the NLP
    pipeline is CPU-bound synchronous code. FastAPI automatically runs sync
    route handlers in a thread pool, keeping the event loop unblocked.

    Args:
        body:    Request body containing the Hebrew utterance string.
        request: FastAPI request object used to access app.state.classifier.

    Returns:
        ReformulateResponse with status, original text, predicted intent,
        and the reformulated Hebrew command (null if status is "failed").

    Raises:
        HTTPException 400: Input failed Stage 1 validation.
                           Generic message — does not reveal which rule failed.
        HTTPException 500: The reformulation module raised an unexpected error.
                           Generic message — does not expose internal details.
    """
    try:
        result = run_pipeline(
            utterance=body.utterance,
            classifier=request.app.state.classifier,
        )
    except ValueError:
        # Stage 1 validation failure (empty input or invalid characters).
        # The generic message deliberately does not specify which rule failed.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input.",
        )
    except RuntimeError:
        # Reformulation module raised an unexpected exception.
        # Log the details server-side; send only a generic message to the client.
        logger.exception("Pipeline RuntimeError for utterance: %r", body.utterance[:60])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )

    return ReformulateResponse(**result)


@app.post(
    "/feedback",
    response_model=FeedbackResponse,
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Failed to write the feedback record.",
        },
    },
    summary="Submit user feedback for a reformulation result",
    description=(
        "Records whether the user reports that Siri understood the reformulated command. "
        "Both answered and unanswered (dialog closed) feedback is accepted. "
        "When the user closed the dialog without answering, `siri_understood` is null."
    ),
    tags=["Feedback"],
)
def submit_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """
    Append one feedback record to logs/feedback.jsonl.

    The record always includes a UTC ISO-8601 timestamp plus all fields from
    the request body. siri_understood is null when the user dismissed the dialog.
    """
    from datetime import datetime, timezone

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_input": body.original_input,
        "intent_id": body.intent_id,
        "intent_label": body.intent_label,
        "reformulated_command": body.reformulated_command,
        "backend_status": body.backend_status,
        "siri_understood": body.siri_understood,
        "notes": body.notes,
    }

    try:
        append_feedback(record)
    except Exception:
        logger.exception("Failed to write feedback record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )

    return FeedbackResponse(ok=True)
