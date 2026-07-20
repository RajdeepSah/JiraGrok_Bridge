"""Health and metadata endpoints (no credentials, no secrets)."""

from fastapi import APIRouter

from core.config import DEFAULT_GROQ_MODEL, load_config
from core.errors import ConfigError

from ..schemas import MetaResponse

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    """Non-secret info for the UI: the fixed Jira base URL and the model in use.

    Deliberately never returns GROQ_API_KEY. If the server is not configured yet,
    returns configured=false instead of erroring, so the UI can show a clear notice.
    """
    try:
        cfg = load_config()
        return MetaResponse(jira_base_url=cfg.jira_base_url, model=cfg.groq_model, configured=True)
    except ConfigError:
        return MetaResponse(jira_base_url="", model=DEFAULT_GROQ_MODEL, configured=False)
