"""
backend package
---------------
FastAPI application for the Hebrew Voice Command Reformulation system.

Package structure:
    schemas.py      — Pydantic request/response models
    model_loader.py — Intent classifier (AlephBERT) loading and inference
    pipeline.py     — End-to-end pipeline orchestration
    main.py         — FastAPI application, lifespan, and route definitions
"""
