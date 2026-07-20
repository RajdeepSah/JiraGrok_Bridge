"""FastAPI backend for the Jira Grok Bridge web app.

Thin HTTP layer over the shared ``core`` package. Import ``create_app`` to build
the ASGI application:

    uvicorn backend.main:create_app --factory --port 8000
"""

from .main import create_app

__all__ = ["create_app"]
