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
from backend.schemas import (
    ErrorResponse,
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
# shutdown logic after the last request.  Using lifespan (rather than the
# deprecated @app.on_event) is the recommended pattern in FastAPI >= 0.99.
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
    # PyTorch tensors and HuggingFace pipelines are garbage-collected here.
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
        "**Pipeline:** AlephBERT intent classifier → heBERT NER → template filling."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins during development so the React/Vite dev server
# (running on a different port) can call the API without browser CORS errors.
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
    description=(
        "Returns HTTP 200 with `status: ok` when the server is running. "
        "`models_loaded` is True once the intent classifier has been loaded "
        "into memory at startup."
    ),
    tags=["Monitoring"],
)
def health_check(request: Request) -> HealthResponse:
    """
    Lightweight liveness probe for load balancers and monitoring tools.

    Returns:
        HealthResponse indicating whether the server and models are ready.
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
            "description": "Utterance is empty or whitespace-only.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal NLP pipeline error.",
        },
    },
    summary="Reformulate a Hebrew utterance",
    description=(
        "Accepts a raw Hebrew voice command, classifies its intent using the "
        "AlephBERT model, extracts named entities via Hebrew NER models, and "
        "returns a structured command that can be read aloud to Siri.\n\n"
        "**Example input:** `תשלחי הודעה לישראל שאני מאחרת`\n\n"
        "**Example output:** `שלח הודעה לישראל: אני מאחרת`"
    ),
    tags=["Pipeline"],
)
def reformulate_utterance(
    body: ReformulateRequest,
    request: Request,
) -> ReformulateResponse:
    """
    Full pipeline endpoint: classify intent → extract entities → build command.

    The route handler is a regular (non-async) function because the NLP
    pipeline is CPU-bound synchronous code. FastAPI automatically runs sync
    route handlers in a thread pool, keeping the event loop unblocked.

    Args:
        body:    Request body containing the Hebrew utterance string.
        request: FastAPI request object used to access app.state.classifier.

    Returns:
        ReformulateResponse with the original text, predicted intent,
        and the reformulated Hebrew command.

    Raises:
        HTTPException 400: If the utterance is empty or whitespace-only.
        HTTPException 500: If the internal NLP pipeline raises an error.
    """
    # Validate input — empty strings are rejected early before hitting the
    # expensive NLP models. The pipeline.run_pipeline() also validates, but
    # we duplicate the check here for a cleaner HTTP response.
    utterance = body.utterance.strip()
    if not utterance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utterance must not be empty.",
        )

    try:
        result = run_pipeline(utterance=utterance, classifier=request.app.state.classifier)
    except ValueError as exc:
        # run_pipeline raises ValueError for invalid input (e.g. empty string).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # run_pipeline raises RuntimeError if the reformulation module fails.
        logger.exception("Pipeline error for utterance: %r", utterance)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ReformulateResponse(**result)
