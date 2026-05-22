"""Vercel serverless entry point — imports the FastAPI app."""
from app.main import app  # noqa: F401 — Vercel looks for `app`
