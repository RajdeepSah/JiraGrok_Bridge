"""The main workflow endpoint: fetch a Jira issue and run it through Groq."""

from fastapi import APIRouter, Depends

from core.config import AppConfig
from core.groq_client import ask_groq, build_groq_client
from core.jira_client import get_issue

from ..deps import JiraCredentials, get_config, require_jira_credentials
from ..schemas import RunRequest, RunResponse

router = APIRouter(tags=["run"])


@router.post("/run", response_model=RunResponse)
def run(
    body: RunRequest,
    auth: JiraCredentials = Depends(require_jira_credentials),
    cfg: AppConfig = Depends(get_config),
) -> RunResponse:
    """Fetch the issue with the caller's Jira credentials, then send it to Groq
    using ``body.instructions`` (the chosen/edited template) as the system prompt.

    Upstream failures raise native requests/groq exceptions and are turned into
    clean JSON by the app-level handlers in backend.exceptions.
    """
    issue = get_issue(cfg.jira_base_url, auth, body.issue_key)

    client = build_groq_client(cfg.groq_api_key)
    result = ask_groq(
        client,
        body.instructions,
        body.issue_key,
        issue["summary"],
        issue["description"],
        model=cfg.groq_model,
        max_tokens=cfg.max_tokens,
    )

    return RunResponse(
        issue_key=body.issue_key,
        summary=issue["summary"],
        description=issue["description"],
        output=result.text,
        truncated=result.truncated,
        model=result.model,
    )
