"""Pydantic request/response models for the API.

Note what is NOT here: there is no field anywhere for the Groq API key, and the
per-user Jira email/token are never modeled here either - they arrive as request
headers (see deps.require_jira_credentials) so they can never be echoed back or
captured in a validation-error message.
"""

from pydantic import BaseModel, Field

# Jira issue keys look like FMDEV-5448: letters, then letters/digits, dash, digits.
# Enforced server-side so a crafted key cannot be interpolated into the Jira path.
ISSUE_KEY_PATTERN = r"^[A-Za-z][A-Za-z0-9]+-\d+$"
_IssueKey = Field(pattern=ISSUE_KEY_PATTERN, max_length=64)


class RunRequest(BaseModel):
    issue_key: str = _IssueKey
    instructions: str = Field(min_length=1, max_length=20000)
    template_id: str | None = Field(default=None, max_length=128)  # audit only; instructions wins


class RunResponse(BaseModel):
    issue_key: str
    summary: str
    description: str
    output: str
    truncated: bool
    model: str


class CommentRequest(BaseModel):
    issue_key: str = _IssueKey
    comment: str = Field(min_length=1, max_length=32000)


class CommentResponse(BaseModel):
    issue_key: str
    posted: bool
    comment_url: str | None = None


class ValidateRequest(BaseModel):
    issue_key: str | None = Field(default=None, pattern=ISSUE_KEY_PATTERN, max_length=64)


class ValidateResponse(BaseModel):
    valid: bool
    issue_exists: bool | None = None


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str


class TemplateDetail(TemplateSummary):
    instructions: str


class MetaResponse(BaseModel):
    jira_base_url: str  # public site origin, shown in the UI - NOT a secret
    model: str
    configured: bool
