"""Post a comment back to Jira (the web equivalent of the CLI's --comment)."""

from urllib.parse import quote

from fastapi import APIRouter, Depends

from core.config import AppConfig
from core.jira_client import post_comment

from ..deps import JiraCredentials, get_config, require_jira_credentials
from ..schemas import CommentRequest, CommentResponse

router = APIRouter(tags=["comment"])


@router.post("/comment", response_model=CommentResponse)
def comment(
    body: CommentRequest,
    auth: JiraCredentials = Depends(require_jira_credentials),
    cfg: AppConfig = Depends(get_config),
) -> CommentResponse:
    """Post ``body.comment`` as a comment on the issue, attributed to the caller."""
    result = post_comment(cfg.jira_base_url, auth, body.issue_key, body.comment)

    comment_url = None
    comment_id = result.get("id")
    if comment_id:
        comment_url = (
            f"{cfg.jira_base_url}/browse/{quote(body.issue_key, safe='')}"
            f"?focusedCommentId={quote(str(comment_id), safe='')}"
        )

    return CommentResponse(issue_key=body.issue_key, posted=True, comment_url=comment_url)
