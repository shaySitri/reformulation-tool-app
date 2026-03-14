"""
conftest.py
-----------
Shared pytest fixtures for the reformulation API test suite.

Model loading note
------------------
The NLP models are heavy (multiple BERT models totalling several GB). Loading
them for every test would make the suite impractically slow. We therefore use
`scope="session"` so models are loaded exactly ONCE for the entire test run
and the TestClient is kept alive across all test modules.

The `with TestClient(app) as client:` pattern triggers FastAPI's lifespan
context manager, which in turn calls:
  1. IntentClassifier.load()                   — loads AlephBERT intent model
  2. (Already done at import time by pipeline.py) — NER models are in memory

Expected startup time: 10–30 seconds on first run (models download/cache).
Subsequent runs (models cached in ~/.cache/huggingface/): ~5–15 seconds.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app  # importing this also loads NER models via pipeline.py


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Session-scoped TestClient fixture.

    Creates a single TestClient for the entire pytest session. The lifespan
    context manager (startup + shutdown) is triggered once by the `with`
    block, not once per test. This means all NLP models load once and are
    shared across every test in the session.

    Yields:
        A configured FastAPI TestClient ready to make HTTP requests.
    """
    with TestClient(app) as test_client:
        yield test_client
