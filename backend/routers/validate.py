"""Optional pre-flight check: are the caller's Jira credentials valid, and (if a
key is given) does the issue exist? Lets the UI validate before a full run."""

import requests
from fastapi import APIRouter, Depends

from core.config import AppConfig
from core.jira_client import get_issue, verify_credentials

from ..deps import JiraCredentials, get_config, require_jira_credentials
from ..schemas import ValidateRequest, ValidateResponse

router = APIRouter(tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
def validate(
    body: ValidateRequest,
    auth: JiraCredentials = Depends(require_jira_credentials),
    cfg: AppConfig = Depends(get_config),
) -> ValidateResponse:
    # Raises HTTPError 401/403 (-> handled as JIRA_AUTH) if the credentials are bad.
    verify_credentials(cfg.jira_base_url, auth)

    issue_exists: bool | None = None
    if body.issue_key:
        try:
            get_issue(cfg.jira_base_url, auth, body.issue_key)
            issue_exists = True
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                issue_exists = False
            else:
                raise

    return ValidateResponse(valid=True, issue_exists=issue_exists)
