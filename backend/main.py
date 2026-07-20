"""FastAPI application factory.

    uvicorn backend.main:create_app --factory --host 127.0.0.1 --port 8000

In production the built React SPA (frontend/dist) is served from this same app, so
the browser and API share one origin and no CORS is needed. For local development
with Vite on :5173, set JGB_DEV_CORS=1 to allow that origin.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import install_log_redaction, register_exception_handlers
from .routers import comment, meta, run, templates, validate

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


class SPAStaticFiles(StaticFiles):
    """Serve Vite assets while supporting client-side, extensionless routes.

    Starlette's ``html=True`` serves ``index.html`` for directory URLs, but it
    does not provide the history fallback that a React router needs. Only a
    missing, extensionless non-API path falls back here; missing files under
    Vite's assets directory (and other extension-bearing files) remain genuine
    404s instead of returning HTML to a script/style request.
    """

    @staticmethod
    def _is_client_route(path: str) -> bool:
        # StaticFiles normalizes URL paths with the host OS separator before
        # calling get_response(), so convert Windows backslashes back to URL form.
        normalized = path.replace("\\", "/").strip("/")
        if not normalized:
            return False  # StaticFiles already serves the root index normally.

        first_segment = normalized.split("/", 1)[0]
        leaf = normalized.rsplit("/", 1)[-1]
        return first_segment not in {"api", "assets"} and "." not in leaf

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or not self._is_client_route(path):
                raise
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    install_log_redaction()

    app = FastAPI(
        title="Jira Grok Bridge",
        description="Send a Jira ticket to Groq with chosen instructions, and post the result back.",
        version="1.0.0",
    )

    register_exception_handlers(app)

    # Dev-only, opt-in CORS for the Vite dev server. Credentials travel in headers,
    # not cookies, so allow_credentials stays False. Never a wildcard.
    if os.environ.get("JGB_DEV_CORS", "").strip().lower() in ("1", "true", "yes"):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=DEV_ORIGINS,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Jira-Email", "X-Jira-Token"],
        )

    # API routes first, so the SPA static mount below never shadows them.
    for module in (meta, templates, run, comment, validate):
        app.include_router(module.router, prefix="/api")

    # Serve the built SPA (index.html + assets) at the root, if it has been built.
    if FRONTEND_DIST.is_dir():
        app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

    return app
