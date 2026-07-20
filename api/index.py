"""Vercel entrypoint for the FastAPI application."""

from backend.main import create_app

app = create_app()
